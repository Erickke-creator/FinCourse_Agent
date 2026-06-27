"""
v5 智能对话 Agent — 基于 DeepSeek V4 + Function Call 的 LLM 驱动小微贷款顾问

核心变化 (v4→v5):
  - 关键词匹配路由 → LLM Function Call Agent 循环
  - agent_kb/ 直接读文件 → kb_bridge 统一查询接口
  - 硬编码回复模板 → LLM 动态生成 + 工具获取实时数据
"""

import json
import os
import httpx
import re
import inspect
import time
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载 kb_bridge 工具（知识库查询）
from kb_bridge import (
    KB_TOOLS_SCHEMA, KB_TOOL_MAP, get_kb_summary,
    search_policies, search_banks, search_cases, get_industry_rules,
    get_credit_tolerance, get_subsidy_policies, get_macro_stats,
    normalize_industry,
)

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com/v1/chat/completions"
MAX_TURNS = 6
TIMEOUT = 30


class AgentConfigurationError(RuntimeError):
    """Chat Agent 缺少必要服务配置。"""

# ============================================================
# System Prompt
# ============================================================
SYSTEM_PROMPT_TEMPLATE = """你是一个专业的小微企业贷款智能顾问 Agent，致力于帮助小微企业主了解贷款政策、评估贷款可行性、匹配合适的银行产品。

## 你的能力
1. **政策解读**：查询国家级和地方级普惠金融政策、贴息补贴规则
2. **银行匹配**：根据企业情况（行业、经营年限、纳税等级、征信等）推荐合适的银行产品
3. **风险评估**：分析贷款被拒风险因子，给出改进建议
4. **案例参考**：搜索相似行业/场景的教学案例，提供诊断链和改进方案
5. **准入检查**：查询行业准入等级、征信容忍度标准

## 知识库规模
{knowledge_summary}

## 重要规则
- **始终使用工具函数获取最新数据**，不凭空编造政策条款或银行产品参数
- 涉及具体金额、利率、年限时，必须从工具返回的数据中提取，不要猜测
- 如果工具返回空结果，如实告知用户"当前知识库中未找到相关信息"
- 给出建议时引用具体政策名称或案例编号作为依据
- 使用专业但通俗的语言，金融术语附带简短解释
- 回复简洁有条理，关键信息用 Emoji 或分段标注
- 用户没有提供完整企业信息时，主动引导补充（行业、金额、经营年限、纳税等级）

## 工具使用优先级
1. **semantic_search_kb**（首选）：向量语义搜索，覆盖全部政策/案例/银行/补贴
2. **search_policies / search_cases / search_banks**（精确查询）：需要特定结构化字段时使用
3. **evaluate_loan**：执行完整贷款评估
4. **run_stress_test**：现金流压力测试
5. **run_multi_agent_analysis**：多Agent综合评估

## 风险提示
- 所有分析仅供参考，实际贷款审批以银行终审为准
- 教学案例均为模拟数据，仅用于说明评估逻辑"""


def _build_system_prompt() -> str:
    kb_summary = get_kb_summary()
    return SYSTEM_PROMPT_TEMPLATE.format(knowledge_summary=kb_summary)


