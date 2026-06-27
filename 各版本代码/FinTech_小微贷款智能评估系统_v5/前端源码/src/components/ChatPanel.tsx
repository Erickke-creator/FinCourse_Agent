/**
 * AI智能对话面板 — 小微贷款顾问Agent
 * 支持：风险评估咨询 / 贷款要求 / 银行选择 / 政策解读等
 */

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Bot, Send, User, Sparkles, RefreshCw, Trash2,
  AlertCircle, Search, Building2, ExternalLink,
} from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  downloadUrl?: string;
  downloadLabel?: string;
}

// 推荐问题
const SUGGESTED_QUESTIONS = [
  { label: '风险评估', q: '我的餐饮店开了2年，月营收6万，征信有一次逾期，能贷到款吗？' },
  { label: '银行推荐', q: '有房产但征信不太好，应该选哪家银行最合适？' },
  { label: '信用违约', q: '被列入失信被执行人名单对贷款有什么影响？' },
  { label: '信用修复', q: '怎么移出企业经营异常名录？需要什么流程？' },
  { label: '企业自查', q: '贷款前应该自查哪些风险点？请给我完整的检查清单' },
  { label: '贷款要求', q: '申请小微企业贷款需要准备什么材料？' },
  { label: '政策补贴', q: '2026年有什么小微企业贷款补贴政策？' },
  { label: '改善建议', q: '怎么提高我的贷款通过率？经营时间比较短' },
];

