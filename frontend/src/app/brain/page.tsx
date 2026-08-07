'use client';

import { useState, useEffect } from 'react';
import { api } from '@/lib/api';

export default function BrainPage() {
  const [stats, setStats] = useState<any>(null);
  const [predictions, setPredictions] = useState<any[]>([]);
  const [patterns, setPatterns] = useState<any[]>([]);
  const [rules, setRules] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'predictions' | 'patterns' | 'rules'>('overview');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [statsData, predData, patData, rulesData] = await Promise.all([
          api.arth.brainStats().catch(() => null),
          api.arth.predictions(50).catch(() => ({ predictions: [] })),
          api.arth.patterns().catch(() => ({ patterns: [] })),
          api.arth.rules().catch(() => ({ rules: [] })),
        ]);
        if (statsData) setStats(statsData);
        setPredictions(predData.predictions || []);
        setPatterns(patData.patterns || []);
        setRules(rulesData.rules || []);
      } catch (err) {
        console.error('Brain fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const triggerReflection = async () => {
    try {
      await api.arth.reflect(7);
      // Refresh data
      const statsData = await api.arth.brainStats().catch(() => null);
      if (statsData) setStats(statsData);
    } catch (err) {
      console.error('Reflection error:', err);
    }
  };

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-6">
        <div className="card text-center py-12">
          <div className="text-4xl mb-4">🧠</div>
          <p style={{ color: '#94A3B8' }}>Loading ARTH&apos;s brain...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">🧠 ARTH&apos;s Brain</h1>
          <p className="text-sm" style={{ color: '#94A3B8' }}>
            Central knowledge base — all learning stored here
          </p>
        </div>
        <button onClick={triggerReflection} className="btn btn-primary">
          🔄 Self-Reflect
        </button>
      </div>

      {/* Overview Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-6">
        <div className="metric-card">
          <p className="metric-label">Predictions</p>
          <p className="metric-value">{stats?.stats?.total_predictions || 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Resolved</p>
          <p className="metric-value">{stats?.stats?.resolved_predictions || 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Accuracy</p>
          <p className="metric-value" style={{ color: (stats?.stats?.overall_accuracy || 0) >= 60 ? '#10B981' : '#F59E0B' }}>
            {stats?.stats?.overall_accuracy?.toFixed(1) || 0}%
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Patterns</p>
          <p className="metric-value">{stats?.stats?.total_patterns || 0}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Active Rules</p>
          <p className="metric-value">{stats?.stats?.active_rules || 0}</p>
        </div>
      </div>

      {/* 30-day accuracy */}
      {stats?.accuracy_30d && stats.accuracy_30d.total_predictions > 0 && (
        <div className="card mb-6">
          <h3 className="font-bold mb-3">30-Day Performance</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Total Predictions</p>
              <p className="text-lg font-bold">{stats.accuracy_30d.total_predictions}</p>
            </div>
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Correct</p>
              <p className="text-lg font-bold text-buy">{stats.accuracy_30d.correct_predictions}</p>
            </div>
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Accuracy</p>
              <p className="text-lg font-bold">{stats.accuracy_30d.accuracy}%</p>
            </div>
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Avg Confidence</p>
              <p className="text-lg font-bold">{stats.accuracy_30d.avg_confidence?.toFixed(1)}%</p>
            </div>
          </div>
          <div className="mt-3">
            <div className="progress-bar">
              <div className="progress-fill" style={{ 
                width: `${stats.accuracy_30d.accuracy}%`,
                backgroundColor: stats.accuracy_30d.accuracy >= 60 ? '#10B981' : stats.accuracy_30d.accuracy >= 40 ? '#F59E0B' : '#EF4444'
              }}></div>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        {(['overview', 'predictions', 'patterns', 'rules'] as const).map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={`nav-tab capitalize ${activeTab === tab ? 'active' : ''}`}>
            {tab}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* How ARTH Learns */}
          <div className="card">
            <h3 className="font-bold mb-3">🔄 How ARTH Learns</h3>
            <div className="space-y-3 text-sm" style={{ color: '#94A3B8' }}>
              <div className="flex gap-2">
                <span className="text-lg">1️⃣</span>
                <div><strong className="text-white">Observe</strong> — Reads market data and charts</div>
              </div>
              <div className="flex gap-2">
                <span className="text-lg">2️⃣</span>
                <div><strong className="text-white">Predict</strong> — Generates BUY/SELL/HOLD signals</div>
              </div>
              <div className="flex gap-2">
                <span className="text-lg">3️⃣</span>
                <div><strong className="text-white">Store</strong> — Logs every prediction to brain</div>
              </div>
              <div className="flex gap-2">
                <span className="text-lg">4️⃣</span>
                <div><strong className="text-white">Resolve</strong> — Checks actual market outcomes</div>
              </div>
              <div className="flex gap-2">
                <span className="text-lg">5️⃣</span>
                <div><strong className="text-white">Learn</strong> — Updates pattern success rates</div>
              </div>
              <div className="flex gap-2">
                <span className="text-lg">6️⃣</span>
                <div><strong className="text-white">Improve</strong> — Generates new rules automatically</div>
              </div>
            </div>
          </div>

          {/* AI Providers */}
          <div className="card">
            <h3 className="font-bold mb-3">🔌 AI Providers</h3>
            <div className="space-y-2">
              {stats?.rules_sample?.length === 0 && predictions.length === 0 ? (
                <p className="text-sm" style={{ color: '#94A3B8' }}>
                  No AI providers configured. Running in rule-based mode.
                  <br /><br />
                  To enable AI, add API keys to your .env file:
                </p>
              ) : null}
              <div className="flex items-center justify-between p-2 rounded" style={{ backgroundColor: '#334155' }}>
                <span className="text-sm">Groq (Llama 3.1 70B)</span>
                <span className="text-xs" style={{ color: '#94A3B8' }}>Fastest free AI</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded" style={{ backgroundColor: '#334155' }}>
                <span className="text-sm">Cohere (Command R)</span>
                <span className="text-xs" style={{ color: '#94A3B8' }}>Best reasoning</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded" style={{ backgroundColor: '#334155' }}>
                <span className="text-sm">HuggingFace</span>
                <span className="text-xs" style={{ color: '#94A3B8' }}>Vision models</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded" style={{ backgroundColor: '#334155' }}>
                <span className="text-sm">Ollama (Local)</span>
                <span className="text-xs" style={{ color: '#94A3B8' }}>Offline, unlimited</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'predictions' && (
        <div className="card">
          <h3 className="font-bold mb-3">Recent Predictions</h3>
          {predictions.length === 0 ? (
            <p className="text-sm text-center py-8" style={{ color: '#94A3B8' }}>
              No predictions yet. ARTH will start storing predictions as you analyze stocks.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ color: '#94A3B8' }}>
                    <th className="text-left py-2">Symbol</th>
                    <th className="text-left py-2">Signal</th>
                    <th className="text-right py-2">Confidence</th>
                    <th className="text-right py-2">Entry</th>
                    <th className="text-left py-2">Outcome</th>
                    <th className="text-right py-2">Return</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.slice(0, 20).map((p: any) => (
                    <tr key={p.id} style={{ borderTop: '1px solid #334155' }}>
                      <td className="py-2 font-medium">{p.symbol}</td>
                      <td className="py-2">
                        <span className={`badge ${p.signal === 'BUY' ? 'text-buy' : p.signal === 'SELL' ? 'text-sell' : 'text-hold'}`}
                          style={{ backgroundColor: p.signal === 'BUY' ? '#10B98122' : p.signal === 'SELL' ? '#EF444422' : '#F59E0B22' }}>
                          {p.signal}
                        </span>
                      </td>
                      <td className="text-right py-2">{p.confidence}%</td>
                      <td className="text-right py-2">₹{p.entry_price?.toFixed(0) || '-'}</td>
                      <td className="py-2">
                        {p.outcome ? (
                          <span style={{ color: p.outcome === 'WIN' ? '#10B981' : p.outcome === 'LOSS' ? '#EF4444' : '#94A3B8' }}>
                            {p.outcome}
                          </span>
                        ) : <span style={{ color: '#64748B' }}>Pending</span>}
                      </td>
                      <td className={`text-right py-2 ${p.actual_return > 0 ? 'text-buy' : p.actual_return < 0 ? 'text-sell' : ''}`}>
                        {p.actual_return ? `${p.actual_return > 0 ? '+' : ''}${p.actual_return}%` : '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'patterns' && (
        <div className="card">
          <h3 className="font-bold mb-3">Learned Patterns</h3>
          {patterns.length === 0 ? (
            <p className="text-sm text-center py-8" style={{ color: '#94A3B8' }}>
              ARTH hasn&apos;t learned any patterns yet. Patterns are learned from successful predictions and backtests.
            </p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {patterns.map((p: any, i: number) => (
                <div key={i} className="rounded-lg p-3" style={{ backgroundColor: '#334155' }}>
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-medium text-sm">{p.pattern_name}</span>
                    <span className="text-xs font-bold" style={{ color: p.success_rate >= 60 ? '#10B981' : '#F59E0B' }}>
                      {p.success_rate?.toFixed(0)}%
                    </span>
                  </div>
                  <div className="text-xs" style={{ color: '#94A3B8' }}>
                    Uses: {p.total_uses} | Type: {p.pattern_type}
                  </div>
                  <div className="progress-bar mt-2">
                    <div className="progress-fill" style={{ 
                      width: `${p.success_rate}%`,
                      backgroundColor: p.success_rate >= 60 ? '#10B981' : '#F59E0B'
                    }}></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {activeTab === 'rules' && (
        <div className="card">
          <h3 className="font-bold mb-3">Active Learning Rules</h3>
          {rules.length === 0 ? (
            <p className="text-sm text-center py-8" style={{ color: '#94A3B8' }}>
              No active rules yet. ARTH generates rules automatically from prediction outcomes.
              Keep using the system and ARTH will learn!
            </p>
          ) : (
            <div className="space-y-2">
              {rules.map((r: any, i: number) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-lg" style={{ backgroundColor: '#334155' }}>
                  <div>
                    <p className="font-medium text-sm">{r.rule_name}</p>
                    <p className="text-xs" style={{ color: '#94A3B8' }}>
                      Type: {r.rule_type} | Success: {r.success_count} | Failure: {r.failure_count}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-sm" style={{ color: r.confidence_score >= 0.7 ? '#10B981' : r.confidence_score >= 0.4 ? '#F59E0B' : '#EF4444' }}>
                      {(r.confidence_score * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs" style={{ color: '#94A3B8' }}>confidence</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
