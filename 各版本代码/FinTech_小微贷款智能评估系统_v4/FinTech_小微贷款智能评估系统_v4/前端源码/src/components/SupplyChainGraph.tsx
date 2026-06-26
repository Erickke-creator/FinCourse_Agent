/**
 * 企业供应链关系网络图 — 风险热力版
 * 用绿→黄→橙→红色谱标识上下游交易集中度风险
 * 高依赖节点 + 红色连线 = 需要关注的信贷风险点
 */

import { useEffect, useRef, useMemo } from 'react';
import * as echarts from 'echarts/core';
import { GraphChart } from 'echarts/charts';
import { TooltipComponent, LegendComponent } from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import type { LoanInput } from '../types';
import { INDUSTRY_LABELS } from '../types';
import { AlertTriangle, Shield, TrendingUp, ChevronDown } from 'lucide-react';

echarts.use([GraphChart, TooltipComponent, LegendComponent, CanvasRenderer]);

interface SupplyChainGraphProps {
  input: LoanInput;
}

// ============================================================
// 风险等级定义
// ============================================================
type RiskLevel = 'safe' | 'moderate' | 'high' | 'critical';

const RISK_CONFIG: Record<RiskLevel, {
  label: string; color: string; bg: string; border: string;
  threshold: number; icon: string; desc: string;
}> = {
  safe:     { label: '分散安全', color: '#10b981', bg: '#ecfdf5', border: '#6ee7b7', threshold: 0.15, icon: '🟢', desc: '占比<15%，风险极低' },
  moderate: { label: '适度关注', color: '#eab308', bg: '#fefce8', border: '#fde047', threshold: 0.25, icon: '🟡', desc: '占比15-25%，需留意' },
  high:     { label: '高度依赖', color: '#f97316', bg: '#fff7ed', border: '#fdba74', threshold: 0.40, icon: '🟠', desc: '占比25-40%，集中风险' },
  critical: { label: '极度集中', color: '#ef4444', bg: '#fef2f2', border: '#fca5a5', threshold: 1.00, icon: '🔴', desc: '占比>40%，严重依赖!' },
};

function getRiskLevel(share: number): RiskLevel {
  if (share < 0.15) return 'safe';
  if (share < 0.25) return 'moderate';
  if (share < 0.40) return 'high';
  return 'critical';
}

// ============================================================
// 供应商/客户名称池
// ============================================================
const SUPPLIER_NAMES = [
  '鑫达原材料', '华东物流', '恒通包装', '博源电子', '瑞丰配件',
  '长信化工', '中联仓储', '明泰五金', '正大食品', '德力机械',
  '金盛纺织', '天宇科技', '丰源商贸', '华美印务', '力恒建材',
];

const CUSTOMER_NAMES = [
  '永辉超市', '海澜之家', '三只松鼠', '百果园', '名创优品',
  '良品铺子', '苏宁易购', '沃尔玛', '全家便利店', '美团优选',
  '盒马鲜生', '京东自营', '大润发', '屈臣氏', '泡泡玛特',
  '周大福', '来伊份', '宜家家居', '迪卡侬', '无印良品',
];

// ============================================================
// 根据企业画像生成带风险标注的供应链
// ============================================================
interface ChainNode {
  id: string;
  name: string;
  category: number;    // 0=核心 1=供应商 2=普通客户 3=电商客户
  symbolSize: number;
  value: number;        // 交易金额(万元/月)
  share: number;        // 占总采购/销售的比例
  riskLevel: RiskLevel;
}

interface ChainLink {
  source: string;
  target: string;
  value: number;
  share: number;
  riskLevel: RiskLevel;
}

