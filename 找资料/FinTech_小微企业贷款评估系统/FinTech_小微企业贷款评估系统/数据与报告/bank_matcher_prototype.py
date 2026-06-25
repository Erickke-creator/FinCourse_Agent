"""
小微企业贷款银行匹配系统——原型代码
FinTech期末作业
基于银行端数据的规则引擎 + ML就绪的特征结构
"""

import json
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


# ============================================================
# 1. 数据结构定义
# ============================================================

class TaxLevel(Enum):
    A = 5
    B = 4
    M = 3
    C = 2
    D = 1


@dataclass
class EnterpriseProfile:
    """小微企业画像"""
    # 基础信息
    business_name: str = ""
    business_age_years: float = 1.0
    registered_capital_wan: float = 50.0
    industry: str = "批发零售业"
    region: str = "广东省"
    employee_count: int = 5

    # 财务数据
    annual_revenue_wan: float = 100.0
    annual_profit_wan: float = 10.0
    cash_flow_wan: float = 15.0
    asset_liability_ratio: float = 0.4

    # 税务数据
    tax_level: TaxLevel = TaxLevel.M
    annual_tax_wan: float = 3.0
    invalid_invoice_ratio: float = 0.05

    # 信用数据
    has_default_history: bool = False
    overdue_count_2yr: int = 0
    credit_inquiry_3m: int = 2
    legal_disputes: int = 0

    # 资产数据
    has_real_estate: bool = False
    real_estate_value_wan: float = 0.0
    has_other_collateral: bool = False

    # 经营稳定性
    revenue_volatility: float = 0.3
    customer_count: int = 10
    customer_concentration: float = 0.3

    # 特殊标签
    is_ecommerce: bool = False
    is_tech_enterprise: bool = False


@dataclass
class BankMatchResult:
    """银行匹配结果"""
    bank_id: str
    bank_name: str
    bank_type: str
    product_name: str
    approval_probability: float  # 0-1
    estimated_interest_rate: float  # 预期利率
    estimated_max_amount: float  # 预期最高额度（万元）
    match_score: float  # 综合匹配度 0-100
    recommendation_reasons: List[str] = field(default_factory=list)
    risk_factors: List[str] = field(default_factory=list)


# ============================================================
# 2. 银行数据加载
# ============================================================

