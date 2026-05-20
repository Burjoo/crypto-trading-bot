import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp, TrendingDown, Bot, Zap, DollarSign,
  BarChart3, Activity, Target, AlertCircle, RefreshCw,
} from 'lucide-react';
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { clsx } from 'clsx';
import { api } from '../store';
import { format } from 'date-fns';

// ── API fetchers ───────────────────────────────────────────────────────────
const fetchPortfolio = () => api.get('/portfolio/summary').then(r => r.data);
const fetchTrades    = () => api.get('/trades?limit=10').then(r => r.data);
const fetchMarket    = () => api.get('/market/overview').then(r => r.data);

// ── Stat Card ─────────────────────────────────────────────────────────────
function StatCard({
  label, value, sub, icon: Icon, color = 'cyan', trend
}: {
  label: string; value: string; sub?: string;
  icon: React.ElementType; color?: string; trend?: 'up' | 'down' | null;
}) {
  const colors: Record<string, string> = {
    cyan:   'text-accent-cyan   bg-accent-cyan/10   border-accent-cyan/20',
    green:  'text-accent-green  bg-accent-green/10  border-accent-green/20',
    red:    'text-accent-red    bg-accent-red/10    border-accent-red/20',
    yellow: 'text-accent-yellow bg-accent-yellow/10 border-accent-yellow/20',
    purple: 'text-accent-purple bg-accent-purple/10 border-accent-purple/20',
  };
  const cls = colors[color] ?? colors.cyan;
  const [textCls] = cls.split(' ');

  return (
    <div className="card p-5 flex flex-col gap-3 hover:border-bg-border/60 transition-colors">
      <div className="flex items-start justify-between">
        <p className="stat-label">{label}</p>
        <div className={clsx('w-8 h-8 rounded-lg border flex items-center justify-center flex-shrink-0', cls)}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div>
        <p className={clsx('font-display font-bold text-2xl', textCls)}>{value}</p>
        {sub && (
          <p className={clsx('text-xs mt-0.5 flex items-center gap-1',
            trend === 'up' ? 'text-accent-green' : trend === 'down' ? 'text-accent-red' : 'text-text-muted'
          )}>
            {trend === 'up' && <TrendingUp className="w-3 h-3" />}
            {trend === 'down' && <TrendingDown className="w-3 h-3" />}
            {sub}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────
function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-bg-card border border-bg-border rounded-lg px-3 py-2 shadow-xl text-xs">
      <p className="text-text-muted mb-1">{label}</p>
      {payload.map((p: any) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono">
          {p.name}: {typeof p.value === 'number' ? `$${p.value.toFixed(2)}` : p.value}
        </p>
      ))}
    </div>
  );
}

// ── Trade Row ──────────────────────────────────────────────────────────────
function TradeRow({ trade }: { trade: any }) {
  const pnl = trade.pnl_usdt ?? 0;
  return (
    <tr className="table-row">
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <span className={clsx('w-1.5 h-1.5 rounded-full flex-shrink-0',
            trade.side === 'buy' ? 'bg-accent-green' : 'bg-accent-red'
          )} />
          <span className="font-mono text-sm text-text-primary">{trade.symbol}</span>
        </div>
      </td>
      <td className="px-4 py-3">
        <span className={clsx('badge text-xs font-medium px-1.5 py-0.5 rounded',
          trade.side === 'buy'
            ? 'bg-accent-green/10 text-accent-green'
            : 'bg-accent-red/10 text-accent-red'
        )}>
          {trade.side.toUpperCase()}
        </span>
      </td>
      <td className="px-4 py-3 font-mono text-sm text-text-secondary">
        ${(trade.entry_price ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
      </td>
      <td className={clsx('px-4 py-3 font-mono text-sm font-medium', pnl >= 0 ? 'text-accent-green' : 'text-accent-red')}>
        {pnl >= 0 ? '+' : ''}{pnl.toFixed(2)}
      </td>
      <td className="px-4 py-3">
        <span className={clsx('text-xs px-1.5 py-0.5 rounded-full border',
          trade.status === 'open'
            ? 'text-accent-cyan border-accent-cyan/30 bg-accent-cyan/5'
            : 'text-text-muted border-bg-border'
        )}>
          {trade.status}
        </span>
      </td>
      <td className="px-4 py-3 text-xs text-text-muted">
        {trade.opened_at ? format(new Date(trade.opened_at), 'MMM d, HH:mm') : '—'}
      </td>
    </tr>
  );
}

// ── Market Row ─────────────────────────────────────────────────────────────
function MarketRow({ item }: { item: any }) {
  const chg = item.change_pct_24h ?? 0;
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-bg-border last:border-0">
      <div className="flex items-center gap-2">
        <div className="w-7 h-7 rounded-full bg-bg-elevated border border-bg-border flex items-center justify-center">
          <span className="text-2xs font-bold text-text-secondary">{item.symbol.split('/')[0].slice(0,3)}</span>
        </div>
        <div>
          <p className="text-sm font-medium text-text-primary">{item.symbol.replace('/USDT','')}</p>
          <p className="text-2xs text-text-muted">Vol: {(item.volume_24h / 1e6).toFixed(1)}M</p>
        </div>
      </div>
      <div className="text-right">
        <p className="font-mono text-sm text-text-primary">
          ${item.price?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
        </p>
        <p className={clsx('text-xs font-mono', chg >= 0 ? 'text-accent-green' : 'text-accent-red')}>
          {chg >= 0 ? '+' : ''}{chg.toFixed(2)}%
        </p>
      </div>
    </div>
  );
}

// ── Main Dashboard ─────────────────────────────────────────────────────────
export default function DashboardPage() {
  const portfolio = useQuery({ queryKey: ['portfolio'], queryFn: fetchPortfolio, refetchInterval: 30_000 });
  const trades    = useQuery({ queryKey: ['trades-recent'], queryFn: fetchTrades });
  const market    = useQuery({ queryKey: ['market-overview'], queryFn: fetchMarket, refetchInterval: 60_000 });

  const p = portfolio.data;
  const equityData = p?.equity_history ?? [];
  const recentTrades = trades.data?.trades ?? [];
  const markets = market.data?.markets ?? [];

  const pnlPositive = (p?.today_pnl_usdt ?? 0) >= 0;
  const totalPositive = (p?.total_pnl_usdt ?? 0) >= 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ── Header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-text-primary">Dashboard</h1>
          <p className="text-text-secondary text-sm mt-0.5">
            {new Date().toLocaleDateString('en-US', { weekday:'long', month:'long', day:'numeric' })}
          </p>
        </div>
        <button
          onClick={() => { portfolio.refetch(); market.refetch(); }}
          className="btn-secondary flex items-center gap-2 text-sm"
        >
          <RefreshCw className={clsx('w-3.5 h-3.5', portfolio.isFetching && 'animate-spin')} />
          Refresh
        </button>
      </div>

      {/* ── Stats Grid ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total P&L"
          value={`${totalPositive ? '+' : ''}$${(p?.total_pnl_usdt ?? 0).toFixed(2)}`}
          sub={`${p?.total_trades ?? 0} closed trades`}
          icon={DollarSign}
          color={totalPositive ? 'green' : 'red'}
          trend={totalPositive ? 'up' : 'down'}
        />
        <StatCard
          label="Today's P&L"
          value={`${pnlPositive ? '+' : ''}$${(p?.today_pnl_usdt ?? 0).toFixed(2)}`}
          sub={`${p?.today_trades ?? 0} trades today`}
          icon={TrendingUp}
          color={pnlPositive ? 'green' : 'red'}
          trend={pnlPositive ? 'up' : 'down'}
        />
        <StatCard
          label="Win Rate"
          value={`${p?.win_rate_pct ?? 0}%`}
          sub="All time"
          icon={Target}
          color="cyan"
        />
        <StatCard
          label="Active Bots"
          value={`${p?.active_bots ?? 0} / ${p?.total_bots ?? 0}`}
          sub={`${p?.open_positions ?? 0} open positions`}
          icon={Bot}
          color="purple"
        />
      </div>

      {/* ── Charts + Market ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Equity curve */}
        <div className="lg:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Equity Curve</h2>
            <span className="badge-cyan text-xs">30 days</span>
          </div>
          {equityData.length > 0 ? (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={equityData}>
                <defs>
                  <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v) => format(new Date(v), 'MMM d')} />
                <YAxis tick={{ fontSize: 10 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="pnl" name="Daily P&L"
                  stroke="#00d4ff" strokeWidth={2} fill="url(#pnlGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex flex-col items-center justify-center text-text-muted gap-2">
              <BarChart3 className="w-8 h-8 opacity-30" />
              <p className="text-sm">No trade history yet</p>
              <p className="text-xs">Start a bot to see your equity curve</p>
            </div>
          )}
        </div>

        {/* Market overview */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="section-title">Markets</h2>
            <span className={clsx('text-xs flex items-center gap-1',
              market.isFetching ? 'text-accent-yellow' : 'text-accent-green'
            )}>
              <span className={clsx('w-1.5 h-1.5 rounded-full', market.isFetching ? 'dot-yellow' : 'dot-green')} />
              {market.isFetching ? 'Updating' : 'Live'}
            </span>
          </div>
          <div className="space-y-0 overflow-y-auto max-h-[240px]">
            {markets.length > 0
              ? markets.map((m: any) => <MarketRow key={m.symbol} item={m} />)
              : Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="py-3 border-b border-bg-border">
                    <div className="h-4 bg-bg-elevated rounded animate-pulse w-3/4 mb-1" />
                    <div className="h-3 bg-bg-elevated rounded animate-pulse w-1/2" />
                  </div>
                ))}
          </div>
        </div>
      </div>

      {/* ── Bots + Trades ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Bot performance */}
        <div className="card p-5">
          <h2 className="section-title mb-4">Bot Performance</h2>
          {(p?.bot_summary?.length ?? 0) > 0 ? (
            <div className="space-y-3">
              {p.bot_summary.map((bot: any) => (
                <div key={bot.id} className="flex items-center justify-between p-3 bg-bg-elevated rounded-lg border border-bg-border">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={clsx('flex-shrink-0', {
                      'dot-green': bot.status === 'running',
                      'dot-red':   bot.status === 'error',
                      'dot-gray':  bot.status === 'stopped',
                    })} />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-text-primary truncate">{bot.name}</p>
                      <p className="text-xs text-text-muted font-mono">{bot.symbol}</p>
                    </div>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className={clsx('text-sm font-mono font-medium', (bot.total_pnl_usdt ?? 0) >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                      {(bot.total_pnl_usdt ?? 0) >= 0 ? '+' : ''}${bot.total_pnl_usdt?.toFixed(2)}
                    </p>
                    <p className="text-xs text-text-muted">{bot.total_trades} trades</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-40 flex flex-col items-center justify-center text-text-muted gap-2">
              <Bot className="w-8 h-8 opacity-30" />
              <p className="text-sm">No bots created</p>
            </div>
          )}
        </div>

        {/* Recent trades */}
        <div className="lg:col-span-2 card overflow-hidden">
          <div className="flex items-center justify-between p-5 border-b border-bg-border">
            <h2 className="section-title">Recent Trades</h2>
            <span className="badge-cyan">Latest 10</span>
          </div>
          {recentTrades.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-bg-border">
                    {['Symbol','Side','Entry','P&L','Status','Time'].map(h => (
                      <th key={h} className="px-4 py-2.5 text-left text-xs text-text-muted uppercase tracking-wider">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recentTrades.map((t: any) => <TradeRow key={t.id} trade={t} />)}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="h-48 flex flex-col items-center justify-center text-text-muted gap-2">
              <Activity className="w-8 h-8 opacity-30" />
              <p className="text-sm">No trades yet</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
