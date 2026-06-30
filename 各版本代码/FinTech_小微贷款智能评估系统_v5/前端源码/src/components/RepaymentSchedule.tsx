import { useState, useEffect } from 'react';

interface ScheduleRow { month: number; payment: number; principal: number; interest: number; balance: number; cumulative_interest: number; }

export default function RepaymentSchedule({ amount, rate, term, monthlyPayment }: { amount: number; rate: number; term: number; monthlyPayment: number }) {
  const [schedule, setSchedule] = useState<ScheduleRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    loadSchedule();
  }, [amount, rate, term]);

  const loadSchedule = async () => {
    setLoading(true);
    try {
      const API = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000';
      const resp = await fetch(`${API}/api/repayment-schedule?amount=${amount}&rate=${rate}&term=${term}`);
      const data = await resp.json();
      if (data.success) setSchedule(data.schedule);
    } catch {}
    setLoading(false);
  };

  const display = showAll ? schedule : schedule.filter((_, i) => i < 12 || i >= schedule.length - 3);

  if (loading) return <div className="text-slate-400 text-xs py-4 text-center">加载还款计划...</div>;
  if (!schedule.length) return null;

  const totalInterest = schedule[schedule.length - 1]?.cumulative_interest || 0;

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-gradient-to-r from-slate-50 to-blue-50 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-slate-700">还款计划表（等额本息）</h3>
        <div className="flex gap-4 mt-1 text-xs text-slate-500">
          <span>月供: <b className="text-blue-600">{monthlyPayment.toFixed(0)} 元</b></span>
          <span>总利息: <b className="text-amber-600">{totalInterest.toFixed(0)} 元</b></span>
        </div>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-slate-50 text-slate-500">
              <th className="py-2 px-3 text-left font-medium">期数</th>
              <th className="py-2 px-3 text-right font-medium">月供</th>
              <th className="py-2 px-3 text-right font-medium">本金</th>
              <th className="py-2 px-3 text-right font-medium">利息</th>
              <th className="py-2 px-3 text-right font-medium">剩余本金</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {display.map((r, i) => {
              const showEllipsis = !showAll && i === 11 && schedule.length > 15;
              return (
                <tr key={r.month} className={`hover:bg-blue-50/30 ${r.month % 2 === 0 ? 'bg-white' : 'bg-slate-50/30'}`}>
                  <td className="py-1.5 px-3 text-slate-600">{showEllipsis ? '...' : r.month}</td>
                  <td className="py-1.5 px-3 text-right font-mono text-slate-700">{r.payment.toFixed(0)}</td>
                  <td className="py-1.5 px-3 text-right font-mono text-emerald-600">{r.principal.toFixed(0)}</td>
                  <td className="py-1.5 px-3 text-right font-mono text-amber-600">{r.interest.toFixed(0)}</td>
                  <td className="py-1.5 px-3 text-right font-mono text-slate-400">{r.balance.toFixed(0)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {schedule.length > 15 && (
        <button onClick={() => setShowAll(!showAll)} className="w-full py-2 text-xs text-blue-500 hover:bg-blue-50 transition">
          {showAll ? '收起' : `展开全部 ${schedule.length} 期`}
        </button>
      )}
    </div>
  );
}
