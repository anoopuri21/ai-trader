'use client';

import { useState, useEffect, useRef } from 'react';
import { createChart, IChartApi, ISeriesApi, CandlestickData, LineData, Time } from 'lightweight-charts';
import { api } from '@/lib/api';
import { cn, formatCurrency, formatPercent, getChangeColor, getSignalBgColor, getSignalTextColor, timeAgo } from '@/lib/utils';
import type { SignalsResponse, IndexData, TradingSignal } from '@/types';

// Chart Component
function StockChart({ symbol }: { symbol: string }) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candlestickSeriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const smaSeriesRef = useRef<ISeriesApi<'Line'> | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#1E293B' },
        textColor: '#94A3B8',
      },
      grid: {
        vertLines: { color: '#334155' },
        horzLines: { color: '#334155' },
      },
      width: chartContainerRef.current.clientWidth,
      height: 300,
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#10B981',
      downColor: '#EF4444',
      borderUpColor: '#10B981',
      borderDownColor: '#EF4444',
      wickUpColor: '#10B981',
      wickDownColor: '#EF4444',
    });

    const smaSeries = chart.addLineSeries({
      color: '#3B82F6',
      lineWidth: 2,
    });

    chartRef.current = chart;
    candlestickSeriesRef.current = candlestickSeries;
    smaSeriesRef.current = smaSeries;

    // Fetch data
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
            open: quote.open[i] as number,
            high: quote.high[i] as number,
            low: quote.low[i] as number,
            close: quote.close[i] as number,
          })).filter(d => d.close !== null);

          const closes = candleData.map(d => d.close);
          const sma20 = candleData.map((d, i) => {
            const start = Math.max(0, i - 19);
            const slice = closes.slice(start, i + 1);
            const avg = slice.reduce((a, b) => a + b, 0) / slice.length;
            return { time: d.time, value: avg };
          });

          candlestickSeries.setData(candleData);
          smaSeries.setData(sma20);
          chart.timeScale().fitContent();
        }
      } catch (err) {
        console.error('Chart data error:', err);
      }
    };

    fetchData();

    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [symbol]);

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
}