BANKS_DATA = [
    {
        "id": "icbc", "name": "工商银行", "type": "国有大型商业银行",
        "product_name": "经营快贷",
        "max_amount_credit": 300, "max_amount_mortgage": 500,
        "min_rate": 2.45, "max_rate": 3.00,
        "min_business_years": 1,
        "requires_collateral_strict": False,
        "tax_friendly": True,
        "collateral_weight": 0.30, "cashflow_weight": 0.25,
        "credit_weight": 0.25, "tax_weight": 0.20,
        "estimated_base_approval": 0.55
    },
    {
        "id": "ccb", "name": "建设银行", "type": "国有大型商业银行",
        "product_name": "惠懂你/抵押快贷/云税贷",
        "max_amount_credit": 500, "max_amount_mortgage": 1000,
        "min_rate": 2.40, "max_rate": 5.00,
        "min_business_years": 1,
        "requires_collateral_strict": False,
        "tax_friendly": True,
        "collateral_weight": 0.25, "cashflow_weight": 0.30,
        "credit_weight": 0.25, "tax_weight": 0.20,
        "estimated_base_approval": 0.62
    },
    {
        "id": "abc", "name": "农业银行", "type": "国有大型商业银行",
        "product_name": "普惠小微贷",
        "max_amount_credit": 300, "max_amount_mortgage": 300,
        "min_rate": 2.35, "max_rate": 2.55,
        "min_business_years": 1,
        "requires_collateral_strict": False,
        "tax_friendly": False,
        "collateral_weight": 0.30, "cashflow_weight": 0.35,
        "credit_weight": 0.20, "tax_weight": 0.15,
        "estimated_base_approval": 0.58
    },
    {
        "id": "boc", "name": "中国银行", "type": "国有大型商业银行",
        "product_name": "银税贷/经营贷",
        "max_amount_credit": 500, "max_amount_mortgage": 500,
        "min_rate": 3.05, "max_rate": 3.60,
        "min_business_years": 2,
        "requires_collateral_strict": False,
        "tax_friendly": True,
        "collateral_weight": 0.20, "cashflow_weight": 0.25,
        "credit_weight": 0.30, "tax_weight": 0.25,
        "estimated_base_approval": 0.50
    },
    {
        "id": "bocomm", "name": "交通银行", "type": "国有大型商业银行",
        "product_name": "个人经营性贷款",
        "max_amount_credit": 500, "max_amount_mortgage": 1000,
        "min_rate": 2.20, "max_rate": 3.00,
        "min_business_years": 2,
        "requires_collateral_strict": True,
        "tax_friendly": False,
        "collateral_weight": 0.40, "cashflow_weight": 0.25,
        "credit_weight": 0.20, "tax_weight": 0.15,
        "estimated_base_approval": 0.40
    },
    {
        "id": "psbc", "name": "邮储银行", "type": "国有大型商业银行",
        "product_name": "小微经营贷",
        "max_amount_credit": 200, "max_amount_mortgage": 200,
        "min_rate": 3.05, "max_rate": 4.00,
        "min_business_years": 0.5,
        "requires_collateral_strict": False,
        "tax_friendly": False,
        "collateral_weight": 0.10, "cashflow_weight": 0.40,
        "credit_weight": 0.30, "tax_weight": 0.20,
        "estimated_base_approval": 0.72
    },
    {
        "id": "cmb", "name": "招商银行", "type": "股份制商业银行",
        "product_name": "招捷贷/生意贷",
        "max_amount_credit": 50, "max_amount_mortgage": 3000,
        "min_rate": 2.35, "max_rate": 3.00,
        "min_business_years": 1,
        "requires_collateral_strict": True,
        "tax_friendly": False,
        "collateral_weight": 0.40, "cashflow_weight": 0.25,
        "credit_weight": 0.20, "tax_weight": 0.15,
        "estimated_base_approval": 0.55
    },
    {
        "id": "citic", "name": "中信银行", "type": "股份制商业银行",
        "product_name": "房抵e贷",
        "max_amount_credit": 500, "max_amount_mortgage": 3000,
        "min_rate": 2.15, "max_rate": 3.00,
        "min_business_years": 2,
        "requires_collateral_strict": True,
        "tax_friendly": False,
        "collateral_weight": 0.50, "cashflow_weight": 0.20,
        "credit_weight": 0.15, "tax_weight": 0.15,
        "estimated_base_approval": 0.38
    },
    {
        "id": "pingan", "name": "平安银行", "type": "股份制商业银行",
        "product_name": "橙e贷（经营版）",
        "max_amount_credit": 300, "max_amount_mortgage": 500,
        "min_rate": 3.00, "max_rate": 5.00,
        "min_business_years": 0.5,
        "requires_collateral_strict": False,
        "tax_friendly": False,
        "collateral_weight": 0.05, "cashflow_weight": 0.45,
        "credit_weight": 0.30, "tax_weight": 0.20,
        "estimated_base_approval": 0.70
    },
    {
        "id": "minsheng", "name": "民生银行", "type": "股份制商业银行",
        "product_name": "云抵贷",
        "max_amount_credit": 0, "max_amount_mortgage": 1000,
        "min_rate": 2.60, "max_rate": 4.00,
        "min_business_years": 1,
        "requires_collateral_strict": True,
        "tax_friendly": False,
        "collateral_weight": 0.45, "cashflow_weight": 0.25,
        "credit_weight": 0.15, "tax_weight": 0.15,
        "estimated_base_approval": 0.45
    },
    {
        "id": "cib", "name": "兴业银行", "type": "股份制商业银行",
        "product_name": "普惠小微贷",
        "max_amount_credit": 300, "max_amount_mortgage": 500,
        "min_rate": 3.07, "max_rate": 4.50,
        "min_business_years": 1,
        "requires_collateral_strict": False,
        "tax_friendly": False,
        "collateral_weight": 0.25, "cashflow_weight": 0.30,
        "credit_weight": 0.25, "tax_weight": 0.20,
        "estimated_base_approval": 0.60
    },
    {
        "id": "spdb", "name": "浦发银行", "type": "股份制商业银行",
        "product_name": "小微快贷/商户贷",
        "max_amount_credit": 120, "max_amount_mortgage": 120,
        "min_rate": 3.10, "max_rate": 3.25,
        "min_business_years": 0.5,
        "requires_collateral_strict": False,
        "tax_friendly": False,
        "collateral_weight": 0.10, "cashflow_weight": 0.40,
        "credit_weight": 0.30, "tax_weight": 0.20,
        "estimated_base_approval": 0.65
    },
    {
        "id": "cebb", "name": "光大银行", "type": "股份制商业银行",
        "product_name": "e担贷/e信贷",
        "max_amount_credit": 200, "max_amount_mortgage": 500,
        "min_rate": 3.19, "max_rate": 4.50,
        "min_business_years": 1,
        "requires_collateral_strict": False,
        "tax_friendly": False,
        "collateral_weight": 0.20, "cashflow_weight": 0.30,
        "credit_weight": 0.25, "tax_weight": 0.25,
        "estimated_base_approval": 0.58
    },
    {
        "id": "webank", "name": "微众银行", "type": "互联网银行",
        "product_name": "微业贷",
        "max_amount_credit": 1000, "max_amount_mortgage": 1000,
        "min_rate": 3.60, "max_rate": 18.00,
        "min_business_years": 1,
        "requires_collateral_strict": False,
        "tax_friendly": True,
        "collateral_weight": 0.00, "cashflow_weight": 0.15,
        "credit_weight": 0.35, "tax_weight": 0.30,
        "estimated_base_approval": 0.80
    },
    {
        "id": "mybank", "name": "网商银行", "type": "互联网银行",
        "product_name": "网商贷",
        "max_amount_credit": 500, "max_amount_mortgage": 500,
        "min_rate": 4.35, "max_rate": 20.00,
        "min_business_years": 0.5,
        "requires_collateral_strict": False,
        "tax_friendly": False,
        "collateral_weight": 0.00, "cashflow_weight": 0.30,
        "credit_weight": 0.25, "tax_weight": 0.15,
        "estimated_base_approval": 0.75
    },
]