// API地址（开发环境默认 localhost，部署时改为实际域名）
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function ChatPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: 'assistant',
      content: '👋 您好！我是小微贷款智能顾问。请输入您的企业信息或贷款问题，我会为您提供专业的分析和建议。',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [enterpriseSearch, setEnterpriseSearch] = useState('');
  const [searching, setSearching] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleEnterpriseSearch = async () => {
    const name = enterpriseSearch.trim();
    if (!name || searching) return;
    setSearching(true);
    setEnterpriseSearch('');

    const userMsg: ChatMessage = { role: 'user', content: `🔍 搜索企业：${name}`, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    try {
      const res = await fetch(`${API_BASE}/api/enterprise/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();

      if (data.found && data.report) {
        const assistantMsg: ChatMessage = { role: 'assistant', content: data.report, timestamp: new Date() };
        setMessages(prev => [...prev, assistantMsg]);
        setShowSuggestions(false);

        // Auto-fill提示
        if (data.auto_fill) {
          const tipMsg: ChatMessage = {
            role: 'assistant',
            content: `💡 该企业的经营数据已可自动填入评估表单。请切换到左侧「📋 企业信息」面板，数据将自动填充，点击评估即可获得26家银行匹配结果。`,
            timestamp: new Date(),
          };
          setMessages(prev => [...prev, tipMsg]);
        }
      } else {
        const msg: ChatMessage = {
          role: 'assistant',
          content: data.message || '未找到该企业信息，请尝试使用完整企业名称。',
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, msg]);
      }
    } catch {
      const errMsg: ChatMessage = {
        role: 'assistant',
        content: '⚠️ 搜索服务暂不可用，请确保后端已启动。',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errMsg]);
    } finally {
      setSearching(false);
    }
  };

  // v5: SSE 流式对话（打字机效果）
  const streamChat = async (query: string, userMsg: ChatMessage) => {
    const resp = await fetch(`${API_BASE}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, session_id: sessionId }),
    });
    const reader = resp.body?.getReader();
    if (!reader) throw new Error('No stream');
    const decoder = new TextDecoder();
    // 创建占位消息
    setMessages(prev => [...prev, { role: 'assistant', content: '', timestamp: new Date() }]);
    let fullText = '';
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const d = JSON.parse(line.slice(6));
            if (d.text) {
              fullText += d.text;
              setMessages(prev => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], content: fullText };
                return copy;
              });
            }
            if (d.done) {
              setMessages(prev => {
                const copy = [...prev];
                copy[copy.length - 1] = { ...copy[copy.length - 1], content: d.full || fullText };
                return copy;
              });
            }
          } catch {}
        }
      }
    }
    setLoading(false);
  };

  const handleSend = async (text?: string) => {
    const query = text || input.trim();
    if (!query || loading) return;

    setInput('');
    setShowSuggestions(false);
    setLoading(true);

    const userMsg: ChatMessage = { role: 'user', content: query, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);

    try {
      // v5: 优先尝试 SSE 流式，失败降级普通请求
      const useStream = true;
      if (useStream) {
        try {
          await streamChat(query, userMsg);
          return;
        } catch { /* fall through to normal */ }
      }
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, session_id: sessionId }),
      });
      const data = await res.json();

      if (data.success) {
        setSessionId(data.session_id);
        const assistantMsg: ChatMessage = {
          role: 'assistant',
          content: data.reply,
          timestamp: new Date(),
          downloadUrl: data.download_url || undefined,
          downloadLabel: data.download_label || undefined,
        };
        setMessages(prev => [...prev, assistantMsg]);
      } else {
        throw new Error(data.reply);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        role: 'assistant',
        content: `⚠️ 抱歉，连接后端服务失败。请确保后端已启动（${API_BASE}）。\n\n错误：${err.message}`,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleReset = async () => {
    try {
      await fetch(`${API_BASE}/api/chat/reset?session_id=${sessionId}`, { method: 'POST' });
    } catch {}
    setMessages([{
      role: 'assistant',
      content: '对话已重置。有什么可以帮您的？',
      timestamp: new Date(),
    }]);
    setSessionId('');
    setShowSuggestions(true);
  };

  const handleKeyDown = (e: any) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 渲染 Markdown 样式的文本
  const renderContent = (text: string) => {
    return text.split('\n').map((line, i) => {
      // Bold
      let formatted = line.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-slate-900">$1</strong>');
      // Emoji headers
      if (line.match(/^[#]+ /)) {
        return <div key={i} className="text-sm font-bold text-slate-800 mt-3 mb-1" dangerouslySetInnerHTML={{ __html: formatted }} />;
      }
      if (line.match(/^[-•]/) || line.match(/^\d+\./)) {
        return <div key={i} className="text-xs text-slate-600 ml-3 leading-relaxed" dangerouslySetInnerHTML={{ __html: formatted }} />;
      }
      if (line.trim() === '') return <div key={i} className="h-2" />;
      return <div key={i} className="text-xs text-slate-600 leading-relaxed" dangerouslySetInnerHTML={{ __html: formatted }} />;
    });
  };

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden flex flex-col" style={{ height: 'calc(100vh - 120px)' }}>
      {/* 标题栏 */}
      <div className="px-5 py-3.5 border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-blue-50 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center shadow-sm">
            <Bot className="w-4.5 h-4.5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-800">小微贷款智能顾问</h3>
            <p className="text-[10px] text-slate-500">AI Agent · 知识库驱动 · 26行数据支撑</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={handleReset}
            className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-white/60 rounded-lg transition"
            title="重置对话">
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 企业搜索框 */}
      <div className="px-4 py-2.5 border-b border-slate-100 bg-gradient-to-r from-amber-50/50 to-orange-50/30 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Building2 className="w-4 h-4 text-amber-500 flex-shrink-0" />
          <div className="flex-1 relative">
            <input
              type="text"
              value={enterpriseSearch}
              onChange={e => setEnterpriseSearch(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') handleEnterpriseSearch(); }}
              placeholder="输入真实企业名称，如：东莞精密制造有限公司..."
              disabled={searching}
              className="w-full bg-white border border-amber-200 rounded-lg pl-3 pr-10 py-1.5 text-xs focus:ring-2 focus:ring-amber-500/20 outline-none disabled:opacity-50 placeholder:text-slate-400"
            />
            <button
              onClick={handleEnterpriseSearch}
              disabled={searching || !enterpriseSearch.trim()}
              className="absolute right-1 top-1/2 -translate-y-1/2 p-1 bg-amber-500 hover:bg-amber-600 text-white rounded disabled:opacity-40 transition"
            >
              <Search className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
        <p className="text-[9px] text-slate-400 mt-1 ml-6">
          输入真实企业全称，系统自动搜索公开信息并生成贷款可行性分析报告
        </p>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3">
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.05 }}
              className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Bot className="w-3.5 h-3.5 text-white" />
                </div>
              )}
              <div className={`max-w-[85%] rounded-xl px-3.5 py-2.5 ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-50 border border-slate-100 text-slate-700'
              }`}>
                {msg.role === 'user' ? (
                  <div className="text-xs leading-relaxed">{msg.content}</div>
                ) : (
                  <div className="text-xs">{renderContent(msg.content)}</div>
                )}
                {/* v5: PDF 下载按钮 */}
                {msg.downloadUrl && (
                  <div className="mt-2">
                    <button
                      onClick={async () => {
                        try {
                          const res = await fetch(`${API_BASE}${msg.downloadUrl}`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ enterprise_name: msg.downloadLabel?.replace('下载 ', '')?.replace(' 的评估报告', '') || '企业' }),
                          });
                          if (!res.ok) throw new Error('下载失败');
                          const blob = await res.blob();
                          const url = URL.createObjectURL(blob);
                          const a = document.createElement('a');
                          a.href = url;
                          a.download = `贷款评估报告_${Date.now()}.pdf`;
                          a.click();
                          URL.revokeObjectURL(url);
                        } catch (e) {
                          alert('下载失败，请重试');
                        }
                      }}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-indigo-500 hover:bg-indigo-600 text-white text-xs rounded-lg transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      {msg.downloadLabel || '下载 PDF 报告'}
                    </button>
                  </div>
                )}
                <div className={`text-[9px] mt-1 ${msg.role === 'user' ? 'text-blue-200' : 'text-slate-400'}`}>
                  {msg.timestamp.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}
                </div>
              </div>
              {msg.role === 'user' && (
                <div className="w-7 h-7 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <User className="w-3.5 h-3.5 text-slate-500" />
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {/* 加载指示器 */}
        {loading && (
          <div className="flex gap-2.5 items-center">
            <div className="w-7 h-7 rounded-lg bg-indigo-100 flex items-center justify-center">
              <Bot className="w-3.5 h-3.5 text-indigo-500" />
            </div>
            <div className="bg-slate-50 border border-slate-100 rounded-xl px-4 py-2.5">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 推荐问题 */}
      {showSuggestions && messages.length <= 1 && (
        <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/50 flex-shrink-0">
          <p className="text-[10px] text-slate-400 mb-2">💡 试试这些问题：</p>
          <div className="flex flex-wrap gap-1.5">
            {SUGGESTED_QUESTIONS.map((sq, i) => (
              <button
                key={i}
                onClick={() => handleSend(sq.q)}
                className="px-2.5 py-1.5 bg-white hover:bg-blue-50 text-slate-600 hover:text-blue-700 rounded-lg text-[11px] border border-slate-200 hover:border-blue-200 transition cursor-pointer"
              >
                {sq.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 输入区 */}
      <div className="px-4 py-3 border-t border-slate-100 flex-shrink-0">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入您的问题，如：我的餐饮店能贷多少？"
            disabled={loading}
            className="flex-1 bg-slate-50 border border-slate-200 rounded-lg px-3.5 py-2 text-sm focus:ring-2 focus:ring-indigo-500/20 outline-none disabled:opacity-50"
          />
          <button
            onClick={() => handleSend()}
            disabled={loading || !input.trim()}
            className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-lg disabled:opacity-40 transition shadow-sm flex items-center gap-1.5"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[9px] text-slate-400 mt-1.5 text-center">
          按 Enter 发送 · AI顾问基于知识库和26家银行数据提供建议
        </p>
      </div>
    </div>
  );
}
