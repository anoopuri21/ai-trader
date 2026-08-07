'use client';

import { useState, useRef, useEffect } from 'react';
import { api } from '@/lib/api';

interface Message {
  role: 'user' | 'arth';
  content: string;
  timestamp: string;
}

export default function ArthPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'arth', content: "Hello! I'm ARTH, your AI trading assistant. I can analyze stocks, explain signals, and share my learnings. Try asking me to analyze RELIANCE, TCS, or ask about my performance!", timestamp: new Date().toISOString() }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [arthStatus, setArthStatus] = useState<any>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.arth.status().then(setArthStatus).catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;
    
    const userMsg: Message = { role: 'user', content: input, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const response = await api.arth.chat(input);
      const arthMsg: Message = { role: 'arth', content: response.response, timestamp: response.timestamp };
      setMessages(prev => [...prev, arthMsg]);
    } catch (err) {
      setMessages(prev => [...prev, { role: 'arth', content: 'Sorry, I encountered an error. Please try again.', timestamp: new Date().toISOString() }]);
    } finally {
      setLoading(false);
    }
  };

  const quickActions = [
    { label: '📊 Analyze RELIANCE', msg: 'Analyze RELIANCE' },
    { label: '📈 Top BUY signals', msg: 'What are the top buy signals today?' },
    { label: '🧠 My performance', msg: 'How accurate are your predictions?' },
    { label: '📉 Market outlook', msg: 'What is the current market outlook?' },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 py-6">
      {/* ARTH Status */}
      <div className="card mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl flex items-center justify-center text-2xl" style={{ background: 'linear-gradient(135deg, #3B82F6, #8B5CF6)' }}>
            🤖
          </div>
          <div>
            <h2 className="text-lg font-bold">ARTH - AI Trading Agent</h2>
            <p className="text-xs" style={{ color: '#94A3B8' }}>
              Status: <span className={arthStatus?.status === 'ready' ? 'text-buy' : 'text-hold'}>
                {arthStatus?.status === 'ready' ? 'AI-Enhanced' : 'Rule-Based Mode'}
              </span>
              {arthStatus?.status === 'ready' && ' • Multiple AI providers active'}
            </p>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="card mb-4" style={{ minHeight: 400, maxHeight: 500, overflowY: 'auto' }}>
        <div className="flex flex-col gap-3 p-2">
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`chat-bubble ${msg.role === 'user' ? 'chat-user' : 'chat-arth'}`} style={{ whiteSpace: 'pre-wrap' }}>
                {msg.role === 'arth' && <span className="text-xs font-bold block mb-1" style={{ color: '#8B5CF6' }}>ARTH</span>}
                {msg.content}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="chat-bubble chat-arth">
                <span className="text-xs font-bold block mb-1" style={{ color: '#8B5CF6' }}>ARTH</span>
                <span className="inline-flex gap-1">
                  <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#8B5CF6', animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#8B5CF6', animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 rounded-full animate-bounce" style={{ backgroundColor: '#8B5CF6', animationDelay: '300ms' }}></span>
                </span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2 mb-4">
        {quickActions.map((action) => (
          <button
            key={action.msg}
            onClick={() => { setInput(action.msg); }}
            className="btn text-xs"
            style={{ backgroundColor: '#334155', color: '#94A3B8' }}
          >
            {action.label}
          </button>
        ))}
      </div>

      {/* Input */}
      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Ask ARTH anything about markets..."
          className="flex-1 px-4 py-3 rounded-xl text-sm"
          style={{ backgroundColor: '#1E293B', border: '1px solid #334155', color: '#F8FAFC', outline: 'none' }}
        />
        <button
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          className="btn btn-primary px-6"
        >
          Send
        </button>
      </div>
    </div>
  );
}