# 行业分类——银行接受度
INDUSTRY_ACCEPTANCE = {
    "制造业": 1.0, "批发零售业": 1.0, "信息技术": 0.95,
    "住宿餐饮": 0.85, "交通运输": 0.90, "农业": 0.90,
    "建筑业": 0.75, "文化体育": 0.80, "科学研究": 0.95,
    "居民服务": 0.85, "教育": 0.85, "卫生": 0.85,
    "金融业": 0.50, "房地产业": 0.30, "娱乐业": 0.45,
    "采矿业": 0.55, "电力热力": 0.80,
}


# ============================================================
# 3. 核心评分函数
# ============================================================

def score_enterprise_health(profile: EnterpriseProfile) -> Tuple[float, Dict]:
    """
    评估企业综合健康度（0-100分）
    基于银行审批指标体系
    """
    scores = {}
    reasons = []
    risks = []

    # 3.1 经营能力评分（满分25）
    age_score = min(profile.business_age_years / 3.0, 1.0) * 10
    if profile.business_age_years < 1:
        risks.append("经营年限不足1年，多数国有大行无法准入")
        reasons.append(f"经营年限{profile.business_age_years}年, 得分较低")
    elif profile.business_age_years >= 3:
        reasons.append(f"经营{profile.business_age_years}年，经营年限优势明显")

    revenue_score = min(math.log10(max(profile.annual_revenue_wan, 1)) / 3, 1.0) * 10
    employee_score = min(profile.employee_count / 20, 1.0) * 5
    scores["经营能力"] = age_score + revenue_score + employee_score

    # 3.2 盈利能力评分（满分20）
    profit_margin = profile.annual_profit_wan / max(profile.annual_revenue_wan, 1)
    profit_score = min(max(profit_margin, 0) / 0.3, 1.0) * 12
    cashflow_score = min(max(profile.cash_flow_wan / max(profile.annual_revenue_wan, 1), 0) / 0.2, 1.0) * 8

    if profit_margin < 0.05:
        risks.append("利润率过低，还款能力存疑")
    if profile.cash_flow_wan <= 0:
        risks.append("经营现金流为负，几乎所有银行都会拒绝")

    scores["盈利能力"] = profit_score + cashflow_score

    # 3.3 信用状况评分（满分30——权重最高）
    credit_score = 30.0
    if profile.has_default_history:
        credit_score -= 15
        risks.append("有历史违约记录，通过率大幅降低")
    if profile.overdue_count_2yr > 0:
        deduction = min(profile.overdue_count_2yr * 3, 15)
        credit_score -= deduction
        risks.append(f"近2年逾期{profile.overdue_count_2yr}次")
    if profile.credit_inquiry_3m > 4:
        credit_score -= min((profile.credit_inquiry_3m - 4) * 2, 10)
        risks.append(f"近3月征信查询{profile.credit_inquiry_3m}次（偏多）")
    if profile.legal_disputes > 0:
        credit_score -= min(profile.legal_disputes * 3, 12)

    credit_score = max(credit_score, 0)
    scores["信用状况"] = credit_score

    # 3.4 税务规范性（满分15）
    tax_score = profile.tax_level.value * 2.0  # A=10, B=8, M=6, C=4, D=2
    if profile.tax_level.value >= 4:
        reasons.append(f"纳税等级{profile.tax_level.name}级，对申请银税贷产品有优势")
    if profile.invalid_invoice_ratio > 0.1:
        tax_score -= 5
        risks.append(f"废票率{profile.invalid_invoice_ratio:.1%}偏高，财务规范性存疑")
    tax_score += min(profile.annual_tax_wan / 10, 1.0) * 5
    scores["税务规范性"] = tax_score

    # 3.5 资产加分（满分10）
    asset_score = 0.0
    if profile.has_real_estate:
        asset_score += 6
        reasons.append("拥有房产，抵押类贷款产品选择空间大")
    if profile.has_other_collateral:
        asset_score += 2
    asset_score += min(profile.registered_capital_wan / 500, 1.0) * 2
    scores["资产实力"] = asset_score

    total = sum(scores.values())
    total = max(min(total, 100), 0)

    return total, {
        "breakdown": scores,
        "reasons": reasons,
        "risks": risks,
        "total_score": total
    }