function generateRiskChain(input: LoanInput) {
  const monthlyRevenueWan = input.monthlyRevenue / 10000;
  const supplierCount = Math.max(3, Math.min(8, Math.floor(monthlyRevenueWan / 5) + 2));
  const customerCount = Math.max(4, Math.min(12, Math.floor(monthlyRevenueWan / 3) + 3));
  const totalSupply = monthlyRevenueWan * 0.65;
  const totalSales = monthlyRevenueWan;

  // 核心企业
  const centerNode: ChainNode = {
    id: 'center', name: '本方企业', category: 0,
    symbolSize: Math.max(45, Math.min(80, 35 + monthlyRevenueWan / 4)),
    value: monthlyRevenueWan, share: 1.0, riskLevel: 'safe',
  };

  // 生成供应商（故意制造1-2个高占比的来体现风险）
  const shuffledSup = [...SUPPLIER_NAMES].sort(() => Math.random() - 0.5);
  const suppliers: ChainNode[] = [];
  const supplyLinks: ChainLink[] = [];

  // 生成不均匀份额，让1-2个供应商占比较高
  const supShares: number[] = [];
  let remainingSup = 1.0;
  for (let i = 0; i < supplierCount; i++) {
    if (i === supplierCount - 1) {
      supShares.push(Number(remainingSup.toFixed(3)));
    } else {
      // 前面的份额随机但不均匀
      const maxShare = remainingSup * (i === 0 ? 0.45 : 0.5);
      const minShare = remainingSup * 0.08;
      const share = Number((minShare + Math.random() * (maxShare - minShare)).toFixed(3));
      supShares.push(share);
      remainingSup -= share;
    }
  }
  // 随机打乱使高份额不总在第一个
  supShares.sort(() => Math.random() - 0.5);

  for (let i = 0; i < supplierCount; i++) {
    const amount = Math.round(totalSupply * supShares[i] * 10) / 10;
    const risk = getRiskLevel(supShares[i]);
    suppliers.push({
      id: `supplier_${i}`, name: shuffledSup[i], category: 1,
      symbolSize: Math.max(16, Math.min(50, 14 + (amount / totalSupply) * 60)),
      value: amount, share: supShares[i], riskLevel: risk,
    });
    supplyLinks.push({
      source: `supplier_${i}`, target: 'center',
      value: amount, share: supShares[i], riskLevel: risk,
    });
  }

  // 生成客户（同样制造不均匀）
  const shuffledCust = [...CUSTOMER_NAMES].sort(() => Math.random() - 0.5);
  const customers: ChainNode[] = [];
  const saleLinks: ChainLink[] = [];

  const custShares: number[] = [];
  let remainingCust = 1.0;
  for (let i = 0; i < customerCount; i++) {
    if (i === customerCount - 1) {
      custShares.push(Number(remainingCust.toFixed(3)));
    } else {
      const maxShare = remainingCust * (i === 0 ? 0.40 : 0.5);
      const minShare = remainingCust * 0.06;
      const share = Number((minShare + Math.random() * (maxShare - minShare)).toFixed(3));
      custShares.push(share);
      remainingCust -= share;
    }
  }
  custShares.sort(() => Math.random() - 0.5);

  for (let i = 0; i < customerCount; i++) {
    const amount = Math.round(totalSales * custShares[i] * 10) / 10;
    const isEcommerce = shuffledCust[i].includes('京东') || shuffledCust[i].includes('美团') ||
      shuffledCust[i].includes('苏宁') || shuffledCust[i].includes('盒马');
    const risk = getRiskLevel(custShares[i]);
    customers.push({
      id: `customer_${i}`, name: shuffledCust[i],
      category: isEcommerce ? 3 : 2,
      symbolSize: Math.max(16, Math.min(52, 14 + (amount / totalSales) * 60)),
      value: amount, share: custShares[i], riskLevel: risk,
    });
    saleLinks.push({
      source: 'center', target: `customer_${i}`,
      value: amount, share: custShares[i], riskLevel: risk,
    });
  }

  return {
    nodes: [centerNode, ...suppliers, ...customers],
    links: [...supplyLinks, ...saleLinks],
    stats: {
      supplierCount, customerCount,
      totalSupply: Math.round(totalSupply),
      totalSales: Math.round(totalSales),
      highRiskSuppliers: suppliers.filter(s => s.riskLevel === 'critical' || s.riskLevel === 'high'),
      highRiskCustomers: customers.filter(c => c.riskLevel === 'critical' || c.riskLevel === 'high'),
    },
  };
}

