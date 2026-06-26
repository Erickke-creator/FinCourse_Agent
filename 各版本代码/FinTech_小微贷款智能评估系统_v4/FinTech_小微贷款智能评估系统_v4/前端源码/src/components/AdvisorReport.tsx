/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { EvaluationResult, LoanInput } from '../types';
import { Sparkles, Terminal, ArrowRight, CheckCircle2, AlertTriangle, Lightbulb, HeartHandshake, RefreshCw } from 'lucide-react';

interface AdvisorReportProps {
  result: EvaluationResult;
  input: LoanInput;
}

export default function AdvisorReport({ result, input }: AdvisorReportProps) {
  const [analyzing, setAnalyzing] = useState(false);
  const [stage, setStage] = useState(0);
  const [expandedSection, setExpandedSection] = useState<'score' | 'risk' | 'tips' | 'inclusive'>('score');

  // Trigger evaluation simulation lines when input values reset/recalculate
  useEffect(() => {
    setAnalyzing(true);
    setStage(0);
    const interval = setInterval(() => {
      setStage((prev) => {
        if (prev >= 3) {
          clearInterval(interval);
          setTimeout(() => setAnalyzing(false), 300);
          return 3;
        }
        return prev + 1;
      });
    }, 450);

    return () => clearInterval(interval);
  }, [result.score]);

  const stages = [
    '⚡正在读取商户财务账期、组织形式及往来流水...',
    '📊正在运行多因子授信模型（现金流自偿比、杠杆饱和率、合规检验）...',
    '🧠正在根据中国人民银行普惠信贷指导大纲生成智能纠偏策略...',
    '✨智能决策书输出完成！',
  ];

  // Map user inputs to readable labels
  const getMerchantText = () => {
    switch (input.merchantType) {
      case 'enterprise': return '小微企业';
      case 'individual': return '个体工商户';
      case 'freelancer': return '自由职业独立合伙商办';
    }
  };

  return (
    <div id="ai-advisor-container" className="bg-gradient-to-br from-slate-900 to-indigo-950 text-slate-100 rounded-2xl border border-slate-800 p-6 shadow-xl relative overflow-hidden">
      {/* Decorative neon ambient top-corner glow */}
      <div className="absolute top-0 right-0 w-64 h-64 bg-emerald-500/10 rounded-full blur-3xl -z-10 pointer-events-none" />
      <div className="absolute bottom-0 left-0 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl -z-10 pointer-events-none" />

      {/* Header bar */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800/80 mb-6">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-emerald-500/20 rounded-lg text-emerald-400">
            <Sparkles className="w-5 h-5 animate-pulse" />
          </div>
          <div>
            <h3 className="text-base font-bold tracking-tight text-white flex items-center gap-1.5">
              AI 智能普惠授信顾问报告
            </h3>
            <p className="text-[10px] text-slate-400">
              数据科学引擎驱动 · 商业信贷自评沙盒
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] text-slate-400 px-2 py-1 bg-slate-800/50 rounded border border-slate-700/50">
          <Terminal className="w-3.5 h-3.5" />
          <span>AG_BOT v4.9_ACTIVE</span>
        </div>
      </div>

      <AnimatePresence mode="wait">
        {analyzing ? (
          /* Analyzing transition view */
          <motion.div
            key="analyzing-state"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="py-12 flex flex-col items-center justify-center space-y-4"
          >
            <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
            <div className="space-y-2 text-center max-w-sm">
              <h4 className="text-xs font-bold text-slate-200">正在生成普惠精算报告...</h4>
              <div className="h-1 w-48 bg-slate-800 rounded-full mx-auto overflow-hidden">
                <motion.div 
                  className="h-full bg-emerald-400"
                  initial={{ width: 0 }}
                  animate={{ width: `${(stage + 1) * 25}%` }}
                  transition={{ duration: 0.3 }}
                />
              </div>
              <p className="text-[10px] text-slate-400 font-mono italic h-8 flex items-center justify-center">
                {stages[stage]}
              </p>
            </div>
          </motion.div>
        ) : (
          /* Report Ready State */
          <motion.div
            key="ready-state"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="space-y-6"
          >
            {/* Brief Introduction */}
            <div className="p-4 bg-slate-800/45 rounded-xl border border-slate-800 text-xs text-slate-300 leading-relaxed">
              根据在评估板填入的信息，经营主体为<span className="text-white font-semibold">【{getMerchantText()}】</span>，正常经营年限为<span className="text-white font-semibold">【{input.operatingYears}年】</span>，
              拟向信贷业务端发起一笔数额为<span className="text-emerald-300 font-bold font-mono">{input.requestedAmount / 10000}万</span>元，期望期限<span className="text-white font-semibold">{input.loanTerm}个月</span>的周转借款。
              本智能顾问基于普惠信贷大模型，围绕四项核心问题对您的融资需求进行全面论证精调：
            </div>

            {/* Accordion Tabs */}
            <div className="space-y-3">
              {/* Score genesis */}
              <div className="border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <button
                  onClick={() => setExpandedSection(expandedSection === 'score' ? 'score' : 'score')} // Force open/simple interaction
                  className={`w-full flex items-center justify-between p-4 text-left transition-colors ${expandedSection === 'score' ? 'bg-slate-800/20 text-emerald-400' : 'hover:bg-slate-800/20 text-slate-300'}`}
                >
                  <span className="text-sm font-semibold flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    1. 评分诊断：为什么我获得了这笔评分 ({result.score}分)？
                  </span>
                </button>
                <div className="p-4 bg-slate-950/40 text-xs text-slate-300 space-y-3 border-t border-slate-900 leading-relaxed">
                  <p>
                    您的评测得分是由您填报的财务结构与合规基线加权而来的。
                    {result.score >= 80 ? (
                      <span>您的分数处于绿色低风险优秀区间。这主要得益于两方面因素的强交叉：首先是<strong className="text-emerald-400">资质的高度合规与稳定性</strong>（无逾期黑点，商照完备），其次是<strong className="text-emerald-400">健康的盈余防线</strong>。充足的流水数据与增信抵押作为副担保，使金融机构几乎不需要承受信息不对称风险，授信可行性极高。</span>
                    ) : result.score >= 55 ? (
                      <span>您的分数落在黄色中等信用区间。这反映出借贷整体模型处于临界点，<strong className="text-amber-400 font-semibold">“资质合规性完备，但流动性能动性一般”</strong>。由于经营年限还处在成长初期，或者当前已有杠杆造成了一定摊付压力，月供占去您净现流的相当比例。通过提高财务自律或追加增信能够快速打破中档僵局。</span>
                    ) : (
                      <span>您的评测属于红色风险警示带，直接申贷面临实质难度。主要一票否决项或重大扣分包括<strong className="text-rose-400">【{input.hasOverdueRecord ? '信用逾期记录未被抹平' : '营业现金流出现严重赤字'}】</strong>。小微金融的底层立足于“自偿性证明”，也就是说，如果月度净结余无法涵盖负债刚性还款
                      （您的还款比率为{result.repaymentPressureRatio === 150 ? '超出承载' : `${result.repaymentPressureRatio}%`}），或者商照流水双空白，资信审核端很难得出“业务能够自救”的结论。</span>
                    )}
                  </p>
                  
                  {/* Detailed strengths items list */}
                  <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/40 space-y-2">
                    <div className="font-semibold text-slate-300 text-[10px] uppercase tracking-wider">有利授信交叉诊断点：</div>
                    <ul className="list-disc list-inside space-y-1 text-slate-400 pl-1">
                      {result.strengths.map((item, idx) => (
                        <li key={idx} className="marker:text-emerald-400">{item}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>

              {/* underlying credit risks */}
              <div className="border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <button
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/20 text-slate-300"
                >
                  <span className="text-sm font-semibold flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-rose-400 animate-pulse" />
                    2. 主动排检：当前最大的融资风险与薄弱环节
                  </span>
                </button>
                <div className="p-4 bg-slate-950/40 text-xs text-slate-300 space-y-3 border-t border-slate-900 leading-relaxed">
                  <p>
                    在小微普惠信贷中，银行最关心的核心是所谓的“真实”与“生计”。通过精算法人资产负债表，您目前面临的<strong>软肋瓶颈</strong>主要是：
                  </p>
                  <div className="space-y-2">
                    {result.risks.map((risk, idx) => (
                      <div key={idx} className="flex gap-2 p-2.5 bg-rose-950/20 border border-rose-900/30 rounded-lg text-rose-300">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5 text-rose-400" />
                        <span>{risk}</span>
                      </div>
                    ))}
                  </div>
                  <p className="text-slate-400 italic text-[10px]">
                    ※ 小常识：个体工商户和小微企业不同于大型公司，多数资产与个人财务强绑定，故个人信用卡逾期或夫妻名下坏账将直接穿透影响经营贷款授信。
                  </p>
                </div>
              </div>

              {/* Pathways to approval */}
              <div className="border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <button
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/20 text-slate-300"
                >
                  <span className="text-sm font-semibold flex items-center gap-2">
                    <Lightbulb className="w-4 h-4 text-yellow-400" />
                    3. 精调策略：如何系统性提高后续小微贷款通过率？
                  </span>
                </button>
                <div className="p-4 bg-slate-950/40 text-xs text-slate-300 space-y-3 border-t border-slate-900 leading-relaxed">
                  <p>
                    普惠金融的精神并非“一拒了之”，而是“信用培育”。为了扭转融资劣势，您可以按照以下路径逐步自我纠偏与信用孵化：
                  </p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-1">
                    {result.improvementTips.map((tip, idx) => (
                      <div key={idx} className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1">
                        <span className="text-[10px] uppercase font-bold text-emerald-400 font-mono">纠偏项 0{idx+1}</span>
                        <p className="text-slate-300 leading-relaxed text-xs">{tip}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Inclusive Finance value */}
              <div className="border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <button
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-slate-800/20 text-slate-300"
                >
                  <span className="text-sm font-semibold flex items-center gap-2">
                    <HeartHandshake className="w-4 h-4 text-blue-400" />
                    4. 价值传递：此辅助工具如何践行“普惠金融”初衷？
                  </span>
                </button>
                <div className="p-4 bg-slate-950/40 text-xs text-slate-300 space-y-2 border-t border-slate-900 leading-relaxed">
                  <p>
                    小微民营主体是中国经济繁华的“毛细血管”，但饱受以下痛点折磨：
                  </p>
                  <ul className="space-y-2 pl-1 mt-1 text-slate-300">
                    <li className="flex gap-2">
                      <span className="text-blue-400 font-bold">1. 破除信息“玻璃墙”:</span>
                      <span>传统金融风控逻辑极其晦涩，商户不知为何被拒。本评测将后台风控规则模型转换为直观的分数、清晰的可视流向和解释，免去小微求告无门的求贷困扰，真正实现<strong>“授之以渔”</strong>。</span>
                    </li>
                    <li className="flex gap-2">
                      <span>🌱</span>
                      <span><strong>防范过度授信陷入循环债:</strong> 等额偿息测算和还款红色警告线，引导商户保持敬畏心，在申贷前期合理预测租金周转，控制借用杠杆比例，让数字普惠带有理性的“人文暖意”。</span>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
