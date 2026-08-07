'use client';

import { useState, useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, LineData, Time } from 'lightweight-charts';
import { api } from '@/lib/api';
import { cn, formatCurrency, formatPercent, getChangeColor, getSignalBgColor, getSignalTextColor, timeAgo } from '@/lib/utils';

// Chart Component
function StockChart({ symbol }: { symbol: string }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: { background: { color: '#1E293B' }, textColor: '#94A3B8' },
      grid: { vertLines: { color: '#334155' }, horzLines: { color: '#334155' } },
      width: chartContainerRef.current.clientWidth,
      height: 280,
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10B981', downColor: '#EF4444',
      borderUpColor: '#10B981', borderDownColor: '#EF4444',
      wickUpColor: '#10B981', wickDownColor: '#EF4444',
    });

    const smaSeries = chart.addLineSeries({ color: '#3B82F6', lineWidth: 2 });

    const fetchData = async () => {
      try {
        const response = await fetch(`https://query1.finance.yahoo.com/v8/finance/chart/${symbol}.NS?interval=1d&range=3mo`);
        const data = await response.json();
        if (data.chart?.result?.[0]) {
          const result = data.chart.result[0];
          const timestamps = result.timestamp as number[];
          const quote = result.indicators.quote[0];
          const candleData: CandlestickData[] = timestamps.map((t, i) => ({
            time: (t as number) as Time,
            open: quote.open[i] as number, high: quote.high[i] as number,
            low: quote.low[i] as number, close: quote.close[i] as number,
          })).filter(d => d.close !== null);
          const closes = candleData.map(d => d.close);
          const sma20 = candleData.map((d, i) => {
            const start = Math.max(0, i - 19);
            const slice = closes.slice(start, i + 1);
            return { time: d.time, value: slice.reduce((a, b) => a + b, 0) / slice.length };
          });
          candlestickSeries.setData(candleData);
          smaSeries.setData(sma20);
          chart.timeScale().fitContent();
        }
      } catch (err) { console.error('Chart error:', err); }
    };
    fetchData();

    const handleResize = () => { chart.applyOptions({ width: chartContainerRef.current?.clientWidth || 300 }); };
    window.addEventListener('resize', handleResize);
    return () => { window.removeEventListener('resize', handleResize); chart.remove(); };
  }, [symbol]);

  return <div ref={chartContainerRef} className="w-full" style={{ height: 280 }} />;
}

