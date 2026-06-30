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
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载 kb_bridge 工具（知识库查询）
from kb_bridge import (
    KB_TOOLS_SCHEMA, KB_TOOL_MAP, get_kb_summary,
    search_policies, search_banks, search_cases, get_industry_rules,
    get_credit_tolerance, get_subsidy_policies, get_macro_stats
)

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com/v1/chat/completions"
MAX_TURNS = 6
TIMEOUT = 30

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
- **引用溯源（重要）**：给出建议时必须引用具体来源，格式：【来源：政策《xxx》/ 案例 CASE-xxx / 银行 xxx】
  例如："建议申请制造业贴息。【来源：政策《普惠金融高质量发展实施意见》(国发[2023]15号)】"
- 使用专业但通俗的语言，金融术语附带简短解释
- 回复简洁有条理，关键信息用 Emoji 或分段标注
- 用户没有提供完整企业信息时，主动引导补充（行业、金额、经营年限、纳税等级）

## 工具使用优先级（v5 深度优化）
1. **semantic_search_kb**（首选）：向量语义搜索，自动并行关键词搜索、合并去重
2. **evaluate_loan** → **counterfactual_analysis** → **what_if_analysis**：先评估→如需改进建议→再敏感性分析
3. **search_policies / search_cases / search_banks**（精确查询）：结构化字段查询
4. **run_stress_test**：现金流压力测试
5. **run_multi_agent_analysis**：多Agent综合评估（分歧时Orchestrator裁决）

## 工具链编排规则
- 用户提到具体金额/行业/年限 → 自动：evaluate_loan → search_policies → search_banks
- 用户问"怎么改进" → 自动：counterfactual_analysis → what_if_analysis
- 用户描述企业 → 自动：extract_enterprise_profile → evaluate_loan
- 多Agent评估出现分歧 → Orchestrator比较推理链 → 选证据最强的答案

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
                "amount": {"type": "number", "description": "申请贷款金额（万元）"},
                "term_years": {"type": "integer", "description": "贷款期限（年）"},
                "industry": {"type": "string", "description": "所属行业"},
                "business_years": {"type": "number", "description": "企业经营年限"},
                "annual_revenue": {"type": "number", "description": "年营业收入（万元）"},
                "tax_level": {"type": "string", "description": "纳税等级: A/B/M/C/D"},
                "has_collateral": {"type": "boolean", "description": "是否有抵押物"},
                "credit_overdues": {"type": "integer", "description": "近2年征信逾期次数"},
            },
            "required": ["amount", "industry"]
        }
    }
}

ENTERPRISE_SEARCH_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_enterprise",
        "description": "在1159家企业数据库中模糊搜索企业名称，返回企业画像和预评估报告。",
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

WHAT_IF_SCHEMA = {
    "type": "function",
    "function": {
        "name": "what_if_analysis",
        "description": "敏感性分析：给定参数变更（如增加抵押物、提升纳税等级），模拟评分变化。用户问'如果有担保人会怎样'时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "has_collateral_or_guarantor": {"type": "boolean", "description": "增加抵押/担保"},
                "tax_level": {"type": "string", "description": "纳税等级: A/B/M/C/D"},
                "has_stable_bank_flow": {"type": "boolean", "description": "稳定银行流水"},
                "has_business_license": {"type": "boolean", "description": "营业执照"},
            },
            "required": []
        }
    }
}

COUNTERFACTUAL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "counterfactual_analysis",
        "description": "反事实解释：分析'要做什么才能让评分从X升到Y'。返回具体可行的改进行动清单。",
        "parameters": {
            "type": "object",
            "properties": {
                "target_score": {"type": "number", "description": "目标评分，如 80"}
            },
            "required": ["target_score"]
        }
    }
}