# ============================================================
# Additional Tools: evaluate_loan + search_enterprise
# ============================================================
EVALUATION_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "evaluate_loan",
        "description": "对企业进行完整贷款可行性评估：5维评分、银行匹配、材料清单、改进建议。需要提供企业基本信息。",
        "parameters": {
            "type": "object",
            "properties": {
                "requested_amount": {"type": "number", "description": "申请贷款金额（元）"},
                "loan_term": {"type": "integer", "description": "贷款期限（月）"},
                "industry": {"type": "string", "description": "所属行业，可传中文行业名或后端行业代码"},
                "operating_years": {"type": "number", "description": "企业经营年限"},
                "monthly_revenue": {"type": "number", "description": "月营业收入（元）"},
                "monthly_fixed_cost": {"type": "number", "description": "月固定成本（元）"},
                "existing_liabilities": {"type": "number", "description": "现有月负债或月还款（元）"},
                "merchant_type": {"type": "string", "description": "主体类型: individual/enterprise/freelancer"},
                "region": {"type": "string", "description": "所在地区，如广东省"},
                "tax_level": {"type": "string", "description": "纳税等级: A/B/M/C/D"},
                "has_business_license": {"type": "boolean", "description": "是否有营业执照"},
                "has_stable_bank_flow": {"type": "boolean", "description": "是否有稳定银行流水"},
                "has_collateral_or_guarantor": {"type": "boolean", "description": "是否有抵押物或担保人"},
                "has_overdue_record": {"type": "boolean", "description": "是否有历史逾期"},
                "overdue_count_2yr": {"type": "integer", "description": "近2年征信逾期次数"},
                "has_real_estate": {"type": "boolean", "description": "是否拥有房产"},
                "real_estate_value": {"type": "number", "description": "房产估值（万元）"},
                "is_ecommerce": {"type": "boolean", "description": "是否为电商经营"},
                "is_tech_enterprise": {"type": "boolean", "description": "是否为科技型或专精特新企业"},
            },
            "required": ["requested_amount", "industry", "operating_years", "monthly_revenue"]
        }
    }
}

ENTERPRISE_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_enterprise",
        "description": "在1100家教学企业画像库中模糊搜索企业名称，返回企业画像和预评估报告。",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "企业名称（支持模糊搜索）"}
            },
            "required": ["name"]
        }
    }
}

# v5 新增工具 Schemas
RAG_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "semantic_search_kb",
        "description": "语义搜索知识库（向量检索），支持自然语言查询政策、案例、银行、补贴。比关键词匹配更智能。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "自然语言查询，如'制造业有哪些贴息政策''逾期记录怎么修复'"},
                "doc_type": {"type": "string", "description": "文档类型过滤: policy/bank/case/industry/subsidy，留空搜全部"}
            },
            "required": ["query"]
        }
    }
}

STRESS_TEST_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_stress_test",
        "description": "对企业现金流进行4种压力场景测试（轻微/中度/严重/极端），评估还款韧性。",
        "parameters": {
            "type": "object",
            "properties": {
                "monthly_revenue": {"type": "number", "description": "月营收（元）"},
                "monthly_fixed_cost": {"type": "number", "description": "月固定成本（元）"},
                "monthly_repayment": {"type": "number", "description": "月还款额（元）"},
                "existing_liabilities": {"type": "number", "description": "现有月负债（元），默认0"},
                "cash_reserve": {"type": "number", "description": "现金储备（元），默认0"},
            },
            "required": ["monthly_revenue", "monthly_fixed_cost", "monthly_repayment"]
        }
    }
}

PDF_EXPORT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "export_pdf_report",
        "description": "将当前评估结果导出为正式 PDF 贷款可行性评估报告。",
        "parameters": {
            "type": "object",
            "properties": {
                "enterprise_name": {"type": "string", "description": "企业名称"}
            },
            "required": ["enterprise_name"]
        }
    }
}

STALENESS_CHECK_SCHEMA = {
    "type": "function",
    "function": {
        "name": "check_kb_staleness",
        "description": "检查知识库时效性：扫描所有政策和案例的最后验证日期，标记过期条目。",
        "parameters": {"type": "object", "properties": {}, "required": []}
    }
}

MULTI_AGENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "run_multi_agent_analysis",
        "description": "启动4个子Agent（征信/银行/政策/风险）并行分析，综合生成企业贷款评估报告。",
        "parameters": {
            "type": "object",
            "properties": {
                "enterprise_name": {"type": "string", "description": "企业名称"},
                "industry": {"type": "string", "description": "所属行业"},
                "requested_amount": {"type": "number", "description": "申请金额（元）"},
                "loan_term": {"type": "integer", "description": "贷款期限（月）"},
                "operating_years": {"type": "number", "description": "经营年限"},
                "monthly_revenue": {"type": "number", "description": "月营业收入（元）"},
                "tax_level": {"type": "string", "description": "纳税等级 A/B/M/C/D"},
            },
            "required": ["industry", "requested_amount", "operating_years", "monthly_revenue"]
        }
    }
}