// Signal Card
function SignalCard({ signal }: { signal: any }) {
  const [showChart, setShowChart] = useState(false);
  const [arthData, setArthData] = useState<any>(null);
  
  const signalColor = signal.signal === 'BUY' ? '#10B981' : signal.signal === 'SELL' ? '#EF4444' : '#F59E0B';

  const loadArthAnalysis = async () => {
    try {
      const data = await api.arth.analyze(signal.stock.symbol);
      setArthData(data);
    } catch (e) { console.error(e); }
  };

  return (
    <div className="card card-hover" style={{ borderColor: `${signalColor}33` }}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold">{signal.stock.symbol}</h3>
          <p className="text-xs" style={{ color: '#94A3B8' }}>{signal.stock.name}</p>
        </div>
        <div className="badge" style={{ backgroundColor: `${signalColor}22`, color: signalColor, border: `1px solid ${signalColor}44` }}>
          {signal.signal}
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <p className="text-xs" style={{ color: '#94A3B8' }}>Price</p>
          <p className="text-lg font-bold">₹{signal.stock.current_price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
        </div>
        <div>
          <p className="text-xs" style={{ color: '#94A3B8' }}>Change</p>
          <p className={`text-lg font-bold ${getChangeColor(signal.stock.change_percent)}`}>
            {signal.stock.change_percent?.toFixed(2)}%
          </p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-2 mb-3 text-xs">
        <div className="rounded-lg p-2" style={{ backgroundColor: '#334155' }}>
          <p style={{ color: '#94A3B8' }}>RSI</p>
          <p className="font-medium">{signal.indicators.rsi?.toFixed(1) || '-'}</p>
        </div>
        <div className="rounded-lg p-2" style={{ backgroundColor: '#334155' }}>
          <p style={{ color: '#94A3B8' }}>SMA20</p>
          <p className="font-medium">{signal.indicators.sma_20?.toFixed(0) || '-'}</p>
        </div>
        <div className="rounded-lg p-2" style={{ backgroundColor: '#334155' }}>
          <p style={{ color: '#94A3B8' }}>MACD</p>
          <p className={`font-medium ${signal.indicators.macd_histogram && signal.indicators.macd_histogram > 0 ? 'text-buy' : 'text-sell'}`}>
            {signal.indicators.macd_histogram?.toFixed(2) || '-'}
          </p>
        </div>
        <div className="rounded-lg p-2" style={{ backgroundColor: '#334155' }}>
          <p style={{ color: '#94A3B8' }}>Conf.</p>
          <p className="font-medium" style={{ color: signalColor }}>{signal.confidence}%</p>
        </div>
      </div>

      {signal.entry_price && (
        <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
          <div className="rounded-lg p-2" style={{ backgroundColor: '#334155' }}>
            <p style={{ color: '#94A3B8' }}>Entry</p>
            <p className="font-medium text-buy">₹{signal.entry_price?.toFixed(0)}</p>
          </div>
          <div className="rounded-lg p-2" style={{ backgroundColor: '#334155' }}>
            <p style={{ color: '#94A3B8' }}>Target</p>
            <p className="font-medium text-buy">₹{signal.target_price?.toFixed(0)}</p>
          </div>
          <div className="rounded-lg p-2" style={{ backgroundColor: '#334155' }}>
            <p style={{ color: '#94A3B8' }}>Stop</p>
            <p className="font-medium text-sell">₹{signal.stop_loss?.toFixed(0)}</p>
          </div>
        </div>
      )}

      {/* Confidence bar */}
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span style={{ color: '#94A3B8' }}>Signal Strength</span>
          <span style={{ color: signalColor }}>{signal.signal_strength}</span>
        </div>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${signal.confidence}%`, backgroundColor: signalColor }}></div>
        </div>
      </div>

      <div className="flex gap-2">
        <button onClick={() => setShowChart(!showChart)} className="btn btn-primary flex-1 text-sm py-2">
          {showChart ? 'Hide Chart' : '📊 Chart'}
        </button>
        {!arthData && (
          <button onClick={loadArthAnalysis} className="btn flex-1 text-sm py-2" style={{ backgroundColor: '#334155' }}>
            🤖 ARTH
          </button>
        )}
      </div>

      {arthData && (
        <div className="mt-3 p-3 rounded-lg text-xs" style={{ backgroundColor: '#0F172A', border: '1px solid #334155' }}>
          <div className="flex items-center gap-2 mb-2">
            <span>🤖</span>
            <span className="font-medium">ARTH Analysis</span>
            <span className="text-xs" style={{ color: '#94A3B8' }}>
              Win Prob: {arthData.probability?.win_probability}%
            </span>
          </div>
          {arthData.ai_reasoning && (
            <p style={{ color: '#94A3B8' }} className="mb-2">{arthData.ai_reasoning?.slice(0, 200)}...</p>
          )}
          <div className="flex gap-2 flex-wrap">
            <span className="badge" style={{ backgroundColor: '#334155' }}>
              Risk: {arthData.probability?.risk_level}
            </span>
            <span className="badge" style={{ backgroundColor: '#334155' }}>
              Size: {arthData.probability?.position_size}
            </span>
            {arthData.patterns?.map((p: any) => (
              <span key={p.name} className="badge" style={{ backgroundColor: '#334155' }}>{p.name}</span>
            ))}
          </div>
        </div>
      )}

      {showChart && (
        <div className="mt-4">
          <StockChart symbol={signal.stock.symbol} />
        </div>
      )}
    </div>
  );
}

// Main Dashboard
export default function Dashboard() {
  const [signals, setSignals] = useState<any>(null);
  const [indices, setIndices] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'BUY' | 'SELL' | 'HOLD'>('all');
  const [indexFilter, setIndexFilter] = useState<'nifty50' | 'niftybank'>('nifty50');
  const [arthStatus, setArthStatus] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [signalsData, indicesData, statusData] = await Promise.all([
          api.signals.all(indexFilter),
          api.prices.indices(),
          api.arth.status().catch(() => null),
        ]);
        setSignals(signalsData);
        setIndices(indicesData.indices || {});
        if (statusData) setArthStatus(statusData);
      } catch (err) {
        console.error('Fetch error:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, [indexFilter]);

  const filteredSignals = signals?.signals?.filter((s: any) => {
    if (filter === 'all') return true;
    return s.signal === filter;
  }) || [];

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* ARTH Status Bar */}
      {arthStatus && (
        <div className="card mb-4 flex items-center gap-4" style={{ borderColor: arthStatus.status === 'ready' ? '#10B98133' : '#F59E0B33' }}>
          <span>🤖</span>
          <div className="flex-1">
            <span className="text-sm font-medium">ARTH Status: </span>
            <span className={`text-sm font-bold ${arthStatus.status === 'ready' ? 'text-buy' : 'text-hold'}`}>
              {arthStatus.status === 'ready' ? 'AI-Enhanced' : 'Rule-Based'}
            </span>
          </div>
          <div className="flex gap-2">
            {arthStatus.providers?.map((p: any) => (
              <span key={p.provider} className="text-xs px-2 py-1 rounded" style={{ backgroundColor: p.available ? '#10B98122' : '#334155', color: p.available ? '#10B981' : '#94A3B8' }}>
                {p.available ? '✓' : '○'} {p.provider}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Index Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {indices['^NSEI'] && (
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm" style={{ color: '#94A3B8' }}>Nifty 50</h2>
                <p className="text-2xl font-bold">
                  {indices['^NSEI'].current_value?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className={`text-xl font-bold ${getChangeColor(indices['^NSEI'].change_percent)}`}>
                {indices['^NSEI'].change_percent?.toFixed(2)}%
              </div>
            </div>
          </div>
        )}
        {indices['^NSEBANK'] && (
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-sm" style={{ color: '#94A3B8' }}>Nifty Bank</h2>
                <p className="text-2xl font-bold">
                  {indices['^NSEBANK'].current_value?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className={`text-xl font-bold ${getChangeColor(indices['^NSEBANK'].change_percent)}`}>
                {indices['^NSEBANK'].change_percent?.toFixed(2)}%
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Summary Cards */}
      {signals && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="metric-card" style={{ borderColor: '#10B98133' }}>
            <p className="metric-label">🟢 BUY Signals</p>
            <p className="metric-value text-buy">{signals.buy_count}</p>
          </div>
          <div className="metric-card" style={{ borderColor: '#EF444433' }}>
            <p className="metric-label">🔴 SELL Signals</p>
            <p className="metric-value text-sell">{signals.sell_count}</p>
          </div>
          <div className="metric-card" style={{ borderColor: '#F59E0B33' }}>
            <p className="metric-label">🟡 HOLD Signals</p>
            <p className="metric-value text-hold">{signals.hold_count}</p>
          </div>
          <div className="metric-card">
            <p className="metric-label">⏰ Last Update</p>
            <p className="text-lg font-bold">{timeAgo(signals.timestamp)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex gap-2">
          <button onClick={() => setIndexFilter('nifty50')} className={`nav-tab ${indexFilter === 'nifty50' ? 'active' : ''}`}>Nifty 50</button>
          <button onClick={() => setIndexFilter('niftybank')} className={`nav-tab ${indexFilter === 'niftybank' ? 'active' : ''}`}>Nifty Bank</button>
        </div>
        <div className="flex gap-2">
          {(['all', 'BUY', 'SELL', 'HOLD'] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`nav-tab capitalize ${filter === f ? 'active' : ''}`}>{f}</button>
          ))}
        </div>
      </div>

      {/* Signals Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="card">
              <div className="skeleton h-4 w-20 mb-2"></div>
              <div className="skeleton h-6 w-32 mb-4"></div>
              <div className="skeleton h-20"></div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredSignals.map((signal: any) => (
            <SignalCard key={signal.stock.symbol} signal={signal} />
          ))}
        </div>
      )}

      {!loading && filteredSignals.length === 0 && (
        <div className="text-center py-12">
          <p style={{ color: '#94A3B8' }}>No signals found for this filter.</p>
        </div>
      )}
    </div>
  );
}
