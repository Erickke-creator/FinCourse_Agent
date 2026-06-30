/**
 * 小微企业贷款智能评估助手 — 类型定义
 * FinTech期末作业 — 银行匹配 + 风险评估
 */

// ============================================
// 商户类型
// ============================================
export type MerchantType = 'individual' | 'enterprise' | 'freelancer';

// ============================================
// 企业画像输入
// ============================================
export interface LoanInput {
  // 基础信息
  merchantType: MerchantType;
  operatingYears: number;
  industry: IndustryType;
  region: string;

  // 财务数据
  monthlyRevenue: number;
  monthlyFixedCost: number;
  existingLiabilities: number;

  // 贷款需求
  requestedAmount: number;
  loanTerm: number;
  annualRate: number;

  // 信用与增强
  taxLevel: TaxLevel;
  hasBusinessLicense: boolean;
  hasStableBankFlow: boolean;
  hasOverdueRecord: boolean;
  overdueCount2yr: number;
  hasCollateralOrGuarantor: boolean;
  hasRealEstate: boolean;
  realEstateValue: number;
  isEcommerce: boolean;
  isTechEnterprise: boolean;
}

// ============================================
// 行业分类
// ============================================
export type IndustryType =
  | 'manufacturing'
  | 'wholesale_retail'
  | 'it_tech'
  | 'hospitality_food'
  | 'transportation'
  | 'agriculture'
  | 'construction'
  | 'culture_sports'
  | 'scientific_research'
  | 'resident_service'
  | 'education'
  | 'healthcare'
  | 'finance'
  | 'real_estate'
  | 'entertainment'
  | 'mining'
  | 'energy_utilities'
  | 'other';

export const INDUSTRY_LABELS: Record<IndustryType, string> = {
  manufacturing: '制造业',
  wholesale_retail: '批发零售业',
  it_tech: '信息技术',
  hospitality_food: '住宿餐饮',
  transportation: '交通运输',
  agriculture: '农业',
  construction: '建筑业',
  culture_sports: '文化体育',
  scientific_research: '科学研究',
  resident_service: '居民服务',
  education: '教育',
  healthcare: '卫生医疗',
  finance: '金融业',
  real_estate: '房地产业',
  entertainment: '娱乐业',
  mining: '采矿业',
  energy_utilities: '电力热力',
  other: '其他行业',
};

export const INDUSTRY_ACCEPTANCE: Record<IndustryType, number> = {
  manufacturing: 1.0,
  wholesale_retail: 1.0,
  it_tech: 0.95,
  hospitality_food: 0.85,
  transportation: 0.90,
  agriculture: 0.90,
  construction: 0.75,
  culture_sports: 0.80,
  scientific_research: 0.95,
  resident_service: 0.85,
  education: 0.85,
  healthcare: 0.85,
  finance: 0.50,
  real_estate: 0.30,
  entertainment: 0.45,
  mining: 0.55,
  energy_utilities: 0.80,
  other: 0.70,
};

// ============================================
// 纳税等级
// ============================================
export type TaxLevel = 'A' | 'B' | 'M' | 'C' | 'D';
export const TAX_LEVEL_SCORE: Record<TaxLevel, number> = { A: 5, B: 4, M: 3, C: 2, D: 1 };

// ============================================
// 风险等级
// ============================================
export type RiskLevel = 'low' | 'medium' | 'high';

// ============================================
// 评分细分
// ============================================
export interface ScoreBreakdown {
  operatingStrength: number;    // 经营实力 0-20
  cashFlowCoverage: number;     // 现金流覆盖 0-20
  creditCompliance: number;     // 信用合规 0-20
  creditEnhancement: number;    // 信用增强 0-20
  leverageRisk: number;         // 杠杆风险 0-20
  supplyChainRisk?: number;     // v5: 供应链风险
}

// ============================================
// 评估结果
// ============================================
export interface EvaluationResult {
  score: number;
  riskLevel: RiskLevel;
  suggestedAmount: number;
  suggestedTerm: number;
  monthlyRepayment: number;
  totalInterest: number;
  netMonthlyCashFlow: number;
  dtiRatio: number;
  repaymentPressureRatio: number;
  strengths: string[];
  risks: string[];
  improvementTips: string[];
  recommendedMaterials: MaterialItem[];
  bankMatches: BankMatchResult[];
  enterpriseHealthScore: number;
  // v5 ML fields (optional — only when backend ML is available)
  mlEnhanced?: boolean;
  mlDefaultProb?: number;
  mlCreditRating?: string;
  mlRiskLevel?: string;
}

// ============================================
// 材料清单
// ============================================
export interface MaterialItem {
  name: string;
  description: string;
  isRequired: boolean;
  category: 'basic' | 'financial' | 'enhancement';
}

// ============================================
// 银行类型
// ============================================
export type BankTier = '国有大型商业银行' | '股份制商业银行' | '城市商业银行' | '农村商业银行' | '互联网银行' | '外资银行';

// ============================================
// 银行匹配结果
// ============================================
export interface BankMatchResult {
  bankId: string;
  bankName: string;
  bankType: BankTier;
  productName: string;
  approvalProbability: number;     // 0-1
  estimatedInterestRate: number;   // 预期利率
  estimatedMaxAmount: number;      // 预期最高额度（万元）
  matchScore: number;              // 综合匹配度 0-100
  recommendationReasons: string[];
  riskFactors: string[];
  loanType: string;
  maxTermYears: number;
}

// ============================================
// 银行产品数据
// ============================================
export interface BankProduct {
  id: string;
  name: string;
  type: BankTier;
  tier: number;
  productName: string;
  loanType: string;
  maxAmountCredit: number;
  maxAmountMortgage: number;
  minRate: number;
  maxRate: number;
  maxTermYears: number;
  minBusinessYears: number;
  requiresCollateralStrict: boolean;
  taxFriendly: boolean;
  collateralWeight: number;
  cashflowWeight: number;
  creditWeight: number;
  taxWeight: number;
  estimatedBaseApproval: number;
  targetEnterprise: string;
}

// ============================================
// API 响应类型
// ============================================
export interface ApiEvaluateResponse {
  success: boolean;
  data?: EvaluationResult;
  error?: string;
}

export interface ApiBanksResponse {
  success: boolean;
  data?: BankProduct[];
  error?: string;
}