ENTERPRISE_PROFILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "extract_enterprise_profile",
        "description": "从用户自然语言描述中提取企业关键信息，返回结构化数据供自动填表。当用户用口语描述自己的企业时调用此工具。",
        "parameters": {
            "type": "object",
            "properties": {
                "description": {"type": "string", "description": "用户对企业/生意的自然语言描述"}
            },
            "required": ["description"]
        }
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
                "amount": {"type": "number", "description": "申请金额（万元）"},
                "business_years": {"type": "number", "description": "经营年限"},
                "tax_level": {"type": "string", "description": "纳税等级 A/B/M/C/D"},
            },
            "required": ["industry", "amount"]
        }
    }
}

# 合并所有 Tools
ALL_TOOLS = KB_TOOLS_SCHEMA + [
    EVALUATION_TOOL_SCHEMA, ENTERPRISE_SEARCH_SCHEMA,
    RAG_SEARCH_SCHEMA, STRESS_TEST_SCHEMA, PDF_EXPORT_SCHEMA,
    STALENESS_CHECK_SCHEMA, MULTI_AGENT_SCHEMA, ENTERPRISE_PROFILE_SCHEMA,
    WHAT_IF_SCHEMA, COUNTERFACTUAL_SCHEMA,
]


async def _evaluate_loan_tool(**kwargs) -> dict:
    """执行贷款评估（桥接到 bank_engine）"""
    from bank_engine import evaluate_loan
    from models import LoanInput
    try:
        # Convert annual→monthly revenue, years→months term
        amount_wy = kwargs.get("amount", 50)          # 万元
        term_years = kwargs.get("term_years", 1)
        annual_rev = kwargs.get("annual_revenue", 100)  # 万元/年
        inp = LoanInput(
            requested_amount=amount_wy * 10000,         # 万元 → 元
            loan_term=term_years * 12,                   # 年 → 月
            industry=kwargs.get("industry", "other"),
            operating_years=kwargs.get("business_years", 3),
            monthly_revenue=(annual_rev * 10000) / 12,  # 万元/年 → 元/月
            tax_level=kwargs.get("tax_level", "M"),
            has_collateral_or_guarantor=kwargs.get("has_collateral", False),
            has_overdue_record=kwargs.get("credit_overdues", 0) > 0,
            overdue_count_2yr=kwargs.get("credit_overdues", 0),
        )
        result = evaluate_loan(inp)
        top_bank = result.bank_matches[0] if result.bank_matches else None
        return {
            "success": True,
            "score": result.score,
            "risk_level": str(result.risk_level),
            "health_score": result.enterprise_health_score,
            "suggested_amount": result.suggested_amount,
            "top_bank_name": top_bank.bank_name if top_bank else None,
            "top_bank_probability": top_bank.approval_probability if top_bank else None,
            "top_matches": [
                {"name": m.bank_name, "probability": m.approval_probability,
                 "estimated_rate": m.estimated_interest_rate, "reasons": m.recommendation_reasons[:3]}
                for m in (result.bank_matches or [])[:5]
            ],
            "strengths": result.strengths,
            "risks": result.risks,
            "materials": [{"name": m.name, "desc": m.description} for m in (result.recommended_materials or [])[:5]],
            "ml_default_prob": getattr(result, "ml_default_prob", None),
            "ml_credit_rating": getattr(result, "ml_credit_rating", None),
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
    """v5 混合RAG：语义+关键词并行搜索 → 合并去重 → 按相关度排序"""
    try:
        from kb_rag import semantic_search, is_available as rag_ok
        if not rag_ok():
            return {"success": False, "message": "RAG 引擎未初始化"}

        # 并行：语义搜索 + 关键词搜索
        semantic_results = semantic_search(query, top_n=5, doc_type=doc_type)

        # 关键词搜索（从 kb_bridge）
        keyword_results = []
        try:
            from kb_bridge import search_policies, search_cases, search_banks
            if not doc_type or doc_type == "policy":
                keyword_results.extend(search_policies(query, top_n=2))
            if not doc_type or doc_type == "case":
                keyword_results.extend(search_cases(industry=query, top_n=2))
        except Exception:
            pass

        # 合并去重（按id）
        seen = set()
        merged = []
        for r in semantic_results:
            rid = r.get("id", "")
            if rid not in seen:
                seen.add(rid)
                r["source"] = "semantic"
                merged.append(r)
        for r in keyword_results:
            rid = str(r.get("rule_id", r.get("case_id", r.get("id", ""))))
            if rid and rid not in seen:
                seen.add(rid)
                merged.append({"id": rid, "content": str(r)[:300], "source": "keyword", "metadata": r})

        return {"success": True, "query": query, "results_count": len(merged),
                "semantic_count": len(semantic_results), "keyword_count": len(keyword_results),
                "results": merged[:7],
                "method": "hybrid"}
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

# 企业画像提取（LLM解析 → 自动填表）
async def _extract_profile_tool(description: str) -> dict:
    if not description or len(description) < 5:
        return {"success": False, "error": "请提供更详细的企业描述（至少5个字）"}
    # 调用 LLM 解析
    try:
        import httpx, os
        key = os.getenv("DEEPSEEK_API_KEY", "")
        if not key:
            return {"success": False, "error": "AI 服务未配置"}
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat", "temperature": 0.1, "max_tokens": 400,
                    "messages": [{"role": "system", "content": """从用户描述中提取企业贷款评估所需信息，返回严格JSON：
{"merchant_type":"individual/enterprise/freelancer","industry":"餐饮业/制造业/批发零售/IT科技/农业/建筑/电商/物流/其他","operating_years":3,"monthly_revenue":80000,"monthly_fixed_cost":40000,"existing_liabilities":0,"requested_amount":200000,"loan_term":12,"tax_level":"A/B/M/C/D","has_business_license":true,"has_stable_bank_flow":true,"has_overdue_record":false,"has_collateral_or_guarantor":false,"region":"广东省","enterprise_name":"企业名"}
如果某字段不确定，用合理默认值。只返回JSON，不要其他文字。"""},
                    {"role": "user", "content": description}
                ]})
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]
            import json as _json
            profile = _json.loads(raw)
            profile["__action"] = "autofill_form"
            profile["success"] = True
            return profile
    except Exception as e:
        return {"success": False, "error": f"提取失败: {str(e)}"}

