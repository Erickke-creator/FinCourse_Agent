/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { motion } from 'motion/react';
import { RiskLevel, ScoreBreakdown } from '../types';
import { ShieldCheck, ShieldAlert, Shield } from 'lucide-react';

interface ScoreGaugeProps {
  score: number;
  riskLevel: RiskLevel;
  breakdown: ScoreBreakdown;
}

export default function ScoreGauge({ score, riskLevel, breakdown }: ScoreGaugeProps) {
  // Helper to coordinate colors
  const getColorScheme = (level: RiskLevel) => {
    switch (level) {
      case 'low':
        return {
          textColor: 'text-emerald-600 dark:text-emerald-400',
          bgColor: 'bg-emerald-50 dark:bg-emerald-950/30',
          borderColor: 'border-emerald-200 dark:border-emerald-800',
          accentColor: '#10b981', // emerald-500
          label: '低风险 (信用极佳)',
          desc: '各项经营与财务指标良好，流动性充足，违约概率极低。推荐匹配低利息政策性包容贷款。',
          icon: ShieldCheck,
        };
      case 'medium':
        return {
          textColor: 'text-amber-600 dark:text-amber-400',
          bgColor: 'bg-amber-50 dark:bg-amber-950/30',
          borderColor: 'border-amber-200 dark:border-amber-800',
          accentColor: '#f59e0b', // amber-500
          label: '中等风险 (信用良好)',
          desc: '基本资质完备，但可能存在轻微杠杆压力或经营流水不饱满。需根据银行建议缩减额度或拉长周期。',
          icon: Shield,
        };
      case 'high':
        return {
          textColor: 'text-rose-600 dark:text-rose-400',
          bgColor: 'bg-rose-50 dark:bg-rose-950/30',
          borderColor: 'border-rose-200 dark:border-rose-800',
          accentColor: '#f43f5e', // rose-500
          label: '高风险 (建议改善)',
          desc: '存在历史逾期或严重现金流倒挂，或者缺乏基础工商照资质。属于风控严格审视区间，当前直接申贷通过率较低。',
          icon: ShieldAlert,
        };
    }
  };

  const scheme = getColorScheme(riskLevel);
  const Icon = scheme.icon;

  // Circular gauge config
  const radius = 80;
  const strokeWidth = 14;
  const circumference = 2 * Math.PI * radius;
  // Arc calculation for gauge: 3/4 semi-circle
  const strokeDashoffset = circumference - (score / 100) * circumference;

  // Map breakdown metrics for display
  const breakdownItems = [
    { label: '主体资质与经营实力', value: breakdown.operatingStrength, max: 20 },
    { label: '还款现金流保障能力', value: breakdown.cashFlowCoverage, max: 20 },
    { label: '征信守规合力表现', value: breakdown.creditCompliance, max: 20 },
    { label: '往来流水与增信措施', value: breakdown.creditEnhancement, max: 20 },
    { label: '已有杠杆负债压力', value: breakdown.leverageRisk, max: 20 },
  ];

  return (
    <div id="credit-score-section" className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm flex flex-col items-center">
      <div className="w-full flex items-center justify-between mb-6">
        <h3 className="text-sm font-bold text-slate-850 flex items-center gap-2">
          <span>🎯 综合贷款风险评估评分</span>
        </h3>
        <span className="text-xs text-slate-400 font-mono">ID: SEC_CRED_2026</span>
      </div>

      {/* SVG Animated Arc Gauge */}
      <div className="relative flex items-center justify-center w-56 h-56">
        <svg className="w-full h-full transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="112"
            cy="112"
            r={radius}
            className="stroke-slate-100 fill-none"
            strokeWidth={strokeWidth}
          />
          {/* Active arc gradient indicator */}
          <motion.circle
            cx="112"
            cy="112"
            r={radius}
            className="fill-none"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset }}
            transition={{ duration: 1.5, ease: 'easeOut' }}
            stroke={scheme.accentColor}
            strokeLinecap="round"
          />
        </svg>

        {/* Info inside the circle */}
        <div className="absolute flex flex-col items-center justify-center text-center">
          <motion.span 
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.6 }}
            className="text-5xl font-black tracking-tight text-slate-900"
          >
            {score}
          </motion.span>
          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-bold mt-1">信用评分</span>
          <div className={`mt-2.5 flex items-center gap-1 py-1 px-3 rounded-full text-xs font-semibold border ${scheme.textColor} ${scheme.bgColor} ${scheme.borderColor}`}>
            <Icon className="w-3.5 h-3.5" />
            <span>{scheme.label}</span>
          </div>
        </div>
      </div>

      {/* Narrative block */}
      <p className="text-xs text-slate-500 text-center px-4 max-w-sm mt-2 leading-relaxed">
        {scheme.desc}
      </p>

      {/* Score breakdown bar charts */}
      <div className="w-full mt-6 space-y-3.5 border-t border-slate-100 pt-5">
        <h4 className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2">五维穿透度量分析</h4>
        {breakdownItems.map((item, idx) => {
          const ratio = (item.value / item.max) * 100;
          return (
            <div key={idx} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-600 font-medium">{item.label}</span>
                <span className="text-slate-500 font-semibold font-mono">{item.value} / {item.max}分</span>
              </div>
              <div className="w-full h-1.5 bg-slate-100 rounded-full overflow-hidden font-mono">
                <motion.div
                  className="h-full rounded-full"
                  style={{ backgroundColor: scheme.accentColor }}
                  initial={{ width: 0 }}
                  animate={{ width: `${ratio}%` }}
                  transition={{ duration: 1, delay: idx * 0.1 }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
