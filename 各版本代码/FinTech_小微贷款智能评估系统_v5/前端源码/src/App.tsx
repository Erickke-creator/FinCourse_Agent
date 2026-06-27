/**
 * 小微贷款智能评估助手 — 仪表盘布局
 * 左侧导航 + 右侧内容区，5个功能模块切换
 */

import { useState, FormEvent, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { evaluateLoanPronto } from './utils/calculator';
import type { LoanInput, EvaluationResult, ScoreBreakdown } from './types';
import ScoreGauge from './components/ScoreGauge';
import FinancialMetrics from './components/FinancialMetrics';
import AdvisorReport from './components/AdvisorReport';
import MaterialChecklist from './components/MaterialChecklist';
import BankMatchPanel from './components/BankMatchPanel';
import SupplyChainGraph from './components/SupplyChainGraph';
import ChatPanel from './components/ChatPanel';
import InclusiveFinanceSlide from './components/InclusiveFinanceSlide';

import {
  Calculator, FileText, BarChart3, Building2, Landmark,
  User, Briefcase, RotateCcw, ArrowRight, Sparkles,
  Store, ShoppingCart, Microscope, Tractor, HardHat,
  Laptop, ShoppingBag, ClipboardCheck, BookOpen,
  ChevronRight, Play, Home,
} from 'lucide-react';

// ============================================================
// 8个多样化案例
// ============================================================
const DEMO_CASES: Record<string, { label: string; icon: any; desc: string; data: LoanInput }> = {
  milktea: {
    label: '奶茶店', icon: Store, desc: '小餐饮创业',
    data: {
      merchantType: 'individual' as const, operatingYears: 2, industry: 'hospitality_food' as const,
      region: '广东省', monthlyRevenue: 60000, monthlyFixedCost: 35000,
      existingLiabilities: 20000, requestedAmount: 100000, loanTerm: 12,
      annualRate: 6.0, taxLevel: 'B' as const, hasBusinessLicense: true,
      hasStableBankFlow: true, hasOverdueRecord: false, overdueCount2yr: 0,
      hasCollateralOrGuarantor: false, hasRealEstate: false, realEstateValue: 0,
      isEcommerce: false, isTechEnterprise: false,
    },
  },
  manufacturing: {
    label: '制造业', icon: Building2, desc: '专精特新',
    data: {
      merchantType: 'enterprise' as const, operatingYears: 5, industry: 'manufacturing' as const,
      region: '江苏省', monthlyRevenue: 500000, monthlyFixedCost: 300000,
      existingLiabilities: 100000, requestedAmount: 500000, loanTerm: 24,
      annualRate: 4.35, taxLevel: 'A' as const, hasBusinessLicense: true,
      hasStableBankFlow: true, hasOverdueRecord: false, overdueCount2yr: 0,
      hasCollateralOrGuarantor: true, hasRealEstate: true, realEstateValue: 300,
      isEcommerce: false, isTechEnterprise: true,
    },
  },
  ecommerce: {
    label: '电商卖家', icon: ShoppingCart, desc: '纯线上经营',
    data: {
      merchantType: 'individual' as const, operatingYears: 3, industry: 'wholesale_retail' as const,
      region: '浙江省', monthlyRevenue: 150000, monthlyFixedCost: 60000,
      existingLiabilities: 0, requestedAmount: 200000, loanTerm: 12,
      annualRate: 5.0, taxLevel: 'B' as const, hasBusinessLicense: true,
      hasStableBankFlow: true, hasOverdueRecord: false, overdueCount2yr: 0,
      hasCollateralOrGuarantor: false, hasRealEstate: false, realEstateValue: 0,
      isEcommerce: true, isTechEnterprise: false,
    },
  },
  agritech: {
    label: '农业合作社', icon: Tractor, desc: '三农主体',
    data: {
      merchantType: 'enterprise' as const, operatingYears: 4, industry: 'agriculture' as const,
      region: '河南省', monthlyRevenue: 80000, monthlyFixedCost: 40000,
      existingLiabilities: 10000, requestedAmount: 100000, loanTerm: 24,
      annualRate: 5.5, taxLevel: 'A' as const, hasBusinessLicense: true,
      hasStableBankFlow: false, hasOverdueRecord: false, overdueCount2yr: 0,
      hasCollateralOrGuarantor: true, hasRealEstate: false, realEstateValue: 0,
      isEcommerce: false, isTechEnterprise: false,
    },
  },
  constructor: {
    label: '建筑承包商', icon: HardHat, desc: '有抵押有负债',
    data: {
      merchantType: 'enterprise' as const, operatingYears: 6, industry: 'construction' as const,
      region: '湖北省', monthlyRevenue: 300000, monthlyFixedCost: 200000,
      existingLiabilities: 500000, requestedAmount: 800000, loanTerm: 36,
      annualRate: 5.5, taxLevel: 'C' as const, hasBusinessLicense: true,
      hasStableBankFlow: true, hasOverdueRecord: true, overdueCount2yr: 3,
      hasCollateralOrGuarantor: true, hasRealEstate: true, realEstateValue: 500,
      isEcommerce: false, isTechEnterprise: false,
    },
  },
  techstartup: {
    label: '科技初创', icon: Microscope, desc: '亏损但有专利',
    data: {
      merchantType: 'enterprise' as const, operatingYears: 0.5, industry: 'it_tech' as const,
      region: '北京市', monthlyRevenue: 20000, monthlyFixedCost: 50000,
      existingLiabilities: 0, requestedAmount: 300000, loanTerm: 36,
      annualRate: 8.0, taxLevel: 'M' as const, hasBusinessLicense: true,
      hasStableBankFlow: false, hasOverdueRecord: false, overdueCount2yr: 0,
      hasCollateralOrGuarantor: false, hasRealEstate: false, realEstateValue: 0,
      isEcommerce: false, isTechEnterprise: true,
    },
  },
  freelancer: {
    label: '自由职业', icon: Laptop, desc: '无执照无流水',
    data: {
      merchantType: 'freelancer' as const, operatingYears: 1.5, industry: 'culture_sports' as const,
      region: '上海市', monthlyRevenue: 15000, monthlyFixedCost: 5000,
      existingLiabilities: 0, requestedAmount: 30000, loanTerm: 6,
      annualRate: 12.0, taxLevel: 'M' as const, hasBusinessLicense: false,
      hasStableBankFlow: false, hasOverdueRecord: false, overdueCount2yr: 0,
      hasCollateralOrGuarantor: false, hasRealEstate: false, realEstateValue: 0,
      isEcommerce: false, isTechEnterprise: false,
    },
  },
  oldretail: {
    label: '批发老店', icon: ShoppingBag, desc: '征信有瑕疵',
    data: {
      merchantType: 'individual' as const, operatingYears: 10, industry: 'wholesale_retail' as const,
      region: '山东省', monthlyRevenue: 200000, monthlyFixedCost: 120000,
      existingLiabilities: 80000, requestedAmount: 300000, loanTerm: 24,
      annualRate: 7.0, taxLevel: 'C' as const, hasBusinessLicense: true,
      hasStableBankFlow: true, hasOverdueRecord: true, overdueCount2yr: 5,
      hasCollateralOrGuarantor: true, hasRealEstate: true, realEstateValue: 200,
      isEcommerce: false, isTechEnterprise: false,
    },
  },
};

// ============================================================
// 导航定义
// ============================================================
type NavSection = 'chat' | 'input' | 'risk' | 'banks' | 'network' | 'materials' | 'about';

const NAV_ITEMS: { id: NavSection; label: string; icon: any; desc?: string }[] = [
  { id: 'chat', label: '智能对话', icon: Sparkles, desc: 'AI贷款顾问' },
  { id: 'input', label: '企业信息', icon: FileText, desc: '经营数据录入' },
  { id: 'risk', label: '风险评估', icon: BarChart3, desc: '信用评分诊断' },
  { id: 'banks', label: '银行匹配', icon: Landmark, desc: '26行通过率预测' },
  { id: 'network', label: '关系网络', icon: ShoppingCart, desc: '供应链图谱' },
  { id: 'materials', label: '材料清单', icon: ClipboardCheck, desc: '申贷材料准备' },
  { id: 'about', label: '普惠金融', icon: BookOpen, desc: 'FinTech理论' },
];

// ============================================================
// 默认表单
// ============================================================
const DEFAULT_INPUT: LoanInput = {
  merchantType: 'individual', operatingYears: 1, industry: 'wholesale_retail', region: '广东省',
  monthlyRevenue: 30000, monthlyFixedCost: 15000, existingLiabilities: 0,
  requestedAmount: 50000, loanTerm: 12, annualRate: 6.0, taxLevel: 'M',
  hasBusinessLicense: true, hasStableBankFlow: false, hasOverdueRecord: false,
  overdueCount2yr: 0, hasCollateralOrGuarantor: false, hasRealEstate: false,
  realEstateValue: 0, isEcommerce: false, isTechEnterprise: false,
};

// ============================================================
// 主组件
// ============================================================
export default function App() {
  const [inputs, setInputs] = useState<LoanInput>(DEFAULT_INPUT);
  const [hasEvaluated, setHasEvaluated] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState<(EvaluationResult & { breakdown: ScoreBreakdown }) | null>(null);
  const [activeCase, setActiveCase] = useState<string | null>(null);
  const [activeNav, setActiveNav] = useState<NavSection>('chat');
  const [showCasePanel, setShowCasePanel] = useState(false);
  const mainRef = useRef<HTMLDivElement>(null);

  const formatCNY = (v: number) =>
    new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 0 }).format(v);

  const handleLoadCase = (caseKey: string) => {
    const item = DEMO_CASES[caseKey];
    if (!item) return;
    setInputs(item.data);
    setActiveCase(caseKey);
    setShowCasePanel(false);
    const res = evaluateLoanPronto(item.data);
    setEvaluationResult(res);
    setHasEvaluated(true);
    setActiveNav('risk');
  };

  const handleReset = () => {
    setInputs(DEFAULT_INPUT);
    setHasEvaluated(false);
    setEvaluationResult(null);
    setActiveCase(null);
    setActiveNav('input');
  };

  const handleEvaluate = (e?: FormEvent) => {
    if (e) e.preventDefault();
    setEvaluationResult(evaluateLoanPronto(inputs));
    setHasEvaluated(true);
    setActiveNav('risk');
    mainRef.current?.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // v5: 调用后端 /api/evaluate（含 ML 预测），失败时降级为本地计算
  const handleEvaluateWithAPI = async (e?: FormEvent) => {
    if (e) e.preventDefault();
    const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000';
    try {
      const resp = await fetch(`${API_BASE}/api/evaluate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          merchant_type: inputs.merchantType,
          operating_years: inputs.operatingYears,
          industry: inputs.industry,
          monthly_revenue: inputs.monthlyRevenue,
          monthly_fixed_cost: inputs.monthlyFixedCost,
          existing_liabilities: inputs.existingLiabilities,
          requested_amount: inputs.requestedAmount,
          loan_term: inputs.loanTerm,
          annual_rate: inputs.annualRate,
          tax_level: inputs.taxLevel,
          has_business_license: inputs.hasBusinessLicense,
          has_stable_bank_flow: inputs.hasStableBankFlow,
          has_overdue_record: inputs.hasOverdueRecord,
          overdue_count_2yr: inputs.overdueCount2yr,
          has_collateral_or_guarantor: inputs.hasCollateralOrGuarantor,
        }),
      });
      if (resp.ok) {
        const data = await resp.json();
        if (data.success && data.data) {
          setEvaluationResult(data.data as EvaluationResult);
          setHasEvaluated(true);
          setActiveNav('risk');
          return;
        }
      }
    } catch (err) {
      console.warn('API evaluation failed, falling back to local:', err);
    }
    // Fallback
    setEvaluationResult(evaluateLoanPronto(inputs));
    setHasEvaluated(true);
    setActiveNav('risk');
  };

  // ============================================================
  // 渲染区域
  // ============================================================

  const renderContent = () => {
    if (!hasEvaluated || !evaluationResult) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-50 to-indigo-100 rounded-2xl flex items-center justify-center mb-6">
            <Calculator className="w-10 h-10 text-blue-500" />
          </div>
          <h2 className="text-xl font-bold text-slate-800 mb-2">普惠金融 · 小微贷款智能评估助手</h2>
          <p className="text-sm text-slate-500 max-w-md mb-8">
            在左侧填入企业经营数据并点击评估，或从下方选择一个真实案例快速体验
          </p>
          <div className="grid grid-cols-4 gap-2 max-w-xl">
            {Object.entries(DEMO_CASES).map(([key, item]) => {
              const Icon = item.icon;
              return (
                <button key={key} onClick={() => handleLoadCase(key)}
                  className="flex flex-col items-center gap-1.5 p-3 bg-white rounded-xl border border-slate-200 hover:border-blue-300 hover:shadow-md transition cursor-pointer">
                  <Icon className="w-5 h-5 text-slate-500" />
                  <span className="text-xs font-medium text-slate-700">{item.label}</span>
                  <span className="text-[10px] text-slate-400">{item.desc}</span>
                </button>
              );
            })}
          </div>
        </div>
      );
    }

    switch (activeNav) {
      case 'input':
        return null; // handled separately
      case 'risk':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
              <ScoreGauge score={evaluationResult.score} riskLevel={evaluationResult.riskLevel} breakdown={evaluationResult.breakdown} />
              <AdvisorReport result={evaluationResult} input={inputs} />
            </div>
            <FinancialMetrics result={evaluationResult} input={inputs} />
          </div>
        );
      case 'banks':
        return evaluationResult.bankMatches?.length > 0
          ? <BankMatchPanel bankMatches={evaluationResult.bankMatches} requestedAmount={inputs.requestedAmount} />
          : <div className="text-center py-20 text-slate-400">请先完成评估</div>;
      case 'chat':
        return <ChatPanel />;
      case 'network':
        return <SupplyChainGraph input={inputs} />;
      case 'materials':
        return <MaterialChecklist materials={evaluationResult.recommendedMaterials} />;
      case 'about':
        return <InclusiveFinanceSlide />;
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* ================================================================ */}
      {/* 左侧导航栏 */}
      {/* ================================================================ */}
      <aside className="w-56 flex-shrink-0 bg-white border-r border-slate-200 flex flex-col h-full">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center shadow-md shadow-blue-200">
              <Calculator className="w-5 h-5 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-900 leading-tight">小微贷款</div>
              <div className="text-sm font-bold text-slate-900 leading-tight">智能评估助手</div>
            </div>
          </div>
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 px-3 py-4 space-y-0.5">
          {NAV_ITEMS.map(item => {
            const Icon = item.icon;
            const isActive = activeNav === item.id;
            const isDisabled = (item.id !== 'chat' && item.id !== 'input' && item.id !== 'about' && item.id !== 'network') && !hasEvaluated;
            return (
              <button
                key={item.id}
                onClick={() => !isDisabled && setActiveNav(item.id)}
                disabled={isDisabled}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-blue-50 text-blue-700 shadow-sm'
                    : isDisabled
                      ? 'text-slate-300 cursor-not-allowed'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <Icon className={`w-4.5 h-4.5 ${isActive ? 'text-blue-600' : isDisabled ? 'text-slate-300' : 'text-slate-400'}`} />
                <span>{item.label}</span>
                {isActive && <ChevronRight className="w-4 h-4 ml-auto text-blue-400" />}
              </button>
            );
          })}
        </nav>

        {/* 快速案例区域 */}
        <div className="px-3 py-3 border-t border-slate-100">
          <button
            onClick={() => setShowCasePanel(!showCasePanel)}
            className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-lg transition"
          >
            <span className="flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              快速案例
            </span>
            <span className="text-[10px] text-slate-400">{Object.keys(DEMO_CASES).length}个</span>
          </button>
          {showCasePanel && (
            <div className="mt-2 grid grid-cols-2 gap-1">
              {Object.entries(DEMO_CASES).map(([key, item]) => {
                const Icon = item.icon;
                const isActiveCase = activeCase === key;
                return (
                  <button key={key} onClick={() => handleLoadCase(key)}
                    className={`flex items-center gap-1.5 px-2 py-1.5 rounded text-[11px] transition ${
                      isActiveCase
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
                    }`}>
                    <Icon className="w-3 h-3" />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* 底部信息 */}
        <div className="px-5 py-3 border-t border-slate-100">
          <div className="text-[10px] text-slate-400 space-y-0.5">
            <div className="flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              <span>30行匹配引擎 v3.1</span>
            </div>
            <div>FinTech 期末成果展示</div>
          </div>
        </div>
      </aside>

      {/* ================================================================ */}
      {/* 右侧主内容区 */}
      {/* ================================================================ */}
      <main ref={mainRef} className="flex-1 overflow-auto">
        {/* 顶栏 */}
        <header className="sticky top-0 z-30 bg-white/95 backdrop-blur border-b border-slate-200 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-slate-500">
              {NAV_ITEMS.find(n => n.id === activeNav)?.label || '企业信息'}
            </span>
            {activeCase && DEMO_CASES[activeCase] && (
              <span className="text-[11px] px-2 py-0.5 bg-blue-50 text-blue-600 rounded-full border border-blue-100">
                当前案例：{DEMO_CASES[activeCase].label} · {DEMO_CASES[activeCase].desc}
              </span>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button onClick={handleReset}
              className="px-3 py-1.5 text-xs text-slate-500 hover:text-slate-700 hover:bg-slate-50 rounded-lg transition flex items-center gap-1.5">
              <RotateCcw className="w-3.5 h-3.5" />
              重置
            </button>
            {hasEvaluated && (
              <button onClick={() => setActiveNav('risk')}
                className={`px-3 py-1.5 text-xs rounded-lg transition flex items-center gap-1.5 ${
                  activeNav === 'risk' ? 'bg-blue-50 text-blue-700' : 'text-slate-500 hover:text-slate-700'
                }`}>
                <BarChart3 className="w-3.5 h-3.5" />
                评估结果
              </button>
            )}
            <button onClick={() => handleEvaluateWithAPI()}
              className="px-4 py-1.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm shadow-blue-200 transition flex items-center gap-1.5">
              <Play className="w-3.5 h-3.5" />
              开始评估
            </button>
            {hasEvaluated && (
              <button onClick={async () => {
                const API_BASE = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000';
                try {
                  const resp = await fetch(`${API_BASE}/api/report/pdf-download`, {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enterprise_name: inputs.industry || '企业', evaluation_result: evaluationResult }),
                  });
                  if (resp.ok) {
                    const blob = await resp.blob();
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a'); a.href = url; a.download = '贷款评估报告.pdf'; a.click();
                    URL.revokeObjectURL(url);
                  } else { alert('PDF 生成失败'); }
                } catch { alert('请确保后端已启动'); }
              }}
              className="px-4 py-1.5 bg-white border border-blue-200 hover:bg-blue-50 text-blue-600 rounded-lg text-xs font-semibold transition flex items-center gap-1.5">
                📥 下载 PDF
              </button>
            )}
          </div>
        </header>

        {/* 内容区 */}
        <div className="max-w-5xl mx-auto px-6 py-6">
          {!hasEvaluated || activeNav === 'input' ? (
            /* ========================================================== */
            /* 企业信息录入表单 */
            /* ========================================================== */
            <div className="space-y-6">
              <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
                  <h2 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                    <FileText className="w-4 h-4 text-blue-500" />
                    商户经营信息录入
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">请如实填入经营与财务数据，系统将为您匹配26家银行的贷款通过概率</p>
                </div>

                <form onSubmit={handleEvaluate} className="p-6 space-y-5">
                  {/* 第一行：基本画像 */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {/* 商户类型 */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">商户类型</label>
                      <div className="grid grid-cols-3 gap-1">
                        {([
                          { id: 'individual' as const, label: '个体户', icon: User },
                          { id: 'enterprise' as const, label: '小微企业', icon: Building2 },
                          { id: 'freelancer' as const, label: '自由职业', icon: Briefcase },
                        ]).map(t => {
                          const Icon = t.icon;
                          const active = inputs.merchantType === t.id;
                          return (
                            <button key={t.id} type="button" onClick={() => setInputs(p => ({ ...p, merchantType: t.id }))}
                              className={`flex flex-col items-center gap-1 py-2 px-1 rounded-lg border text-[11px] transition cursor-pointer ${
                                active ? 'bg-blue-600 text-white border-blue-600 font-semibold' : 'bg-white text-slate-500 border-slate-200 hover:bg-slate-50'
                              }`}>
                              <Icon className="w-3.5 h-3.5" />
                              {t.label}
                            </button>
                          );
                        })}
                      </div>
                    </div>

                    {/* 行业 */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">所属行业</label>
                      <select value={inputs.industry}
                        onChange={e => setInputs(p => ({ ...p, industry: e.target.value as any }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none">
                        {[
                          { v: 'manufacturing', l: '制造业' }, { v: 'wholesale_retail', l: '批发零售' },
                          { v: 'it_tech', l: '信息技术' }, { v: 'hospitality_food', l: '住宿餐饮' },
                          { v: 'transportation', l: '交通运输' }, { v: 'agriculture', l: '农业' },
                          { v: 'construction', l: '建筑业' }, { v: 'culture_sports', l: '文化体育' },
                          { v: 'resident_service', l: '居民服务' }, { v: 'education', l: '教育' },
                          { v: 'healthcare', l: '卫生医疗' }, { v: 'other', l: '其他' },
                        ].map(o => <option key={o.v} value={o.v}>{o.l}</option>)}
                      </select>
                    </div>

                    {/* 地区 */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">所在地区</label>
                      <select value={inputs.region}
                        onChange={e => setInputs(p => ({ ...p, region: e.target.value }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none">
                        {['广东省','浙江省','江苏省','北京市','上海市','四川省','湖北省','山东省','福建省','河南省','湖南省','其他'].map(r =>
                          <option key={r} value={r}>{r}</option>
                        )}
                      </select>
                    </div>

                    {/* 纳税等级 */}
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">纳税等级</label>
                      <select value={inputs.taxLevel}
                        onChange={e => setInputs(p => ({ ...p, taxLevel: e.target.value as any }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none">
                        <option value="A">A级 (优秀)</option>
                        <option value="B">B级 (良好)</option>
                        <option value="M">M级 (新设)</option>
                        <option value="C">C级 (一般)</option>
                        <option value="D">D级 (较差)</option>
                      </select>
                    </div>
                  </div>

                  {/* 第二行：经营与财务 */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="space-y-1.5">
                      <div className="flex justify-between">
                        <label className="text-xs font-semibold text-slate-500">经营年限</label>
                        <span className="text-xs font-mono font-bold text-slate-700">{inputs.operatingYears}年</span>
                      </div>
                      <input type="range" min="0" max="10" step="0.5" value={inputs.operatingYears}
                        onChange={e => setInputs(p => ({ ...p, operatingYears: Number(e.target.value) }))}
                        className="w-full accent-blue-600" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">月营收 (元)</label>
                      <input type="number" required min="1000" step="1000" value={inputs.monthlyRevenue}
                        onChange={e => setInputs(p => ({ ...p, monthlyRevenue: Number(e.target.value) }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-mono" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">月固定成本 (元)</label>
                      <input type="number" required min="0" step="500" value={inputs.monthlyFixedCost}
                        onChange={e => setInputs(p => ({ ...p, monthlyFixedCost: Number(e.target.value) }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-mono" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">已有负债 (元)</label>
                      <input type="number" required min="0" step="500" value={inputs.existingLiabilities}
                        onChange={e => setInputs(p => ({ ...p, existingLiabilities: Number(e.target.value) }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-mono" />
                    </div>
                  </div>

                  {/* 第三行：贷款需求 */}
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    <div className="space-y-1.5">
                      <div className="flex justify-between">
                        <label className="text-xs font-semibold text-slate-500">申请金额</label>
                        <span className="text-xs font-mono font-bold text-blue-600">{formatCNY(inputs.requestedAmount)}</span>
                      </div>
                      <input type="range" min="10000" max="1000000" step="5000" value={inputs.requestedAmount}
                        onChange={e => setInputs(p => ({ ...p, requestedAmount: Number(e.target.value) }))}
                        className="w-full accent-blue-600" />
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">贷款期限</label>
                      <select value={inputs.loanTerm}
                        onChange={e => setInputs(p => ({ ...p, loanTerm: Number(e.target.value) }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-mono">
                        {[3,6,12,24,36,60].map(m => <option key={m} value={m}>{m}个月</option>)}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">预期年利率</label>
                      <select value={inputs.annualRate}
                        onChange={e => setInputs(p => ({ ...p, annualRate: Number(e.target.value) }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-mono">
                        {[3.5,4.35,6.0,8.5,12.0].map(r => <option key={r} value={r}>{r}%</option>)}
                      </select>
                    </div>
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-500">近2年逾期次数</label>
                      <input type="range" min="0" max="10" step="1" value={inputs.overdueCount2yr}
                        onChange={e => setInputs(p => ({ ...p, overdueCount2yr: Number(e.target.value) }))}
                        className="w-full accent-red-500" />
                      <span className="text-[10px] text-slate-400">{inputs.overdueCount2yr}次</span>
                    </div>
                  </div>

                  {/* 第四行：信用增强（勾选项） */}
                  <div className="flex flex-wrap gap-x-6 gap-y-2 pt-1">
                    {[
                      { key: 'hasBusinessLicense' as const, label: '具备营业执照', color: 'blue' },
                      { key: 'hasStableBankFlow' as const, label: '稳定银行流水', color: 'blue' },
                      { key: 'hasRealEstate' as const, label: '拥有房产', color: 'blue' },
                      { key: 'hasCollateralOrGuarantor' as const, label: '有抵押/担保', color: 'blue' },
                      { key: 'isEcommerce' as const, label: '电商/线上经营', color: 'indigo' },
                      { key: 'isTechEnterprise' as const, label: '科技/专精特新', color: 'indigo' },
                      { key: 'hasOverdueRecord' as const, label: '有历史逾期记录', color: 'red' },
                    ].map(item => (
                      <label key={item.key} className="flex items-center gap-2 cursor-pointer">
                        <input type="checkbox" checked={!!inputs[item.key]}
                          onChange={e => setInputs(p => ({ ...p, [item.key]: e.target.checked }))}
                          className={`w-4 h-4 rounded border-slate-300 focus:ring-2 cursor-pointer ${
                            item.color === 'red' ? 'text-red-500 focus:ring-red-200' : 'text-blue-600 focus:ring-blue-200'
                          }`} />
                        <span className={`text-xs ${item.color === 'red' ? 'text-red-600 font-semibold' : 'text-slate-600'}`}>
                          {item.label}
                        </span>
                      </label>
                    ))}
                  </div>

                  {/* 房产价值（条件显示） */}
                  {inputs.hasRealEstate && (
                    <div className="w-48">
                      <label className="text-xs font-semibold text-slate-500">房产估值 (万元)</label>
                      <input type="number" min="0" step="10" value={inputs.realEstateValue}
                        onChange={e => setInputs(p => ({ ...p, realEstateValue: Number(e.target.value) }))}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg py-2 px-3 text-sm focus:ring-2 focus:ring-blue-500/20 outline-none font-mono mt-1" />
                    </div>
                  )}

                  {/* 提交按钮 */}
                  <button type="submit"
                    className="w-full bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white py-3 rounded-xl font-bold text-sm transition shadow-md shadow-blue-200 flex items-center justify-center gap-2">
                    <Play className="w-4 h-4" />
                    开始智能评估 + 银行匹配
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </form>
              </div>

              {/* 未评估时的案例推荐 */}
              {!hasEvaluated && (
                <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
                  <h3 className="text-sm font-bold text-slate-700 mb-4 flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-amber-500" />
                    选择一个真实案例快速体验
                  </h3>
                  <div className="grid grid-cols-4 gap-3">
                    {Object.entries(DEMO_CASES).map(([key, item]) => {
                      const Icon = item.icon;
                      return (
                        <button key={key} onClick={() => handleLoadCase(key)}
                          className="flex flex-col items-center gap-2 p-4 bg-slate-50 hover:bg-blue-50 rounded-xl border border-slate-100 hover:border-blue-200 transition cursor-pointer">
                          <Icon className="w-6 h-6 text-slate-500" />
                          <span className="text-sm font-medium text-slate-700">{item.label}</span>
                          <span className="text-[11px] text-slate-400">{item.desc}</span>
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* ========================================================== */
            /* 评估后的结果展示 */
            /* ========================================================== */
            <AnimatePresence mode="wait">
              <motion.div key={activeNav} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                {activeNav === 'risk' && (
                  <>
                    <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                      <ScoreGauge score={evaluationResult!.score} riskLevel={evaluationResult!.riskLevel} breakdown={evaluationResult!.breakdown} />
                      <AdvisorReport result={evaluationResult!} input={inputs} />
                    </div>
                    <FinancialMetrics result={evaluationResult!} input={inputs} />
                  </>
                )}
                {activeNav === 'banks' && evaluationResult!.bankMatches?.length > 0 && (
                  <BankMatchPanel bankMatches={evaluationResult!.bankMatches} requestedAmount={inputs.requestedAmount} />
                )}
                {activeNav === 'chat' && <ChatPanel />}
                {activeNav === 'network' && <SupplyChainGraph input={inputs} />}
                {activeNav === 'materials' && (
                  <MaterialChecklist materials={evaluationResult!.recommendedMaterials} />
                )}
                {activeNav === 'about' && <InclusiveFinanceSlide />}
              </motion.div>
            </AnimatePresence>
          )}
        </div>
      </main>
    </div>
  );
}
