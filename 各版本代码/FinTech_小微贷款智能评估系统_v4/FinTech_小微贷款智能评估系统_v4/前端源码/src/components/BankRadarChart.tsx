/**
 * 银行对比雷达图 — 多维可视化对比TOP5银行
 * 维度：通过概率 / 利率优势 / 额度高低 / 期限灵活 / 门槛友好
 */

import { useEffect, useRef, useMemo } from 'react';
import * as echarts from 'echarts/core';
import { RadarChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
} from 'echarts/components';
import { CanvasRenderer } from 'echarts/renderers';
import { BankMatchResult } from '../types';

// 注册必需的组件
echarts.use([
  RadarChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  CanvasRenderer,
]);

interface BankRadarChartProps {
  bankMatches: BankMatchResult[];
  requestedAmount: number;
}

// 银行品牌色
const BANK_COLORS: Record<string, string> = {
  icbc: '#c41230',
  ccb: '#0066b3',
  abc: '#00877a',
  boc: '#a5182d',
  bocomm: '#004e9e',
  psbc: '#007a3d',
  cmb: '#e60012',
  citic: '#d50000',
  pingan: '#ff6600',
  minsheng: '#006c4c',
  cib: '#004098',
  spdb: '#003d7a',
  cebb: '#6e1b89',
  webank: '#7b3ff2',
  mybank: '#1677ff',
};

function getBankColor(bankId: string, idx: number): string {
  return BANK_COLORS[bankId] || ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'][idx];
}

export default function BankRadarChart({ bankMatches }: BankRadarChartProps) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  const top5 = useMemo(() => bankMatches.slice(0, 5), [bankMatches]);

  // 标准化各维度数据（0-100）
  const normalize = (values: number[], reverse = false) => {
    const min = Math.min(...values);
    const max = Math.max(...values);
    if (max === min) return values.map(() => 50);
    return values.map(v => {
      const norm = ((v - min) / (max - min)) * 100;
      return reverse ? 100 - norm : norm;
    });
  };

  const allProbs = top5.map(b => b.approvalProbability * 100);
  const allRates = top5.map(b => b.estimatedInterestRate);
  const allAmounts = top5.map(b => b.estimatedMaxAmount);
  const allTerms = top5.map(b => b.maxTermYears);
  const allScores = top5.map(b => b.matchScore);

  const probsNorm = normalize(allProbs);
  const ratesNorm = normalize(allRates, true); // 利率越低越好
  const amountsNorm = normalize(allAmounts);
  const termsNorm = normalize(allTerms);
  const scoresNorm = normalize(allScores);

  const indicator = [
    { name: '通过概率', max: 100 },
    { name: '利率优势', max: 100 },
    { name: '额度优势', max: 100 },
    { name: '期限灵活', max: 100 },
    { name: '综合匹配', max: 100 },
  ];

  const seriesData = top5.map((bank, idx) => ({
    name: bank.bankName,
    value: [probsNorm[idx], ratesNorm[idx], amountsNorm[idx], termsNorm[idx], scoresNorm[idx]],
    original: {
      prob: (bank.approvalProbability * 100).toFixed(0) + '%',
      rate: bank.estimatedInterestRate + '%',
      amount: bank.estimatedMaxAmount + '万',
      term: bank.maxTermYears + '年',
      score: bank.matchScore,
    },
  }));

  useEffect(() => {
    if (!chartRef.current) return;

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    const option: echarts.EChartsCoreOption = {
      tooltip: {
        trigger: 'item',
        backgroundColor: 'rgba(255,255,255,0.96)',
        borderColor: '#e2e8f0',
        borderWidth: 1,
        textStyle: { color: '#334155', fontSize: 11 },
        formatter: (params: any) => {
          if (!params.name || !params.value) return '';
          const orig = seriesData[params.dataIndex]?.original;
          if (!orig) return '';
          return `
            <div style="font-weight:700;font-size:13px;margin-bottom:6px;color:#1e293b;">
              ${params.name}
            </div>
            <div style="line-height:1.8;font-size:11px;">
              <span style="color:#64748b;">通过概率：</span><b>${orig.prob}</b><br/>
              <span style="color:#64748b;">利率：</span><b>${orig.rate}</b><br/>
              <span style="color:#64748b;">额度：</span><b>${orig.amount}</b><br/>
              <span style="color:#64748b;">期限：</span><b>${orig.term}</b><br/>
              <span style="color:#64748b;">匹配分：</span><b>${orig.score}/100</b>
            </div>
          `;
        },
      },
      legend: {
        bottom: 0,
        textStyle: { fontSize: 10, color: '#64748b' },
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 12,
        data: seriesData.map(s => s.name),
      },
      radar: {
        center: ['50%', '48%'],
        radius: '58%',
        indicator,
        shape: 'polygon',
        splitNumber: 4,
        axisName: {
          color: '#475569',
          fontSize: 10,
          borderRadius: 3,
          padding: [2, 4],
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(59,130,246,0.02)', 'rgba(59,130,246,0.02)', 'rgba(59,130,246,0.02)', 'rgba(59,130,246,0.02)'],
          },
        },
        axisLine: { lineStyle: { color: 'rgba(0,0,0,0.08)' } },
        splitLine: { lineStyle: { color: 'rgba(0,0,0,0.06)' } },
      },
      series: [
        {
          type: 'radar',
          symbol: 'circle',
          symbolSize: 5,
          lineStyle: { width: 2 },
          areaStyle: { opacity: 0.12 },
          emphasis: {
            lineStyle: { width: 3 },
            areaStyle: { opacity: 0.25 },
          },
          data: seriesData.map((s, idx) => ({
            ...s,
            itemStyle: { color: getBankColor(top5[idx].bankId, idx) },
            lineStyle: { color: getBankColor(top5[idx].bankId, idx) },
            areaStyle: { color: getBankColor(top5[idx].bankId, idx) },
          })),
        },
      ],
    };

    chartInstance.current.setOption(option);

    const handleResize = () => chartInstance.current?.resize();
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [bankMatches]);

  return (
    <div className="bg-slate-50/50 border border-slate-100 rounded-xl p-4">
      <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 text-center">
        🎯 TOP5 银行多维对比雷达图
      </h4>
      <div ref={chartRef} style={{ width: '100%', height: '320px' }} />
      <p className="text-[10px] text-slate-400 text-center mt-1">
        面积越大代表综合适配度越高 · 各维度已归一化至0-100
      </p>
    </div>
  );
}
