"""
Bank matching engine — Python implementation.
Mirrors the frontend TypeScript logic for server-side evaluation.
"""

import math
import numpy as np
from typing import List, Tuple, Dict
from models import (
    LoanInput, EvaluationResult, BankMatchResult, MaterialItem,
    ScoreBreakdown, RiskLevel, TaxLevel, IndustryType, MerchantType,
)

# ---- Tax level scoring ----
TAX_LEVEL_SCORE: Dict[TaxLevel, float] = {
    TaxLevel.A: 5.0,
    TaxLevel.B: 4.0,
    TaxLevel.M: 3.0,
    TaxLevel.C: 2.0,
    TaxLevel.D: 1.0,
}

# ---- Industry acceptance ----
INDUSTRY_ACCEPTANCE: Dict[IndustryType, float] = {
    IndustryType.manufacturing: 1.0,
    IndustryType.wholesale_retail: 1.0,
    IndustryType.it_tech: 0.95,
    IndustryType.hospitality_food: 0.85,
    IndustryType.transportation: 0.90,
    IndustryType.agriculture: 0.90,
    IndustryType.construction: 0.75,
    IndustryType.culture_sports: 0.80,
    IndustryType.scientific_research: 0.95,
    IndustryType.resident_service: 0.85,
    IndustryType.education: 0.85,
    IndustryType.healthcare: 0.85,
    IndustryType.finance: 0.50,
    IndustryType.real_estate: 0.30,
    IndustryType.entertainment: 0.45,
    IndustryType.mining: 0.55,
    IndustryType.energy_utilities: 0.80,
    IndustryType.other: 0.70,
}