def calculate_bank_approval_probability(
    profile: EnterpriseProfile,
    bank: dict,
    health_score: float
) -> float:
    """
    计算企业在特定银行的贷款审批通过概率
    基于银行偏好权重和企业特征匹配
    """
    base_prob = bank["estimated_base_approval"]

    # 经营年限检查
    if profile.business_age_years < bank["min_business_years"]:
        base_prob *= 0.5  # 不满足最低年限要求

    # 硬性抵押要求检查
    if bank["requires_collateral_strict"] and not profile.has_real_estate:
        base_prob *= 0.3  # 严格抵押要求但企业无房产

    # 征信影响
    if profile.has_default_history:
        base_prob *= 0.4
    if profile.overdue_count_2yr > 3:
        base_prob *= 0.7
    if profile.overdue_count_2yr > 6:
        base_prob *= 0.5

    # 银行偏好匹配度
    # 基于银行权重计算特征匹配分
    cashflow_ratio = profile.cash_flow_wan / max(profile.annual_revenue_wan, 1)
    cashflow_ok = 1.0 if cashflow_ratio > 0.1 else 0.5

    credit_ok = 1.0
    if profile.overdue_count_2yr > 0:
        credit_ok -= 0.15 * profile.overdue_count_2yr
    if profile.has_default_history:
        credit_ok -= 0.5
    credit_ok = max(credit_ok, 0.1)

    tax_ok = min(profile.tax_level.value / 5.0, 1.0)

    collateral_bonus = 1.0
    if profile.has_real_estate:
        collateral_bonus = 1.3

    # 银行偏好加权
    match_factor = (
        bank["collateral_weight"] * collateral_bonus +
        bank["cashflow_weight"] * cashflow_ok +
        bank["credit_weight"] * credit_ok +
        bank["tax_weight"] * tax_ok
    )

    # 互联网银行特殊加分
    if bank["type"] == "互联网银行":
        if profile.is_ecommerce:
            match_factor *= 1.2
        if profile.business_age_years < 1:
            match_factor *= 1.1  # 互联网银行对短年限容忍度高

    # 行业接受度
    industry_factor = INDUSTRY_ACCEPTANCE.get(profile.industry, 0.7)

    # 健康评分影响
    health_factor = 0.5 + (health_score / 200)  # 0.5-1.0

    prob = base_prob * match_factor * industry_factor * health_factor
    return max(min(prob, 0.98), 0.01)


def estimate_interest_rate(profile: EnterpriseProfile, bank: dict, prob: float) -> float:
    """估计企业在该银行的贷款利率"""
    base_rate = bank["min_rate"]
    max_rate = bank["max_rate"]

    # 信用越好，利率越接近下限
    credit_factor = 1.0
    if profile.has_default_history:
        credit_factor += 0.3
    credit_factor += profile.overdue_count_2yr * 0.05

    # 抵押降低利率
    if profile.has_real_estate:
        credit_factor -= 0.15

    # 审批概率越高，利率越低
    prob_factor = (1 - prob) * (max_rate - base_rate) * 0.5

    estimated = base_rate * credit_factor + prob_factor
    return max(min(estimated, max_rate), base_rate)


