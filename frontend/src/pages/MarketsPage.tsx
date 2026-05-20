import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ComposedChart, Bar, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { TrendingUp, TrendingDown, RefreshCw, BarChart3, Search } from 'lucide-react';
import { clsx } from 'clsx';
import { api } from '../store';
import { format } from 'date-fns';

const SYMBOLS = ['BTC/USDT','ETH/USDT','BNB/USDT','SOL/USDT','XRP/USDT',
                 'ADA/USDT','AVAX/USDT','DOT/USDT','MATIC/USDT','LINK/USDT'];
const TIMEFRAMES = ['15m','1h','4h','1d'];

function CandleTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  const chg = d.close - d.open;
  return (
    <div className="bg-bg-card border border-bg-border rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-text-muted mb-1.5">{d.dateStr}</p>
      <div className="space-y-0.5 font-mono">
        <p className="text-text-secondary">O: <span className="text-text-primary">${d.open?.toLocaleString()}</span></p>
        <p className="text-text-secondary">H: <span className="text-accent-green">${d.high?.toLocaleString()}</span></p>
        <p className="text-text-secondary">L: <span className="text-accent-red">${d.low?.toLocaleString()}</span></p>
        <p className="text-text-secondary">C: <span className="text-text-primary">${d.close?.toLocaleString()}</span></p>
        <p className={clsx('font-medium', chg >= 0 ? 'text-accent-green' : 'text-accent-red')}>
          {chg >= 0 ? '+' : ''}{chg.toFixed(2)} ({((chg / d.open) * 100).toFixed(2)}%)
        </p>
      </div>
    </div>
  );
}

// Custom candlestick rendered as a bar chart using composed chart
function CustomCandlestick(props: any) {
  const { x, y, width, height, open, close, low, high } = props;
  const isGreen = close >= open;
  const color = isGreen ? '#00ff87' : '#ff3b6b';
  const bodyTop = Math.min(open, close);
  const bodyH   = Math.max(Math.abs(close - open), 1);

  return (
    <g>
      {/* Wick */}
      <line x1={x + width / 2} y1={y} x2={x + width / 2} y2={y + height} stroke={color} strokeWidth={1} opacity={0.6} />
      {/* Body */}
      <rect x={x + 1} y={y + (bodyTop - low) / (high - low) * height * -1 + height}
        width={width - 2} height={Math.max(bodyH / (high - low) * height, 2)}
        fill={color} fillOpacity={0.85} rx={1} />
    </g>
  );
}