# ---- Bank products database ----
BANKS_DB = [
    {"id": "icbc", "name": "工商银行", "type": "国有大型商业银行", "tier": 1,
     "product_name": "经营快贷", "loan_type": "信用+抵押",
     "max_amount_credit": 300, "max_amount_mortgage": 500,
     "min_rate": 2.45, "max_rate": 3.00, "max_term_years": 10,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": True,
     "collateral_weight": 0.30, "cashflow_weight": 0.25, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.55, "target_enterprise": "成立时间长、纳税规范、征信优良的小微企业"},
    {"id": "ccb", "name": "建设银行", "type": "国有大型商业银行", "tier": 1,
     "product_name": "惠懂你/云税贷", "loan_type": "信用+抵押组合",
     "max_amount_credit": 500, "max_amount_mortgage": 1000,
     "min_rate": 2.40, "max_rate": 5.00, "max_term_years": 10,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": True,
     "collateral_weight": 0.25, "cashflow_weight": 0.30, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.62, "target_enterprise": "个体户、轻资产小微企业、科创企业"},
    {"id": "abc", "name": "农业银行", "type": "国有大型商业银行", "tier": 1,
     "product_name": "普惠小微贷", "loan_type": "信用+抵押",
     "max_amount_credit": 300, "max_amount_mortgage": 300,
     "min_rate": 2.35, "max_rate": 2.55, "max_term_years": 10,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.30, "cashflow_weight": 0.35, "credit_weight": 0.20, "tax_weight": 0.15,
     "estimated_base_approval": 0.58, "target_enterprise": "本地有固定经营场所的实体小微企业"},
    {"id": "boc", "name": "中国银行", "type": "国有大型商业银行", "tier": 1,
     "product_name": "银税贷/经营贷", "loan_type": "信用为主",
     "max_amount_credit": 500, "max_amount_mortgage": 500,
     "min_rate": 3.05, "max_rate": 3.60, "max_term_years": 3,
     "min_business_years": 2, "requires_collateral_strict": False, "tax_friendly": True,
     "collateral_weight": 0.20, "cashflow_weight": 0.25, "credit_weight": 0.30, "tax_weight": 0.25,
     "estimated_base_approval": 0.50, "target_enterprise": "稳健经营的成熟小微企业"},
    {"id": "bocomm", "name": "交通银行", "type": "国有大型商业银行", "tier": 1,
     "product_name": "个人经营性贷款", "loan_type": "抵押+信用",
     "max_amount_credit": 500, "max_amount_mortgage": 1000,
     "min_rate": 2.20, "max_rate": 3.00, "max_term_years": 10,
     "min_business_years": 2, "requires_collateral_strict": True, "tax_friendly": False,
     "collateral_weight": 0.40, "cashflow_weight": 0.25, "credit_weight": 0.20, "tax_weight": 0.15,
     "estimated_base_approval": 0.40, "target_enterprise": "有优质资产的较大规模小微企业"},
    {"id": "psbc", "name": "邮储银行", "type": "国有大型商业银行", "tier": 1,
     "product_name": "小微经营贷", "loan_type": "信用为主",
     "max_amount_credit": 200, "max_amount_mortgage": 200,
     "min_rate": 3.05, "max_rate": 4.00, "max_term_years": 8,
     "min_business_years": 0.5, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.10, "cashflow_weight": 0.40, "credit_weight": 0.30, "tax_weight": 0.20,
     "estimated_base_approval": 0.72, "target_enterprise": "初创企业、个体工商户、县域小微"},
    {"id": "cmb", "name": "招商银行", "type": "股份制商业银行", "tier": 2,
     "product_name": "招捷贷/生意贷", "loan_type": "抵押+信用",
     "max_amount_credit": 50, "max_amount_mortgage": 3000,
     "min_rate": 2.35, "max_rate": 3.00, "max_term_years": 20,
     "min_business_years": 1, "requires_collateral_strict": True, "tax_friendly": False,
     "collateral_weight": 0.40, "cashflow_weight": 0.25, "credit_weight": 0.20, "tax_weight": 0.15,
     "estimated_base_approval": 0.55, "target_enterprise": "有房产抵押的中小微企业"},
    {"id": "citic", "name": "中信银行", "type": "股份制商业银行", "tier": 2,
     "product_name": "房抵e贷", "loan_type": "抵押为主",
     "max_amount_credit": 500, "max_amount_mortgage": 3000,
     "min_rate": 2.15, "max_rate": 3.00, "max_term_years": 20,
     "min_business_years": 2, "requires_collateral_strict": True, "tax_friendly": False,
     "collateral_weight": 0.50, "cashflow_weight": 0.20, "credit_weight": 0.15, "tax_weight": 0.15,
     "estimated_base_approval": 0.38, "target_enterprise": "有优质房产的规模化小微企业"},
    {"id": "pingan", "name": "平安银行", "type": "股份制商业银行", "tier": 2,
     "product_name": "橙e贷（经营版）", "loan_type": "纯信用+抵押双选",
     "max_amount_credit": 300, "max_amount_mortgage": 500,
     "min_rate": 3.00, "max_rate": 5.00, "max_term_years": 10,
     "min_business_years": 0.5, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.05, "cashflow_weight": 0.45, "credit_weight": 0.30, "tax_weight": 0.20,
     "estimated_base_approval": 0.70, "target_enterprise": "初创小微、个体工商户、电商"},
    {"id": "minsheng", "name": "民生银行", "type": "股份制商业银行", "tier": 2,
     "product_name": "云抵贷", "loan_type": "抵押",
     "max_amount_credit": 0, "max_amount_mortgage": 1000,
     "min_rate": 2.60, "max_rate": 4.00, "max_term_years": 10,
     "min_business_years": 1, "requires_collateral_strict": True, "tax_friendly": False,
     "collateral_weight": 0.45, "cashflow_weight": 0.25, "credit_weight": 0.15, "tax_weight": 0.15,
     "estimated_base_approval": 0.45, "target_enterprise": "有符合要求房产的小微企业"},
    {"id": "cib", "name": "兴业银行", "type": "股份制商业银行", "tier": 2,
     "product_name": "普惠小微贷", "loan_type": "信用+抵押",
     "max_amount_credit": 300, "max_amount_mortgage": 500,
     "min_rate": 3.07, "max_rate": 4.50, "max_term_years": 10,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.25, "cashflow_weight": 0.30, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.60, "target_enterprise": "各类型小微企业"},
    {"id": "spdb", "name": "浦发银行", "type": "股份制商业银行", "tier": 2,
     "product_name": "小微快贷/商户贷", "loan_type": "信用",
     "max_amount_credit": 120, "max_amount_mortgage": 120,
     "min_rate": 3.10, "max_rate": 3.25, "max_term_years": 5,
     "min_business_years": 0.5, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.10, "cashflow_weight": 0.40, "credit_weight": 0.30, "tax_weight": 0.20,
     "estimated_base_approval": 0.65, "target_enterprise": "小额融资需求的小微商户"},
    {"id": "cebb", "name": "光大银行", "type": "股份制商业银行", "tier": 2,
     "product_name": "e担贷/e信贷", "loan_type": "信用+担保",
     "max_amount_credit": 200, "max_amount_mortgage": 500,
     "min_rate": 3.19, "max_rate": 4.50, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.30, "credit_weight": 0.25, "tax_weight": 0.25,
     "estimated_base_approval": 0.58, "target_enterprise": "有一定经营基础的小微企业"},
    {"id": "webank", "name": "微众银行(互联网)", "type": "互联网银行", "tier": 3,
     "product_name": "微业贷", "loan_type": "纯信用",
     "max_amount_credit": 1000, "max_amount_mortgage": 1000,
     "min_rate": 3.60, "max_rate": 18.00, "max_term_years": 3,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": True,
     "collateral_weight": 0.00, "cashflow_weight": 0.15, "credit_weight": 0.35, "tax_weight": 0.30,
     "estimated_base_approval": 0.80, "target_enterprise": "纳税正常的各类小微企业"},
    {"id": "mybank", "name": "网商银行(互联网)", "type": "互联网银行", "tier": 3,
     "product_name": "网商贷", "loan_type": "纯信用",
     "max_amount_credit": 500, "max_amount_mortgage": 500,
     "min_rate": 4.35, "max_rate": 20.00, "max_term_years": 3,
     "min_business_years": 0.5, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.00, "cashflow_weight": 0.30, "credit_weight": 0.25, "tax_weight": 0.15,
     "estimated_base_approval": 0.75, "target_enterprise": "电商商户、支付宝生态经营者"},

    # === 城市商业银行 (8家重点) ===
    {"id": "bjbank", "name": "北京银行", "type": "城市商业银行", "tier": 3,
     "product_name": "京e贷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 200, "max_amount_mortgage": 500,
     "min_rate": 3.45, "max_rate": 5.50, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.35, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.62, "target_enterprise": "北京及京津冀地区小微企业和个体工商户"},
    {"id": "jsbank", "name": "江苏银行", "type": "城市商业银行", "tier": 3,
     "product_name": "随e贷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 300, "max_amount_mortgage": 500,
     "min_rate": 3.35, "max_rate": 5.00, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.35, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.64, "target_enterprise": "江苏省内制造业及供应链上下游小微企业"},
    {"id": "nbbank", "name": "宁波银行", "type": "城市商业银行", "tier": 3,
     "product_name": "容易贷·小微版", "loan_type": "信用为主",
     "max_amount_credit": 300, "max_amount_mortgage": 500,
     "min_rate": 3.50, "max_rate": 5.50, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.15, "cashflow_weight": 0.35, "credit_weight": 0.30, "tax_weight": 0.20,
     "estimated_base_approval": 0.63, "target_enterprise": "浙江省内外贸及制造业小微企业"},
    {"id": "njbank", "name": "南京银行", "type": "城市商业银行", "tier": 3,
     "product_name": "鑫快捷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 200, "max_amount_mortgage": 500,
     "min_rate": 3.40, "max_rate": 5.50, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.35, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.60, "target_enterprise": "南京及周边地区科技型中小微企业"},
    {"id": "shbank", "name": "上海银行", "type": "城市商业银行", "tier": 3,
     "product_name": "上行e贷·普惠版", "loan_type": "信用+抵押",
     "max_amount_credit": 300, "max_amount_mortgage": 1000,
     "min_rate": 3.30, "max_rate": 5.00, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": True,
     "collateral_weight": 0.25, "cashflow_weight": 0.30, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.61, "target_enterprise": "上海地区服务业与贸易类小微企业"},
    {"id": "hrbbank", "name": "杭州银行", "type": "城市商业银行", "tier": 3,
     "product_name": "杭e贷·科易版", "loan_type": "信用为主",
     "max_amount_credit": 300, "max_amount_mortgage": 500,
     "min_rate": 3.50, "max_rate": 5.50, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.15, "cashflow_weight": 0.30, "credit_weight": 0.30, "tax_weight": 0.25,
     "estimated_base_approval": 0.62, "target_enterprise": "杭州及浙江地区科技和电商小微企业"},
    {"id": "cdbank", "name": "成都银行", "type": "城市商业银行", "tier": 3,
     "product_name": "蓉e贷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 200, "max_amount_mortgage": 500,
     "min_rate": 3.60, "max_rate": 6.00, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.35, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.58, "target_enterprise": "成渝地区双城经济圈小微企业和个体商户"},
    {"id": "csbank", "name": "长沙银行", "type": "城市商业银行", "tier": 3,
     "product_name": "快乐e贷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 200, "max_amount_mortgage": 500,
     "min_rate": 3.65, "max_rate": 6.00, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.35, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.57, "target_enterprise": "湖南省内中小微企业和农业产业化主体"},

    # === 互联网银行 (新增新网银行) ===
    {"id": "xwbank", "name": "新网银行(互联网)", "type": "互联网银行", "tier": 3,
     "product_name": "好商贷/好事贷", "loan_type": "纯信用",
     "max_amount_credit": 100, "max_amount_mortgage": 100,
     "min_rate": 5.00, "max_rate": 18.00, "max_term_years": 3,
     "min_business_years": 0.5, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.00, "cashflow_weight": 0.40, "credit_weight": 0.20, "tax_weight": 0.15,
     "estimated_base_approval": 0.68, "target_enterprise": "个体工商户和新市民创业者，三农小微"},

    # === 外资银行 (2家) ===
    {"id": "scbank", "name": "渣打银行(中国)", "type": "外资银行", "tier": 4,
     "product_name": "中小企业无抵押贷款", "loan_type": "信用为主",
     "max_amount_credit": 150, "max_amount_mortgage": 300,
     "min_rate": 4.50, "max_rate": 8.00, "max_term_years": 3,
     "min_business_years": 2, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.15, "cashflow_weight": 0.35, "credit_weight": 0.30, "tax_weight": 0.20,
     "estimated_base_approval": 0.42, "target_enterprise": "有进出口业务和规范财务的中型小微企业"},
    {"id": "hsbc", "name": "汇丰银行(中国)", "type": "外资银行", "tier": 4,
     "product_name": "小微企业营运资金贷款", "loan_type": "信用+抵押",
     "max_amount_credit": 200, "max_amount_mortgage": 500,
     "min_rate": 4.00, "max_rate": 7.00, "max_term_years": 3,
     "min_business_years": 2, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.30, "credit_weight": 0.30, "tax_weight": 0.20,
     "estimated_base_approval": 0.35, "target_enterprise": "跨境贸易和外资供应链上的规范经营小微企业"},

    # === 新增城商行 ===
    {"id": "qdbank", "name": "青岛银行", "type": "城市商业银行", "tier": 3,
     "product_name": "青银e贷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 200, "max_amount_mortgage": 500,
     "min_rate": 3.55, "max_rate": 5.80, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.35, "credit_weight": 0.25, "tax_weight": 0.20,
     "estimated_base_approval": 0.59, "target_enterprise": "山东半岛蓝色经济区中小微企业"},

    {"id": "xmbank", "name": "厦门国际银行", "type": "城市商业银行", "tier": 3,
     "product_name": "跨境e贷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 300, "max_amount_mortgage": 800,
     "min_rate": 3.60, "max_rate": 5.50, "max_term_years": 5,
     "min_business_years": 1, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.20, "cashflow_weight": 0.30, "credit_weight": 0.30, "tax_weight": 0.20,
     "estimated_base_approval": 0.57, "target_enterprise": "福建及海西经济区有外贸背景的中小微企业"},

    # === 县级农商行 ===
    {"id": "shundebank", "name": "顺德农商银行", "type": "农村商业银行", "tier": 4,
     "product_name": "顺商贷·小微版", "loan_type": "信用+抵押",
     "max_amount_credit": 100, "max_amount_mortgage": 300,
     "min_rate": 3.80, "max_rate": 6.50, "max_term_years": 5,
     "min_business_years": 0.5, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.15, "cashflow_weight": 0.40, "credit_weight": 0.20, "tax_weight": 0.25,
     "estimated_base_approval": 0.70, "target_enterprise": "佛山顺德本地小微制造企业和个体工商户"},

    {"id": "kunshanbank", "name": "昆山农商银行", "type": "农村商业银行", "tier": 4,
     "product_name": "昆商贷·普惠版", "loan_type": "纯信用",
     "max_amount_credit": 80, "max_amount_mortgage": 200,
     "min_rate": 3.90, "max_rate": 7.00, "max_term_years": 3,
     "min_business_years": 0.5, "requires_collateral_strict": False, "tax_friendly": False,
     "collateral_weight": 0.10, "cashflow_weight": 0.45, "credit_weight": 0.20, "tax_weight": 0.25,
     "estimated_base_approval": 0.72, "target_enterprise": "苏州昆山台资配套和本地个体工商户"},
]


