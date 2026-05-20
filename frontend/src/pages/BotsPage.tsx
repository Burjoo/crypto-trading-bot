import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Bot, Play, Square, Plus, Trash2, Settings,
  TrendingUp, TrendingDown, Zap, AlertCircle, ChevronRight,
} from 'lucide-react';
import { clsx } from 'clsx';
import { api } from '../store';
import toast from 'react-hot-toast';

const STRATEGIES = [
  { value: 'ma_crossover', label: 'MA Crossover' },
  { value: 'rsi',          label: 'RSI Strategy' },
  { value: 'macd',         label: 'MACD Momentum' },
  { value: 'breakout',     label: 'Breakout' },
];

const STATUS_CONFIG: Record<string, { dot: string; badge: string; label: string }> = {
  running: { dot: 'dot-green',  badge: 'badge-green',  label: 'Running' },
  stopped: { dot: 'dot-gray',   badge: 'text-text-muted border-bg-border bg-bg-elevated border text-xs px-2 py-0.5 rounded-full', label: 'Stopped' },
  paused:  { dot: 'dot-yellow', badge: 'badge-yellow', label: 'Paused' },
  error:   { dot: 'dot-red',    badge: 'badge-red',    label: 'Error' },
};

export default function BotsPage() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [selectedBot, setSelectedBot] = useState<any>(null);
  const [form, setForm] = useState({
    name: '', exchange_id: '', strategy_type: 'ma_crossover',
    symbol: 'BTC/USDT', timeframe: '1h',
    position_size_usdt: 100, stop_loss_pct: 2, take_profit_pct: 4,
    max_daily_loss_usdt: 500, max_open_trades: 1,
  });

  const { data: botsData, isLoading } = useQuery({
    queryKey: ['bots'],
    queryFn: () => api.get('/bots').then(r => r.data),
    refetchInterval: 15_000,
  });
  const { data: exData } = useQuery({
    queryKey: ['exchanges'],
    queryFn: () => api.get('/exchanges').then(r => r.data),
  });

  const startBot  = useMutation({ mutationFn: (id: string) => api.post(`/bots/${id}/start`), onSuccess: () => { qc.invalidateQueries({queryKey:['bots']}); toast.success('Bot started!'); } });
  const stopBot   = useMutation({ mutationFn: (id: string) => api.post(`/bots/${id}/stop`),  onSuccess: () => { qc.invalidateQueries({queryKey:['bots']}); toast.success('Bot stopped'); } });
  const deleteBot = useMutation({ mutationFn: (id: string) => api.delete(`/bots/${id}`),     onSuccess: () => { qc.invalidateQueries({queryKey:['bots']}); toast.success('Bot deleted'); } });

  const createBot = useMutation({
    mutationFn: () => api.post('/bots', { ...form, strategy_params: {} }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bots'] });
      setShowCreate(false);
      toast.success('Bot created!');
    },
    onError: (err: any) => toast.error(err?.response?.data?.detail ?? 'Failed'),
  });

  const bots = botsData?.bots ?? [];
  const exchanges = exData?.exchanges ?? [];

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display font-bold text-2xl text-text-primary flex items-center gap-2">
            <Bot className="w-6 h-6 text-accent-cyan" /> Trading Bots
          </h1>
          <p className="text-text-secondary text-sm mt-0.5">
            {bots.filter((b: any) => b.status === 'running').length} running · {bots.length} total
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary flex items-center gap-2 text-sm">
          <Plus className="w-4 h-4" /> New Bot
        </button>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-lg p-6 animate-slide-in">
            <h2 className="section-title mb-4">Create Bot</h2>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Bot Name</label>
                  <input value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} className="input" placeholder="My BTC Bot" />
                </div>
                <div>
                  <label className="label">Symbol</label>
                  <input value={form.symbol} onChange={e => setForm(p => ({...p, symbol: e.target.value}))} className="input" placeholder="BTC/USDT" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Exchange</label>
                  <select value={form.exchange_id} onChange={e => setForm(p => ({...p, exchange_id: e.target.value}))} className="input">
                    <option value="">Select exchange…</option>
                    {exchanges.map((e: any) => <option key={e.id} value={e.id}>{e.label} ({e.name})</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Strategy</label>
                  <select value={form.strategy_type} onChange={e => setForm(p => ({...p, strategy_type: e.target.value}))} className="input">
                    {STRATEGIES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Timeframe</label>
                  <select value={form.timeframe} onChange={e => setForm(p => ({...p, timeframe: e.target.value}))} className="input">
                    {['1m','5m','15m','1h','4h','1d'].map(t => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label">Position Size (USDT)</label>
                  <input type="number" value={form.position_size_usdt} onChange={e => setForm(p => ({...p, position_size_usdt: +e.target.value}))} className="input" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label">Stop Loss %</label>
                  <input type="number" value={form.stop_loss_pct} step="0.1" onChange={e => setForm(p => ({...p, stop_loss_pct: +e.target.value}))} className="input" />
                </div>
                <div>
                  <label className="label">Take Profit %</label>
                  <input type="number" value={form.take_profit_pct} step="0.1" onChange={e => setForm(p => ({...p, take_profit_pct: +e.target.value}))} className="input" />
                </div>
              </div>
              <div className="p-3 rounded-lg bg-accent-cyan/5 border border-accent-cyan/20 text-xs text-accent-cyan flex items-start gap-2">
                <Zap className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                All new bots start in <strong>paper trading mode</strong> — no real funds at risk.
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowCreate(false)} className="btn-secondary flex-1">Cancel</button>
              <button
                onClick={() => createBot.mutate()}
                disabled={createBot.isPending || !form.name || !form.exchange_id}
                className="btn-primary flex-1 flex items-center justify-center gap-2"
              >
                {createBot.isPending ? <span className="w-4 h-4 border-2 border-bg-primary/30 border-t-bg-primary rounded-full animate-spin" /> : <Plus className="w-4 h-4" />}
                Create Bot
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Bot grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({length: 3}).map((_, i) => (
            <div key={i} className="card p-5 space-y-3 animate-pulse">
              <div className="h-5 bg-bg-elevated rounded w-2/3" />
              <div className="h-4 bg-bg-elevated rounded w-1/2" />
              <div className="h-8 bg-bg-elevated rounded" />
            </div>
          ))}
        </div>
      ) : bots.length === 0 ? (
        <div className="card p-12 flex flex-col items-center justify-center text-text-muted gap-3">
          <Bot className="w-12 h-12 opacity-20" />
          <p className="font-medium text-text-secondary">No bots yet</p>
          <p className="text-sm">Create your first trading bot to get started</p>
          <button onClick={() => setShowCreate(true)} className="btn-primary text-sm mt-2 flex items-center gap-2">
            <Plus className="w-4 h-4" /> Create Bot
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {bots.map((bot: any) => {
            const sc = STATUS_CONFIG[bot.status] ?? STATUS_CONFIG.stopped;
            const pnlPos = (bot.total_pnl_usdt ?? 0) >= 0;
            return (
              <div key={bot.id} className="card p-5 flex flex-col gap-4 hover:border-bg-border/80 transition-all group">
                {/* Header */}
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <span className={sc.dot} />
                    <div className="min-w-0">
                      <p className="font-medium text-text-primary truncate">{bot.name}</p>
                      <p className="text-xs text-text-muted font-mono">{bot.symbol} · {bot.timeframe}</p>
                    </div>
                  </div>
                  <span className={sc.badge}>{sc.label}</span>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="text-center p-2 rounded bg-bg-elevated">
                    <p className={clsx('font-mono font-semibold text-sm', pnlPos ? 'text-accent-green' : 'text-accent-red')}>
                      {pnlPos ? '+' : ''}${bot.total_pnl_usdt?.toFixed(2)}
                    </p>
                    <p className="text-2xs text-text-muted mt-0.5">Total P&L</p>
                  </div>
                  <div className="text-center p-2 rounded bg-bg-elevated">
                    <p className="font-mono font-semibold text-sm text-text-primary">{bot.win_rate_pct ?? 0}%</p>
                    <p className="text-2xs text-text-muted mt-0.5">Win Rate</p>
                  </div>
                  <div className="text-center p-2 rounded bg-bg-elevated">
                    <p className="font-mono font-semibold text-sm text-text-primary">{bot.total_trades ?? 0}</p>
                    <p className="text-2xs text-text-muted mt-0.5">Trades</p>
                  </div>
                </div>

                {/* Risk params */}
                <div className="flex gap-2 text-xs text-text-muted">
                  {bot.stop_loss_pct && <span className="badge-red">SL {bot.stop_loss_pct}%</span>}
                  {bot.take_profit_pct && <span className="badge-green">TP {bot.take_profit_pct}%</span>}
                  <span className="badge-cyan">${bot.position_size_usdt}</span>
                </div>

                {bot.error_message && (
                  <div className="flex items-start gap-2 p-2 rounded bg-accent-red/5 border border-accent-red/20">
                    <AlertCircle className="w-3.5 h-3.5 text-accent-red flex-shrink-0 mt-0.5" />
                    <p className="text-xs text-accent-red">{bot.error_message}</p>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-1 border-t border-bg-border">
                  {bot.status !== 'running' ? (
                    <button
                      onClick={() => startBot.mutate(bot.id)}
                      disabled={startBot.isPending}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-accent-green/10
                        text-accent-green border border-accent-green/20 text-sm font-medium
                        hover:bg-accent-green/20 transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" /> Start
                    </button>
                  ) : (
                    <button
                      onClick={() => stopBot.mutate(bot.id)}
                      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-accent-yellow/10
                        text-accent-yellow border border-accent-yellow/20 text-sm font-medium
                        hover:bg-accent-yellow/20 transition-colors"
                    >
                      <Square className="w-3.5 h-3.5" /> Stop
                    </button>
                  )}
                  <button
                    onClick={() => { if (confirm('Delete this bot?')) deleteBot.mutate(bot.id); }}
                    className="p-2 rounded-lg text-text-muted hover:text-accent-red hover:bg-accent-red/10 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