// ============================================================
// 组件
// ============================================================
export default function SupplyChainGraph({ input }: SupplyChainGraphProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const { nodes, links, stats } = useMemo(() => generateRiskChain(input), [input]);

  useEffect(() => {
    if (!chartRef.current) return;
    if (!chartInstance.current) chartInstance.current = echarts.init(chartRef.current);

    const categories = [
      { name: '核心企业', itemStyle: { color: '#3b82f6' }, symbol: 'roundRect' },
      { name: '上游供应商', itemStyle: { color: '#94a3b8' }, symbol: 'circle' },
      { name: '下游客户', itemStyle: { color: '#94a3b8' }, symbol: 'circle' },
      { name: '电商平台', itemStyle: { color: '#94a3b8' }, symbol: 'diamond' },
    ];

    const option: echarts.EChartsCoreOption = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.97)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#334155', fontSize: 12 },
        formatter: (params: any) => {
          if (params.dataType === 'edge') {
            const riskCfg = RISK_CONFIG[params.data.riskLevel || 'safe'];
            return `<div style="font-weight:700;font-size:13px;margin-bottom:4px;">${params.data.source} → ${params.data.target}</div>
              <div style="line-height:1.8;font-size:11px;">
                交易金额：<b>${params.data.value?.toFixed(1)}万元/月</b><br/>
                占比：<b>${(params.data.share * 100).toFixed(1)}%</b><br/>
                风险：<span style="color:${riskCfg.color};font-weight:700;">${riskCfg.icon} ${riskCfg.label}</span>
              </div>`;
          }
          const d = params.data;
          if (d.category === 0) {
            return `<b style="font-size:14px;">${d.name}</b><br/>
              <span style="color:#64748b;">月交易规模：</span><b>${d.value?.toFixed(1)}万元</b><br/>
              <span style="color:#3b82f6;">核心企业 · 信用评估主体</span>`;
          }
          const riskCfg = RISK_CONFIG[d.riskLevel || 'safe'];
          return `<b style="font-size:13px;">${d.name}</b><br/>
            <div style="line-height:1.8;font-size:11px;">
              类型：${categories[d.category]?.name || ''}<br/>
              交易额：<b>${d.value?.toFixed(1)}万元/月</b><br/>
              占比：<b>${(d.share * 100).toFixed(1)}%</b><br/>
              风险：<span style="color:${riskCfg.color};font-weight:700;">${riskCfg.icon} ${riskCfg.label}</span><br/>
              <span style="color:#94a3b8;font-size:10px;">${riskCfg.desc}</span>
            </div>`;
        },
      },
      series: [{
        type: 'graph', layout: 'force', roam: true, draggable: true,
        categories,
        data: nodes.map(n => {
          const riskCfg = RISK_CONFIG[n.riskLevel];
          const isHighRisk = n.riskLevel === 'critical' || n.riskLevel === 'high';
          return {
            ...n,
            label: {
              show: n.category === 0 || n.share > 0.15,
              position: n.category === 0 ? 'inside' : 'right',
              fontSize: n.category === 0 ? 13 : 10,
              fontWeight: n.category === 0 ? 'bold' : isHighRisk ? 'bold' : 'normal',
              color: n.category === 0 ? '#fff' : isHighRisk ? riskCfg.color : '#475569',
            },
            itemStyle: {
              color: n.category === 0 ? '#3b82f6'
                : n.category === 1 ? riskCfg.color   // 供应商用风险色
                : n.category === 3 ? riskCfg.color   // 电商用风险色
                : riskCfg.color,                       // 普通客户用风险色
              borderColor: n.category === 0 ? '#1d4ed8'
                : isHighRisk ? riskCfg.color : riskCfg.border,
              borderWidth: n.category === 0 ? 3 : isHighRisk ? 2.5 : 1.5,
              shadowBlur: n.category === 0 ? 18 : isHighRisk ? 10 : 0,
              shadowColor: n.category === 0 ? 'rgba(59,130,246,0.35)'
                : isHighRisk ? riskCfg.color + '60' : 'transparent',
              // 高风险节点加虚线边框动画效果
              borderType: isHighRisk && n.category !== 0 ? 'dashed' : 'solid',
            },
          };
        }),
        links: links.map(l => {
          const riskCfg = RISK_CONFIG[l.riskLevel];
          const isHighRisk = l.riskLevel === 'critical' || l.riskLevel === 'high';
          return {
            ...l,
            lineStyle: {
              color: riskCfg.color,
              width: Math.max(1, Math.min(5, l.value / 6)),
              opacity: isHighRisk ? 0.75 : 0.4,
              curveness: 0.12,
              type: isHighRisk ? 'dashed' : 'solid',
            },
          };
        }),
        force: {
          repulsion: 380,
          gravity: 0.12,
          edgeLength: [70, 200],
          layoutAnimation: true,
          friction: 0.6,
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 5, opacity: 0.95 },
          itemStyle: { shadowBlur: 25, shadowColor: 'rgba(0,0,0,0.25)' },
        },
        edgeSymbol: ['none', 'arrow'],
        edgeSymbolSize: [0, 8],
        scaleLimit: { min: 0.5, max: 3 },
      }],
    };

    chartInstance.current.setOption(option);
    const h = () => chartInstance.current?.resize();
    window.addEventListener('resize', h);
    return () => window.removeEventListener('resize', h);
  }, [nodes, links]);

  // 获取风险预警列表
  const allHighRisk = [
    ...stats.highRiskSuppliers.map(s => ({ ...s, type: '供应商' })),
    ...stats.highRiskCustomers.map(c => ({ ...c, type: '客户' })),
  ].sort((a, b) => b.share - a.share);

  const hasCriticalRisks = allHighRisk.some(r => r.riskLevel === 'critical');

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
      {/* 标题栏 */}
      <div className="px-6 py-4 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <span className={`w-1.5 h-5 rounded-full ${hasCriticalRisks ? 'bg-red-500' : 'bg-blue-500'}`} />
              企业供应链关系网络 · 风险热力图
            </h3>
            <p className="text-xs text-slate-500 mt-1">
              节点颜色 = 交易集中度风险 · 红色虚线 = 高依赖警告
            </p>
          </div>

          {/* 统计摘要 */}
          <div className="flex items-center gap-2">
            <div className="text-center px-3 py-1.5 bg-slate-50 rounded-lg">
              <div className="text-[10px] text-slate-500">上游</div>
              <div className="text-sm font-bold text-slate-700">{stats.supplierCount}家</div>
            </div>
            <div className="text-center px-3 py-1.5 bg-slate-50 rounded-lg">
              <div className="text-[10px] text-slate-500">下游</div>
              <div className="text-sm font-bold text-slate-700">{stats.customerCount}家</div>
            </div>
            <div className="text-center px-3 py-1.5 bg-slate-50 rounded-lg">
              <div className="text-[10px] text-slate-500">月总额</div>
              <div className="text-sm font-bold text-slate-700">{stats.totalSupply + stats.totalSales}万</div>
            </div>
            {hasCriticalRisks && (
              <div className="flex items-center gap-1.5 px-3 py-1.5 bg-red-50 rounded-lg border border-red-200 animate-pulse">
                <AlertTriangle className="w-4 h-4 text-red-500" />
                <span className="text-xs font-bold text-red-600">风险预警</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 风险图例 */}
      <div className="px-6 py-2.5 bg-slate-50/50 border-b border-slate-100 flex items-center gap-1 flex-wrap">
        <span className="text-[10px] text-slate-500 mr-2 font-medium">风险色谱:</span>
        {Object.entries(RISK_CONFIG).map(([key, cfg]) => (
          <span key={key}
            className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-medium"
            style={{ backgroundColor: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}` }}>
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: cfg.color }} />
            {cfg.label} &lt;{(cfg.threshold * 100).toFixed(0)}%
          </span>
        ))}
        <span className="ml-auto text-[10px] text-slate-400">💡 拖拽节点 · 滚轮缩放 · 悬停详情</span>
      </div>

      {/* 图表主体 */}
      <div ref={chartRef} style={{ width: '100%', height: '460px' }} />

      {/* 底部：风险分析面板 */}
      <div className="border-t border-slate-100">
        {/* 高风险预警列表 */}
        {allHighRisk.length > 0 && (
          <div className="px-6 py-3 bg-red-50/30 border-b border-red-100">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              <span className="text-xs font-bold text-red-700">
                集中度风险预警 ({allHighRisk.length}项)
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
              {allHighRisk.slice(0, 6).map((item, i) => {
                const cfg = RISK_CONFIG[item.riskLevel];
                return (
                  <div key={i}
                    className="flex items-center justify-between px-3 py-2 rounded-lg text-xs"
                    style={{ backgroundColor: cfg.bg, border: `1px solid ${cfg.border}` }}>
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: cfg.color }} />
                      <span className="font-medium" style={{ color: cfg.color }}>
                        {item.name}
                      </span>
                      <span className="text-slate-400">({item.type})</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono font-bold" style={{ color: cfg.color }}>
                        {(item.share * 100).toFixed(1)}%
                      </span>
                      <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ backgroundColor: cfg.color + '20', color: cfg.color }}>
                        {cfg.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* 信用评估总结 */}
        <div className="px-6 py-3 grid grid-cols-3 gap-4 text-xs">
          <div className="space-y-1">
            <span className="text-slate-400 flex items-center gap-1">
              <Shield className="w-3 h-3" />
              供应链集中度
            </span>
            <div className={`font-semibold ${stats.highRiskSuppliers.length > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {stats.highRiskSuppliers.length > 1
                ? `高风险：${stats.highRiskSuppliers.length}家供应商占比过大`
                : stats.highRiskSuppliers.length === 1
                  ? '注意：1家供应商依赖偏高'
                  : '健康：供应商分布均衡'}
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-slate-400 flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              客户多元化
            </span>
            <div className={`font-semibold ${stats.highRiskCustomers.length > 0 ? 'text-red-600' : 'text-emerald-600'}`}>
              {stats.highRiskCustomers.length > 1
                ? `高风险：${stats.highRiskCustomers.length}家客户占比过大`
                : stats.highRiskCustomers.length === 1
                  ? '注意：1家客户依赖偏高'
                  : '健康：客户群分布均衡'}
            </div>
          </div>
          <div className="space-y-1">
            <span className="text-slate-400 flex items-center gap-1">
              <ChevronDown className="w-3 h-3" />
              信贷审批影响
            </span>
            <div className={`font-semibold ${hasCriticalRisks ? 'text-red-600' : 'text-blue-600'}`}>
              {hasCriticalRisks
                ? '集中度风险将显著降低银行通过率'
                : allHighRisk.length > 0
                  ? '建议优化供应链结构以提升评分'
                  : '供应链稳健，信用评估加分项'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
