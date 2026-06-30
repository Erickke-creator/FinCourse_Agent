"""
v5 多 Agent 协作评估模块 (Bonus)
4 个子 Agent 并行评估 → Orchestrator 综合 → 生成最终报告

Agent 分工:
  1. Credit Assessor   — 征信评估 + 违约概率
  2. Bank Matcher      — 银行产品匹配
  3. Policy Advisor    — 政策/补贴匹配
  4. Risk Analyzer     — 风险因子分析 + 压力测试
"""

import asyncio
import json
import os
import httpx
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = "https://api.deepseek.com/v1/chat/completions"


@dataclass
class AgentReport:
    agent_name: str
    role: str
    findings: str
    score: float          # 0-10 置信度
    recommendation: str
    data: dict = field(default_factory=dict)


# ============================================================
# 子 Agent 定义
# ============================================================
SUB_AGENTS = {
    "credit_assessor": {
        "name": "征信评估师",
        "role": "分析企业征信记录、纳税等级、经营年限，评估信用风险",
        "focus": ["征信逾期次数", "纳税等级", "经营年限", "营业执照", "ML违约概率"],
    },
    "bank_matcher": {
        "name": "银行匹配师",
        "role": "根据企业画像匹配最佳银行产品，比较利率和审批概率",
        "focus": ["行业准入", "贷款金额", "抵押物", "银行偏好权重", "审批概率"],
    },
    "policy_advisor": {
        "name": "政策顾问",
        "role": "搜索适用的国家和地方补贴/贴息政策，计算可节省成本",
        "focus": ["国家级政策", "地方补贴", "贴息利率", "申请条件", "截止日期"],
    },
    "risk_analyzer": {
        "name": "风险分析师",
        "role": "现金流压力测试 + DTI分析 + 被拒因子权重分析",
        "focus": ["现金流覆盖", "DTI比率", "还款压力", "压力测试", "被拒因子"],
    },
}


def _build_sub_agent_prompt(agent_key: str, enterprise_profile: dict) -> str:
    """为每个子 Agent 构建专用 system prompt"""
    agent = SUB_AGENTS[agent_key]
    profile_text = json.dumps(enterprise_profile, ensure_ascii=False, indent=2)

    return f"""你是一个专业的{agent['role']}，负责小微贷款评估中的「{agent['name']}」环节。

## 当前企业档案
{profile_text}

## 你的任务
1. 根据你的专业领域（{' / '.join(agent['focus'])}），给出针对性分析
2. 给出一个 0-10 的置信度评分
3. 给出 1-2 条具体可行的建议

## 输出格式（严格 JSON）
{{
  "findings": "你的分析发现（100字以内）",
  "score": 8.5,
  "recommendation": "具体建议",
  "risk_flags": ["风险点1", "风险点2"]
}}

只返回 JSON，不要其他内容。"""


async def _call_sub_agent(agent_key: str, enterprise_profile: dict) -> Optional[AgentReport]:
    """调用 DeepSeek V4 执行子 Agent 分析"""
    if not DEEPSEEK_API_KEY or not DEEPSEEK_API_KEY.startswith("sk-"):
        return None

    agent = SUB_AGENTS[agent_key]
    prompt = _build_sub_agent_prompt(agent_key, enterprise_profile)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                DEEPSEEK_BASE,
                headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": f"请以{agent['name']}的身份，分析该企业的贷款可行性。"}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},
                }
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"]

            # 解析 JSON
            parsed = json.loads(raw)
            return AgentReport(
                agent_name=agent["name"],
                role=agent["role"],
                findings=parsed.get("findings", ""),
                score=float(parsed.get("score", 5)),
                recommendation=parsed.get("recommendation", ""),
                data={"risk_flags": parsed.get("risk_flags", [])},
            )
    except Exception as e:
        print(f"[MultiAgent] {agent_key} 失败: {e}")
        return None


async def run_multi_agent(enterprise_profile: dict) -> dict:
    """
    并行运行 4 个子 Agent，综合生成评估报告。
    """
    # 并行调用
    tasks = [
        _call_sub_agent(key, enterprise_profile)
        for key in SUB_AGENTS
    ]
    results = await asyncio.gather(*tasks)

    # 过滤失败的
    valid_results = [r for r in results if r is not None]

    if not valid_results:
        return {"success": False, "message": "多 Agent 评估失败（所有子 Agent 均未返回结果）"}

    # 综合得分
    avg_score = sum(r.score for r in valid_results) / len(valid_results)

    # 汇总风险标记
    all_flags = []
    for r in valid_results:
        all_flags.extend(r.data.get("risk_flags", []))

    # v5: 分歧检测与仲裁
    scores = [r.score for r in valid_results]
    score_range = max(scores) - min(scores) if len(scores) >= 2 else 0
    has_disagreement = score_range >= 2.5  # 置信度差距超过2.5分 = 分歧

    arbitration_note = ""
    if has_disagreement and len(valid_results) >= 2:
        # 找分歧最大的两个Agent
        sorted_agents = sorted(valid_results, key=lambda r: r.score)
        low = sorted_agents[0]
        high = sorted_agents[-1]
        # Orchestrator 仲裁: 看谁有更具体的证据
        low_detail = len(low.findings) if low.findings else 0
        high_detail = len(high.findings) if high.findings else 0
        # 证据更具体的一方胜出
        winner = high if high_detail >= low_detail else low
        arbitration_note = (
            f"⚠️ Agent 分歧: {low.agent_name}(置信度{low.score}) vs {high.agent_name}(置信度{high.score})，"
            f"差距{score_range:.1f}分。Orchestrator 采纳证据更充分的 {winner.agent_name} 的判断。"
        )

    # Orchestrator 综合报告
    overall = "多 Agent 协作评估完成。\n\n"
    for r in valid_results:
        agreement_mark = "✓" if abs(r.score - avg_score) <= 2 else "⚠"
        overall += f"{agreement_mark} 【{r.agent_name}】(置信度 {r.score}/10)\n{r.findings}\n→ {r.recommendation}\n\n"
    if arbitration_note:
        overall += f"\n{arbitration_note}"

    return {
        "success": True,
        "agents_deployed": len(valid_results),
        "agents_failed": 4 - len(valid_results),
        "average_confidence": round(avg_score, 1),
        "score_range": round(score_range, 1),
        "has_disagreement": has_disagreement,
        "arbitration": arbitration_note if arbitration_note else None,
        "overall_assessment": overall,
        "risk_flags": list(set(all_flags)),
        "verdict": "建议放款" if avg_score >= 7 else ("谨慎放款" if avg_score >= 5 else "建议拒贷或大幅调整条件"),
        "agents": [
            {"name": r.agent_name, "score": r.score, "recommendation": r.recommendation, "agrees": abs(r.score - avg_score) <= 2}
            for r in valid_results
        ],
    }