def estimate_max_amount(profile: EnterpriseProfile, bank: dict, prob: float) -> float:
    """估计企业能获得的最高贷款额度"""
    if profile.has_real_estate:
        base_limit = bank["max_amount_mortgage"]
    else:
        base_limit = bank["max_amount_credit"]

    # 基于年度营收的比例（一般不超过年营收的30-50%）
    revenue_limit = profile.annual_revenue_wan * 0.4

    # 基于房产价值的比例（抵押率一般60-70%）
    if profile.has_real_estate and profile.real_estate_value_wan > 0:
        collateral_limit = profile.real_estate_value_wan * 0.65
    else:
        collateral_limit = float("inf")

    # 基于净利润的倍数（一般不超过年净利润的3-5倍）
    if profile.annual_profit_wan > 0:
        profit_limit = profile.annual_profit_wan * 4
    else:
        profit_limit = 0

    raw_limit = min(base_limit, revenue_limit, collateral_limit, profit_limit if profit_limit > 0 else float("inf"))
    raw_limit = max(raw_limit, 10)  # 最低10万

    # 审批概率调整
    adjusted = raw_limit * (0.5 + prob * 0.5)

    return round(adjusted, 1)


# ============================================================
# 4. 银行匹配主函数
# ============================================================

def match_banks(profile: EnterpriseProfile) -> List[BankMatchResult]:
    """
    核心函数：将小微企业画像与所有银行匹配
    返回按通过概率排序的银行列表
    """
    # 第一步：计算企业健康度
    health_score, health_detail = score_enterprise_health(profile)

    print(f"\n{'='*60}")
    print(f"  企业: {profile.business_name or '(未命名)'}")
    print(f"  行业: {profile.industry}  |  经营年限: {profile.business_age_years}年")
    print(f"  年营收: {profile.annual_revenue_wan}万  |  年利润: {profile.annual_profit_wan}万")
    print(f"  纳税等级: {profile.tax_level.name}级  |  征信逾期: {profile.overdue_count_2yr}次")
    print(f"  {'有房产✓' if profile.has_real_estate else '无房产✗'}  |  "
          f"{'电商✓' if profile.is_ecommerce else ''}")
    print(f"  企业健康度评分: {health_score:.1f}/100")
    print(f"{'='*60}\n")

    if health_detail["risks"]:
        print("⚠️  风险提示:")
        for risk in health_detail["risks"]:
            print(f"    • {risk}")
        print()

    # 第二步：逐银行计算通过概率
    results = []
    for bank in BANKS_DATA:
        prob = calculate_bank_approval_probability(profile, bank, health_score)
        rate = estimate_interest_rate(profile, bank, prob)
        amount = estimate_max_amount(profile, bank, prob)

        # 生成推荐理由
        reasons = []
        if prob > 0.7:
            reasons.append(f"审批通过概率高（{prob:.0%}）")
        if rate <= bank["min_rate"] * 1.1:
            reasons.append(f"预期利率接近该行最低（{rate:.2f}%）")
        if amount >= 300:
            reasons.append(f"预期额度较高（{amount:.0f}万）")
        if bank["type"] == "互联网银行" and not profile.has_real_estate:
            reasons.append("纯信用无抵押，线上快速审批")
        if bank["id"] == "psbc":
            reasons.append("门槛最亲民，对初创企业包容度最高")
        if bank["id"] == "pingan" and not profile.has_real_estate:
            reasons.append("门槛最低的股份行，纯信用额度高")
        if bank["id"] in ["citic", "cmb"] and profile.has_real_estate:
            reasons.append(f"有优质抵押物，利率低至{rate:.2f}%")
        if profile.tax_level.value >= 4 and bank["tax_friendly"]:
            reasons.append(f"纳税等级{profile.tax_level.name}级，银税贷优势")

        risk_factors = []
        if prob < 0.4:
            risk_factors.append(f"该行通过率偏低（{prob:.0%}）")
        if bank["requires_collateral_strict"] and not profile.has_real_estate:
            risk_factors.append("该行严格要求抵押物")
        if profile.business_age_years < bank["min_business_years"]:
            risk_factors.append(f"经营年限不足该行要求的{bank['min_business_years']}年")

        match_score = prob * 60 + (1 - (rate - 2.0) / 4.0) * 30 + min(amount / 500, 1) * 10
        match_score = max(min(match_score, 100), 0)

        results.append(BankMatchResult(
            bank_id=bank["id"],
            bank_name=bank["name"],
            bank_type=bank["type"],
            product_name=bank["product_name"],
            approval_probability=round(prob, 4),
            estimated_interest_rate=round(rate, 2),
            estimated_max_amount=amount,
            match_score=round(match_score, 1),
            recommendation_reasons=reasons,
            risk_factors=risk_factors
        ))

    # 按通过概率排序
    results.sort(key=lambda x: x.approval_probability, reverse=True)
    return results


