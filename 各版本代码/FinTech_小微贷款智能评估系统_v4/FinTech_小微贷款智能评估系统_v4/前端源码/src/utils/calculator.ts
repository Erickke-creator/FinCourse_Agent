/**
 * 小微企业贷款智能评估助手 — 核心计算引擎
 * 包含：EMI计算、五维评分、银行匹配
 */

import {
  LoanInput,
  EvaluationResult,
  RiskLevel,
  ScoreBreakdown,
  BankMatchResult,
  BankProduct,
  INDUSTRY_ACCEPTANCE,
  TAX_LEVEL_SCORE,
} from '../types';

// ============================================
// 银行产品数据库（嵌入式）
// ============================================
export const BANKS_DB: BankProduct[] = [
  {
    id: 'icbc', name: '工商银行', type: '国有大型商业银行', tier: 1,
    productName: '经营快贷', loanType: '信用+抵押',
    maxAmountCredit: 300, maxAmountMortgage: 500,
    minRate: 2.45, maxRate: 3.00, maxTermYears: 10,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: true,
    collateralWeight: 0.30, cashflowWeight: 0.25, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.55, targetEnterprise: '成立时间长、纳税规范、征信优良的小微企业',
  },
  {
    id: 'ccb', name: '建设银行', type: '国有大型商业银行', tier: 1,
    productName: '惠懂你/云税贷', loanType: '信用+抵押组合',
    maxAmountCredit: 500, maxAmountMortgage: 1000,
    minRate: 2.40, maxRate: 5.00, maxTermYears: 10,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: true,
    collateralWeight: 0.25, cashflowWeight: 0.30, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.62, targetEnterprise: '个体户、轻资产小微企业、科创企业',
  },
  {
    id: 'abc', name: '农业银行', type: '国有大型商业银行', tier: 1,
    productName: '普惠小微贷', loanType: '信用+抵押',
    maxAmountCredit: 300, maxAmountMortgage: 300,
    minRate: 2.35, maxRate: 2.55, maxTermYears: 10,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.30, cashflowWeight: 0.35, creditWeight: 0.20, taxWeight: 0.15,
    estimatedBaseApproval: 0.58, targetEnterprise: '本地有固定经营场所的实体小微企业',
  },
  {
    id: 'boc', name: '中国银行', type: '国有大型商业银行', tier: 1,
    productName: '银税贷/经营贷', loanType: '信用为主',
    maxAmountCredit: 500, maxAmountMortgage: 500,
    minRate: 3.05, maxRate: 3.60, maxTermYears: 3,
    minBusinessYears: 2, requiresCollateralStrict: false, taxFriendly: true,
    collateralWeight: 0.20, cashflowWeight: 0.25, creditWeight: 0.30, taxWeight: 0.25,
    estimatedBaseApproval: 0.50, targetEnterprise: '稳健经营的成熟小微企业',
  },
  {
    id: 'bocomm', name: '交通银行', type: '国有大型商业银行', tier: 1,
    productName: '个人经营性贷款', loanType: '抵押+信用',
    maxAmountCredit: 500, maxAmountMortgage: 1000,
    minRate: 2.20, maxRate: 3.00, maxTermYears: 10,
    minBusinessYears: 2, requiresCollateralStrict: true, taxFriendly: false,
    collateralWeight: 0.40, cashflowWeight: 0.25, creditWeight: 0.20, taxWeight: 0.15,
    estimatedBaseApproval: 0.40, targetEnterprise: '有优质资产的较大规模小微企业',
  },
  {
    id: 'psbc', name: '邮储银行', type: '国有大型商业银行', tier: 1,
    productName: '小微经营贷', loanType: '信用为主',
    maxAmountCredit: 200, maxAmountMortgage: 200,
    minRate: 3.05, maxRate: 4.00, maxTermYears: 8,
    minBusinessYears: 0.5, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.10, cashflowWeight: 0.40, creditWeight: 0.30, taxWeight: 0.20,
    estimatedBaseApproval: 0.72, targetEnterprise: '初创企业、个体工商户、县域小微',
  },
  {
    id: 'cmb', name: '招商银行', type: '股份制商业银行', tier: 2,
    productName: '招捷贷/生意贷', loanType: '抵押+信用',
    maxAmountCredit: 50, maxAmountMortgage: 3000,
    minRate: 2.35, maxRate: 3.00, maxTermYears: 20,
    minBusinessYears: 1, requiresCollateralStrict: true, taxFriendly: false,
    collateralWeight: 0.40, cashflowWeight: 0.25, creditWeight: 0.20, taxWeight: 0.15,
    estimatedBaseApproval: 0.55, targetEnterprise: '有房产抵押的中小微企业',
  },
  {
    id: 'citic', name: '中信银行', type: '股份制商业银行', tier: 2,
    productName: '房抵e贷', loanType: '抵押为主',
    maxAmountCredit: 500, maxAmountMortgage: 3000,
    minRate: 2.15, maxRate: 3.00, maxTermYears: 20,
    minBusinessYears: 2, requiresCollateralStrict: true, taxFriendly: false,
    collateralWeight: 0.50, cashflowWeight: 0.20, creditWeight: 0.15, taxWeight: 0.15,
    estimatedBaseApproval: 0.38, targetEnterprise: '有优质房产的规模化小微企业',
  },
  {
    id: 'pingan', name: '平安银行', type: '股份制商业银行', tier: 2,
    productName: '橙e贷（经营版）', loanType: '纯信用+抵押双选',
    maxAmountCredit: 300, maxAmountMortgage: 500,
    minRate: 3.00, maxRate: 5.00, maxTermYears: 10,
    minBusinessYears: 0.5, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.05, cashflowWeight: 0.45, creditWeight: 0.30, taxWeight: 0.20,
    estimatedBaseApproval: 0.70, targetEnterprise: '初创小微、个体工商户、电商',
  },
  {
    id: 'minsheng', name: '民生银行', type: '股份制商业银行', tier: 2,
    productName: '云抵贷', loanType: '抵押',
    maxAmountCredit: 0, maxAmountMortgage: 1000,
    minRate: 2.60, maxRate: 4.00, maxTermYears: 10,
    minBusinessYears: 1, requiresCollateralStrict: true, taxFriendly: false,
    collateralWeight: 0.45, cashflowWeight: 0.25, creditWeight: 0.15, taxWeight: 0.15,
    estimatedBaseApproval: 0.45, targetEnterprise: '有符合要求房产的小微企业',
  },
  {
    id: 'cib', name: '兴业银行', type: '股份制商业银行', tier: 2,
    productName: '普惠小微贷', loanType: '信用+抵押',
    maxAmountCredit: 300, maxAmountMortgage: 500,
    minRate: 3.07, maxRate: 4.50, maxTermYears: 10,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.25, cashflowWeight: 0.30, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.60, targetEnterprise: '各类型小微企业',
  },
  {
    id: 'spdb', name: '浦发银行', type: '股份制商业银行', tier: 2,
    productName: '小微快贷/商户贷', loanType: '信用',
    maxAmountCredit: 120, maxAmountMortgage: 120,
    minRate: 3.10, maxRate: 3.25, maxTermYears: 5,
    minBusinessYears: 0.5, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.10, cashflowWeight: 0.40, creditWeight: 0.30, taxWeight: 0.20,
    estimatedBaseApproval: 0.65, targetEnterprise: '小额融资需求的小微商户',
  },
  {
    id: 'cebb', name: '光大银行', type: '股份制商业银行', tier: 2,
    productName: 'e担贷/e信贷', loanType: '信用+担保',
    maxAmountCredit: 200, maxAmountMortgage: 500,
    minRate: 3.19, maxRate: 4.50, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.30, creditWeight: 0.25, taxWeight: 0.25,
    estimatedBaseApproval: 0.58, targetEnterprise: '有一定经营基础的小微企业',
  },
  {
    id: 'webank', name: '微众银行(互联网)', type: '互联网银行', tier: 3,
    productName: '微业贷', loanType: '纯信用',
    maxAmountCredit: 1000, maxAmountMortgage: 1000,
    minRate: 3.60, maxRate: 18.00, maxTermYears: 3,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: true,
    collateralWeight: 0.00, cashflowWeight: 0.15, creditWeight: 0.35, taxWeight: 0.30,
    estimatedBaseApproval: 0.80, targetEnterprise: '纳税正常的各类小微企业',
  },
  {
    id: 'mybank', name: '网商银行(互联网)', type: '互联网银行', tier: 3,
    productName: '网商贷', loanType: '纯信用',
    maxAmountCredit: 500, maxAmountMortgage: 500,
    minRate: 4.35, maxRate: 20.00, maxTermYears: 3,
    minBusinessYears: 0.5, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.00, cashflowWeight: 0.30, creditWeight: 0.25, taxWeight: 0.15,
    estimatedBaseApproval: 0.75, targetEnterprise: '电商商户、支付宝生态经营者',
  },

  // ========== 城市商业银行 (8家) ==========
  {
    id: 'bjbank', name: '北京银行', type: '城市商业银行', tier: 3,
    productName: '京e贷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 200, maxAmountMortgage: 500,
    minRate: 3.45, maxRate: 5.50, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.35, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.62, targetEnterprise: '北京及京津冀地区小微企业',
  },
  {
    id: 'jsbank', name: '江苏银行', type: '城市商业银行', tier: 3,
    productName: '随e贷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 300, maxAmountMortgage: 500,
    minRate: 3.35, maxRate: 5.00, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.35, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.64, targetEnterprise: '江苏省内制造业及供应链小微企业',
  },
  {
    id: 'nbbank', name: '宁波银行', type: '城市商业银行', tier: 3,
    productName: '容易贷·小微版', loanType: '信用为主',
    maxAmountCredit: 300, maxAmountMortgage: 500,
    minRate: 3.50, maxRate: 5.50, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.15, cashflowWeight: 0.35, creditWeight: 0.30, taxWeight: 0.20,
    estimatedBaseApproval: 0.63, targetEnterprise: '浙江省内外贸及制造业小微企业',
  },
  {
    id: 'njbank', name: '南京银行', type: '城市商业银行', tier: 3,
    productName: '鑫快捷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 200, maxAmountMortgage: 500,
    minRate: 3.40, maxRate: 5.50, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.35, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.60, targetEnterprise: '南京及周边科技型中小微企业',
  },
  {
    id: 'shbank', name: '上海银行', type: '城市商业银行', tier: 3,
    productName: '上行e贷·普惠版', loanType: '信用+抵押',
    maxAmountCredit: 300, maxAmountMortgage: 1000,
    minRate: 3.30, maxRate: 5.00, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: true,
    collateralWeight: 0.25, cashflowWeight: 0.30, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.61, targetEnterprise: '上海地区服务业与贸易类小微企业',
  },
  {
    id: 'hrbbank', name: '杭州银行', type: '城市商业银行', tier: 3,
    productName: '杭e贷·科易版', loanType: '信用为主',
    maxAmountCredit: 300, maxAmountMortgage: 500,
    minRate: 3.50, maxRate: 5.50, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.15, cashflowWeight: 0.30, creditWeight: 0.30, taxWeight: 0.25,
    estimatedBaseApproval: 0.62, targetEnterprise: '杭州及浙江地区科技和电商小微企业',
  },
  {
    id: 'cdbank', name: '成都银行', type: '城市商业银行', tier: 3,
    productName: '蓉e贷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 200, maxAmountMortgage: 500,
    minRate: 3.60, maxRate: 6.00, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.35, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.58, targetEnterprise: '成渝地区双城经济圈小微企业',
  },
  {
    id: 'csbank', name: '长沙银行', type: '城市商业银行', tier: 3,
    productName: '快乐e贷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 200, maxAmountMortgage: 500,
    minRate: 3.65, maxRate: 6.00, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.35, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.57, targetEnterprise: '湖南省内中小微企业和农业主体',
  },

  // ========== 互联网银行 (新增) ==========
  {
    id: 'xwbank', name: '新网银行(互联网)', type: '互联网银行', tier: 3,
    productName: '好商贷/好事贷', loanType: '纯信用',
    maxAmountCredit: 100, maxAmountMortgage: 100,
    minRate: 5.00, maxRate: 18.00, maxTermYears: 3,
    minBusinessYears: 0.5, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.00, cashflowWeight: 0.40, creditWeight: 0.20, taxWeight: 0.15,
    estimatedBaseApproval: 0.68, targetEnterprise: '个体工商户和新市民创业者，三农小微',
  },

  // ========== 外资银行 (2家) ==========
  {
    id: 'scbank', name: '渣打银行(中国)', type: '外资银行', tier: 4,
    productName: '中小企业无抵押贷款', loanType: '信用为主',
    maxAmountCredit: 150, maxAmountMortgage: 300,
    minRate: 4.50, maxRate: 8.00, maxTermYears: 3,
    minBusinessYears: 2, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.15, cashflowWeight: 0.35, creditWeight: 0.30, taxWeight: 0.20,
    estimatedBaseApproval: 0.42, targetEnterprise: '有进出口业务的规范中型小微企业',
  },
  {
    id: 'hsbc', name: '汇丰银行(中国)', type: '外资银行', tier: 4,
    productName: '小微企业营运资金贷款', loanType: '信用+抵押',
    maxAmountCredit: 200, maxAmountMortgage: 500,
    minRate: 4.00, maxRate: 7.00, maxTermYears: 3,
    minBusinessYears: 2, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.30, creditWeight: 0.30, taxWeight: 0.20,
    estimatedBaseApproval: 0.35, targetEnterprise: '跨境贸易和外资供应链规范企业',
  },

  // ========== 新增城商行 ==========
  {
    id: 'qdbank', name: '青岛银行', type: '城市商业银行', tier: 3,
    productName: '青银e贷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 200, maxAmountMortgage: 500,
    minRate: 3.55, maxRate: 5.80, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.35, creditWeight: 0.25, taxWeight: 0.20,
    estimatedBaseApproval: 0.59, targetEnterprise: '山东半岛蓝色经济区中小微企业',
  },
  {
    id: 'xmbank', name: '厦门国际银行', type: '城市商业银行', tier: 3,
    productName: '跨境e贷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 300, maxAmountMortgage: 800,
    minRate: 3.60, maxRate: 5.50, maxTermYears: 5,
    minBusinessYears: 1, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.20, cashflowWeight: 0.30, creditWeight: 0.30, taxWeight: 0.20,
    estimatedBaseApproval: 0.57, targetEnterprise: '福建及海西经济区中小微企业',
  },

  // ========== 县级农商行 ==========
  {
    id: 'shundebank', name: '顺德农商银行', type: '农村商业银行', tier: 4,
    productName: '顺商贷·小微版', loanType: '信用+抵押',
    maxAmountCredit: 100, maxAmountMortgage: 300,
    minRate: 3.80, maxRate: 6.50, maxTermYears: 5,
    minBusinessYears: 0.5, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.15, cashflowWeight: 0.40, creditWeight: 0.20, taxWeight: 0.25,
    estimatedBaseApproval: 0.70, targetEnterprise: '佛山顺德本地小微制造企业和个体工商户',
  },
  {
    id: 'kunshanbank', name: '昆山农商银行', type: '农村商业银行', tier: 4,
    productName: '昆商贷·普惠版', loanType: '纯信用',
    maxAmountCredit: 80, maxAmountMortgage: 200,
    minRate: 3.90, maxRate: 7.00, maxTermYears: 3,
    minBusinessYears: 0.5, requiresCollateralStrict: false, taxFriendly: false,
    collateralWeight: 0.10, cashflowWeight: 0.45, creditWeight: 0.20, taxWeight: 0.25,
    estimatedBaseApproval: 0.72, targetEnterprise: '苏州昆山台资配套和本地个体工商户',
  },
];

