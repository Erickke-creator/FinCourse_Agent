/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState, useEffect } from 'react';
import { EvaluationResult } from '../types';
import { CheckSquare, Square, FolderOpen, AlertCircle, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';

interface MaterialChecklistProps {
  materials: EvaluationResult['recommendedMaterials'];
}

export default function MaterialChecklist({ materials }: MaterialChecklistProps) {
  // Store ready documents state to allow classroom interactive click toggles
  const [readyMap, setReadyMap] = useState<Record<string, boolean>>({});

  // Reset readyMap when recommended materials change due to input re-evaluation
  useEffect(() => {
    const initial: Record<string, boolean> = {};
    materials.forEach((mat) => {
      // By default, let's mark standard required materials as false, and some optional ones
      initial[mat.name] = mat.isRequired ? false : false;
    });
    setReadyMap(initial);
  }, [materials]);

  const toggleReady = (name: string) => {
    setReadyMap((prev) => ({
      ...prev,
      [name]: !prev[name],
    }));
  };

  // Calculations
  const totalCount = materials.length;
  const readyCount = Object.values(readyMap).filter(Boolean).length;
  const progressPercent = totalCount > 0 ? Math.round((readyCount / totalCount) * 100) : 0;

  // Grouping
  const grouped = {
    basic: materials.filter((m) => m.category === 'basic'),
    financial: materials.filter((m) => m.category === 'financial'),
    enhancement: materials.filter((m) => m.category === 'enhancement'),
  };

  const categoryLabels = {
    basic: '🏛️ 经营主体基础准入类 (合规基线)',
    financial: '📊 财务自偿流转核实类 (还款证实)',
    enhancement: '🛡️ 增信信用防备兜底类 (分险加权)',
  };

  return (
    <div id="material-checklist-box" className="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-bold text-slate-850 flex items-center gap-2">
            <span>📁 普惠申贷精益材料动态清单</span>
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            系统根据您的经营特征和拟贷数据智能过滤，勾选状态供模拟预排检使用
          </p>
        </div>
        
        {/* Dynamic Ready Progress Ring */}
        <div className="bg-emerald-50 px-4 py-2 rounded-xl border border-emerald-100 flex items-center gap-3 self-start sm:self-center">
          <div className="text-left">
            <div className="text-[10px] text-emerald-600 font-semibold uppercase tracking-wider">
              材料备排排程度
            </div>
            <div className="text-lg font-extrabold text-emerald-800 font-mono">
              {progressPercent}%
            </div>
          </div>
          <div className="h-8 w-px bg-emerald-200" />
          <div className="text-xs text-emerald-700 font-mono">
            已齐: {readyCount} / {totalCount}
          </div>
        </div>
      </div>

      {/* Checklist Sections */}
      <div className="space-y-6">
        {(['basic', 'financial', 'enhancement'] as const).map((cat) => {
          const list = grouped[cat];
          if (list.length === 0) return null;

          return (
            <div key={cat} className="space-y-3">
              <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 border-l-2 border-blue-600 pl-2">
                {categoryLabels[cat]}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {list.map((item, idx) => {
                  const isReady = !!readyMap[item.name];
                  return (
                    <motion.div
                      key={idx}
                      whileHover={{ y: -1 }}
                      onClick={() => toggleReady(item.name)}
                      className={`p-3.5 rounded-xl border cursor-pointer select-none transition-all flex items-start gap-3 ${
                        isReady 
                          ? 'border-emerald-200 bg-emerald-50/20 text-emerald-950 shadow-sm' 
                          : 'border-slate-100 bg-slate-50 text-slate-700 hover:bg-slate-100/55 hover:border-slate-200'
                      }`}
                    >
                      <div className="mt-0.5 flex-shrink-0 text-emerald-600">
                        {isReady ? (
                          <CheckSquare className="w-4.5 h-4.5 fill-emerald-100" />
                        ) : (
                          <Square className="w-4.5 h-4.5 text-slate-300" />
                        )}
                      </div>
                      
                      <div className="space-y-1">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className={`text-xs font-bold ${isReady ? 'text-emerald-950' : 'text-slate-800'}`}>
                            {item.name}
                          </span>
                          {item.isRequired ? (
                            <span className="text-[10px] bg-red-100 text-red-700 px-1.5 py-0.2 rounded font-semibold">
                              前置强制
                            </span>
                          ) : (
                            <span className="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.2 rounded font-semibold">
                              审优加分
                            </span>
                          )}
                        </div>
                        <p className="text-[11px] text-slate-400 leading-normal">
                          {item.description}
                        </p>
                      </div>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Guidance bottom card */}
      <div className="flex items-center gap-2.5 p-3.5 bg-slate-50 border border-slate-100 rounded-xl text-xs text-slate-500">
        <AlertCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
        <span>
          <strong>💡 现场备审建议：</strong>在真实的银企对接中，前两类证明文件直接通过会决定是否进入额度精测，最后一类则能决定银行最终给您的审批利率能否贴近政策底线。
        </span>
      </div>
    </div>
  );
}
