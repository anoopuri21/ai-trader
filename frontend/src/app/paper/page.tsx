'use client';

import { useState, useEffect } from 'react';

const API_BASE = '';

async function fetchApi(endpoint: string, options: RequestInit = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export default function PaperTradingPage() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [performance, setPerformance] = useState<any>(null);
  const [symbol, setSymbol] = useState('');
  const [loading, setLoading] = useState(false);
  const [autoTradeResult, setAutoTradeResult] = useState<any>(null);

  const fetchData = async () => {
    try {
      const [port, tradeHist, perf] = await Promise.all([
        fetchApi('/api/paper/portfolio'),
        fetchApi('/api/paper/trades?limit=20'),
        fetchApi('/api/paper/performance'),
      ]);
      setPortfolio(port);
      setTrades(tradeHist.trades || []);
      setPerformance(perf);
    } catch (e) { console.error(e); }
  };

  useEffect(() => { fetchData(); }, []);

  const autoTrade = async () => {
    if (!symbol.trim()) return;
    setLoading(true);
    setAutoTradeResult(null);
    try {
      const result = await fetchApi(`/api/paper/auto-trade/${symbol.toUpperCase()}`, { method: 'POST' });
      setAutoTradeResult(result);
      await fetchData();
    } catch (e) { console.error(e); }
    setLoading(false);
  };

  const closePosition = async (id: number) => {
    try {
      await fetchApi(`/api/paper/close/${id}`, { method: 'POST' });
      await fetchData();
    } catch (e) { console.error(e); }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-2">📊 Paper Trading Simulator</h1>
      <p className="text-sm mb-6" style={{ color: '#94A3B8' }}>
        Test ARTH&apos;s signals with virtual money. No risk, all learning.
      </p>

      {/* Portfolio Summary */}
      {portfolio && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
          <div className="metric-card">
            <p className="metric-label">💰 Total Value</p>
            <p className="metric-value">₹{portfolio.total_value?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">📈 Total P&L</p>
            <p className={`metric-value ${portfolio.total_pnl >= 0 ? 'text-buy' : 'text-sell'}`}>
              {portfolio.total_pnl >= 0 ? '+' : ''}₹{portfolio.total_pnl?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}
            </p>
          </div>
          <div className="metric-card">
            <p className="metric-label">📊 Return</p>
            <p className={`metric-value ${portfolio.total_pnl_percent >= 0 ? 'text-buy' : 'text-sell'}`}>
              {portfolio.total_pnl_percent?.toFixed(2)}%
            </p>
          </div>
          <div className="metric-card">
            <p className="metric-label">💵 Available Cash</p>
            <p className="metric-value">₹{portfolio.current_cash?.toLocaleString('en-IN', { minimumFractionDigits: 0 })}</p>
          </div>
        </div>
      )}

      {/* Auto Trade */}
      <div className="card mb-6">
        <h3 className="font-bold mb-3">🤖 Auto-Trade with ARTH</h3>
        <p className="text-xs mb-3" style={{ color: '#94A3B8' }}>
          ARTH analyzes the stock and automatically opens a paper position if the signal is strong enough (≥60% confidence).
        </p>
        <div className="flex gap-2">
          <input
            value={symbol}
            onChange={(e) => setSymbol(e.target.value.toUpperCase())}
            placeholder="Enter stock symbol (e.g., RELIANCE)"
            className="flex-1 px-3 py-2 rounded-lg text-sm"
            style={{ backgroundColor: '#334155', border: '1px solid #475569', color: '#F8FAFC' }}
          />
          <button onClick={autoTrade} disabled={loading || !symbol.trim()} className="btn btn-primary px-6">
            {loading ? '⏳ Analyzing...' : '🚀 Auto Trade'}
          </button>
        </div>
        {autoTradeResult && (
          <div className="mt-3 p-3 rounded-lg text-sm" style={{ backgroundColor: '#0F172A', border: '1px solid #334155' }}>
            {autoTradeResult.action === 'TRADED' ? (
              <div>
                <p className="font-bold text-buy">✅ Position Opened!</p>
                <p style={{ color: '#94A3B8' }}>
                  {autoTradeResult.signal} signal with {autoTradeResult.confidence}% confidence.
                  Bought {autoTradeResult.trade?.quantity} shares at ₹{autoTradeResult.trade?.entry_price}
                </p>
              </div>
            ) : (
              <div>
                <p className="font-bold text-hold">⏭️ Skipped</p>
                <p style={{ color: '#94A3B8' }}>{autoTradeResult.reason}</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Open Positions */}
      {portfolio?.positions?.length > 0 && (
        <div className="card mb-6">
          <h3 className="font-bold mb-3">📌 Open Positions ({portfolio.open_positions})</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ color: '#94A3B8' }}>
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-left py-2">Type</th>
                  <th className="text-right py-2">Qty</th>
                  <th className="text-right py-2">Entry</th>
                  <th className="text-right py-2">Current</th>
                  <th className="text-right py-2">P&L</th>
                  <th className="text-center py-2">Action</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((pos: any) => {
                  const pnl = pos.unrealized_pnl || 0;
                  return (
                    <tr key={pos.id} style={{ borderTop: '1px solid #334155' }}>
                      <td className="py-2 font-medium">{pos.symbol}</td>
                      <td className="py-2">
                        <span className={`badge ${pos.type === 'LONG' ? 'text-buy' : 'text-sell'}`}
                          style={{ backgroundColor: pos.type === 'LONG' ? '#10B98122' : '#EF444422' }}>
                          {pos.type}
                        </span>
                      </td>
                      <td className="text-right py-2">{pos.quantity}</td>
                      <td className="text-right py-2">₹{pos.entry_price?.toFixed(0)}</td>
                      <td className="text-right py-2">₹{pos.current_price?.toFixed(0) || pos.entry_price?.toFixed(0)}</td>
                      <td className={`text-right py-2 font-bold ${pnl >= 0 ? 'text-buy' : 'text-sell'}`}>
                        {pnl >= 0 ? '+' : ''}₹{pnl?.toFixed(0)}
                      </td>
                      <td className="text-center py-2">
                        <button onClick={() => closePosition(pos.id)} className="btn text-xs" style={{ backgroundColor: '#EF444422', color: '#EF4444' }}>
                          Close
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Performance */}
      {performance && performance.total_trades > 0 && (
        <div className="card mb-6">
          <h3 className="font-bold mb-3">📈 Performance</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Total Trades</p>
              <p className="text-lg font-bold">{performance.total_trades}</p>
            </div>
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Win Rate</p>
              <p className="text-lg font-bold" style={{ color: (performance.win_rate || 0) >= 50 ? '#10B981' : '#F59E0B' }}>
                {performance.win_rate}%
              </p>
            </div>
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Avg Return</p>
              <p className={`text-lg font-bold ${performance.avg_return >= 0 ? 'text-buy' : 'text-sell'}`}>
                {performance.avg_return >= 0 ? '+' : ''}{performance.avg_return}%
              </p>
            </div>
            <div>
              <p className="text-xs" style={{ color: '#94A3B8' }}>Total P&L</p>
              <p className={`text-lg font-bold ${performance.total_pnl >= 0 ? 'text-buy' : 'text-sell'}`}>
                ₹{performance.total_pnl?.toLocaleString('en-IN')}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Trade History */}
      {trades.length > 0 && (
        <div className="card">
          <h3 className="font-bold mb-3">📝 Trade History</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ color: '#94A3B8' }}>
                  <th className="text-left py-2">Symbol</th>
                  <th className="text-left py-2">Type</th>
                  <th className="text-right py-2">Entry</th>
                  <th className="text-right py-2">Exit</th>
                  <th className="text-right py-2">P&L</th>
                  <th className="text-left py-2">Reason</th>
                </tr>
              </thead>
              <tbody>
                {trades.map((t: any) => (
                  <tr key={t.id} style={{ borderTop: '1px solid #334155' }}>
                    <td className="py-2 font-medium">{t.symbol}</td>
                    <td className="py-2">
                      <span className={t.type === 'LONG' ? 'text-buy' : 'text-sell'}>{t.type}</span>
                    </td>
                    <td className="text-right py-2">₹{t.entry_price}</td>
                    <td className="text-right py-2">₹{t.exit_price}</td>
                    <td className={`text-right py-2 font-bold ${t.pnl >= 0 ? 'text-buy' : 'text-sell'}`}>
                      {t.pnl >= 0 ? '+' : ''}₹{t.pnl}
                    </td>
                    <td className="py-2 text-xs" style={{ color: '#94A3B8' }}>{t.exit_reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