# 合并所有 Tools
ALL_TOOLS = KB_TOOLS_SCHEMA + [
    EVALUATION_TOOL_SCHEMA, ENTERPRISE_SEARCH_SCHEMA,
    RAG_SEARCH_SCHEMA, STRESS_TEST_SCHEMA,
    STALENESS_CHECK_SCHEMA, MULTI_AGENT_SCHEMA,
]


def _first_present(data: dict, key: str, default=None):
    value = data.get(key)
    return default if value is None else value


def _build_loan_input(kwargs: dict):
    """
    使用后端 LoanInput 真实字段构造输入。

    旧字段仅作过渡兼容：amount 单位为万元、term_years 为年、
    annual_revenue 为万元/年。Agent Schema 已不再暴露这些旧字段。
    """
    from models import LoanInput

    requested_amount = kwargs.get("requested_amount")
    if requested_amount is None and kwargs.get("amount") is not None:
        requested_amount = float(kwargs["amount"]) * 10000
    requested_amount = float(requested_amount if requested_amount is not None else 500000)

    loan_term = kwargs.get("loan_term")
    if loan_term is None and kwargs.get("term_years") is not None:
        loan_term = int(float(kwargs["term_years"]) * 12)
    loan_term = int(loan_term if loan_term is not None else 12)

    monthly_revenue = kwargs.get("monthly_revenue")
    if monthly_revenue is None and kwargs.get("annual_revenue") is not None:
        monthly_revenue = float(kwargs["annual_revenue"]) * 10000 / 12
    monthly_revenue = float(monthly_revenue if monthly_revenue is not None else 30000)

    operating_years = kwargs.get("operating_years", kwargs.get("business_years", 3))
    overdue_count = int(kwargs.get("overdue_count_2yr", kwargs.get("credit_overdues", 0)) or 0)
    collateral = kwargs.get("has_collateral_or_guarantor", kwargs.get("has_collateral", False))
    industry_code, _ = normalize_industry(str(kwargs.get("industry", "other")))
    valid_industries = {item.value for item in __import__("models").IndustryType}
    if industry_code not in valid_industries:
        industry_code = "other"

    tax_level = str(kwargs.get("tax_level", "M")).upper()
    if tax_level not in {"A", "B", "M", "C", "D"}:
        tax_level = "M"

    merchant_type = str(kwargs.get("merchant_type", "enterprise")).lower()
    merchant_aliases = {"个体户": "individual", "个体工商户": "individual", "小微企业": "enterprise", "企业": "enterprise", "自由职业": "freelancer"}
    merchant_type = merchant_aliases.get(merchant_type, merchant_type)
    if merchant_type not in {"individual", "enterprise", "freelancer"}:
        merchant_type = "enterprise"

    return LoanInput(
        merchant_type=merchant_type,
        operating_years=float(operating_years),
        industry=industry_code,
        region=str(kwargs.get("region", "广东省")),
        monthly_revenue=monthly_revenue,
        monthly_fixed_cost=float(_first_present(kwargs, "monthly_fixed_cost", monthly_revenue * 0.5)),
        existing_liabilities=float(_first_present(kwargs, "existing_liabilities", 0)),
        requested_amount=requested_amount,
        loan_term=loan_term,
        annual_rate=float(_first_present(kwargs, "annual_rate", 6.0)),
        tax_level=tax_level,
        has_business_license=bool(_first_present(kwargs, "has_business_license", True)),
        has_stable_bank_flow=bool(_first_present(kwargs, "has_stable_bank_flow", False)),
        has_overdue_record=bool(_first_present(kwargs, "has_overdue_record", overdue_count > 0)),
        overdue_count_2yr=overdue_count,
        has_collateral_or_guarantor=bool(collateral),
        has_real_estate=bool(_first_present(kwargs, "has_real_estate", False)),
        real_estate_value=float(_first_present(kwargs, "real_estate_value", 0)),
        is_ecommerce=bool(_first_present(kwargs, "is_ecommerce", False)),
        is_tech_enterprise=bool(_first_present(kwargs, "is_tech_enterprise", False)),
    )


