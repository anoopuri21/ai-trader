'use client';

import { useState } from 'react';
import { api } from '@/lib/api';

export default function BacktestPage() {
  const [symbol, setSymbol] = useState('RELIANCE');
  const [strategy, setStrategy] = useState('rule_based');
  const [result, setResult] = useState<any>(null);
  const [compareResult, setCompareResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'single' | 'compare'>('single');

  const strategies = [
    { id: 'rule_based', name: 'Rule-Based', desc: 'SMA + RSI + MACD crossover' },
    { id: 'momentum', name: 'Momentum', desc: 'RSI + Volume momentum' },
    { id: 'mean_reversion', name: 'Mean Reversion', desc: 'Bollinger Bands reversion' },
    { id: 'combined', name: 'Combined', desc: 'All strategies with ARTH weights' },
  ];

  const runBacktest = async () => {
    setLoading(true);
    try {
      if (activeTab === 'single') {
        const data = await api.backtest.run(symbol, strategy);
        setResult(data);
      } else {
        const data = await api.backtest.compare(symbol);
        setCompareResult(data);
      }
    } catch (err) {
      console.error('Backtest error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-6">
      <h1 className="text-2xl font-bold mb-2">📉 Backtesting Engine</h1>
      <p className="text-sm mb-6" style={{ color: '#94A3B8' }}>
        Test strategies against historical data. ARTH learns from every backtest.
      </p>

      {/* Controls */}
      <div className="card mb-6">
        <div className="flex flex-wrap gap-3 mb-4">
          <div className="flex gap-2">
            <button onClick={() => setActiveTab('single')} className={`nav-tab ${activeTab === 'single' ? 'active' : ''}`}>Single Strategy</button>
            <button onClick={() => setActiveTab('compare')} className={`nav-tab ${activeTab === 'compare' ? 'active' : ''}`}>Compare All</button>
          </div>
        </div>

        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="text-xs block mb-1" style={{ color: '#94A3B8' }}>Stock Symbol</label>
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="px-3 py-2 rounded-lg text-sm"
              style={{ backgroundColor: '#334155', border: '1px solid #475569', color: '#F8FAFC' }}
              placeholder="RELIANCE"
            />
          </div>
          
          {activeTab === 'single' && (
            <div>
              <label className="text-xs block mb-1" style={{ color: '#94A3B8' }}>Strategy</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="px-3 py-2 rounded-lg text-sm"
                style={{ backgroundColor: '#334155', border: '1px solid #475569', color: '#F8FAFC' }}
              >
                {strategies.map(s => (
                  <option key={s.id} value={s.id}>{s.name} - {s.desc}</option>
                ))}
              </select>
            </div>
          )}

          <button onClick={runBacktest} disabled={loading} className="btn btn-primary px-6">
            {loading ? '⏳ Running...' : '🚀 Run Backtest'}
          </button>
        </div>
      </div>

      {/* Results */}
      {loading && (
        <div className="card text-center py-8">
          <div className="text-4xl mb-4">📊</div>
          <p style={{ color: '#94A3B8' }}>Running backtest for {symbol}...</p>
          <p className="text-xs mt-2" style={{ color: '#64748B' }}>Fetching historical data and simulating trades</p>
        </div>
      )}

      {/* Single Strategy Result */}
      {result && !loading && (
        <div>
          {/* Metrics */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
            <div className="metric-card">
              <p className="metric-label">Total Return</p>
              <p className={`metric-value ${result.metrics.total_return >= 0 ? 'text-buy' : 'text-sell'}`}>
                {result.metrics.total_return?.toFixed(1)}%
              </p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Win Rate</p>
              <p className="metric-value">{result.metrics.win_rate?.toFixed(1)}%</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Total Trades</p>
              <p className="metric-value">{result.metrics.total_trades}</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Profit Factor</p>
              <p className="metric-value">{result.metrics.profit_factor?.toFixed(2) || '∞'}</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Sharpe Ratio</p>
              <p className="metric-value">{result.metrics.sharpe_ratio?.toFixed(2)}</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Max Drawdown</p>
              <p className="metric-value text-sell">-{result.metrics.max_drawdown?.toFixed(1)}%</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Avg Profit</p>
              <p className="metric-value text-buy">+{result.metrics.avg_profit?.toFixed(2)}%</p>
            </div>
            <div className="metric-card">
              <p className="metric-label">Avg Loss</p>
              <p className="metric-value text-sell">{result.metrics.avg_loss?.toFixed(2)}%</p>
            </div>
          </div>

          {/* Trade History */}
          <div className="card">
            <h3 className="font-bold mb-3">Recent Trades ({result.trades?.length || 0})</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ color: '#94A3B8' }}>
                    <th className="text-left py-2">Type</th>
                    <th className="text-right py-2">Entry</th>
                    <th className="text-right py-2">Exit</th>
                    <th className="text-right py-2">P&L</th>
                    <th className="text-left py-2">Exit Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades?.slice(-10).reverse().map((trade: any, i: number) => (
                    <tr key={i} style={{ borderTop: '1px solid #334155' }}>
                      <td className="py-2">
                        <span className={`badge ${trade.type === 'long' ? 'text-buy' : 'text-sell'}`}
                          style={{ backgroundColor: trade.type === 'long' ? '#10B98122' : '#EF444422' }}>
                          {trade.type.toUpperCase()}
                        </span>
                      </td>
                      <td className="text-right py-2">₹{trade.entry_price}</td>
                      <td className="text-right py-2">₹{trade.exit_price}</td>
                      <td className={`text-right py-2 font-bold ${trade.pnl_percent >= 0 ? 'text-buy' : 'text-sell'}`}>
                        {trade.pnl_percent >= 0 ? '+' : ''}{trade.pnl_percent}%
                      </td>
                      <td className="py-2 text-xs" style={{ color: '#94A3B8' }}>{trade.exit_reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Compare Results */}
      {compareResult && !loading && (
        <div>
          <div className="card mb-4">
            <h3 className="font-bold mb-3">Strategy Comparison - {symbol}</h3>
            <p className="text-sm mb-4" style={{ color: '#94A3B8' }}>
              Best strategy: <span className="font-bold text-buy">{compareResult.best_strategy}</span> ({compareResult.best_return?.toFixed(1)}% return)
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {Object.entries(compareResult.strategies || {}).map(([name, metrics]: [string, any]) => (
                <div key={name} className="rounded-lg p-3" style={{ backgroundColor: '#334155' }}>
                  <h4 className="font-medium mb-2 capitalize">{name.replace('_', ' ')}</h4>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div><span style={{ color: '#94A3B8' }}>Return:</span> <span className={metrics.total_return >= 0 ? 'text-buy' : 'text-sell'}>{metrics.total_return?.toFixed(1)}%</span></div>
                    <div><span style={{ color: '#94A3B8' }}>Win Rate:</span> {metrics.win_rate?.toFixed(1)}%</div>
                    <div><span style={{ color: '#94A3B8' }}>Trades:</span> {metrics.total_trades}</div>
                    <div><span style={{ color: '#94A3B8' }}>Sharpe:</span> {metrics.sharpe_ratio?.toFixed(2)}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