async def _multi_agent_tool(**kwargs) -> dict:
    try:
        from multi_agent import run_multi_agent_local
        from bank_engine import evaluate_loan
        from models import LoanInput
        amount_wy = kwargs.get("amount", 50)
        inp = LoanInput(
            requested_amount=amount_wy * 10000,
            loan_term=kwargs.get("term_years", 1) * 12,
            industry=kwargs.get("industry", "other"),
            operating_years=kwargs.get("business_years", 3),
            tax_level=kwargs.get("tax_level", "M"),
        )
        result = evaluate_loan(inp)
        info = {"name": kwargs.get("enterprise_name", ""), "industry": kwargs.get("industry", ""),
                "amount": kwargs.get("amount", 50), "annual_revenue": 100}
        return run_multi_agent_local(result.model_dump(), info)
    except Exception as e:
        return {"success": False, "error": str(e)}

# 完整的 Tool Map
TOOL_MAP = {
    **KB_TOOL_MAP,
    "evaluate_loan": lambda **kw: _evaluate_loan_tool(**kw),
    "search_enterprise": lambda name="", **kw: _search_enterprise_tool(name),
    "semantic_search_kb": lambda **kw: _semantic_search_tool(**kw),
    "run_stress_test": lambda **kw: _stress_test_tool(**kw),
    "export_pdf_report": lambda **kw: _pdf_export_tool(**kw),
    "check_kb_staleness": lambda **kw: _staleness_check_tool(),
    "run_multi_agent_analysis": lambda **kw: _multi_agent_tool(**kw),
    "extract_enterprise_profile": lambda **kw: _extract_profile_tool(**kw),
    "what_if_analysis": lambda **kw: _what_if_tool(**kw),
    "counterfactual_analysis": lambda **kw: _counterfactual_tool(**kw),
}