def run_multi_agent_sync(enterprise_profile: dict) -> dict:
    """同步包装器：优先 LLM 真并行，降级本地规则"""
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY.startswith("sk-"):
        try:
            return asyncio.run(run_multi_agent(enterprise_profile))
        except Exception as e:
            print(f"[MultiAgent] LLM mode failed, falling back to local: {e}")
    from bank_engine import evaluate_loan
    from models import LoanInput
    inp = LoanInput(requested_amount=enterprise_profile.get("amount", 50) * 10000,
                    loan_term=12, industry=enterprise_profile.get("industry", "other"))
    result = evaluate_loan(inp)
    return run_multi_agent_local(result.model_dump(), enterprise_profile)


# ============================================================
# 降级：无 API Key 时用本地评估替代
# ============================================================
def run_multi_agent_local(evaluation_result: dict, enterprise_info: dict) -> dict:
    """
    本地版多 Agent 评估（不依赖 LLM API）。
    基于 bank_engine + kb_bridge + stress_test 的规则引擎综合。
    """
    from kb_bridge import search_policies, search_banks, search_cases, get_rejection_factors
    from stress_test import run_stress_test, stress_test_summary

    score = evaluation_result.get("score", 0)
    risk = evaluation_result.get("risk_level", "unknown")
    breakdown = evaluation_result.get("breakdown", {})

    # 1. 征信评估
    op = breakdown.get("operating_strength", 0)
    cc = breakdown.get("credit_compliance", 0)
    credit_score = min(10, (op + cc) / 4)
    credit_findings = f"经营实力 {op}/20, 征信合规 {cc}/20"
    credit_rec = "征信良好" if cc >= 18 else "建议改善征信记录" if cc < 10 else "征信一般，可尝试中小银行"

    # 2. 银行匹配
    banks = evaluation_result.get("bank_matches", [])[:3]
    bank_score = min(10, len(banks) * 3)
    bank_findings = f"匹配到 {len(banks)} 家银行"
    bank_rec = f"首选: {banks[0].get('bank_name', 'N/A')}" if banks else "暂无合适银行"

    # 3. 政策匹配
    policies = search_policies(enterprise_info.get("industry", ""), top_n=3)
    policy_score = min(10, len(policies) * 3)
    policy_findings = f"找到 {len(policies)} 条相关政策"
    policy_rec = policies[0].get("document_title", "暂无匹配政策") if policies else "建议关注当地贴息政策"

    # 4. 风险分析
    stress_results = run_stress_test(
        monthly_revenue=enterprise_info.get("annual_revenue", 100) * 10000 / 12,
        monthly_fixed_cost=enterprise_info.get("annual_revenue", 100) * 0.6 * 10000 / 12,
        existing_liabilities=0,
        monthly_repayment=evaluation_result.get("monthly_repayment", 5000),
    )
    stress_summary = stress_test_summary(stress_results)
    risk_score = 10 if stress_summary["overall_verdict"] == "强韧" else (7 if stress_summary["overall_verdict"] == "稳健" else (4 if stress_summary["overall_verdict"] == "承压" else 2))
    risk_findings = f"压力测试: {stress_summary['scenarios_passed']}/{stress_summary['scenarios_tested']} 通过, 综合评价: {stress_summary['overall_verdict']}"
    risk_rec = stress_summary["key_risk"]

    agents = [
        {"name": "征信评估师", "score": credit_score, "recommendation": credit_rec},
        {"name": "银行匹配师", "score": bank_score, "recommendation": bank_rec},
        {"name": "政策顾问", "score": policy_score, "recommendation": policy_rec},
        {"name": "风险分析师", "score": risk_score, "recommendation": risk_rec},
    ]
    avg_score = sum(a["score"] for a in agents) / 4

    return {
        "success": True,
        "mode": "local",
        "agents_deployed": 4,
        "average_confidence": round(avg_score, 1),
        "overall_assessment": f"本地规则引擎综合评估。\n征信: {credit_findings}\n银行: {bank_findings}\n政策: {policy_findings}\n风险: {risk_findings}",
        "verdict": "建议放款" if avg_score >= 7 else ("谨慎放款" if avg_score >= 5 else "建议调整条件"),
        "agents": agents,
    }
