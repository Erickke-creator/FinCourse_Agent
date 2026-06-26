/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { motion } from 'motion/react';
import { EvaluationResult, LoanInput } from '../types';
import { Landmark, TrendingUp, AlertCircle, Percent, Receipt, Calendar, AlertTriangle, ShieldCheck } from 'lucide-react';

interface FinancialMetricsProps {
  result: EvaluationResult;
  input: LoanInput;
}

export default function FinancialMetrics({ result, input }: FinancialMetricsProps) {
  const {
    suggestedAmount,
    suggestedTerm,
    monthlyRepayment,
    totalInterest,
    netMonthlyCashFlow,
    repaymentPressureRatio,
    dtiRatio
  } = result;

  // Formatting currency
  const formatCNY = (value: number) => {
    return new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 0 }).format(value);
  };

  // Stress indicator style & levels
  const getPressureConfig = (ratio: number) => {
    if (netMonthlyCashFlow <= 0) {
      return {
        level: '严重失容 (净流为负)',
        color: 'text-red-500 bg-red-50 border-red-200',
        barColor: 'bg-red-500',
        icon: AlertTriangle,
        desc: '当前经营已严重资不抵债，无法覆盖拟贷款。不建议在此财务状态下举借新债。',
      };
    }
    if (ratio > 50) {
      return {
        level: '极高风险 (过度负债)',
        color: 'text-red-500 bg-red-50 border-red-200',
        barColor: 'bg-red-500',
        icon: AlertTriangle,
        desc: '超过一半的净收入需要用来偿还本息，抵御突发经营波动的能力极其脆弱。',
      };
    }
    if (ratio > 35) {
      return {
        level: '偏高风险 (安全偏紧)',
        color: 'text-amber-500 bg-amber-50 border-amber-200',
        barColor: 'bg-amber-500',
        icon: AlertCircle,
        desc: '月还款额占净收入的35%-50%之间。建议拉长期限或减少申贷本金以缓解还款重负。',
      };
    }
    return {
      level: '低风险 (合理边际)',
      color: 'text-emerald-500 bg-emerald-50 border-emerald-200',
      barColor: 'bg-emerald-500',
      icon: ShieldCheck,
      desc: '月供额度完全在经营承受范围。借贷风险属于安全系数较高的理性授信区间。',
    };
  };

  const pressure = getPressureConfig(repaymentPressureRatio);
  const PressureIcon = pressure.icon;

  // Let's create a beautiful custom bar comparing cash flow metrics
  const maxBarValue = Math.max(input.monthlyRevenue, input.monthlyFixedCost, input.existingLiabilities, netMonthlyCashFlow);
  const getPercentageWidth = (value: number) => {
    return `${Math.max(3, (value / maxBarValue) * 100)}%`;
  };

  return (
    <div id="financial-analysis-dashboard" className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-bold text-slate-850 flex items-center gap-2">
          <span>📊 融资授信与还款压力测算</span>
        </h3>
        <span className="text-xs font-semibold px-2 py-1 bg-blue-50 text-blue-600 rounded">
          等额本息 (EMI)
        </span>
      </div>

      {/* Grid of four main financial data cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Suggested loan size */}
        <div className="border border-slate-100 bg-slate-50/50 rounded-xl p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-emerald-500/20 group-hover:scale-110 transition-transform">
            <Landmark className="w-16 h-16 stroke-1" />
          </div>
          <div className="text-xs text-slate-500 font-semibold">建议融资金额</div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold font-mono text-emerald-600">
              {formatCNY(suggestedAmount)}
            </span>
            <span className="text-xs text-slate-400">元</span>
          </div>
          <div className="text-xs text-slate-400 mt-2 flex items-center gap-1">
            <span>申请首选:</span>
            <span className="font-mono text-slate-500">{formatCNY(input.requestedAmount)}</span>
            {suggestedAmount < input.requestedAmount && (
              <span className="text-rose-500 ml-1 font-semibold">(缩减审定)</span>
            )}
          </div>
        </div>

        {/* Suggested Term */}
        <div className="border border-slate-100 bg-slate-50/50 rounded-xl p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-indigo-500/20 group-hover:scale-110 transition-transform">
            <Calendar className="w-16 h-16 stroke-1" />
          </div>
          <div className="text-xs text-slate-500 font-semibold">建议还款期限</div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold font-mono text-cyan-600">
              {suggestedTerm}
            </span>
            <span className="text-xs text-slate-400">个月</span>
          </div>
          <div className="text-xs text-slate-400 mt-2">
            <span>申请首选: {input.loanTerm} 个月 </span>
            {suggestedTerm > input.loanTerm && (
              <span className="text-blue-500 font-medium ml-1">(展期降压建议)</span>
            )}
          </div>
        </div>

        {/* Monthly Installment (EMI) */}
        <div className="border border-slate-100 bg-slate-50/50 rounded-xl p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-orange-500/20 group-hover:scale-110 transition-transform">
            <Receipt className="w-16 h-16 stroke-1" />
          </div>
          <div className="text-xs text-slate-500 font-semibold">预测月供还款额</div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold font-mono text-slate-850">
              {formatCNY(monthlyRepayment)}
            </span>
            <span className="text-xs text-slate-400">元/月</span>
          </div>
          <div className="text-xs text-slate-400 mt-2">
            按固定年利率 <span className="font-mono font-medium text-slate-500">{input.annualRate}%</span> 等额偿算
          </div>
        </div>

        {/* Total Interest Cost */}
        <div className="border border-slate-100 bg-slate-50/50 rounded-xl p-4 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-3 text-slate-500/20 group-hover:scale-110 transition-transform">
            <Percent className="w-16 h-16 stroke-1" />
          </div>
          <div className="text-xs text-slate-500 font-semibold">融资总利息支出</div>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-2xl font-bold font-mono text-slate-705">
              {formatCNY(totalInterest)}
            </span>
            <span className="text-xs text-slate-400">元</span>
          </div>
          <div className="text-xs text-slate-400 mt-2">
            息费占比借款总数的 <span className="font-mono text-slate-500">{((totalInterest / suggestedAmount) * 100).toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Repayment Pressure & DTI Alert Module */}
      <div className={`border p-4 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${pressure.color}`}>
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <PressureIcon className="w-5 h-5 flex-shrink-0" />
            <h4 className="font-bold text-sm">授信还款压力水平：{pressure.level}</h4>
          </div>
          <p className="text-xs text-slate-650 leading-relaxed max-w-xl">
            {pressure.desc}
          </p>
        </div>
        <div className="text-right flex-shrink-0 md:bg-white/50 md:px-5 md:py-3 md:rounded-lg md:border md:border-current/10 min-w-[150px]">
          <div className="text-[10px] text-slate-400 uppercase tracking-widest leading-none font-bold">
            月供 / 月净现金
          </div>
          <div className="text-2xl font-black font-mono mt-0.5">
            {repaymentPressureRatio === 150 ? '溢出' : `${repaymentPressureRatio}%`}
          </div>
          <p className="text-[10px] text-slate-400 leading-none">
            安全水位上限为 40%
          </p>
        </div>
      </div>

      {/* Cash Flow Visual Stack (Comparing income/fixed cost/debt/loan emi) */}
      <div className="space-y-4 pt-4 border-t border-slate-150">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">📜 营业现金流水流向穿透图</h4>
        <div className="space-y-3.5">
          {/* Revenue */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span className="font-medium text-slate-700 flex items-center gap-1">🟢 经营总收入 (Revenue)</span>
              <span className="font-mono font-bold text-slate-900">{formatCNY(input.monthlyRevenue)}</span>
            </div>
            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-emerald-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: getPercentageWidth(input.monthlyRevenue) }}
                transition={{ duration: 1 }}
              />
            </div>
          </div>

          {/* Fixed cost */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span className="font-medium text-slate-700 flex items-center gap-1">🔴 经营固定成本 (Fixed Cost)</span>
              <span className="font-mono font-semibold text-slate-800">-{formatCNY(input.monthlyFixedCost)}</span>
            </div>
            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden font-mono">
              <motion.div
                className="h-full bg-orange-400 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: getPercentageWidth(input.monthlyFixedCost) }}
                transition={{ duration: 1 }}
              />
            </div>
          </div>

          {/* Existing Liabilities */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span className="font-medium text-slate-700 flex items-center gap-1">🟡 已有债务偿还 (Liabilities)</span>
              <span className="font-mono font-semibold text-slate-800">-{formatCNY(input.existingLiabilities)}</span>
            </div>
            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-amber-400 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: getPercentageWidth(input.existingLiabilities) }}
                transition={{ duration: 1 }}
              />
            </div>
          </div>

          {/* New EMI Proposed */}
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-slate-500">
              <span className="font-medium text-slate-700 flex items-center gap-1">🔵 拟新增申贷月供 (New Loan payment)</span>
              <span className="font-mono font-black text-blue-600">-{formatCNY(monthlyRepayment)}</span>
            </div>
            <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
              <motion.div
                className="h-full bg-blue-500 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: getPercentageWidth(monthlyRepayment) }}
                transition={{ duration: 1 }}
              />
            </div>
          </div>

          {/* Bottom Net Margin Summary */}
          <div className="flex justify-between items-center text-xs p-3 bg-slate-50 rounded-lg mt-2">
            <span className="font-medium text-slate-650">剩余备偿经营净盈余 (Net Remaining Free Cash Flow):</span>
            <span className={`font-mono font-extrabold text-sm ${netMonthlyCashFlow - monthlyRepayment > 0 ? 'text-emerald-600' : 'text-rose-500'}`}>
              {formatCNY(netMonthlyCashFlow - monthlyRepayment)} / 月
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
