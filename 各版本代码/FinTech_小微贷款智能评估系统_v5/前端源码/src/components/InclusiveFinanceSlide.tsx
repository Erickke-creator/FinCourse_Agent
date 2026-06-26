/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BookOpen, Database, TrendingDown, Award, HelpCircle } from 'lucide-react';
import { motion } from 'motion/react';

export default function InclusiveFinanceSlide() {
  const values = [
    {
      title: '🔐 降低小微主体融资信息门槛',
      icon: BookOpen,
      iconColor: 'text-indigo-500 bg-indigo-50',
      tag: '破除玻璃门',
      desc: '传统商业信贷审核多隐藏于银行柜面和内部风控系统中，属于信息非黑盒。本智能评估器将复杂的“精算评分”转换为易懂的反馈机制，用通俗语言指导小微业主“如何补齐资料、规范记账”，赋予弱势主体极度匮乏的基础金融素养知情权。'
    },
    {
      title: '📡 动态数据穿透缓解信息不对称',
      icon: Database,
      iconColor: 'text-emerald-500 bg-emerald-50',
      tag: '量化资信力',
      desc: '普惠信贷的卡点在于商家“无法证明自己真实有盈利”。本助手鼓励商户盘点和归集“商照、纳税、银行电子流水、第三方收银单”，从而将原本模糊的交易“数字化、资产化”。通过数据自证缓解政银企三方不对称，实现精准制信。'
    },
    {
      title: '📈 理性压力测算防范过度借债',
      icon: TrendingDown,
      iconColor: 'text-rose-500 bg-rose-50',
      tag: '防范债务陷阱',
      desc: '小微商户生命周期脆弱，盲目扩张极易导致资金链折戟。助手首创引入“剩余备偿净盈余”与“还款红线压力提示”，在商户提交申贷材料前，就等额本息公式直接算出具体的资金抽走效应。帮助他们科学决策，将债务稳稳锁在安全边际之内。'
    }
  ];

  return (
    <div id="course-presentation-section" className="bg-slate-50 border border-slate-200 rounded-2xl p-6 md:p-8 space-y-6">
      {/* Slide Badge Head */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-slate-200/60 pb-5">
        <div className="space-y-1">
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-blue-50 text-blue-700 text-xs font-semibold rounded-md">
            <Award className="w-3.5 h-3.5 text-blue-600" />
            <span>金融科技课程期末成果展示</span>
          </div>
          <h3 className="text-base font-bold text-slate-900 mt-2">
            🎓 课堂演示：普惠金融的三维底盘价值
          </h3>
          <p className="text-xs text-slate-500">
            本网页展示原型通过“以商户为核心自证”和“数字压力警度”研判，践行数字普惠金融支小支微初心
          </p>
        </div>
        <div className="text-xs font-mono text-slate-400 font-medium h-fit bg-white border border-slate-200 py-1.5 px-3 rounded-md">
          授课教师：金融学 / FinTech 教研组
        </div>
      </div>

      {/* Grid values cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {values.map((val, idx) => {
          const Icon = val.icon;
          return (
            <motion.div
              key={idx}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4 hover:shadow-md transition-all relative overflow-hidden group"
              whileHover={{ y: -3 }}
            >
              {/* Highlight background tag */}
              <div className="absolute top-0 right-0 py-1 px-3 bg-slate-50 text-slate-400 text-[10px] uppercase font-bold rounded-bl-lg font-mono">
                {val.tag}
              </div>

              <div className="flex items-center gap-3">
                <div className={`p-2.5 rounded-lg flex-shrink-0 ${val.iconColor}`}>
                  <Icon className="w-5 h-5" />
                </div>
                <h4 className="text-sm font-bold text-slate-800 leading-snug">
                  {val.title}
                </h4>
              </div>

              <p className="text-xs text-slate-500 leading-relaxed">
                {val.desc}
              </p>
            </motion.div>
          );
        })}
      </div>

      {/* Visual footnotes */}
      <div className="bg-white/60 p-4 rounded-xl border border-slate-150 text-xs text-slate-500 flex flex-col md:flex-row md:items-center justify-between gap-3 leading-relaxed">
        <div className="flex gap-2 items-start md:items-center">
          <HelpCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5 md:mt-0" />
          <span>
            <strong>演示亮点提示：</strong> 您可以点击顶部的<strong>“填入奶茶店案例”</strong>快速初始化数据，并且拖动额度与还款年限，观察系统如何动态实时调整评分星级与建议清单。
          </span>
        </div>
        <span className="font-mono text-[10px] text-slate-400 text-left md:text-right">
          © 基于国家“构建数字普惠金融授信体系”号召设计
        </span>
      </div>
    </div>
  );
}