# ============================================================
# 5. 结果输出
# ============================================================

def print_results(results: List[BankMatchResult]):
    """格式化输出匹配结果"""
    print("🏦 银行匹配结果（按通过概率排序）:")
    print("-" * 80)

    for i, r in enumerate(results):
        prob_bar = "█" * int(r.approval_probability * 20) + "░" * (20 - int(r.approval_probability * 20))
        print(f"\n  [{i+1}] {r.bank_name} ({r.bank_type})")
        print(f"      产品: {r.product_name}")
        print(f"      通过概率: {r.approval_probability:.1%}  [{prob_bar}]")
        print(f"      预期利率: {r.estimated_interest_rate:.2f}%  |  预期额度: {r.estimated_max_amount:.0f}万")
        print(f"      综合匹配: {r.match_score:.0f}/100")

        if r.recommendation_reasons:
            print(f"      ✅ {', '.join(r.recommendation_reasons[:3])}")
        if r.risk_factors:
            print(f"      ⚠️  {', '.join(r.risk_factors[:2])}")

    # Top 3推荐摘要
    print(f"\n{'='*60}")
    print("🎯 TOP 3 推荐银行:")
    for i, r in enumerate(results[:3]):
        print(f"  {i+1}. {r.bank_name} — 通过概率{r.approval_probability:.1%}, "
              f"利率{r.estimated_interest_rate:.2f}%, 额度约{r.estimated_max_amount:.0f}万")
    print(f"{'='*60}\n")


# ============================================================
# 6. 测试案例
# ============================================================

def run_test_cases():
    """运行多种典型小微企业的测试案例"""

    print("\n" + "=" * 70)
    print("  小微企业贷款银行匹配系统 —— 原型演示")
    print("  FinTech期末作业 - 银行端数据驱动")
    print("=" * 70)

    # 案例1：稳健经营、有房产的中型企业
    print("\n\n📋 【案例1】稳健经营、有房产的制造业企业")
    profile1 = EnterpriseProfile(
        business_name="东莞精密制造有限公司",
        business_age_years=5,
        registered_capital_wan=500,
        industry="制造业",
        region="广东省",
        employee_count=30,
        annual_revenue_wan=800,
        annual_profit_wan=120,
        cash_flow_wan=150,
        tax_level=TaxLevel.A,
        annual_tax_wan=40,
        invalid_invoice_ratio=0.01,
        has_default_history=False,
        overdue_count_2yr=0,
        credit_inquiry_3m=1,
        has_real_estate=True,
        real_estate_value_wan=600,
        revenue_volatility=0.15,
        customer_count=25
    )
    results1 = match_banks(profile1)
    print_results(results1)

    # 案例2：初创、无抵押的个体工商户
    print("\n\n📋 【案例2】初创、无抵押的餐饮个体工商户")
    profile2 = EnterpriseProfile(
        business_name="老王面馆",
        business_age_years=0.8,
        registered_capital_wan=10,
        industry="住宿餐饮",
        region="四川省",
        employee_count=3,
        annual_revenue_wan=30,
        annual_profit_wan=5,
        cash_flow_wan=8,
        tax_level=TaxLevel.M,
        annual_tax_wan=1,
        invalid_invoice_ratio=0.08,
        has_default_history=False,
        overdue_count_2yr=1,
        credit_inquiry_3m=2,
        has_real_estate=False,
        revenue_volatility=0.4,
        customer_count=50
    )
    results2 = match_banks(profile2)
    print_results(results2)

    # 案例3：电商卖家、无固定资产
    print("\n\n📋 【案例3】淘宝电商卖家、纯线上经营")
    profile3 = EnterpriseProfile(
        business_name="潮流数码专营店",
        business_age_years=2,
        registered_capital_wan=30,
        industry="批发零售业",
        region="浙江省",
        employee_count=5,
        annual_revenue_wan=200,
        annual_profit_wan=25,
        cash_flow_wan=30,
        tax_level=TaxLevel.B,
        annual_tax_wan=8,
        invalid_invoice_ratio=0.03,
        has_default_history=False,
        overdue_count_2yr=0,
        credit_inquiry_3m=3,
        has_real_estate=False,
        is_ecommerce=True,
        revenue_volatility=0.25,
        customer_count=500
    )
    results3 = match_banks(profile3)
    print_results(results3)

    # 案例4：征信有瑕疵、但有资产
    print("\n\n📋 【案例4】征信有瑕疵、但有房产的小微企业")
    profile4 = EnterpriseProfile(
        business_name="某建筑装饰工程公司",
        business_age_years=3,
        registered_capital_wan=100,
        industry="建筑业",
        region="江苏省",
        employee_count=12,
        annual_revenue_wan=300,
        annual_profit_wan=20,
        cash_flow_wan=10,
        asset_liability_ratio=0.65,
        tax_level=TaxLevel.C,
        annual_tax_wan=5,
        invalid_invoice_ratio=0.12,
        has_default_history=False,
        overdue_count_2yr=4,
        credit_inquiry_3m=6,
        legal_disputes=1,
        has_real_estate=True,
        real_estate_value_wan=400,
        revenue_volatility=0.35,
        customer_count=8
    )
    results4 = match_banks(profile4)
    print_results(results4)


