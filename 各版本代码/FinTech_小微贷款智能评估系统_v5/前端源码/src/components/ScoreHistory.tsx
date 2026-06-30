import { useState, useEffect } from 'react';

interface ScoreRecord { score: number; risk_level: string; enterprise_name: string; created_at: string; }

export default function ScoreHistory() {
  const [records, setRecords] = useState<ScoreRecord[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadHistory(); }, []);

  const loadHistory = async () => {
    try {
      const API = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000';
      const resp = await fetch(`${API}/api/scores/history?limit=10`);
      const data = await resp.json();
      if (data.success) setRecords(data.history);
    } catch {}
    setLoading(false);
  };

  if (loading) return <div className="text-slate-400 text-xs py-4 text-center">加载评分历史...</div>;
  if (!records.length) return <div className="text-slate-400 text-xs py-4 text-center">暂无评估记录。完成一次评估后这里会显示趋势图。</div>;

  const maxScore = Math.max(...records.map(r => r.score), 100);
  const minScore = Math.min(...records.map(r => r.score), 0);
  const range = maxScore - minScore || 1;

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="px-4 py-3 bg-gradient-to-r from-indigo-50 to-blue-50 border-b border-slate-100">
        <h3 className="text-sm font-semibold text-slate-700">评分历史趋势</h3>
        <p className="text-xs text-slate-400 mt-0.5">最近 {records.length} 次评估</p>
      </div>
      <div className="p-4">
        {/* Simple SVG trend chart */}
        <svg viewBox="0 0 300 120" className="w-full h-32">
          {/* Grid lines */}
          {[0, 25, 50, 75, 100].map(y => (
            <g key={y}>
              <line x1="30" y1={100 - (y / 100) * 100} x2="290" y2={100 - (y / 100) * 100} stroke="#e2e8f0" strokeWidth="0.5" />
              <text x="25" y={103 - (y / 100) * 100} fill="#94a3b8" fontSize="7" textAnchor="end">{y}</text>
            </g>
          ))}
          {/* Score line */}
          <polyline
            fill="none" stroke="#2563eb" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
            points={records.map((r, i) => `${30 + (i / Math.max(records.length - 1, 1)) * 260},${100 - ((r.score - 0) / 100) * 100}`).join(' ')}
          />
          {/* Dots */}
          {records.map((r, i) => {
            const x = 30 + (i / Math.max(records.length - 1, 1)) * 260;
            const y = 100 - (r.score / 100) * 100;
            const color = r.score >= 80 ? '#16a34a' : r.score >= 55 ? '#f59e0b' : '#dc2626';
            return (
              <g key={i}>
                <circle cx={x} cy={y} r="4" fill={color} stroke="white" strokeWidth="1.5" />
                <text x={x} y={y - 8} fill="#475569" fontSize="8" textAnchor="middle">{r.score}</text>
              </g>
            );
          })}
        </svg>
        {/* Legend */}
        <div className="flex flex-wrap gap-2 mt-3">
          {records.map((r, i) => {
            const color = r.score >= 80 ? 'bg-green-100 text-green-700' : r.score >= 55 ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700';
            return (
              <div key={i} className={`text-xs px-2 py-0.5 rounded-full ${color}`}>
                {r.enterprise_name || `#${i + 1}`}: {r.score}分
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