// Signal Card Component
function SignalCard({ signal }: { signal: TradingSignal }) {
  const [showChart, setShowChart] = useState(false);
  
  return (
    <div className="card-hover">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold text-white">{signal.stock.symbol}</h3>
          <p className="text-xs text-gray-400">{signal.stock.name}</p>
        </div>
        <div className={cn('badge', getSignalBgColor(signal.signal), 'text-white')}>
          {signal.signal}
        </div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <p className="text-xs text-gray-400">Price</p>
          <p className="text-lg font-semibold text-white">{formatCurrency(signal.stock.current_price)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-400">Change</p>
          <p className={cn('text-lg font-semibold', getChangeColor(signal.stock.change_percent))}>
            {formatPercent(signal.stock.change_percent)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
        <div className="bg-dark-bg rounded p-2">
          <p className="text-gray-400">RSI</p>
          <p className="text-white font-medium">{signal.indicators.rsi?.toFixed(1) || 'N/A'}</p>
        </div>
        <div className="bg-dark-bg rounded p-2">
          <p className="text-gray-400">SMA20</p>
          <p className="text-white font-medium">{signal.indicators.sma_20?.toFixed(0) || 'N/A'}</p>
        </div>
        <div className="bg-dark-bg rounded p-2">
          <p className="text-gray-400">Confidence</p>
          <p className={cn('font-medium', getSignalTextColor(signal.signal))}>
            {signal.confidence}%
          </p>
        </div>
      </div>

      {signal.entry_price && (
        <div className="grid grid-cols-3 gap-2 mb-3 text-xs">
          <div className="bg-dark-bg rounded p-2">
            <p className="text-gray-400">Entry</p>
            <p className="text-buy font-medium">{formatCurrency(signal.entry_price)}</p>
          </div>
          <div className="bg-dark-bg rounded p-2">
            <p className="text-gray-400">Target</p>
            <p className="text-buy font-medium">{formatCurrency(signal.target_price || 0)}</p>
          </div>
          <div className="bg-dark-bg rounded p-2">
            <p className="text-gray-400">Stop</p>
            <p className="text-sell font-medium">{formatCurrency(signal.stop_loss || 0)}</p>
          </div>
        </div>
      )}

      <button
        onClick={() => setShowChart(!showChart)}
        className="w-full btn btn-primary text-sm py-2"
      >
        {showChart ? 'Hide Chart' : 'View Chart'}
      </button>

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
  const [signals, setSignals] = useState<SignalsResponse | null>(null);
  const [indices, setIndices] = useState<Record<string, IndexData>>({});
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'buy' | 'sell' | 'hold'>('all');
  const [indexFilter, setIndexFilter] = useState<'nifty50' | 'niftybank'>('nifty50');

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [signalsData, indicesData] = await Promise.all([
          api.signals.all(indexFilter),
          api.prices.indices(),
        ]);
        setSignals(signalsData);
        setIndices(indicesData.indices || {});
      } catch (err) {
        console.error('Fetch error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [indexFilter]);

  const filteredSignals = signals?.signals.filter(s => {
    if (filter === 'all') return true;
    return s.signal === filter.toUpperCase();
  }) || [];

  return (
    <div className="container mx-auto px-4 py-6">
      {/* Index Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {indices['^NSEI'] && (
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-gray-400 text-sm">Nifty 50</h2>
                <p className="text-2xl font-bold text-white">
                  {indices['^NSEI'].current_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className={cn('text-xl font-semibold', getChangeColor(indices['^NSEI'].change_percent))}>
                {formatPercent(indices['^NSEI'].change_percent)}
              </div>
            </div>
          </div>
        )}
        {indices['^NSEBANK'] && (
          <div className="card">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-gray-400 text-sm">Nifty Bank</h2>
                <p className="text-2xl font-bold text-white">
                  {indices['^NSEBANK'].current_value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className={cn('text-xl font-semibold', getChangeColor(indices['^NSEBANK'].change_percent))}>
                {formatPercent(indices['^NSEBANK'].change_percent)}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Summary Cards */}
      {signals && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="card bg-buy/10 border-buy/30">
            <p className="text-xs text-gray-400">BUY Signals</p>
            <p className="text-3xl font-bold text-buy">{signals.buy_count}</p>
          </div>
          <div className="card bg-sell/10 border-sell/30">
            <p className="text-xs text-gray-400">SELL Signals</p>
            <p className="text-3xl font-bold text-sell">{signals.sell_count}</p>
          </div>
          <div className="card bg-hold/10 border-hold/30">
            <p className="text-xs text-gray-400">HOLD Signals</p>
            <p className="text-3xl font-bold text-hold">{signals.hold_count}</p>
          </div>
          <div className="card">
            <p className="text-xs text-gray-400">Last Update</p>
            <p className="text-lg font-semibold text-white">{timeAgo(signals.timestamp)}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-4 mb-6">
        <div className="flex gap-2">
          <button
            onClick={() => setIndexFilter('nifty50')}
            className={cn('btn', indexFilter === 'nifty50' ? 'btn-primary' : 'bg-dark-card')}
          >
            Nifty 50
          </button>
          <button
            onClick={() => setIndexFilter('niftybank')}
            className={cn('btn', indexFilter === 'niftybank' ? 'btn-primary' : 'bg-dark-card')}
          >
            Nifty Bank
          </button>
        </div>
        <div className="flex gap-2">
          {['all', 'buy', 'sell', 'hold'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f as typeof filter)}
              className={cn('btn capitalize', filter === f ? 'btn-primary' : 'bg-dark-card')}
            >
              {f}
            </button>
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
          {filteredSignals.map((signal) => (
            <SignalCard key={signal.stock.symbol} signal={signal} />
          ))}
        </div>
      )}

      {!loading && filteredSignals.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-400">No signals found for this filter.</p>
        </div>
      )}
    </div>
  );
}
