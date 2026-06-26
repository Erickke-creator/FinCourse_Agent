/**
 * 银行匹配面板 — 小程序核心差异化功能
 * 展示：通过概率排名、银行对比雷达图、产品详情
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { BankMatchResult } from '../types';
import BankRadarChart from './BankRadarChart';
import {
  Building2,
  TrendingUp,
  Percent,
  Coins,
  Shield,
  ChevronDown,
  ChevronUp,
  Trophy,
  Target,
  AlertTriangle,
  Sparkles,
  ArrowRight,
} from 'lucide-react';

interface BankMatchPanelProps {
  bankMatches: BankMatchResult[];
  requestedAmount: number;
}

export default function BankMatchPanel({ bankMatches, requestedAmount }: BankMatchPanelProps) {
  const [expandedBankId, setExpandedBankId] = useState<string | null>(null);
  const [showAllBanks, setShowAllBanks] = useState(false);

  const top5 = bankMatches.slice(0, 5);
  const top1 = bankMatches[0];
  const displayedBanks = showAllBanks ? bankMatches : bankMatches.slice(0, 8);

  // 银行类型颜色
  const getBankTypeColor = (type: string) => {
    if (type.includes('国有')) return 'bg-red-100 text-red-700 border-red-200';
    if (type.includes('股份')) return 'bg-blue-100 text-blue-700 border-blue-200';
    if (type.includes('互联网')) return 'bg-purple-100 text-purple-700 border-purple-200';
    if (type.includes('城市')) return 'bg-teal-100 text-teal-700 border-teal-200';
    if (type.includes('外资')) return 'bg-orange-100 text-orange-700 border-orange-200';
    return 'bg-slate-100 text-slate-700 border-slate-200';
  };

  const getProbColor = (prob: number) => {
    if (prob >= 0.6) return 'text-emerald-600';
    if (prob >= 0.3) return 'text-amber-600';
    return 'text-rose-600';
  };

  const getProbBg = (prob: number) => {
    if (prob >= 0.6) return 'bg-emerald-50 border-emerald-200';
    if (prob >= 0.3) return 'bg-amber-50 border-amber-200';
    return 'bg-rose-50 border-rose-200';
  };

  const formatCNY = (v: number) =>
    new Intl.NumberFormat('zh-CN', { style: 'currency', currency: 'CNY', maximumFractionDigits: 0 }).format(v * 10000);

  return (
    <div id="bank-match-panel" className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-6">
      {/* 标题栏 */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-sm font-bold text-slate-850 flex items-center gap-2">
            <Building2 className="w-4 h-4 text-blue-600" />
            🏦 银行智能匹配 — 您的贷款通过概率预测
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            基于15家主流银行的产品偏好与风控模型，精准预测您在每家银行的审批通过概率
          </p>
        </div>
        {top1 && (
          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-amber-50 to-yellow-50 border border-amber-200 rounded-lg">
            <Trophy className="w-4 h-4 text-amber-500" />
            <span className="text-xs font-semibold text-amber-700">
              最佳匹配: <span className="text-amber-900">{top1.bankName}</span>
            </span>
          </div>
        )}
      </div>

      {/* TOP 3 快速卡片 */}
      {top1 && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {bankMatches.slice(0, 3).map((bank, idx) => (
            <motion.div
              key={bank.bankId}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
              className={`relative rounded-xl border-2 p-4 ${
                idx === 0
                  ? 'border-amber-400 bg-gradient-to-br from-amber-50/50 to-yellow-50/30 shadow-md'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              {idx === 0 && (
                <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-amber-400 text-white text-[10px] font-bold rounded-full shadow">
                  🥇 最佳
                </div>
              )}
              {idx === 1 && (
                <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-slate-300 text-slate-600 text-[10px] font-bold rounded-full">
                  🥈
                </div>
              )}
              {idx === 2 && (
                <div className="absolute -top-2 -right-2 px-2 py-0.5 bg-orange-300 text-orange-700 text-[10px] font-bold rounded-full">
                  🥉
                </div>
              )}

              <div className="flex items-center gap-2 mb-2">
                <span className={`text-[10px] px-1.5 py-0.5 rounded border font-medium ${getBankTypeColor(bank.bankType)}`}>
                  {bank.bankType}
                </span>
              </div>
              <div className="text-sm font-bold text-slate-900">{bank.bankName}</div>
              <div className="text-[10px] text-slate-500 mt-0.5">{bank.productName}</div>

              <div className="mt-3 flex items-baseline gap-1">
                <span className={`text-2xl font-black ${getProbColor(bank.approvalProbability)}`}>
                  {(bank.approvalProbability * 100).toFixed(0)}%
                </span>
                <span className="text-xs text-slate-400">通过率</span>
              </div>

              <div className="mt-2 flex items-center gap-3 text-[10px] text-slate-500">
                <span className="flex items-center gap-1">
                  <Percent className="w-3 h-3" />
                  {bank.estimatedInterestRate}%
                </span>
                <span className="flex items-center gap-1">
                  <Coins className="w-3 h-3" />
                  {bank.estimatedMaxAmount}万
                </span>
              </div>
            </motion.div>
          ))}
        </div>
      )}

      {/* 雷达图 + 银行列表 */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* 左侧：雷达图 */}
        <div className="lg:col-span-2">
          <BankRadarChart bankMatches={top5} requestedAmount={requestedAmount} />
        </div>

        {/* 右侧：银行排序列表 */}
        <div className="lg:col-span-3 space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              📋 全部银行通过概率排名
            </h4>
            <span className="text-[10px] text-slate-400">共 {bankMatches.length} 家银行</span>
          </div>

          <div className="space-y-2 max-h-[420px] overflow-y-auto pr-1">
            {displayedBanks.map((bank, idx) => {
              const isExpanded = expandedBankId === bank.bankId;
              const probBar = bank.approvalProbability * 100;

              return (
                <motion.div
                  key={bank.bankId}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.03 }}
                  className={`border rounded-xl transition-all ${
                    isExpanded
                      ? 'border-blue-300 bg-blue-50/30 shadow-sm'
                      : 'border-slate-100 bg-white hover:border-slate-200 hover:bg-slate-50/50'
                  }`}
                >
                  {/* 摘要行 */}
                  <div
                    className="flex items-center gap-3 p-3 cursor-pointer"
                    onClick={() => setExpandedBankId(isExpanded ? null : bank.bankId)}
                  >
                    {/* 排名 */}
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold ${
                      idx < 3 ? 'bg-amber-100 text-amber-700' : 'bg-slate-100 text-slate-500'
                    }`}>
                      {idx + 1}
                    </div>

                    {/* 银行名称和产品 */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-slate-800">{bank.bankName}</span>
                        <span className={`text-[9px] px-1 py-0.5 rounded ${getBankTypeColor(bank.bankType)}`}>
                          {bank.bankType}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400 truncate">{bank.productName}</div>
                    </div>

                    {/* 通过概率进度条 */}
                    <div className="hidden sm:flex items-center gap-2 min-w-[120px]">
                      <div className="w-16 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                        <motion.div
                          className={`h-full rounded-full ${probBar >= 60 ? 'bg-emerald-500' : probBar >= 30 ? 'bg-amber-400' : 'bg-rose-400'}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${probBar}%` }}
                          transition={{ duration: 1, delay: 0.2 }}
                        />
                      </div>
                      <span className={`text-xs font-bold ${getProbColor(bank.approvalProbability)}`}>
                        {probBar.toFixed(0)}%
                      </span>
                    </div>

                    {/* 利率和额度 */}
                    <div className="hidden md:flex items-center gap-3 text-[10px] text-slate-500 min-w-[120px] justify-end">
                      <span>{bank.estimatedInterestRate}%</span>
                      <span className="font-mono">{bank.estimatedMaxAmount}万</span>
                    </div>

                    {/* 匹配分 */}
                    <div className={`hidden sm:flex items-center justify-center w-9 h-9 rounded-lg text-xs font-bold ${
                      bank.matchScore >= 70 ? 'bg-emerald-100 text-emerald-700' :
                      bank.matchScore >= 40 ? 'bg-amber-100 text-amber-700' :
                      'bg-slate-100 text-slate-500'
                    }`}>
                      {bank.matchScore}
                    </div>

                    {isExpanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
                  </div>

                  {/* 展开详情 */}
                  <AnimatePresence>
                    {isExpanded && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <div className="px-4 pb-4 space-y-3 border-t border-slate-100 pt-3">
                          {/* 推荐理由 */}
                          {bank.recommendationReasons.length > 0 && (
                            <div className="space-y-1">
                              <span className="text-[10px] font-semibold text-emerald-600 flex items-center gap-1">
                                <Sparkles className="w-3 h-3" /> 推荐理由
                              </span>
                              {bank.recommendationReasons.map((r, i) => (
                                <div key={i} className="text-xs text-slate-600 flex items-start gap-1.5">
                                  <ArrowRight className="w-3 h-3 text-emerald-400 mt-0.5 flex-shrink-0" />
                                  <span>{r}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* 风险提示 */}
                          {bank.riskFactors.length > 0 && (
                            <div className="space-y-1">
                              <span className="text-[10px] font-semibold text-rose-600 flex items-center gap-1">
                                <AlertTriangle className="w-3 h-3" /> 风险提示
                              </span>
                              {bank.riskFactors.map((r, i) => (
                                <div key={i} className="text-xs text-rose-600 flex items-start gap-1.5">
                                  <span className="text-rose-400">•</span>
                                  <span>{r}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* 产品详情 */}
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[10px]">
                            <div className="bg-slate-50 p-2 rounded">
                              <span className="text-slate-400">贷款类型</span>
                              <div className="font-semibold text-slate-700">{bank.loanType}</div>
                            </div>
                            <div className="bg-slate-50 p-2 rounded">
                              <span className="text-slate-400">最长年限</span>
                              <div className="font-semibold text-slate-700">{bank.maxTermYears}年</div>
                            </div>
                            <div className="bg-slate-50 p-2 rounded">
                              <span className="text-slate-400">综合匹配</span>
                              <div className="font-semibold text-slate-700">{bank.matchScore}/100</div>
                            </div>
                            <div className="bg-slate-50 p-2 rounded">
                              <span className="text-slate-400">利率范围</span>
                              <div className="font-semibold text-slate-700">{bank.estimatedInterestRate}%</div>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>

          {/* 展开全部 */}
          {bankMatches.length > 8 && (
            <button
              onClick={() => setShowAllBanks(!showAllBanks)}
              className="w-full py-2 text-xs text-blue-600 hover:text-blue-700 font-medium flex items-center justify-center gap-1"
            >
              {showAllBanks ? '收起' : `查看全部 ${bankMatches.length} 家银行`}
              {showAllBanks ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          )}
        </div>
      </div>

      {/* 底部建议 */}
      <div className="flex items-center gap-2.5 p-3.5 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl text-xs text-slate-600">
        <Target className="w-4 h-4 text-blue-500 flex-shrink-0" />
        <span>
          <strong>💡 策略建议：</strong>
          建议同时向通过概率最高的<strong>2-3家银行</strong>提交申请，提高整体获批概率。
          国有大行利率更低但审批更严，股份行灵活度更高，互联网银行更适合无抵押的线上经营者。
          关注当地财政贴息政策，部分行业首年利率可降至"1字头"。
        </span>
      </div>
    </div>
  );
}
