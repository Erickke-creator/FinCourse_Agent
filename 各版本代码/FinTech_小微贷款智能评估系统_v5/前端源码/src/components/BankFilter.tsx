import { useState, useMemo } from 'react';

interface Bank { bank_name: string; bank_type: string; product_name: string; loan_type: string; approval_probability: number; estimated_interest_rate: number; max_term_years: number; }

export default function BankFilter({ banks }: { banks: Bank[] }) {
  const [maxRate, setMaxRate] = useState(10);
  const [loanType, setLoanType] = useState('');
  const [minProb, setMinProb] = useState(0);
  const [search, setSearch] = useState('');

  const filtered = useMemo(() => banks.filter(b => {
    if (b.estimated_interest_rate > maxRate) return false;
    if (loanType && b.loan_type !== loanType) return false;
    if (b.approval_probability < minProb / 100) return false;
    if (search && !b.bank_name.includes(search) && !b.product_name.includes(search)) return false;
    return true;
  }), [banks, maxRate, loanType, minProb, search]);

  const types = [...new Set(banks.map(b => b.loan_type))];

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-gradient-to-r from-slate-50 to-blue-50 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-slate-700">银行产品筛选</h3>
        <p className="text-xs text-slate-400">{filtered.length} / {banks.length} 家匹配</p>
      </div>
      <div className="p-3 flex flex-wrap gap-2 border-b border-slate-100">
        <input value={search} onChange={e => setSearch(e.target.value)} placeholder="搜索银行或产品..."
          className="text-xs border border-slate-200 rounded px-2 py-1 w-40 focus:outline-none focus:border-blue-400" />
        <select value={loanType} onChange={e => setLoanType(e.target.value)}
          className="text-xs border border-slate-200 rounded px-2 py-1 focus:outline-none">
          <option value="">全部类型</option>
          {types.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <label className="text-xs text-slate-500 flex items-center gap-1">
          利率 ≤ <input type="number" value={maxRate} onChange={e => setMaxRate(+e.target.value)}
            className="w-14 text-xs border border-slate-200 rounded px-1 py-0.5" min={2} max={20} />%
        </label>
        <label className="text-xs text-slate-500 flex items-center gap-1">
          审批 ≥ <input type="number" value={minProb} onChange={e => setMinProb(+e.target.value)}
            className="w-14 text-xs border border-slate-200 rounded px-1 py-0.5" min={0} max={100} />%
        </label>
      </div>
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="w-full text-xs">
          <thead className="sticky top-0 bg-slate-50">
            <tr className="text-slate-500">
              <th className="py-2 px-3 text-left">银行</th>
              <th className="py-2 px-3 text-left">产品</th>
              <th className="py-2 px-3 text-center">类型</th>
              <th className="py-2 px-3 text-right">审批</th>
              <th className="py-2 px-3 text-right">利率</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filtered.map((b, i) => (
              <tr key={i} className={i % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}>
                <td className="py-1.5 px-3 font-medium text-slate-700">{b.bank_name}</td>
                <td className="py-1.5 px-3 text-slate-600">{b.product_name}</td>
                <td className="py-1.5 px-3 text-center">
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${b.loan_type === '信用贷' ? 'bg-green-100 text-green-600' : b.loan_type === '抵押贷' ? 'bg-amber-100 text-amber-600' : 'bg-blue-100 text-blue-600'}`}>{b.loan_type}</span>
                </td>
                <td className="py-1.5 px-3 text-right font-mono">{b.approval_probability ? `${(b.approval_probability * 100).toFixed(0)}%` : '-'}</td>
                <td className="py-1.5 px-3 text-right font-mono text-blue-600">{b.estimated_interest_rate?.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && <div className="text-center py-6 text-slate-400 text-xs">无匹配结果，尝试放宽筛选条件</div>}
      </div>
    </div>
  );
}
