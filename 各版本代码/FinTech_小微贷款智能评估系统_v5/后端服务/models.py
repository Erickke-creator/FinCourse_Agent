"""
Pydantic data models for the SME loan evaluation API.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MerchantType(str, Enum):
    individual = "individual"
    enterprise = "enterprise"
    freelancer = "freelancer"


class TaxLevel(str, Enum):
    A = "A"
    B = "B"
    M = "M"
    C = "C"
    D = "D"


class IndustryType(str, Enum):
    manufacturing = "manufacturing"
    wholesale_retail = "wholesale_retail"
    it_tech = "it_tech"
    hospitality_food = "hospitality_food"
    transportation = "transportation"
    agriculture = "agriculture"
    construction = "construction"
    culture_sports = "culture_sports"
    scientific_research = "scientific_research"
    resident_service = "resident_service"
    education = "education"
    healthcare = "healthcare"
    finance = "finance"
    real_estate = "real_estate"
    entertainment = "entertainment"
    mining = "mining"
    energy_utilities = "energy_utilities"
    other = "other"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# ---- Input ----
class LoanInput(BaseModel):
    merchant_type: MerchantType = MerchantType.individual
    operating_years: float = Field(ge=0, le=50, default=1.0)
    industry: IndustryType = IndustryType.wholesale_retail
    region: str = "广东省"

    # Financials
    monthly_revenue: float = Field(ge=0, default=30000)
    monthly_fixed_cost: float = Field(ge=0, default=15000)
    existing_liabilities: float = Field(ge=0, default=0)

    # Loan request
    requested_amount: float = Field(ge=1000, default=50000)
    loan_term: int = Field(default=12)
    annual_rate: float = Field(ge=0, le=36, default=6.0)

    # Credit & enhancements
    tax_level: TaxLevel = TaxLevel.M
    has_business_license: bool = True
    has_stable_bank_flow: bool = False
    has_overdue_record: bool = False
    overdue_count_2yr: int = Field(ge=0, le=100, default=0)
    has_collateral_or_guarantor: bool = False
    has_real_estate: bool = False
    real_estate_value: float = Field(ge=0, default=0)
    is_ecommerce: bool = False
    is_tech_enterprise: bool = False


# ---- Output ----
class MaterialItem(BaseModel):
    name: str
    description: str
    is_required: bool
    category: str  # basic | financial | enhancement


class ScoreBreakdown(BaseModel):
    operating_strength: float
    cash_flow_coverage: float
    credit_compliance: float
    credit_enhancement: float
    leverage_risk: float


class BankMatchResult(BaseModel):
    bank_id: str
    bank_name: str
    bank_type: str
    product_name: str
    approval_probability: float
    estimated_interest_rate: float
    estimated_max_amount: float  # 万元
    match_score: float
    recommendation_reasons: List[str]
    risk_factors: List[str]
    loan_type: str
    max_term_years: int


class EvaluationResult(BaseModel):
    score: float
    risk_level: RiskLevel
    suggested_amount: float
    suggested_term: int
    monthly_repayment: float
    total_interest: float
    net_monthly_cash_flow: float
    dti_ratio: float
    repayment_pressure_ratio: float
    strengths: List[str]
    risks: List[str]
    improvement_tips: List[str]
    recommended_materials: List[MaterialItem]
    bank_matches: List[BankMatchResult]
    enterprise_health_score: float
    breakdown: ScoreBreakdown
    ml_enhanced: bool = False
    ml_default_prob: Optional[float] = None
    ml_credit_rating: Optional[str] = None
    ml_risk_level: Optional[str] = None


class BankProductResponse(BaseModel):
    id: str
    name: str
    type: str
    product_name: str
    loan_type: str
    max_amount_credit: float
    max_amount_mortgage: float
    min_rate: float
    max_rate: float
    max_term_years: int
    min_business_years: float
    target_enterprise: str


class ApiResponse(BaseModel):
    success: bool
    data: Optional[EvaluationResult] = None
    error: Optional[str] = None