# ============================================================
# 7. 模型训练接口（预留）
# ============================================================

def prepare_training_features(profiles: List[EnterpriseProfile]) -> Tuple[List, List[str]]:
    """
    将企业画像列表转换为ML训练特征矩阵
    供后续XGBoost/LightGBM训练使用
    """
    feature_names = [
        "business_age_years", "registered_capital_wan", "employee_count",
        "annual_revenue_wan", "annual_profit_wan", "profit_margin",
        "cash_flow_wan", "asset_liability_ratio",
        "tax_level_encoded", "annual_tax_wan", "invalid_invoice_ratio",
        "has_default_history", "overdue_count_2yr", "credit_inquiry_3m",
        "legal_disputes", "has_real_estate", "real_estate_value_wan",
        "has_other_collateral", "revenue_volatility",
        "customer_count", "customer_concentration",
        "is_ecommerce", "is_tech_enterprise"
    ]

    X = []
    for p in profiles:
        features = [
            p.business_age_years,
            p.registered_capital_wan,
            p.employee_count,
            p.annual_revenue_wan,
            p.annual_profit_wan,
            p.annual_profit_wan / max(p.annual_revenue_wan, 1),
            p.cash_flow_wan,
            p.asset_liability_ratio,
            p.tax_level.value,
            p.annual_tax_wan,
            p.invalid_invoice_ratio,
            1 if p.has_default_history else 0,
            p.overdue_count_2yr,
            p.credit_inquiry_3m,
            p.legal_disputes,
            1 if p.has_real_estate else 0,
            p.real_estate_value_wan,
            1 if p.has_other_collateral else 0,
            p.revenue_volatility,
            p.customer_count,
            p.customer_concentration,
            1 if p.is_ecommerce else 0,
            1 if p.is_tech_enterprise else 0,
        ]
        X.append(features)

    return X, feature_names


if __name__ == "__main__":
    run_test_cases()

    # 演示特征矩阵生成
    print("\n\n📊 ML训练就绪检查:")
    print("  特征数量: 23个")
    print("  - 基础特征: 3个 (经营年限、注册资本、员工数)")
    print("  - 财务特征: 5个 (营收、利润、利润率、现金流、资产负债率)")
    print("  - 税务特征: 3个 (纳税等级、纳税额、废票率)")
    print("  - 信用特征: 4个 (历史违约、逾期次数、查询次数、法律纠纷)")
    print("  - 资产特征: 3个 (房产、房产价值、其他抵押)")
    print("  - 稳定性特征: 3个 (波动性、客户数、客户集中度)")
    print("  - 标签特征: 2个 (电商、科技企业)")
    print("  模型推荐: XGBoost/LightGBM (处理不平衡数据优势)")
    print("  数据集: CUMCM 2020 + ChinaZJB + 自建规则标注")