// ============================================
// EMI计算
// ============================================
export function calculateEMI(principal: number, annualRate: number, termMonths: number): number {
  if (principal <= 0) return 0;
  if (annualRate <= 0) return principal / termMonths;
  const monthlyRate = (annualRate / 100) / 12;
  const emi = (principal * monthlyRate * Math.pow(1 + monthlyRate, termMonths)) /
              (Math.pow(1 + monthlyRate, termMonths) - 1);
  return Number(emi.toFixed(2));
}

// ============================================
// 企业健康度综合评分 (0-100)
// ============================================
export function scoreEnterpriseHealth(input: LoanInput): {
  totalScore: number;
  risks: string[];
  reasons: string[];
} {
  const risks: string[] = [];
  const reasons: string[] = [];
  let totalScore = 0;

  // 1. 经营能力 (25分)
  const ageScore = Math.min(input.operatingYears / 3.0, 1.0) * 10;
  if (input.operatingYears < 1) risks.push('经营年限不足1年，多数国有大行无法准入');
  if (input.operatingYears >= 3) reasons.push(`经营${input.operatingYears}年，经营年限优势明显`);

  const revenueScore = Math.min(Math.log10(Math.max(input.monthlyRevenue / 10000, 1)) / 2, 1.0) * 10;
  const licenseScore = input.hasBusinessLicense ? 5 : 1;
  totalScore += ageScore + revenueScore + licenseScore;

  // 2. 盈利能力 (20分)
  const netMonthly = input.monthlyRevenue - input.monthlyFixedCost - input.existingLiabilities;
  const profitMargin = input.monthlyRevenue > 0
    ? netMonthly / input.monthlyRevenue : 0;
  const profitScore = Math.min(Math.max(profitMargin, 0) / 0.3, 1.0) * 12;
  const cashFlowOk = netMonthly > 0 ? 8 : 0;
  if (netMonthly <= 0) risks.push('经营净现金流为负，几乎所有银行都会拒绝');
  totalScore += profitScore + cashFlowOk;

  // 3. 信用状况 (30分 - 权重最高)
  let creditScore = 30;
  if (input.hasOverdueRecord) {
    creditScore -= 15;
    risks.push('有历史逾期记录，通过率大幅降低');
  }
  if (input.overdueCount2yr > 0) {
    creditScore -= Math.min(input.overdueCount2yr * 3, 15);
    risks.push(`近2年逾期${input.overdueCount2yr}次`);
  }
  if (input.overdueCount2yr > 6) {
    creditScore -= 5;
    risks.push('逾期次数超过多数银行容忍上限');
  }
  creditScore = Math.max(creditScore, 0);
  totalScore += creditScore;

  // 4. 税务规范性 (15分)
  const taxScore = TAX_LEVEL_SCORE[input.taxLevel] * 2.0;
  if (TAX_LEVEL_SCORE[input.taxLevel] >= 4) {
    reasons.push(`纳税等级${input.taxLevel}级，对申请银税贷产品有优势`);
  }
  totalScore += taxScore;

  // 5. 资产加分 (10分)
  let assetScore = 0;
  if (input.hasRealEstate) { assetScore += 6; reasons.push('拥有房产，抵押类贷款产品选择空间大'); }
  if (input.hasCollateralOrGuarantor) assetScore += 2;
  if (input.isTechEnterprise) { assetScore += 2; reasons.push('科创企业，可享受专项贷款产品'); }
  totalScore += assetScore;

  totalScore = Math.max(5, Math.min(100, totalScore));
  return { totalScore, risks, reasons };
}

