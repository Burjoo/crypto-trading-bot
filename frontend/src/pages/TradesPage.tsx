import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { History, TrendingUp, TrendingDown, Filter, Download, Search } from 'lucide-react';
import { clsx } from 'clsx';
import { format } from 'date-fns';
import { api } from '../store';

export default function TradesPage() {
  const [statusFilter, setStatusFilter] = useState('');
  const [search, setSearch] = useState('');

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['trades', statusFilter],
    queryFn: () => api.get(`/trades?limit=100${statusFilter ? `&status=${statusFilter}` : ''}`).then(r => r.data),
    refetchInterval: 30_000,
  });

  const trades: any[] = (data?.trades ?? []).filter((t: any) =>
    !search || t.symbol.toLowerCase().includes(search.toLowerCase())
  );

  const closed = trades.filter(t => t.status === 'closed');
  const totalPnl  = closed.reduce((s, t) => s + (t.pnl_usdt ?? 0), 0);
  const wins      = closed.filter(t => (t.pnl_usdt ?? 0) > 0);
  const winRate   = closed.length ? (wins.length / closed.length * 100) : 0;
  const avgPnl    = closed.length ? totalPnl / closed.length : 0;

  const downloadCsv = () => {
    const rows = [
      ['Symbol','Side','Status','Entry Price','Exit Price','Quantity','PnL (USDT)','PnL %','Exit Reason','Opened At','Closed At'],
      ...trades.map(t => [
        t.symbol, t.side, t.status, t.entry_price, t.exit_price ?? '',
        t.quantity, t.pnl_usdt ?? '', t.pnl_pct ?? '', t.exit_reason ?? '',
        t.opened_at, t.closed_at ?? '',
      ])
    ];
    const csv = rows.map(r => r.join(',')).join('\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    a.download = `trades_${Date.now()}.csv`;
    a.click();
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="font-display font-bold text-2xl text-text-primary flex items-center gap-2">
            <History className="w-6 h-6 text-accent-cyan" /> Trade History
          </h1>
          <p className="text-text-secondary text-sm mt-0.5">{data?.total ?? 0} total trades</p>
        </div>
        <button onClick={downloadCsv} className="btn-secondary flex items-center gap-2 text-sm">
          <Download className="w-3.5 h-3.5" /> Export CSV
        </button>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total P&L',   value: `${totalPnl >= 0 ? '+' : ''}$${totalPnl.toFixed(2)}`,  color: totalPnl >= 0 ? 'text-accent-green' : 'text-accent-red' },
          { label: 'Win Rate',    value: `${winRate.toFixed(1)}%`,  color: winRate >= 50 ? 'text-accent-green' : 'text-accent-red' },
          { label: 'Avg P&L',     value: `${avgPnl >= 0 ? '+' : ''}$${avgPnl.toFixed(2)}`, color: avgPnl >= 0 ? 'text-accent-green' : 'text-accent-red' },
          { label: 'Closed Trades', value: closed.length.toString(), color: 'text-text-primary' },
        ].map(s => (
          <div key={s.label} className="card p-4">
            <p className="stat-label">{s.label}</p>
            <p className={clsx('font-display font-bold text-xl mt-1', s.color)}>{s.value}</p>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input value={search} onChange={e => setSearch(e.target.value)}
            className="input pl-9 text-sm" placeholder="Filter by symbol…" />
        </div>
        <div className="flex gap-2">
          {[['', 'All'], ['open', 'Open'], ['closed', 'Closed']].map(([val, label]) => (
            <button key={val} onClick={() => setStatusFilter(val)}
              className={clsx('px-3 py-1.5 rounded text-xs font-medium transition-colors',
                statusFilter === val
                  ? 'bg-accent-cyan/15 text-accent-cyan border border-accent-cyan/30'
                  : 'btn-secondary text-xs py-1.5'
              )}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-bg-border bg-bg-elevated/50">
                {['Symbol','Side','Status','Entry','Exit','Qty','P&L','P&L %','Reason','Opened','Closed'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs text-text-muted uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="border-b border-bg-border">
                    {Array.from({ length: 11 }).map((_, j) => (
                      <td key={j} className="px-4 py-3">
                        <div className="h-4 bg-bg-elevated rounded animate-pulse" />
                      </td>
                    ))}
                  </tr>
                ))
              ) : trades.length === 0 ? (
                <tr>
                  <td colSpan={11} className="px-4 py-16 text-center text-text-muted">
                    <History className="w-8 h-8 opacity-20 mx-auto mb-2" />
                    <p>No trades found</p>
                  </td>
                </tr>
              ) : (
                trades.map((t: any) => {
                  const pnl = t.pnl_usdt ?? 0;
                  const pnlPct = t.pnl_pct ?? 0;
                  return (
                    <tr key={t.id} className="table-row text-sm">
                      <td className="px-4 py-3">
                        <span className="font-mono font-medium text-text-primary">{t.symbol}</span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx('font-medium', t.side === 'buy' ? 'text-accent-green' : 'text-accent-red')}>
                          {t.side.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={clsx('text-xs px-1.5 py-0.5 rounded-full border',
                          t.status === 'open'
                            ? 'text-accent-cyan border-accent-cyan/30 bg-accent-cyan/5'
                            : 'text-text-muted border-bg-border'
                        )}>
                          {t.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-mono text-text-secondary">${t.entry_price?.toFixed(4)}</td>
                      <td className="px-4 py-3 font-mono text-text-secondary">
                        {t.exit_price ? `$${t.exit_price.toFixed(4)}` : <span className="text-text-muted">—</span>}
                      </td>
                      <td className="px-4 py-3 font-mono text-text-muted">{t.quantity?.toFixed(4)}</td>
                      <td className={clsx('px-4 py-3 font-mono font-medium', pnl >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                        {t.status === 'closed' ? `${pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}` : <span className="text-text-muted">—</span>}
                      </td>
                      <td className={clsx('px-4 py-3 font-mono', pnlPct >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                        {t.status === 'closed' ? `${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%` : '—'}
                      </td>
                      <td className="px-4 py-3 text-text-muted text-xs">{t.exit_reason ?? '—'}</td>
                      <td className="px-4 py-3 text-text-muted text-xs whitespace-nowrap">
                        {t.opened_at ? format(new Date(t.opened_at), 'MMM d, HH:mm') : '—'}
                      </td>
                      <td className="px-4 py-3 text-text-muted text-xs whitespace-nowrap">
                        {t.closed_at ? format(new Date(t.closed_at), 'MMM d, HH:mm') : '—'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