# ============================================================
# What-if + Counterfactual tools
# ============================================================
def _what_if_tool(**kwargs) -> dict:
    try:
        from what_if import what_if
        from models import LoanInput
        # Get current session's evaluation context
        inp = LoanInput(requested_amount=50000, loan_term=12, industry="other")
        return what_if(inp, {k: v for k, v in kwargs.items() if v is not None})
    except Exception as e:
        return {"success": False, "error": str(e)}

def _counterfactual_tool(target_score: float = 80) -> dict:
    try:
        from what_if import counterfactual
        from models import LoanInput
        inp = LoanInput(requested_amount=50000, loan_term=12, industry="other")
        return counterfactual(inp, target_score)
    except Exception as e:
        return {"success": False, "error": str(e)}


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
    last_evaluation: dict = field(default_factory=dict)
    autofill_data: dict = field(default_factory=dict)      # v5: 自动填表数据
    created_at: str = ""

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
        return _fallback_response(user_message)

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
                func_args = json.loads(tc["function"]["arguments"])

                tool_func = TOOL_MAP.get(func_name)
                if tool_func:
                    try:
                        if func_name == "search_enterprise":
                            result = await _search_enterprise_tool(**func_args)
                        elif func_name == "evaluate_loan":
                            result = await _evaluate_loan_tool(**func_args)
                            if isinstance(result, dict) and result.get("success"):
                                session.last_evaluation = result
                                # v5: 保存评分历史
                                try:
                                    from chat_history import save_evaluation
                                    save_evaluation(session.session_id, result.get("score", 0),
                                                    result.get("risk_level", ""),
                                                    func_args.get("industry", "unknown"),
                                                    result)
                                except Exception:
                                    pass
                        elif func_name == "export_pdf_report":
                            result = await _pdf_export_tool(
                                enterprise_name=func_args.get("enterprise_name", ""),
                                eval_result=session.last_evaluation
                            )
                        else:
                            result = tool_func(**func_args)
                    except Exception as e:
                        result = {"success": False, "error": str(e)}
                else:
                    result = {"success": False, "error": f"未知工具: {func_name}"}

                # v5: 检测下载动作
                if isinstance(result, dict) and result.get("__action") == "download_pdf":
                    session.download_url = result.get("download_url")
                    session.download_label = result.get("enterprise_name", "下载报告")
                    result = {"success": True, "message": result.get("message", "")}
                # v5: 检测自动填表动作
                if isinstance(result, dict) and result.get("__action") == "autofill_form":
                    session.autofill_data = {k: v for k, v in result.items()
                                             if k not in ("__action", "success") and v is not None}

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, ensure_ascii=False, default=str)
                })
            continue

        if msg.get("content"):
            return msg["content"]

    return "分析过程中需要的信息较多，请尝试更具体地描述您的问题。"


# ============================================================
# 降级模式（无 API Key）
# ============================================================
def _fallback_response(user_message: str) -> str:
    """无 LLM 时的降级：基于知识库搜索给出建议"""
    msg_lower = user_message.lower()

    # 尝试搜索知识库
    policies = search_policies(user_message, top_n=2)
    cases = search_cases(industry="", scenario="")

    lines = [
        "当前 AI 分析服务未启用（未配置 DeepSeek API Key）。",
        "",
    ]

    # 尝试企业搜索
    for word in user_message.split():
        if len(word) >= 2:
            try:
                from enterprise_search import analyze_enterprise
                report = analyze_enterprise(word)
                if report and report.get("found"):
                    lines.append(f"找到企业 `{word}` 的预评估报告。")
                    lines.append(f"评分: {report.get('score')}, 风险: {report.get('risk_level')}")
                    lines.append(f"推荐银行: {report.get('top_bank', '暂无')}")
                    break
            except:
                pass

    if policies:
        lines.append(f"相关政策: {policies[0].get('document_title', '')}")
    if cases:
        lines.append(f"相似案例: {cases[0].get('id', '')} - {cases[0].get('result', '')}")

    lines.append("")
    lines.append("启用 AI 分析：在 `.env` 中添加 `DEEPSEEK_API_KEY=sk-xxx`。")
    return "\n".join(lines)


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
