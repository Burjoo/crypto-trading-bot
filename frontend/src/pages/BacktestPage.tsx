import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  AreaChart, Area, LineChart, Line, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine,
} from 'recharts';
import {
  FlaskConical, TrendingUp, TrendingDown, Target, BarChart3,
  AlertTriangle, CheckCircle, Play, ChevronDown,
} from 'lucide-react';
import { clsx } from 'clsx';
import { api } from '../store';
import toast from 'react-hot-toast';

const schema = z.object({
  strategy_type:     z.enum(['ma_crossover', 'rsi', 'macd', 'breakout']),
  symbol:            z.string().min(1),
  timeframe:         z.enum(['15m','1h','4h','1d']),
  exchange:          z.enum(['binance','bybit']),
  limit:             z.coerce.number().min(100).max(5000),
  initial_capital:   z.coerce.number().min(100),
  commission_pct:    z.coerce.number().min(0).max(1),
  stop_loss_pct:     z.coerce.number().min(0.1).max(50),
  take_profit_pct:   z.coerce.number().min(0.1).max(200),
  risk_per_trade_pct:z.coerce.number().min(0.1).max(10),
  // MA params
  fast_period:       z.coerce.number().optional(),
  slow_period:       z.coerce.number().optional(),
  // RSI params
  rsi_period:        z.coerce.number().optional(),
  oversold:          z.coerce.number().optional(),
  overbought:        z.coerce.number().optional(),
});
type FormData = z.infer<typeof schema>;

function MetricCard({ label, value, good, note }: { label: string; value: string; good?: boolean; note?: string }) {
  return (
    <div className="card p-4">
      <p className="stat-label">{label}</p>
      <p className={clsx('font-display font-bold text-xl mt-1',
        good === true  ? 'text-accent-green' :
        good === false ? 'text-accent-red'   : 'text-text-primary'
      )}>
        {value}
      </p>
      {note && <p className="text-xs text-text-muted mt-0.5">{note}</p>}
    </div>
  );
}