def calculate_emi(principal: float, annual_rate: float, term_months: int) -> float:
    """Calculate Equal Monthly Installment."""
    if principal <= 0:
        return 0.0
    if annual_rate <= 0:
        return principal / term_months
    monthly_rate = (annual_rate / 100.0) / 12.0
    emi = (principal * monthly_rate * (1 + monthly_rate) ** term_months) / \
          ((1 + monthly_rate) ** term_months - 1)
    return round(emi, 2)


def score_enterprise_health(inp: LoanInput) -> Tuple[float, List[str], List[str]]:
    """Calculate enterprise health score (0-100)."""
    risks: List[str] = []
    reasons: List[str] = []
    total = 0.0

    # 1. Operating capability (25 pts)
    age_score = min(inp.operating_years / 3.0, 1.0) * 10
    if inp.operating_years < 1:
        risks.append("经营年限不足1年，多数国有大行无法准入")
    if inp.operating_years >= 3:
        reasons.append(f"经营{inp.operating_years}年，经营年限优势明显")

    revenue_score = min(math.log10(max(inp.monthly_revenue / 10000, 1)) / 2, 1.0) * 10
    license_score = 5.0 if inp.has_business_license else 1.0
    total += age_score + revenue_score + license_score

    # 2. Profitability (20 pts)
    net_monthly = inp.monthly_revenue - inp.monthly_fixed_cost - inp.existing_liabilities
    profit_margin = net_monthly / inp.monthly_revenue if inp.monthly_revenue > 0 else 0
    profit_score = min(max(profit_margin, 0) / 0.3, 1.0) * 12
    cashflow_ok = 8.0 if net_monthly > 0 else 0.0
    if net_monthly <= 0:
        risks.append("经营净现金流为负，几乎所有银行都会拒绝")
    total += profit_score + cashflow_ok

    # 3. Credit (30 pts)
    credit_score = 30.0
    if inp.has_overdue_record:
        credit_score -= 15
        risks.append("有历史逾期记录，通过率大幅降低")
    if inp.overdue_count_2yr > 0:
        credit_score -= min(inp.overdue_count_2yr * 3, 15)
        risks.append(f"近2年逾期{inp.overdue_count_2yr}次")
    credit_score = max(credit_score, 0)
    total += credit_score

    # 4. Tax compliance (15 pts)
    tax_score = TAX_LEVEL_SCORE.get(inp.tax_level, 3.0) * 2.0
    if TAX_LEVEL_SCORE.get(inp.tax_level, 3.0) >= 4:
        reasons.append(f"纳税等级{inp.tax_level.value}级，对申请银税贷产品有优势")
    total += tax_score

    # 5. Asset bonus (10 pts)
    asset_score = 0.0
    if inp.has_real_estate:
        asset_score += 6
        reasons.append("拥有房产，抵押类贷款产品选择空间大")
    if inp.has_collateral_or_guarantor:
        asset_score += 2
    if inp.is_tech_enterprise:
        asset_score += 2
        reasons.append("科创企业，可享受专项贷款产品")
    total += asset_score

    total = max(5.0, min(100.0, total))
    return total, risks, reasons