export default function MarketsPage() {
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT');
  const [timeframe, setTimeframe] = useState('1h');
  const [search, setSearch] = useState('');

  const { data: overview, isFetching: ovFetching, refetch } = useQuery({
    queryKey: ['market-overview'],
    queryFn: () => api.get('/market/overview').then(r => r.data),
    refetchInterval: 30_000,
  });

  const { data: ohlcvData, isLoading: chartLoading } = useQuery({
    queryKey: ['ohlcv', selectedSymbol, timeframe],
    queryFn: () => api.get(`/market/ohlcv?symbol=${encodeURIComponent(selectedSymbol)}&timeframe=${timeframe}&limit=120`).then(r => r.data),
    refetchInterval: 60_000,
  });

  const markets: any[] = overview?.markets ?? [];
  const filtered = markets.filter(m =>
    m.symbol.toLowerCase().includes(search.toLowerCase())
  );

  const candles = (ohlcvData?.candles ?? []).map((c: any) => ({
    ...c,
    dateStr: format(new Date(c.timestamp), timeframe === '1d' ? 'MMM d' : 'MMM d HH:mm'),
    // For the custom bar rendering we need high-low range as the bar height
    range: c.high - c.low,
    bodySize: Math.abs(c.close - c.open),
    isGreen: c.close >= c.open,
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-text-primary flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-accent-cyan" /> Markets
          </h1>
          <p className="text-text-secondary text-sm mt-0.5">Live cryptocurrency prices and charts</p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw className={clsx('w-3.5 h-3.5', ovFetching && 'animate-spin')} /> Refresh
        </button>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Symbol list */}
        <div className="card p-0 overflow-hidden">
          <div className="p-4 border-b border-bg-border">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                className="input pl-9 text-sm"
                placeholder="Search markets…"
              />
            </div>
          </div>
          <div className="overflow-y-auto max-h-[520px]">
            {(filtered.length > 0 ? filtered : markets).map((m: any) => {
              const chg = m.change_pct_24h ?? 0;
              const isSelected = selectedSymbol === m.symbol;
              return (
                <button
                  key={m.symbol}
                  onClick={() => setSelectedSymbol(m.symbol)}
                  className={clsx(
                    'w-full flex items-center justify-between px-4 py-3 border-b border-bg-border last:border-0 text-left transition-colors',
                    isSelected ? 'bg-accent-cyan/5 border-l-2 border-l-accent-cyan' : 'hover:bg-bg-elevated'
                  )}
                >
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-bg-elevated border border-bg-border flex items-center justify-center flex-shrink-0">
                      <span className="text-2xs font-bold text-text-secondary">
                        {m.symbol.split('/')[0].slice(0, 3)}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-text-primary">{m.symbol.replace('/USDT', '')}</p>
                      <p className="text-2xs text-text-muted">Vol ${(m.volume_24h / 1e6).toFixed(1)}M</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm text-text-primary">
                      ${m.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </p>
                    <p className={clsx('text-xs font-mono flex items-center gap-0.5 justify-end', chg >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                      {chg >= 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                      {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Chart panel */}
        <div className="xl:col-span-2 card p-5 space-y-4">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h2 className="font-display font-semibold text-lg text-text-primary">{selectedSymbol}</h2>
              {markets.find((m: any) => m.symbol === selectedSymbol) && (() => {
                const m = markets.find((m: any) => m.symbol === selectedSymbol);
                const chg = m.change_pct_24h ?? 0;
                return (
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="font-mono font-bold text-xl text-text-primary">
                      ${m.price?.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                    <span className={clsx('text-sm font-mono', chg >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                      {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
                    </span>
                  </div>
                );
              })()}
            </div>
            <div className="flex gap-1">
              {TIMEFRAMES.map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={clsx(
                    'px-3 py-1.5 rounded text-xs font-medium transition-colors',
                    timeframe === tf
                      ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30'
                      : 'text-text-muted hover:text-text-secondary hover:bg-bg-elevated'
                  )}
                >
                  {tf}
                </button>
              ))}
            </div>
          </div>

          {/* Stats row */}
          {markets.find((m: any) => m.symbol === selectedSymbol) && (() => {
            const m = markets.find((m: any) => m.symbol === selectedSymbol);
            return (
              <div className="grid grid-cols-3 gap-3">
                {[
                  { label: '24h High', value: `$${m.high_24h?.toLocaleString(undefined,{minimumFractionDigits:2})}`, color: 'text-accent-green' },
                  { label: '24h Low',  value: `$${m.low_24h?.toLocaleString(undefined,{minimumFractionDigits:2})}`,  color: 'text-accent-red' },
                  { label: '24h Volume', value: `$${(m.volume_24h / 1e6).toFixed(1)}M`, color: 'text-text-primary' },
                ].map(s => (
                  <div key={s.label} className="bg-bg-elevated rounded-lg p-3 text-center">
                    <p className="text-2xs text-text-muted uppercase tracking-wider mb-1">{s.label}</p>
                    <p className={clsx('font-mono font-semibold text-sm', s.color)}>{s.value}</p>
                  </div>
                ))}
              </div>
            );
          })()}

          {/* Price chart using line chart (OHLCV simplified) */}
          {chartLoading ? (
            <div className="h-[300px] flex items-center justify-center">
              <span className="w-8 h-8 border-2 border-bg-border border-t-accent-cyan rounded-full animate-spin" />
            </div>
          ) : candles.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <ComposedChart data={candles} margin={{ top: 5, right: 5, left: 0, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="dateStr"
                  tick={{ fontSize: 10 }}
                  interval={Math.floor(candles.length / 8)}
                />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 10 }}
                  tickFormatter={(v) => `$${(v/1000).toFixed(1)}k`}
                  width={60}
                />
                <Tooltip content={<CandleTooltip />} />
                {/* Volume bars at bottom */}
                <Bar dataKey="volume" fill="#1e2d45" opacity={0.4} yAxisId={1} />
                {/* Close price line */}
                <Line
                  type="monotone"
                  dataKey="close"
                  stroke="#00d4ff"
                  strokeWidth={1.5}
                  dot={false}
                  activeDot={{ r: 3, fill: '#00d4ff' }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-text-muted">
              <p>No chart data</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
