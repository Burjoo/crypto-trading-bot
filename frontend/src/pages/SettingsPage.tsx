import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Settings, Link, Plus, Trash2, Shield, Bell,
  User, Check, AlertTriangle, X, Eye, EyeOff,
} from 'lucide-react';
import { clsx } from 'clsx';
import { api, useAuthStore } from '../store';
import toast from 'react-hot-toast';

const EXCHANGES = [
  { id: 'binance',     name: 'Binance',     color: '#f0b90b', desc: 'World\'s largest exchange by volume' },
  { id: 'bybit',       name: 'Bybit',       color: '#f7a600', desc: 'Popular derivatives & spot exchange' },
  { id: 'coinbasepro', name: 'Coinbase Pro', color: '#0052ff', desc: 'US-regulated crypto exchange' },
];

export default function SettingsPage() {
  const { user } = useAuthStore();
  const qc = useQueryClient();
  const [activeTab, setActiveTab] = useState<'exchanges'|'profile'|'notifications'>('exchanges');
  const [showAddExchange, setShowAddExchange] = useState(false);
  const [showSecret, setShowSecret] = useState(false);
  const [exchangeForm, setExchangeForm] = useState({
    name: 'binance', label: '', api_key: '', api_secret: '',
    passphrase: '', is_paper_trading: true,
  });

  const { data: exData, isLoading } = useQuery({
    queryKey: ['exchanges'],
    queryFn: () => api.get('/exchanges').then(r => r.data),
  });

  const addExchange = useMutation({
    mutationFn: () => api.post('/exchanges', exchangeForm),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['exchanges'] });
      setShowAddExchange(false);
      setExchangeForm({ name:'binance', label:'', api_key:'', api_secret:'', passphrase:'', is_paper_trading:true });
      toast.success('Exchange connected!');
    },
    onError: (e: any) => toast.error(e?.response?.data?.detail ?? 'Connection failed'),
  });

  const deleteExchange = useMutation({
    mutationFn: (id: string) => api.delete(`/exchanges/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['exchanges'] }); toast.success('Removed'); },
  });

  const exchanges = exData?.exchanges ?? [];
  const TABS = [
    { id: 'exchanges',     label: 'Exchanges',     icon: Link },
    { id: 'profile',       label: 'Profile',       icon: User },
    { id: 'notifications', label: 'Notifications', icon: Bell },
  ] as const;

  return (
    <div className="space-y-6 animate-fade-in max-w-3xl">
      <div>
        <h1 className="font-display font-bold text-2xl text-text-primary flex items-center gap-2">
          <Settings className="w-6 h-6 text-accent-cyan" /> Settings
        </h1>
        <p className="text-text-secondary text-sm mt-0.5">Manage your account and exchange connections</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-bg-elevated rounded-xl border border-bg-border w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)}
            className={clsx('flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === id
                ? 'bg-bg-card text-text-primary shadow-sm'
                : 'text-text-muted hover:text-text-secondary'
            )}>
            <Icon className="w-4 h-4" />{label}
          </button>
        ))}
      </div>

      {/* ── Exchanges tab ── */}
      {activeTab === 'exchanges' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="section-title">Connected Exchanges</h2>
            <button onClick={() => setShowAddExchange(true)} className="btn-primary text-sm flex items-center gap-2">
              <Plus className="w-4 h-4" /> Connect Exchange
            </button>
          </div>

          {exchanges.length === 0 && !isLoading ? (
            <div className="card p-10 flex flex-col items-center justify-center text-text-muted gap-3">
              <Link className="w-10 h-10 opacity-20" />
              <p className="font-medium text-text-secondary">No exchanges connected</p>
              <p className="text-sm text-center max-w-xs">Connect an exchange to enable live trading. Paper trading mode is on by default — no real funds needed.</p>
              <button onClick={() => setShowAddExchange(true)} className="btn-primary text-sm mt-2 flex items-center gap-2">
                <Plus className="w-4 h-4" /> Connect Exchange
              </button>
            </div>
          ) : (
            <div className="space-y-3">
              {exchanges.map((ex: any) => {
                const info = EXCHANGES.find(e => e.id === ex.name) ?? EXCHANGES[0];
                return (
                  <div key={ex.id} className="card p-4 flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg flex items-center justify-center text-xs font-bold flex-shrink-0"
                        style={{ background: `${info.color}20`, border: `1px solid ${info.color}30`, color: info.color }}>
                        {info.name.slice(0,2)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-text-primary">{ex.label}</p>
                          <span className={clsx('text-xs px-1.5 py-0.5 rounded-full border',
                            ex.is_paper_trading
                              ? 'text-accent-yellow border-accent-yellow/30 bg-accent-yellow/5'
                              : 'text-accent-green border-accent-green/30 bg-accent-green/5'
                          )}>
                            {ex.is_paper_trading ? 'Paper' : 'Live'}
                          </span>
                        </div>
                        <p className="text-xs text-text-muted">{info.name} · Key: {ex.api_key_hint}</p>
                      </div>
                    </div>
                    <button onClick={() => { if (confirm('Remove this exchange?')) deleteExchange.mutate(ex.id); }}
                      className="p-2 rounded-lg text-text-muted hover:text-accent-red hover:bg-accent-red/5 transition-colors flex-shrink-0">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

          {/* Exchange options */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
            {EXCHANGES.map(ex => (
              <div key={ex.id} className="card p-4 border border-bg-border hover:border-bg-border/80 transition-colors">
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-6 h-6 rounded text-xs font-bold flex items-center justify-center"
                    style={{ background: `${ex.color}20`, color: ex.color }}>
                    {ex.name.slice(0,2)}
                  </div>
                  <span className="font-medium text-sm text-text-primary">{ex.name}</span>
                </div>
                <p className="text-xs text-text-muted">{ex.desc}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Profile tab ── */}
      {activeTab === 'profile' && (
        <div className="card p-6 space-y-5">
          <h2 className="section-title">Profile Information</h2>
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-2xl bg-accent-cyan/15 border border-accent-cyan/30 flex items-center justify-center">
              <span className="text-accent-cyan text-2xl font-bold font-display">
                {user?.username?.[0]?.toUpperCase()}
              </span>
            </div>
            <div>
              <p className="font-semibold text-text-primary text-lg">{user?.username}</p>
              <p className="text-text-muted text-sm">{user?.email}</p>
              <span className="badge-cyan mt-1">{user?.role}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div>
              <label className="label">Username</label>
              <input defaultValue={user?.username} className="input" disabled />
            </div>
            <div>
              <label className="label">Email</label>
              <input defaultValue={user?.email} className="input" disabled />
            </div>
            <div>
              <label className="label">Full Name</label>
              <input defaultValue={user?.full_name ?? ''} className="input" placeholder="Your full name" />
            </div>
            <div>
              <label className="label">Telegram Chat ID</label>
              <input className="input" placeholder="Find via @userinfobot" />
            </div>
          </div>
          <button className="btn-primary text-sm flex items-center gap-2 w-fit">
            <Check className="w-4 h-4" /> Save Changes
          </button>
        </div>
      )}

      {/* ── Notifications tab ── */}
      {activeTab === 'notifications' && (
        <div className="card p-6 space-y-5">
          <h2 className="section-title">Notification Preferences</h2>
          <div className="p-3 rounded-lg bg-accent-yellow/5 border border-accent-yellow/20 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-accent-yellow flex-shrink-0 mt-0.5" />
            <p className="text-xs text-accent-yellow">
              Telegram notifications require a Bot Token in your server config and your Chat ID in the profile tab.
            </p>
          </div>
          <div className="space-y-3">
            {[
              { key: 'trade_open',      label: 'Trade Opened',    desc: 'When a bot opens a new position' },
              { key: 'trade_close',     label: 'Trade Closed',    desc: 'When a position is closed' },
              { key: 'stop_loss',       label: 'Stop Loss Hit',   desc: 'When stop-loss triggers' },
              { key: 'take_profit',     label: 'Take Profit Hit', desc: 'When take-profit triggers' },
              { key: 'bot_error',       label: 'Bot Errors',      desc: 'When a bot encounters an error' },
              { key: 'daily_summary',   label: 'Daily Summary',   desc: 'End-of-day performance report' },
            ].map(item => (
              <div key={item.key} className="flex items-center justify-between py-3 border-b border-bg-border last:border-0">
                <div>
                  <p className="text-sm font-medium text-text-primary">{item.label}</p>
                  <p className="text-xs text-text-muted">{item.desc}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" defaultChecked className="sr-only peer" />
                  <div className="w-10 h-5 bg-bg-elevated peer-focus:outline-none rounded-full peer
                    peer-checked:after:translate-x-5 after:content-[''] after:absolute after:top-0.5
                    after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4
                    after:transition-all peer-checked:bg-accent-cyan border border-bg-border
                    peer-checked:border-accent-cyan/50" />
                </label>
              </div>
            ))}
          </div>
          <button className="btn-primary text-sm flex items-center gap-2 w-fit">
            <Check className="w-4 h-4" /> Save Preferences
          </button>
        </div>
      )}

      {/* ── Add Exchange Modal ── */}
      {showAddExchange && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="card w-full max-w-md p-6 animate-slide-in">
            <div className="flex items-center justify-between mb-5">
              <h2 className="section-title">Connect Exchange</h2>
              <button onClick={() => setShowAddExchange(false)} className="text-text-muted hover:text-text-primary">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="label">Exchange</label>
                <select value={exchangeForm.name} onChange={e => setExchangeForm(p=>({...p,name:e.target.value}))} className="input">
                  {EXCHANGES.map(e => <option key={e.id} value={e.id}>{e.name}</option>)}
                </select>
              </div>
              <div>
                <label className="label">Label</label>
                <input value={exchangeForm.label} onChange={e => setExchangeForm(p=>({...p,label:e.target.value}))}
                  className="input" placeholder="My Binance account" />
              </div>
              <div>
                <label className="label">API Key</label>
                <input value={exchangeForm.api_key} onChange={e => setExchangeForm(p=>({...p,api_key:e.target.value}))}
                  className="input font-mono text-sm" placeholder="Paste your API key" />
              </div>
              <div>
                <label className="label">API Secret</label>
                <div className="relative">
                  <input value={exchangeForm.api_secret}
                    onChange={e => setExchangeForm(p=>({...p,api_secret:e.target.value}))}
                    type={showSecret ? 'text' : 'password'}
                    className="input font-mono text-sm pr-10" placeholder="Paste your API secret" />
                  <button type="button" onClick={() => setShowSecret(!showSecret)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-secondary">
                    {showSecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>
              {exchangeForm.name === 'coinbasepro' && (
                <div>
                  <label className="label">Passphrase</label>
                  <input value={exchangeForm.passphrase} onChange={e => setExchangeForm(p=>({...p,passphrase:e.target.value}))}
                    type="password" className="input" placeholder="Coinbase Pro passphrase" />
                </div>
              )}
              <div className="flex items-center gap-3 p-3 rounded-lg bg-bg-elevated border border-bg-border">
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" checked={exchangeForm.is_paper_trading}
                    onChange={e => setExchangeForm(p=>({...p,is_paper_trading:e.target.checked}))} className="sr-only peer" />
                  <div className="w-10 h-5 bg-bg-primary peer-checked:bg-accent-cyan rounded-full
                    peer-checked:after:translate-x-5 after:content-[''] after:absolute after:top-0.5
                    after:left-0.5 after:bg-white after:rounded-full after:h-4 after:w-4 after:transition-all
                    border border-bg-border relative" />
                </label>
                <div>
                  <p className="text-sm font-medium text-text-primary">Paper Trading Mode</p>
                  <p className="text-xs text-text-muted">Simulate trades without using real funds</p>
                </div>
              </div>
              <div className="flex items-start gap-2 text-xs text-text-muted">
                <Shield className="w-3.5 h-3.5 flex-shrink-0 mt-0.5 text-accent-green" />
                API keys are encrypted with AES-256 before storage. We never have access to withdraw funds.
              </div>
            </div>
            <div className="flex gap-3 mt-5">
              <button onClick={() => setShowAddExchange(false)} className="btn-secondary flex-1">Cancel</button>
              <button onClick={() => addExchange.mutate()}
                disabled={addExchange.isPending || !exchangeForm.label || !exchangeForm.api_key || !exchangeForm.api_secret}
                className="btn-primary flex-1 flex items-center justify-center gap-2">
                {addExchange.isPending
                  ? <span className="w-4 h-4 border-2 border-bg-primary/30 border-t-bg-primary rounded-full animate-spin" />
                  : <Link className="w-4 h-4" />}
                Connect
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