def calculate_bank_approval(inp: LoanInput, bank: dict, health_score: float) -> BankMatchResult:
    """Calculate approval probability for a specific bank."""
    base_prob = bank["estimated_base_approval"]

    # Business age check
    if inp.operating_years < bank["min_business_years"]:
        base_prob *= 0.5

    # Collateral requirement
    if bank["requires_collateral_strict"] and not inp.has_real_estate:
        base_prob *= 0.3

    # Credit impact
    if inp.has_overdue_record:
        base_prob *= 0.4
    if inp.overdue_count_2yr > 3:
        base_prob *= 0.7
    if inp.overdue_count_2yr > 6:
        base_prob *= 0.5

    # Industry acceptance
    industry_factor = INDUSTRY_ACCEPTANCE.get(inp.industry, 0.7)

    # Bank preference matching
    net_monthly = inp.monthly_revenue - inp.monthly_fixed_cost - inp.existing_liabilities
    cashflow_ratio = net_monthly / inp.monthly_revenue if inp.monthly_revenue > 0 else 0
    cashflow_ok = 1.0 if cashflow_ratio > 0.1 else 0.5

    credit_ok = 1.0
    if inp.overdue_count_2yr > 0:
        credit_ok -= 0.15 * inp.overdue_count_2yr
    if inp.has_overdue_record:
        credit_ok -= 0.5
    credit_ok = max(credit_ok, 0.1)

    tax_ok = TAX_LEVEL_SCORE.get(inp.tax_level, 3.0) / 5.0
    collateral_bonus = 1.3 if inp.has_real_estate else 1.0

    match_factor = (
        bank["collateral_weight"] * collateral_bonus +
        bank["cashflow_weight"] * cashflow_ok +
        bank["credit_weight"] * credit_ok +
        bank["tax_weight"] * tax_ok
    )

    # Internet bank special
    if bank["type"] == "互联网银行":
        if inp.is_ecommerce:
            base_prob *= 1.2
        if inp.operating_years < 1:
            base_prob *= 1.1

    health_factor = 0.5 + (health_score / 200.0)
    prob = base_prob * match_factor * industry_factor * health_factor
    prob = max(0.01, min(0.98, prob))

    # Rate estimation
    rate = bank["min_rate"]
    if inp.has_overdue_record:
        rate += 0.5
    rate += inp.overdue_count_2yr * 0.1
    if inp.has_real_estate:
        rate -= 0.2
    rate = max(bank["min_rate"], min(bank["max_rate"], rate))

    # Amount estimation
    if inp.has_real_estate and bank["max_amount_mortgage"] > 0:
        # bank amounts are in 万元, monthly_revenue is in 元
        monthly_revenue_wan = inp.monthly_revenue / 10000
        max_amt = min(bank["max_amount_mortgage"], monthly_revenue_wan * 0.4 * 12)
        if inp.real_estate_value > 0:
            # real_estate_value is in 万元, mortgage rate ~65%
            max_amt = min(max_amt, inp.real_estate_value * 0.65)
    else:
        monthly_revenue_wan = inp.monthly_revenue / 10000
        max_amt = min(bank["max_amount_credit"], monthly_revenue_wan * 0.4 * 12)
    max_amt = max(10, round(max_amt))

    # Reasons
    reasons: List[str] = []
    if prob > 0.6:
        reasons.append(f"审批通过概率高（{prob*100:.0f}%）")
    if rate <= bank["min_rate"] * 1.05:
        reasons.append(f"预期利率接近该行最低（{rate:.2f}%）")
    if max_amt >= 200:
        reasons.append(f"预期额度较高（{max_amt}万）")
    if bank["type"] == "互联网银行" and not inp.has_real_estate:
        reasons.append("纯信用无抵押，线上快速审批")
    if bank["id"] == "psbc":
        reasons.append("门槛最亲民，对初创企业包容度最高")
    if bank["id"] == "pingan" and not inp.has_real_estate:
        reasons.append("股份行中门槛最低，纯信用额度高")
    if bank.get("tax_friendly") and TAX_LEVEL_SCORE.get(inp.tax_level, 3.0) >= 4:
        reasons.append(f"纳税等级{inp.tax_level.value}级，银税贷优势明显")
    if inp.is_ecommerce and bank["type"] == "互联网银行":
        reasons.append("电商经营数据可替代传统征信")

    # Risk factors
    risk_factors: List[str] = []
    if prob < 0.3:
        risk_factors.append(f"该行通过率偏低（{prob*100:.0f}%）")
    if bank["requires_collateral_strict"] and not inp.has_real_estate:
        risk_factors.append("该行严格要求抵押物")
    if inp.operating_years < bank["min_business_years"]:
        risk_factors.append(f"经营年限不足（需≥{bank['min_business_years']}年）")
    if inp.has_overdue_record:
        risk_factors.append("存在逾期记录")

    # Match score
    match_score = prob * 60 + (1 - (rate - 2.0) / 5.0) * 25 + min(max_amt / 500, 1) * 15
    match_score = max(5, min(100, match_score))

    return BankMatchResult(
        bank_id=bank["id"],
        bank_name=bank["name"],
        bank_type=bank["type"],
        product_name=bank["product_name"],
        approval_probability=round(prob, 4),
        estimated_interest_rate=round(rate, 2),
        estimated_max_amount=max_amt,
        match_score=round(match_score, 1),
        recommendation_reasons=reasons if reasons else ["可以尝试申请"],
        risk_factors=risk_factors,
        loan_type=bank["loan_type"],
        max_term_years=bank["max_term_years"],
    )