// ============================================
// 银行通过概率计算
// ============================================
export function calculateBankApproval(
  input: LoanInput,
  bank: BankProduct,
  healthScore: number
): BankMatchResult {
  let baseProb = bank.estimatedBaseApproval;

  // 经营年限
  if (input.operatingYears < bank.minBusinessYears) {
    baseProb *= 0.5;
  }

  // 硬抵押要求
  if (bank.requiresCollateralStrict && !input.hasRealEstate) {
    baseProb *= 0.3;
  }

  // 征信影响
  if (input.hasOverdueRecord) baseProb *= 0.4;
  if (input.overdueCount2yr > 3) baseProb *= 0.7;
  if (input.overdueCount2yr > 6) baseProb *= 0.5;

  // 行业接受度
  const industryFactor = INDUSTRY_ACCEPTANCE[input.industry] ?? 0.7;

  // 银行偏好匹配
  const netMonthly = input.monthlyRevenue - input.monthlyFixedCost - input.existingLiabilities;
  const cashflowRatio = input.monthlyRevenue > 0 ? netMonthly / input.monthlyRevenue : 0;
  const cashflowOk = cashflowRatio > 0.1 ? 1.0 : 0.5;

  let creditOk = 1.0;
  if (input.overdueCount2yr > 0) creditOk -= 0.15 * input.overdueCount2yr;
  if (input.hasOverdueRecord) creditOk -= 0.5;
  creditOk = Math.max(creditOk, 0.1);

  const taxOk = TAX_LEVEL_SCORE[input.taxLevel] / 5.0;
  const collateralBonus = input.hasRealEstate ? 1.3 : 1.0;

  const matchFactor =
    bank.collateralWeight * collateralBonus +
    bank.cashflowWeight * cashflowOk +
    bank.creditWeight * creditOk +
    bank.taxWeight * taxOk;

  // 互联网银行特殊
  if (bank.type === '互联网银行') {
    if (input.isEcommerce) baseProb *= 1.2;
    if (input.operatingYears < 1) baseProb *= 1.1;
  }

  const healthFactor = 0.5 + (healthScore / 200);
  let prob = baseProb * matchFactor * industryFactor * healthFactor;
  prob = Math.max(0.01, Math.min(0.98, prob));

  // 利率估计
  let rate = bank.minRate;
  if (input.hasOverdueRecord) rate += 0.5;
  rate += input.overdueCount2yr * 0.1;
  if (input.hasRealEstate) rate -= 0.2;
  rate = Math.max(bank.minRate, Math.min(bank.maxRate, rate));

  // 额度估计
  let maxAmt: number;
  if (input.hasRealEstate && bank.maxAmountMortgage > 0) {
    const monthlyRevenueWan = input.monthlyRevenue / 10000;
    maxAmt = Math.min(bank.maxAmountMortgage, monthlyRevenueWan * 0.4 * 12);
    if (input.realEstateValue > 0) maxAmt = Math.min(maxAmt, input.realEstateValue * 0.65);
  } else {
    const monthlyRevenueWan = input.monthlyRevenue / 10000;
    maxAmt = Math.min(bank.maxAmountCredit, monthlyRevenueWan * 0.4 * 12);
  }
  maxAmt = Math.max(10, Math.round(maxAmt));

  // 推荐理由
  const reasons: string[] = [];
  if (prob > 0.6) reasons.push(`审批通过概率高（${(prob * 100).toFixed(0)}%）`);
  if (rate <= bank.minRate * 1.05) reasons.push(`预期利率接近该行最低（${rate.toFixed(2)}%）`);
  if (maxAmt >= 200) reasons.push(`预期额度较高（${maxAmt}万）`);
  if (bank.type === '互联网银行' && !input.hasRealEstate) reasons.push('纯信用无抵押，线上快速审批');
  if (bank.id === 'psbc') reasons.push('门槛最亲民，对初创企业包容度最高');
  if (bank.id === 'pingan' && !input.hasRealEstate) reasons.push('股份行中门槛最低，纯信用额度高');
  if (BANKS_DB.find(b => b.id === bank.id)?.taxFriendly && TAX_LEVEL_SCORE[input.taxLevel] >= 4) {
    reasons.push(`纳税等级${input.taxLevel}级，银税贷优势明显`);
  }
  if (input.isEcommerce && bank.type === '互联网银行') reasons.push('电商经营数据可替代传统征信');

  // 风险因素
  const riskFactors: string[] = [];
  if (prob < 0.3) riskFactors.push(`该行通过率偏低（${(prob * 100).toFixed(0)}%）`);
  if (bank.requiresCollateralStrict && !input.hasRealEstate) riskFactors.push('该行严格要求抵押物');
  if (input.operatingYears < bank.minBusinessYears) riskFactors.push(`经营年限不足（需≥${bank.minBusinessYears}年）`);
  if (input.hasOverdueRecord) riskFactors.push('存在逾期记录');
  if (bank.minRate > 4) riskFactors.push('融资成本偏高');

  // 综合匹配分
  const matchScore = Math.round(
    prob * 60 + (1 - (rate - 2.0) / 5.0) * 25 + Math.min(maxAmt / 500, 1) * 15
  );
  const clampedScore = Math.max(5, Math.min(100, matchScore));

  return {
    bankId: bank.id,
    bankName: bank.name,
    bankType: bank.type,
    productName: bank.productName,
    approvalProbability: Math.round(prob * 10000) / 10000,
    estimatedInterestRate: Math.round(rate * 100) / 100,
    estimatedMaxAmount: maxAmt,
    matchScore: clampedScore,
    recommendationReasons: reasons.length > 0 ? reasons : ['可以尝试申请'],
    riskFactors,
    loanType: bank.loanType,
    maxTermYears: bank.maxTermYears,
  };
}

