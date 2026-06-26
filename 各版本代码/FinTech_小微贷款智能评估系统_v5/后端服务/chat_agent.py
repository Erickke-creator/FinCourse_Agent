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
- 给出建议时引用具体政策名称或案例编号作为依据
- 使用专业但通俗的语言，金融术语附带简短解释
- 回复简洁有条理，关键信息用 Emoji 或分段标注
- 用户没有提供完整企业信息时，主动引导补充（行业、金额、经营年限、纳税等级）

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

# 合并所有 Tools
ALL_TOOLS = KB_TOOLS_SCHEMA + [EVALUATION_TOOL_SCHEMA, ENTERPRISE_SEARCH_SCHEMA]


async def _evaluate_loan_tool(**kwargs) -> dict:
    """执行贷款评估（桥接到 bank_engine）"""
    from bank_engine import evaluate_loan
    from models import LoanInput
    try:
        inp = LoanInput(
            amount=kwargs.get("amount", 50),
            term_years=kwargs.get("term_years", 1),
            industry=kwargs.get("industry", "其他"),
            business_years=kwargs.get("business_years", 3),
            annual_revenue=kwargs.get("annual_revenue", 100),
            tax_level=kwargs.get("tax_level", "M"),
            has_collateral=kwargs.get("has_collateral", False),
            credit_overdues=kwargs.get("credit_overdues", 0),
        )
        result = evaluate_loan(inp)
        return {
            "success": True,
            "score": result.score,
            "risk_level": result.risk_level,
            "health_score": result.health_score,
            "suggested_amount": result.suggested_amount,
            "suggested_rate": result.suggested_rate,
            "top_bank": result.top_bank,
            "top_matches": [
                {"name": m.bank_name, "probability": m.approval_probability,
                 "estimated_rate": m.estimated_rate, "reasons": m.match_reasons[:3]}
                for m in (result.bank_matches or [])[:5]
            ],
            "strengths": result.strengths,
            "risks": result.risks,
            "materials": result.materials[:5] if result.materials else [],
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


# 完整的 Tool Map
TOOL_MAP = {
    **KB_TOOL_MAP,
    "evaluate_loan": lambda **kw: _evaluate_loan_tool(**kw),
    "search_enterprise": lambda name="", **kw: _search_enterprise_tool(name),
}


# ============================================================
# Session 管理
# ============================================================
@dataclass
class ChatSession:
    session_id: str
    history: list = field(default_factory=list)         # [{role, content}]
    enterprise_profile: dict = field(default_factory=dict)  # 提取的企业信息
    created_at: str = ""

_active_sessions: dict[str, ChatSession] = {}


def get_or_create_session(session_id: str) -> ChatSession:
    if session_id not in _active_sessions:
        _active_sessions[session_id] = ChatSession(session_id=session_id)
    if len(_active_sessions) > 100:
        oldest = min(_active_sessions.keys(), key=lambda k: _active_sessions[k].created_at)
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
                        else:
                            result = tool_func(**func_args)
                    except Exception as e:
                        result = {"success": False, "error": str(e)}
                else:
                    result = {"success": False, "error": f"未知工具: {func_name}"}

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