def evaluate_loan(inp: LoanInput) -> EvaluationResult:
    """Main evaluation function — full pipeline."""
    # 1. Cash flow
    net_monthly_cash_flow = inp.monthly_revenue - inp.monthly_fixed_cost - inp.existing_liabilities
    monthly_repayment = calculate_emi(inp.requested_amount, inp.annual_rate, inp.loan_term)
    total_interest = round(monthly_repayment * inp.loan_term - inp.requested_amount, 2)

    repayment_pressure_ratio = (
        round((monthly_repayment / net_monthly_cash_flow) * 100, 1)
        if net_monthly_cash_flow > 0 else 150.0
    )

    total_liability_with_payment = inp.existing_liabilities + monthly_repayment
    dti_ratio = (
        round((total_liability_with_payment / inp.monthly_revenue) * 100, 1)
        if inp.monthly_revenue > 0 else 200.0
    )

    # 2. Five-dimension scoring
    # A. Operating strength (0-20)
    operating_strength = 0.0
    if inp.operating_years >= 5:
        operating_strength += 10
    elif inp.operating_years >= 3:
        operating_strength += 8
    elif inp.operating_years >= 1:
        operating_strength += 5
    else:
        operating_strength += 3
    operating_strength += 6 if inp.has_business_license else 1
    if inp.merchant_type == MerchantType.enterprise:
        operating_strength += 4
    elif inp.merchant_type == MerchantType.individual:
        operating_strength += 3
    else:
        operating_strength += 2

    # B. Cash flow coverage (0-20)
    cash_flow_coverage = 0.0
    if net_monthly_cash_flow <= 0:
        cash_flow_coverage = 0
    else:
        coverage = net_monthly_cash_flow / (monthly_repayment or 1)
        if coverage >= 3.0:
            cash_flow_coverage = 20
        elif coverage >= 2.0:
            cash_flow_coverage = 17
        elif coverage >= 1.5:
            cash_flow_coverage = 14
        elif coverage >= 1.0:
            cash_flow_coverage = 10
        elif coverage >= 0.5:
            cash_flow_coverage = 6
        else:
            cash_flow_coverage = 3

    # C. Credit compliance (0-20)
    credit_compliance = 0.0 if inp.has_overdue_record else 20.0

    # D. Credit enhancement (0-20)
    credit_enhancement = 0.0
    if inp.has_stable_bank_flow:
        credit_enhancement += 10
    if inp.has_collateral_or_guarantor:
        credit_enhancement += 10

    # E. Leverage risk (0-20)
    liability_to_revenue = inp.existing_liabilities / (inp.monthly_revenue or 1)
    if liability_to_revenue == 0:
        leverage_risk = 20.0
    elif liability_to_revenue <= 0.1:
        leverage_risk = 18.0
    elif liability_to_revenue <= 0.25:
        leverage_risk = 15.0
    elif liability_to_revenue <= 0.5:
        leverage_risk = 10.0
    elif liability_to_revenue <= 0.8:
        leverage_risk = 5.0
    else:
        leverage_risk = 2.0

    raw_score = operating_strength + cash_flow_coverage + credit_compliance + credit_enhancement + leverage_risk
    if inp.has_overdue_record:
        raw_score = min(raw_score, 48)
    score = max(10, min(100, raw_score))

    # Risk level
    if score < 55:
        risk_level = RiskLevel.high
    elif score < 80:
        risk_level = RiskLevel.medium
    else:
        risk_level = RiskLevel.low

    # 3. Suggested amount/term
    suggested_amount = inp.requested_amount
    suggested_term = inp.loan_term
    if risk_level == RiskLevel.high:
        suggested_amount = min(inp.requested_amount * 0.4, inp.monthly_revenue * 1.5)
        suggested_amount = max(0, math.floor(suggested_amount / 1000) * 1000)
        suggested_term = min(36, max(12, inp.loan_term + 6))
    elif risk_level == RiskLevel.medium:
        suggested_amount = min(inp.requested_amount * 0.85, inp.monthly_revenue * 3.5)
        suggested_amount = max(0, math.floor(suggested_amount / 1000) * 1000)
        if repayment_pressure_ratio > 35:
            suggested_term = min(36, inp.loan_term + 12)
    else:
        suggested_amount = min(inp.requested_amount, inp.monthly_revenue * 5)
    suggested_amount = max(10000, math.floor(suggested_amount))

    # 4. Strengths & risks
    strengths: List[str] = []
    risks: List[str] = []
    improvement_tips: List[str] = []

    if inp.operating_years >= 3:
        strengths.append(f"商家经营时间达 {inp.operating_years} 年，具备良好的业务韧性。")
    if inp.has_business_license:
        strengths.append("持有正式工商营业执照，具有正规主体合规展业的合法身份。")
    if inp.has_stable_bank_flow:
        strengths.append("商户拥有长期稳定的银行流水，能够交叉核验营收真实性。")
    if net_monthly_cash_flow > monthly_repayment * 2.5:
        strengths.append("当前经营净现金流充裕，对月供覆盖倍数在2.5倍以上。")
    if inp.has_collateral_or_guarantor:
        strengths.append("具备有效的抵押资产或第三方担保。")
    if not inp.has_overdue_record and score >= 75:
        strengths.append("征信信用记录良好，无历史逾期瑕疵。")

    if inp.has_overdue_record:
        risks.append("存在征信历史违约或还款不及时导致的逾期记录。")
    if net_monthly_cash_flow <= 0:
        risks.append(f"现阶段经营净现金流为负（约{net_monthly_cash_flow:.0f}元），存在还款来源断流风险。")
    elif repayment_pressure_ratio > 40:
        risks.append(f"月供占经营净现金流高达{repayment_pressure_ratio}%，还款安全边际低。")
    if not inp.has_business_license:
        risks.append("尚未办理营业执照，缺乏银行风控基础资质认定。")
    if not inp.has_stable_bank_flow:
        risks.append("缺乏系统性银行流水，信贷机构难以独立定量财务状况。")

    if not strengths:
        strengths.append("经营成本相对透明，申请期限符合常规业务循环。")
    if not risks:
        risks.append("暂无明显行业风控一票否决指标。")

    if inp.has_overdue_record:
        improvement_tips.append("建立资金到期提醒机制，逐步用优良还款表现覆盖历史污点。")
    if not inp.has_business_license:
        improvement_tips.append("建议前往市场监管部门补办营业执照。")
    if not inp.has_stable_bank_flow:
        improvement_tips.append("将微信、支付宝等收款统一归集至主开户行，沉淀至少6个月流水。")
    if repayment_pressure_ratio > 30:
        improvement_tips.append("建议拉长贷款期限或适当下调融资金额，控制月供负荷。")
    if not improvement_tips:
        improvement_tips.append("维持当前极佳信用，建立3-6个月经营流动现金储备。")
        improvement_tips.append("关注当地财政贴息和创业担保贷款等绿色融资渠道。")

    # 5. Materials
    recommended_materials = [
        MaterialItem(name="经营主体资质证明", description="营业执照正副本或企业法人执照复印件。",
                     is_required=inp.has_business_license, category="basic"),
        MaterialItem(name="法定代表人及出资人身份证件", description="实际控制人及配偶有效身份证复印件。",
                     is_required=True, category="basic"),
        MaterialItem(name="经营场所租赁合同与水电费单据", description="租赁合同及近3个月水电费凭证。",
                     is_required=True, category="basic"),
        MaterialItem(name="银行/电子支付流水单", description="最近6个月银行对公流水或第三方支付商户报告。",
                     is_required=not inp.has_stable_bank_flow, category="financial"),
        MaterialItem(name="近期完税证明或财务报表", description="资产负债表与利润表；个体商户可用纳税申报代替。",
                     is_required=inp.merchant_type == MerchantType.enterprise, category="financial"),
        MaterialItem(name="资产确权或共同反担保材料", description="房产证、车辆登记证或第三方担保人合同。",
                     is_required=inp.has_collateral_or_guarantor, category="enhancement"),
    ]

    # 6. Bank matching
    health_score, health_risks, health_reasons = score_enterprise_health(inp)
    bank_matches = [
        calculate_bank_approval(inp, bank, health_score) for bank in BANKS_DB
    ]
    bank_matches.sort(key=lambda x: x.approval_probability, reverse=True)

    # 7. ML inference (v5 enhancement)
    ml_default_prob = None
    ml_credit_rating = None
    ml_risk_level = None
    ml_enhanced = False
    try:
        from ml_inference import MLPredictor
        predictor = MLPredictor()
        enterprise_dict = {
            "operating_years": inp.operating_years,
            "monthly_revenue": inp.monthly_revenue,
            "has_overdue_record": 1 if inp.has_overdue_record else 0,
            "has_collateral": 1 if inp.has_collateral_or_guarantor else 0,
            "has_business_license": 1 if inp.has_business_license else 0,
            "merchant_type": inp.merchant_type.value,
            "industry": inp.industry,
        }
        ml_result = predictor.predict_all(enterprise_dict)
        ml_default_prob = ml_result.get("default_probability")
        ml_credit_rating = ml_result.get("credit_rating")
        ml_risk_level = ml_result.get("risk_level")
        ml_enhanced = True
    except Exception:
        pass  # ML not available — graceful degradation

    return EvaluationResult(
        score=score,
        risk_level=risk_level,
        suggested_amount=suggested_amount,
        suggested_term=suggested_term,
        monthly_repayment=monthly_repayment,
        total_interest=total_interest,
        net_monthly_cash_flow=net_monthly_cash_flow,
        dti_ratio=dti_ratio,
        repayment_pressure_ratio=repayment_pressure_ratio,
        strengths=strengths,
        risks=risks,
        improvement_tips=improvement_tips,
        recommended_materials=recommended_materials,
        bank_matches=bank_matches,
        enterprise_health_score=round(health_score),
        breakdown=ScoreBreakdown(
            operating_strength=operating_strength,
            cash_flow_coverage=cash_flow_coverage,
            credit_compliance=credit_compliance,
            credit_enhancement=credit_enhancement,
            leverage_risk=leverage_risk,
        ),
        ml_enhanced=ml_enhanced,
        ml_default_prob=ml_default_prob,
        ml_credit_rating=ml_credit_rating,
        ml_risk_level=ml_risk_level,
    )