async def _evaluate_loan_tool(**kwargs) -> dict:
    """执行贷款评估（桥接到 bank_engine）"""
    from bank_engine import evaluate_loan
    try:
        inp = _build_loan_input(kwargs)
        result = evaluate_loan(inp)
        return {
            "success": True,
            "score": result.score,
            "risk_level": result.risk_level.value,
            "enterprise_health_score": result.enterprise_health_score,
            "suggested_amount": result.suggested_amount,
            "suggested_term": result.suggested_term,
            "monthly_repayment": result.monthly_repayment,
            "repayment_pressure_ratio": result.repayment_pressure_ratio,
            "strengths": result.strengths,
            "risks": result.risks,
            "improvement_tips": result.improvement_tips,
            "bank_matches": [m.model_dump(mode="json") for m in (result.bank_matches or [])[:5]],
            "recommended_materials": [m.model_dump(mode="json") for m in (result.recommended_materials or [])],
            "ml_enhanced": result.ml_enhanced,
            "ml_default_prob": result.ml_default_prob,
            "ml_credit_rating": result.ml_credit_rating,
            "ml_risk_level": result.ml_risk_level,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _search_enterprise_tool(name: str) -> dict:
    """企业搜索（桥接到 enterprise_search）"""
    try:
        from enterprise_search import analyze_enterprise
        report = analyze_enterprise(name)
        return report if report else {"found": False, "message": f"未找到'{name}'的相关企业"}
    except Exception as e:
        return {"found": False, "error": str(e)}


# v5 新工具实现
async def _semantic_search_tool(query: str, doc_type: str = "") -> dict:
    try:
        from kb_rag import semantic_search, is_available as rag_ok
        if not rag_ok():
            return {"success": False, "message": "RAG 引擎未初始化（chromadb 未安装）"}
        results = semantic_search(query, top_n=5, doc_type=doc_type)
        return {"success": True, "query": query, "results_count": len(results), "results": results}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _stress_test_tool(**kwargs) -> dict:
    try:
        from stress_test import run_stress_test, stress_test_summary
        results = run_stress_test(
            monthly_revenue=kwargs.get("monthly_revenue", 50000),
            monthly_fixed_cost=kwargs.get("monthly_fixed_cost", 30000),
            existing_liabilities=kwargs.get("existing_liabilities", 0),
            monthly_repayment=kwargs.get("monthly_repayment", 10000),
            cash_reserve=kwargs.get("cash_reserve", 0),
        )
        summary = stress_test_summary(results)
        return {
            "success": True,
            "summary": summary,
            "scenarios": [
                {"name": r.scenario, "can_survive": r.can_survive, "risk": r.risk_level,
                 "cashflow": r.stressed_monthly_cashflow, "repay_ratio": r.stressed_repayment_ratio}
                for r in results
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _pdf_export_tool(enterprise_name: str = "", eval_result: dict = None) -> dict:
    try:
        from report_pdf import generate_pdf_report, is_available as pdf_ok
        if not pdf_ok():
            return {"success": False, "error": "PDF 导出不可用：未找到中文字体（需要 PingFang/SimHei/Noto Sans CJK）"}

        # 优先使用传入的评估结果，否则生成默认报告
        if eval_result and eval_result.get("score"):
            result_data = eval_result
        else:
            from bank_engine import evaluate_loan
            from models import LoanInput
            inp = LoanInput(requested_amount=500000, loan_term=12, industry="other")
            result_data = evaluate_loan(inp).model_dump()

        path = generate_pdf_report(result_data, {"name": enterprise_name})
        return {
            "success": True,
            "file_path": path,
            "download_url": f"/api/report/pdf-download",
            "enterprise_name": enterprise_name,
            "message": f"报告已生成，点击下方按钮保存",
            "__action": "download_pdf",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _staleness_check_tool() -> dict:
    try:
        from kb_staleness import get_staleness_summary, check_all
        report = check_all()
        return {"success": True, "summary": get_staleness_summary(), "health_score": report["health_score"]}
    except Exception as e:
        return {"success": False, "error": str(e)}

async def _multi_agent_tool(**kwargs) -> dict:
    try:
        from multi_agent import run_multi_agent_local
        from bank_engine import evaluate_loan
        inp = _build_loan_input(kwargs)
        result = evaluate_loan(inp)
        info = {
            "name": kwargs.get("enterprise_name", ""),
            "industry": kwargs.get("industry", ""),
            "amount": inp.requested_amount / 10000,
            "annual_revenue": inp.monthly_revenue * 12 / 10000,
        }
        return run_multi_agent_local(result.model_dump(), info)
    except Exception as e:
        return {"success": False, "error": str(e)}

# 完整的 Tool Map
TOOL_MAP = {
    **KB_TOOL_MAP,
    "evaluate_loan": _evaluate_loan_tool,
    "search_enterprise": _search_enterprise_tool,
    "semantic_search_kb": _semantic_search_tool,
    "run_stress_test": _stress_test_tool,
    "check_kb_staleness": _staleness_check_tool,
    "run_multi_agent_analysis": _multi_agent_tool,
}


async def _execute_tool(func_name: str, func_args: dict) -> dict | list:
    """统一执行同步和异步 Agent 工具，确保协程不会被序列化成字符串。"""
    tool_func = TOOL_MAP.get(func_name)
    if not tool_func:
        return {"success": False, "error": f"未知工具: {func_name}"}
    try:
        result = tool_func(**func_args)
        if inspect.isawaitable(result):
            result = await result
        return result
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


# ============================================================
# Session 管理
# ============================================================
@dataclass
class ChatSession:
    session_id: str
    history: list = field(default_factory=list)
    enterprise_profile: dict = field(default_factory=dict)
    download_url: str = ""
    download_label: str = ""
    last_evaluation: dict = field(default_factory=dict)  # v5: store last eval result
    created_at: float = field(default_factory=time.time)

_active_sessions: dict[str, ChatSession] = {}


def get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _active_sessions:
        session = ChatSession(session_id=session_id)
        # v5: 从 SQLite 恢复历史
        try:
            from chat_history import load_session
            saved = load_session(session_id)
            if saved["history"]:
                session.history = saved["history"]
            if saved["profile"]:
                session.enterprise_profile = saved["profile"]
        except Exception:
            pass
        _active_sessions[session_id] = session
    if len(_active_sessions) > 100:
        oldest = min(_active_sessions.keys(), key=lambda k: _active_sessions[k].created_at)
        # v5: 淘汰前持久化
        try:
            from chat_history import save_session
            s = _active_sessions[oldest]
            save_session(s.session_id, s.history, s.enterprise_profile)
        except Exception:
            pass
        del _active_sessions[oldest]
    return _active_sessions[session_id]


# ============================================================
# Agent 循环
# ============================================================
def is_llm_available() -> bool:
    return bool(DEEPSEEK_API_KEY and DEEPSEEK_API_KEY.startswith("sk-"))


async def run_agent(user_message: str, session_id: str = "default") -> str:
    """
    LLM Agent 主循环：
    user_message → DeepSeek V4 → [tool_calls → execute → observe] × N → 最终回复
    """
    if not is_llm_available():
        raise AgentConfigurationError(
            "Chat Agent 未配置 DEEPSEEK_API_KEY，已禁用无 Key 的伪智能降级回答。"
        )

    session = get_or_create_session(session_id)
    system_prompt = _build_system_prompt()

    # 如果有企业档案，注入上下文
    if session.enterprise_profile:
        profile_text = json.dumps(session.enterprise_profile, ensure_ascii=False)
        system_prompt += f"\n\n## 当前企业档案\n{profile_text}"

    messages = [
        {"role": "system", "content": system_prompt},
        *session.history[-20:],  # 最近 10 轮
        {"role": "user", "content": user_message}
    ]

    for turn in range(MAX_TURNS):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(
                    DEEPSEEK_BASE,
                    headers={
                        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": messages,
                        "tools": ALL_TOOLS,
                        "temperature": 0.3,
                        "max_tokens": 1500,
                    }
                )
                resp.raise_for_status()
                result = resp.json()
        except httpx.TimeoutException:
            return "很抱歉，AI 服务响应超时，请稍后重试。"
        except Exception as e:
            return f"AI 服务暂时不可用，请稍后重试。您仍可使用「企业评估」页面进行贷款可行性分析。"

        choice = result["choices"][0]
        msg = choice["message"]
        finish_reason = choice.get("finish_reason")

        # LLM 直接回复（无需工具）
        if finish_reason == "stop" and msg.get("content"):
            final = msg["content"]

            # 保存到历史
            session.history.append({"role": "user", "content": user_message})
            session.history.append({"role": "assistant", "content": final})

            # 尝试提取企业信息
            _extract_profile(session, user_message, final)

            # v5: SQLite 持久化
            try:
                from chat_history import save_session
                save_session(session.session_id, session.history, session.enterprise_profile)
            except Exception:
                pass

            return final

        # LLM 需要调工具
        tool_calls = msg.get("tool_calls", [])
        if tool_calls:
            messages.append({
                "role": "assistant",
                "content": msg.get("content") or "",
                "tool_calls": tool_calls
            })

            for tc in tool_calls:
                func_name = tc["function"]["name"]
                try:
                    func_args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError as exc:
                    result = {"success": False, "error": f"工具参数不是有效 JSON: {exc}"}
                else:
                    result = await _execute_tool(func_name, func_args)
                    if func_name == "evaluate_loan" and isinstance(result, dict) and result.get("success"):
                        session.last_evaluation = result
                        try:
                            from chat_history import save_evaluation
                            save_evaluation(
                                session.session_id,
                                result.get("score", 0),
                                result.get("risk_level", ""),
                                func_args.get("industry", "unknown"),
                                result,
                            )
                        except Exception:
                            pass

                # v5: 检测下载动作
                if isinstance(result, dict) and result.get("__action") == "download_pdf":
                    session.download_url = result.get("download_url")
                    session.download_label = result.get("enterprise_name", "下载报告")
                    # 不让 LLM 看到 __action 内部字段
                    result = {"success": True, "message": result.get("message", "")}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str)
                })
            continue

        if msg.get("content"):
            return msg["content"]

    return "分析过程中需要的信息较多，请尝试更具体地描述您的问题。"


def _extract_profile(session: ChatSession, user_msg: str, ai_reply: str):
    """从对话中提取企业关键信息，累积到 session profile"""
    patterns = {
        "amount": r'(\d+[\d.]*)\s*万',
        "years": r'(\d+[\d.]*)\s*年',
        "industry": r'(制造业|批发|零售|餐饮|建筑|IT|科技|农业|物流|电商|外贸)',
        "tax_level": r'纳税等级[：:]\s*([A-E])',
    }
    for key, pattern in patterns.items():
        match = re.search(pattern, user_msg + ai_reply)
        if match and key not in session.enterprise_profile:
            session.enterprise_profile[key] = match.group(1)