// ============================================
// 主评估函数（兼容旧接口 + 新增银行匹配）
// ============================================
export function evaluateLoanPronto(input: LoanInput): EvaluationResult & { breakdown: ScoreBreakdown } {
  const {
    merchantType, operatingYears, monthlyRevenue, monthlyFixedCost,
    existingLiabilities, requestedAmount, loanTerm, annualRate,
    hasBusinessLicense, hasStableBankFlow, hasOverdueRecord, hasCollateralOrGuarantor,
  } = input;

  // 1. 现金流计算
  const netMonthlyCashFlow = monthlyRevenue - monthlyFixedCost - existingLiabilities;
  const monthlyRepayment = calculateEMI(requestedAmount, annualRate, loanTerm);
  const totalInterest = Number((monthlyRepayment * loanTerm - requestedAmount).toFixed(2));

  const repaymentPressureRatio = netMonthlyCashFlow > 0
    ? Number(((monthlyRepayment / netMonthlyCashFlow) * 100).toFixed(1))
    : 150.0;

  const totalLiabilityWithPayment = existingLiabilities + monthlyRepayment;
  const dtiRatio = monthlyRevenue > 0
    ? Number(((totalLiabilityWithPayment / monthlyRevenue) * 100).toFixed(1))
    : 200.0;

  // 2. 五维评分
  // A. 经营实力 (0-20)
  let operatingStrength = 0;
  if (operatingYears >= 5) operatingStrength += 10;
  else if (operatingYears >= 3) operatingStrength += 8;
  else if (operatingYears >= 1) operatingStrength += 5;
  else operatingStrength += 3;
  if (hasBusinessLicense) operatingStrength += 6;
  else operatingStrength += 1;
  if (merchantType === 'enterprise') operatingStrength += 4;
  else if (merchantType === 'individual') operatingStrength += 3;
  else operatingStrength += 2;

  // B. 现金流覆盖 (0-20)
  let cashFlowCoverage = 0;
  if (netMonthlyCashFlow <= 0) cashFlowCoverage = 0;
  else {
    const coverage = netMonthlyCashFlow / (monthlyRepayment || 1);
    if (coverage >= 3.0) cashFlowCoverage = 20;
    else if (coverage >= 2.0) cashFlowCoverage = 17;
    else if (coverage >= 1.5) cashFlowCoverage = 14;
    else if (coverage >= 1.0) cashFlowCoverage = 10;
    else if (coverage >= 0.5) cashFlowCoverage = 6;
    else cashFlowCoverage = 3;
  }

  // C. 信用合规 (0-20)
  const creditCompliance = hasOverdueRecord ? 0 : 20;

  // D. 信用增强 (0-20)
  let creditEnhancement = 0;
  if (hasStableBankFlow) creditEnhancement += 10;
  if (hasCollateralOrGuarantor) creditEnhancement += 10;

  // E. 杠杆风险 (0-20)
  let leverageRisk = 0;
  const liabilityToRevenue = existingLiabilities / (monthlyRevenue || 1);
  if (liabilityToRevenue === 0) leverageRisk = 20;
  else if (liabilityToRevenue <= 0.1) leverageRisk = 18;
  else if (liabilityToRevenue <= 0.25) leverageRisk = 15;
  else if (liabilityToRevenue <= 0.5) leverageRisk = 10;
  else if (liabilityToRevenue <= 0.8) leverageRisk = 5;
  else leverageRisk = 2;

  let rawScore = operatingStrength + cashFlowCoverage + creditCompliance + creditEnhancement + leverageRisk;
  if (hasOverdueRecord) rawScore = Math.min(rawScore, 48);
  const score = Math.max(10, Math.min(100, rawScore));

  // 风险等级
  let riskLevel: RiskLevel = 'low';
  if (score < 55) riskLevel = 'high';
  else if (score < 80) riskLevel = 'medium';

  // 3. 建议额度与期限
  let suggestedAmount = requestedAmount;
  let suggestedTerm = loanTerm;
  if (riskLevel === 'high') {
    suggestedAmount = Math.min(requestedAmount * 0.4, monthlyRevenue * 1.5);
    suggestedAmount = Math.max(0, Math.floor(suggestedAmount / 1000) * 1000);
    suggestedTerm = Math.min(36, Math.max(12, loanTerm + 6));
  } else if (riskLevel === 'medium') {
    suggestedAmount = Math.min(requestedAmount * 0.85, monthlyRevenue * 3.5);
    suggestedAmount = Math.max(0, Math.floor(suggestedAmount / 1000) * 1000);
    if (repaymentPressureRatio > 35) suggestedTerm = Math.min(36, loanTerm + 12);
  } else {
    suggestedAmount = Math.min(requestedAmount, monthlyRevenue * 5);
  }
  suggestedAmount = Math.max(10000, Math.floor(suggestedAmount));

  // 4. 优劣势分析
  const strengths: string[] = [];
  const risks: string[] = [];
  const improvementTips: string[] = [];

  if (operatingYears >= 3) strengths.push(`商家经营时间达 ${operatingYears} 年，越过了小微主体通常的前三年生存敏感期，具备良好的业务韧性与基本客户群。`);
  if (hasBusinessLicense) strengths.push('持有正式工商营业执照，具有正规主体合规展业的合法身份。');
  if (hasStableBankFlow) strengths.push('商户拥有长期稳定的银行对公活期或经营流水，能够交叉核验其实际营收真实性。');
  if (netMonthlyCashFlow > monthlyRepayment * 2.5) strengths.push('当前经营净现金流充裕，对拟申贷资金的月供覆盖倍数在2.5倍以上。');
  if (hasCollateralOrGuarantor) strengths.push('具备有效的实体抵押资产或第三方联保，属于极佳的分险缓冲手段。');
  if (!hasOverdueRecord && score >= 75) strengths.push('征信信用记录良好，无任何历史逾期瑕疵，是典型的小微诚信标杆商户。');

  if (hasOverdueRecord) risks.push('存在征信历史违约或还款不及时导致的逾期记录。在信贷实践中属于重大负面指标。');
  if (netMonthlyCashFlow <= 0) risks.push(`现阶段商户经营净现金流为负（约 ${netMonthlyCashFlow} 元），存在实质性还款来源断流风险。`);
  else if (repaymentPressureRatio > 40) risks.push(`申贷月供占经营净现金流高达 ${repaymentPressureRatio}%，还款安全边际非常低。`);
  if (!hasBusinessLicense) risks.push('目前尚未办理营业执照，缺乏银行风控最基础的主体合规资质认定。');
  if (!hasStableBankFlow) risks.push('缺乏系统性的商业银行往来流水，信贷机构难以独立定量其财务状况。');

  if (strengths.length === 0) strengths.push('经营成本相对透明，申请期限符合常规业务循环。');
  if (risks.length === 0) risks.push('暂无明显行业风控一票否决指标。');

  if (hasOverdueRecord) improvementTips.push('建立严格的资金到期提醒机制，按时偿还现有各项利息，逐步用长期优良还款表现覆盖历史污点。');
  if (!hasBusinessLicense) improvementTips.push('建议前往当地市场监管部门补办工商户营业执照。');
  if (!hasStableBankFlow) improvementTips.push('逐步把微信、支付宝等第三方收款归集，统一缴存至主开户行，沉淀出至少连续六个月的完整流水记录。');
  if (repaymentPressureRatio > 30) improvementTips.push(`当前月供额度吃紧。建议主动拉长贷款期限或适当下调融资金额，控制日常月供负荷。`);

  if (improvementTips.length === 0) {
    improvementTips.push('维持当前的极佳信用。建议建立中短期资金池，保持3-6个月经营流动现金储备。');
    improvementTips.push('积极利用普惠金融政策性降息契机，关注当地财政贴息和创业担保贷款等绿色融资渠道。');
  }

  // 5. 材料清单
  const recommendedMaterials = [
    { name: '经营主体资质证明', description: '个体工商户营业执照正副本或企业法人执照复印件。', isRequired: hasBusinessLicense, category: 'basic' as const },
    { name: '法定代表人及出资人身份证件', description: '商户实际控制人、配偶有效二代身份证复印件。', isRequired: true, category: 'basic' as const },
    { name: '经营场所租赁合同与水电费单据', description: '有效期内的租赁合同及近3个月水电费凭证。', isRequired: true, category: 'basic' as const },
    { name: '银行/电子支付流水单', description: '最近至少6个月的银行对公流水或支付宝/微信商户后台收入报告。', isRequired: !hasStableBankFlow, category: 'financial' as const },
    { name: '近期完税证明或财务报表', description: '小微企业需提供资产负债表与利润表；个体商户可用纳税申报代替。', isRequired: merchantType === 'enterprise', category: 'financial' as const },
    { name: '资产确权或共同反担保材料', description: '房产证、车辆登记证或第三方担保人的联签合同。', isRequired: hasCollateralOrGuarantor, category: 'enhancement' as const },
  ];

  // 6. 银行匹配
  const healthResult = scoreEnterpriseHealth(input);
  const bankMatches: BankMatchResult[] = BANKS_DB
    .map(bank => calculateBankApproval(input, bank, healthResult.totalScore))
    .sort((a, b) => b.approvalProbability - a.approvalProbability);

  return {
    score,
    riskLevel,
    suggestedAmount,
    suggestedTerm,
    monthlyRepayment,
    totalInterest,
    netMonthlyCashFlow,
    dtiRatio,
    repaymentPressureRatio,
    strengths,
    risks,
    improvementTips,
    recommendedMaterials,
    bankMatches,
    enterpriseHealthScore: Math.round(healthResult.totalScore),
    breakdown: { operatingStrength, cashFlowCoverage, creditCompliance, creditEnhancement, leverageRisk },
  };
}
