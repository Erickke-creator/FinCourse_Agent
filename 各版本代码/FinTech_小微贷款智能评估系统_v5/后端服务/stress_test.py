"""
v5 现金流压力测试模块
模拟三种压力场景：营收下降 / 成本上升 / 付款延迟
"""

import math
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StressScenario:
    name: str
    description: str
    revenue_change: float       # 营收变化率（-0.3 = 下降30%）
    cost_change: float          # 成本变化率（0.2 = 上升20%）
    payment_delay_months: int   # 客户付款延迟月数


@dataclass
class StressResult:
    scenario: str
    description: str
    original_monthly_cashflow: float
    stressed_monthly_cashflow: float
    original_dti: float
    stressed_dti: float
    original_repayment_ratio: float
    stressed_repayment_ratio: float
    can_survive: bool           # 是否撑得住
    risk_level: str             # low / medium / high / critical
    recommendation: str


# 预设压力场景
SCENARIOS = [
    StressScenario(
        name="轻微压力",
        description="营收下降10%，成本不变，回款正常",
        revenue_change=-0.10, cost_change=0.0, payment_delay_months=0,
    ),
    StressScenario(
        name="中度压力",
        description="营收下降25%，原材料成本上升15%，回款延迟1个月",
        revenue_change=-0.25, cost_change=0.15, payment_delay_months=1,
    ),
    StressScenario(
        name="严重压力",
        description="营收腰斩50%，各项成本上升25%，回款延迟3个月",
        revenue_change=-0.50, cost_change=0.25, payment_delay_months=3,
    ),
    StressScenario(
        name="极端压力",
        description="营收暴跌70%，成本暴涨40%，回款延迟6个月（类似疫情封控）",
        revenue_change=-0.70, cost_change=0.40, payment_delay_months=6,
    ),
]


def run_stress_test(
    monthly_revenue: float,
    monthly_fixed_cost: float,
    existing_liabilities: float,
    monthly_repayment: float,
    cash_reserve: float = 0.0,
) -> list[StressResult]:
    """
    执行全面压力测试，返回各场景分析结果。
    """
    original_cashflow = monthly_revenue - monthly_fixed_cost - existing_liabilities
    original_dti = (existing_liabilities / monthly_revenue * 100) if monthly_revenue > 0 else 200
    original_repay_ratio = (monthly_repayment / original_cashflow * 100) if original_cashflow > 0 else 200

    results = []

    for scenario in SCENARIOS:
        stressed_revenue = monthly_revenue * (1 + scenario.revenue_change)
        stressed_cost = monthly_fixed_cost * (1 + scenario.cost_change)

        # 回款延迟影响：当月实际收款减少
        effective_revenue = stressed_revenue * max(0.3, 1 - 0.15 * scenario.payment_delay_months)

        stressed_cashflow = effective_revenue - stressed_cost - existing_liabilities
        stressed_dti = (existing_liabilities / stressed_revenue * 100) if stressed_revenue > 0 else 200
        stressed_repay_ratio = (monthly_repayment / stressed_cashflow * 100) if stressed_cashflow > 0 else 200

        # 可动用现金储备覆盖月数
        reserve_months = cash_reserve / max(abs(stressed_cashflow), 1) if cash_reserve > 0 else 0

        # 判断风险等级
        if stressed_cashflow > 0 and stressed_repay_ratio < 40 and reserve_months > 3:
            risk_level = "low"
            can_survive = True
        elif stressed_cashflow > 0 and stressed_repay_ratio < 60:
            risk_level = "medium"
            can_survive = True
        elif stressed_cashflow > 0 or reserve_months > 6:
            risk_level = "high"
            can_survive = True
        else:
            risk_level = "critical"
            can_survive = False

        # 生成建议
        if can_survive and risk_level == "low":
            rec = "当前经营弹性充足，即使在此压力场景下仍可正常还贷。"
        elif can_survive and risk_level == "medium":
            rec = "建议：① 建立3-6个月经营现金储备；② 与银行协商备用授信额度；③ 优化应收账款周期。"
        elif can_survive and risk_level == "high":
            rec = "建议：① 立即减少非必要支出；② 寻求政府纾困贴息支持；③ 与贷款行协商展期或调整还款计划；④ 考虑追加抵质押物以降低利率。"
        else:
            rec = "⚠️ 极端压力下企业将面临严重流动性危机。建议：① 立即启动应急预案；② 申请贷款展期/重组；③ 寻求股东增资或引入战略投资者；④ 关注当地中小企业纾困政策。"

        results.append(StressResult(
            scenario=scenario.name,
            description=scenario.description,
            original_monthly_cashflow=round(original_cashflow, 0),
            stressed_monthly_cashflow=round(stressed_cashflow, 0),
            original_dti=round(original_dti, 1),
            stressed_dti=round(stressed_dti, 1),
            original_repayment_ratio=round(original_repay_ratio, 1),
            stressed_repayment_ratio=round(stressed_repay_ratio, 1),
            can_survive=can_survive,
            risk_level=risk_level,
            recommendation=rec,
        ))

    return results


def stress_test_summary(results: list[StressResult]) -> dict:
    """生成压力测试摘要，用于 Agent 回复"""
    passed = sum(1 for r in results if r.can_survive)
    worst = max(results, key=lambda r: r.stressed_repayment_ratio)

    levels = [r.risk_level for r in results]
    return {
        "scenarios_tested": len(results),
        "scenarios_passed": passed,
        "worst_case": worst.scenario,
        "worst_repayment_ratio": worst.stressed_repayment_ratio,
        "overall_verdict": "强韧" if passed == 4 else ("稳健" if passed >= 3 else ("承压" if passed >= 2 else "脆弱")),
        "key_risk": worst.recommendation,
    }