export default function BacktestPage() {
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'equity'|'drawdown'|'trades'>('equity');

  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      strategy_type: 'ma_crossover',
      symbol: 'BTC/USDT',
      timeframe: '1h',
      exchange: 'binance',
      limit: 500,
      initial_capital: 10000,
      commission_pct: 0.1,
      stop_loss_pct: 2,
      take_profit_pct: 4,
      risk_per_trade_pct: 1,
      fast_period: 9,
      slow_period: 21,
      rsi_period: 14,
      oversold: 30,
      overbought: 70,
    },
  });

  const strategyType = watch('strategy_type');

  const onSubmit = async (data: FormData) => {
    setLoading(true);
    try {
      const strategyParams: any = {};
      if (data.strategy_type === 'ma_crossover') {
        strategyParams.fast_period = data.fast_period;
        strategyParams.slow_period = data.slow_period;
      } else if (data.strategy_type === 'rsi') {
        strategyParams.rsi_period  = data.rsi_period;
        strategyParams.oversold    = data.oversold;
        strategyParams.overbought  = data.overbought;
      }

      const res = await api.post('/backtest/run', {
        strategy_type:      data.strategy_type,
        strategy_params:    strategyParams,
        symbol:             data.symbol,
        timeframe:          data.timeframe,
        exchange:           data.exchange,
        limit:              data.limit,
        initial_capital:    data.initial_capital,
        commission_pct:     data.commission_pct,
        stop_loss_pct:      data.stop_loss_pct,
        take_profit_pct:    data.take_profit_pct,
        risk_per_trade_pct: data.risk_per_trade_pct,
      });
      setResult(res.data);
      toast.success('Backtest complete!');
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Backtest failed');
    } finally {
      setLoading(false);
    }
  };

  const perf = result?.performance;
  const trds = result?.trades;

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="font-display font-bold text-2xl text-text-primary flex items-center gap-2">
          <FlaskConical className="w-6 h-6 text-accent-cyan" /> Backtesting
        </h1>
        <p className="text-text-secondary text-sm mt-1">Test your strategies against historical market data</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* ── Config form ── */}
        <div className="card p-6 space-y-4">
          <h2 className="section-title">Configuration</h2>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Strategy */}
            <div>
              <label className="label">Strategy</label>
              <select {...register('strategy_type')} className="input">
                <option value="ma_crossover">Moving Average Crossover</option>
                <option value="rsi">RSI Mean Reversion</option>
                <option value="macd">MACD Momentum</option>
                <option value="breakout">Breakout</option>
              </select>
            </div>

            {/* Symbol & Timeframe */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Symbol</label>
                <input {...register('symbol')} className="input" placeholder="BTC/USDT" />
              </div>
              <div>
                <label className="label">Timeframe</label>
                <select {...register('timeframe')} className="input">
                  {['15m','1h','4h','1d'].map(t => <option key={t}>{t}</option>)}
                </select>
              </div>
            </div>

            {/* Exchange & Candles */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Exchange</label>
                <select {...register('exchange')} className="input">
                  <option value="binance">Binance</option>
                  <option value="bybit">Bybit</option>
                </select>
              </div>
              <div>
                <label className="label">Candles</label>
                <input {...register('limit')} type="number" className="input" />
              </div>
            </div>

            {/* Capital */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Capital (USDT)</label>
                <input {...register('initial_capital')} type="number" className="input" />
              </div>
              <div>
                <label className="label">Risk / Trade %</label>
                <input {...register('risk_per_trade_pct')} type="number" step="0.1" className="input" />
              </div>
            </div>

            {/* Stop/TP */}
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Stop Loss %</label>
                <input {...register('stop_loss_pct')} type="number" step="0.1" className="input" />
              </div>
              <div>
                <label className="label">Take Profit %</label>
                <input {...register('take_profit_pct')} type="number" step="0.1" className="input" />
              </div>
            </div>

            {/* Strategy-specific params */}
            {strategyType === 'ma_crossover' && (
              <div className="p-3 rounded-lg bg-bg-elevated border border-bg-border space-y-3">
                <p className="text-xs text-text-muted uppercase tracking-wider font-medium">MA Parameters</p>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Fast EMA</label>
                    <input {...register('fast_period')} type="number" className="input" />
                  </div>
                  <div>
                    <label className="label">Slow EMA</label>
                    <input {...register('slow_period')} type="number" className="input" />
                  </div>
                </div>
              </div>
            )}

            {strategyType === 'rsi' && (
              <div className="p-3 rounded-lg bg-bg-elevated border border-bg-border space-y-3">
                <p className="text-xs text-text-muted uppercase tracking-wider font-medium">RSI Parameters</p>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="label">Period</label>
                    <input {...register('rsi_period')} type="number" className="input" />
                  </div>
                  <div>
                    <label className="label">Oversold</label>
                    <input {...register('oversold')} type="number" className="input" />
                  </div>
                  <div>
                    <label className="label">Overbought</label>
                    <input {...register('overbought')} type="number" className="input" />
                  </div>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full flex items-center justify-center gap-2 h-11 mt-2"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-bg-primary/30 border-t-bg-primary rounded-full animate-spin" />
                  Running…
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Run Backtest
                </>
              )}
            </button>
          </form>
        </div>

        {/* ── Results ── */}
        <div className="xl:col-span-2 space-y-4">
          {result ? (
            <>
              {/* Summary banner */}
              <div className={clsx('p-4 rounded-xl border flex items-center gap-3',
                perf.total_return_pct >= 0
                  ? 'bg-accent-green/5 border-accent-green/20'
                  : 'bg-accent-red/5 border-accent-red/20'
              )}>
                {perf.total_return_pct >= 0
                  ? <CheckCircle className="w-5 h-5 text-accent-green flex-shrink-0" />
                  : <AlertTriangle className="w-5 h-5 text-accent-red flex-shrink-0" />
                }
                <div>
                  <p className="font-medium text-text-primary">
                    {result.symbol} · {result.strategy} · {result.timeframe}
                  </p>
                  <p className="text-xs text-text-muted">
                    {result.period.start?.slice(0,10)} → {result.period.end?.slice(0,10)}
                    &nbsp;·&nbsp; ${result.capital.initial.toLocaleString()} → ${result.capital.final.toLocaleString()}
                  </p>
                </div>
              </div>

              {/* Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <MetricCard label="Total Return"   value={`${perf.total_return_pct >= 0 ? '+' : ''}${perf.total_return_pct}%`} good={perf.total_return_pct >= 0} />
                <MetricCard label="Sharpe Ratio"   value={perf.sharpe_ratio.toFixed(2)}   good={perf.sharpe_ratio > 1} note={perf.sharpe_ratio > 1 ? 'Good' : 'Below 1'} />
                <MetricCard label="Max Drawdown"   value={`${perf.max_drawdown_pct.toFixed(1)}%`} good={perf.max_drawdown_pct > -20} />
                <MetricCard label="Win Rate"       value={`${trds.win_rate_pct}%`}         good={trds.win_rate_pct >= 50} />
                <MetricCard label="Total Trades"   value={trds.total.toString()} />
                <MetricCard label="Profit Factor"  value={trds.profit_factor === Infinity ? '∞' : trds.profit_factor.toFixed(2)} good={trds.profit_factor > 1.5} />
                <MetricCard label="Avg Risk/Reward" value={trds.avg_risk_reward.toFixed(2)} good={trds.avg_risk_reward >= 2} />
                <MetricCard label="Expectancy"     value={`$${trds.expectancy_usdt.toFixed(2)}`} good={trds.expectancy_usdt > 0} />
              </div>

              {/* Chart tabs */}
              <div className="card overflow-hidden">
                <div className="flex border-b border-bg-border">
                  {(['equity','drawdown','trades'] as const).map(tab => (
                    <button
                      key={tab}
                      onClick={() => setActiveTab(tab)}
                      className={clsx('px-5 py-3 text-sm font-medium capitalize transition-colors',
                        activeTab === tab
                          ? 'text-accent-cyan border-b-2 border-accent-cyan bg-accent-cyan/5'
                          : 'text-text-muted hover:text-text-secondary'
                      )}
                    >
                      {tab === 'equity' ? 'Equity Curve' : tab === 'drawdown' ? 'Drawdown' : 'Trade Log'}
                    </button>
                  ))}
                </div>

                <div className="p-5">
                  {activeTab === 'equity' && (
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={result.equity_curve}>
                        <defs>
                          <linearGradient id="eq" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#00d4ff" stopOpacity={0.25} />
                            <stop offset="95%" stopColor="#00d4ff" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" tick={{fontSize:10}} tickFormatter={v => v?.slice(5,10)} interval="preserveStartEnd" />
                        <YAxis tick={{fontSize:10}} tickFormatter={v => `$${(v/1000).toFixed(1)}k`} />
                        <Tooltip formatter={(v: any) => [`$${Number(v).toFixed(2)}`, 'Equity']} />
                        <ReferenceLine y={result.capital.initial} stroke="#4a6070" strokeDasharray="4 4" />
                        <Area type="monotone" dataKey="equity" stroke="#00d4ff" strokeWidth={2} fill="url(#eq)" dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  )}

                  {activeTab === 'drawdown' && (
                    <ResponsiveContainer width="100%" height={280}>
                      <AreaChart data={result.drawdown_series}>
                        <defs>
                          <linearGradient id="dd" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%"  stopColor="#ff3b6b" stopOpacity={0.3} />
                            <stop offset="95%" stopColor="#ff3b6b" stopOpacity={0} />
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" tick={{fontSize:10}} tickFormatter={v => v?.slice(5,10)} interval="preserveStartEnd" />
                        <YAxis tick={{fontSize:10}} tickFormatter={v => `${v.toFixed(1)}%`} />
                        <Tooltip formatter={(v: any) => [`${Number(v).toFixed(2)}%`, 'Drawdown']} />
                        <Area type="monotone" dataKey="drawdown_pct" stroke="#ff3b6b" strokeWidth={2} fill="url(#dd)" dot={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  )}

                  {activeTab === 'trades' && (
                    <div className="overflow-x-auto max-h-[280px] overflow-y-auto">
                      <table className="w-full text-xs">
                        <thead className="sticky top-0 bg-bg-card">
                          <tr className="border-b border-bg-border">
                            {['Entry','Exit','Side','Entry $','Exit $','P&L','P&L %','Reason'].map(h => (
                              <th key={h} className="px-3 py-2 text-left text-text-muted">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {result.trade_log.map((t: any, i: number) => (
                            <tr key={i} className="table-row">
                              <td className="px-3 py-2 font-mono text-text-muted">{t.entry_time?.slice(5,16)}</td>
                              <td className="px-3 py-2 font-mono text-text-muted">{t.exit_time?.slice(5,16)}</td>
                              <td className="px-3 py-2">
                                <span className={clsx('font-medium', t.side === 'buy' ? 'text-accent-green' : 'text-accent-red')}>
                                  {t.side.toUpperCase()}
                                </span>
                              </td>
                              <td className="px-3 py-2 font-mono">${t.entry_price?.toFixed(2)}</td>
                              <td className="px-3 py-2 font-mono">${t.exit_price?.toFixed(2)}</td>
                              <td className={clsx('px-3 py-2 font-mono font-medium', t.pnl_usdt >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                                {t.pnl_usdt >= 0 ? '+' : ''}{t.pnl_usdt?.toFixed(2)}
                              </td>
                              <td className={clsx('px-3 py-2 font-mono', t.pnl_pct >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                                {t.pnl_pct >= 0 ? '+' : ''}{t.pnl_pct?.toFixed(2)}%
                              </td>
                              <td className="px-3 py-2 text-text-muted">{t.exit_reason}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </div>
            </>
          ) : (
            <div className="card h-full min-h-[400px] flex flex-col items-center justify-center text-text-muted gap-3">
              <FlaskConical className="w-12 h-12 opacity-20" />
              <p className="font-medium text-text-secondary">Run a backtest to see results</p>
              <p className="text-sm text-center max-w-xs">
                Configure your strategy, symbol and parameters, then click "Run Backtest"
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
