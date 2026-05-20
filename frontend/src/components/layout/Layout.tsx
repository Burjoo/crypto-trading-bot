import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import {
  LayoutDashboard, Bot, FlaskConical, History, BookOpen,
  LineChart, Settings, LogOut, Bell, Menu, X, Wifi, WifiOff,
  TrendingUp, ChevronRight,
} from 'lucide-react';
import { useAuthStore, useUIStore } from '../../store';
import { usePriceFeed } from '../../hooks/useWebSocket';
import { clsx } from 'clsx';
import toast from 'react-hot-toast';

const NAV = [
  { to: '/',         icon: LayoutDashboard, label: 'Dashboard'  },
  { to: '/markets',  icon: LineChart,        label: 'Markets'    },
  { to: '/bots',     icon: Bot,              label: 'Bots'       },
  { to: '/backtest', icon: FlaskConical,     label: 'Backtest'   },
  { to: '/trades',   icon: History,          label: 'Trades'     },
  { to: '/journal',  icon: BookOpen,         label: 'Journal'    },
];

const TICKER_SYMBOLS = ['BTC/USDT','ETH/USDT','SOL/USDT','BNB/USDT','XRP/USDT'];

export default function Layout() {
  const { user, logout } = useAuthStore();
  const { sidebarOpen, toggleSidebar } = useUIStore();
  const navigate = useNavigate();
  const { prices, connected } = usePriceFeed();
  const [alertsOpen, setAlertsOpen] = useState(false);

  const handleLogout = () => {
    logout();
    toast.success('Logged out');
    navigate('/login');
  };

  return (
    <div className="flex h-screen bg-bg-primary overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className={clsx(
        'flex flex-col bg-bg-secondary border-r border-bg-border transition-all duration-300 z-30',
        sidebarOpen ? 'w-56' : 'w-16'
      )}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-4 border-b border-bg-border h-16">
          <div className="w-8 h-8 rounded-lg bg-accent-cyan/20 border border-accent-cyan/40 flex items-center justify-center flex-shrink-0">
            <TrendingUp className="w-4 h-4 text-accent-cyan" />
          </div>
          {sidebarOpen && (
            <span className="font-display font-bold text-sm text-text-primary whitespace-nowrap">
              CryptoBot <span className="text-accent-cyan">Pro</span>
            </span>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-1 px-2 overflow-y-auto">
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) => clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group relative',
                isActive
                  ? 'bg-accent-cyan/10 text-accent-cyan border border-accent-cyan/20'
                  : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
              )}
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {sidebarOpen && <span className="font-medium">{label}</span>}
              {!sidebarOpen && (
                <span className="absolute left-14 bg-bg-elevated border border-bg-border
                  text-text-primary text-xs px-2 py-1 rounded whitespace-nowrap
                  opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
                  {label}
                </span>
              )}
            </NavLink>
          ))}
        </nav>

        {/* Bottom */}
        <div className="border-t border-bg-border p-3 space-y-2">
          <NavLink to="/settings" className={({ isActive }) => clsx(
            'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-150',
            isActive ? 'text-accent-cyan' : 'text-text-secondary hover:text-text-primary hover:bg-bg-elevated'
          )}>
            <Settings className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>Settings</span>}
          </NavLink>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-text-secondary
              hover:text-accent-red hover:bg-accent-red/5 transition-all duration-150"
          >
            <LogOut className="w-4 h-4 flex-shrink-0" />
            {sidebarOpen && <span>Log out</span>}
          </button>

          {sidebarOpen && user && (
            <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-bg-elevated mt-1">
              <div className="w-7 h-7 rounded-full bg-accent-cyan/20 border border-accent-cyan/30
                flex items-center justify-center text-accent-cyan text-xs font-bold flex-shrink-0">
                {user.username[0].toUpperCase()}
              </div>
              <div className="overflow-hidden">
                <p className="text-xs font-medium text-text-primary truncate">{user.username}</p>
                <p className="text-2xs text-text-muted truncate">{user.email}</p>
              </div>
            </div>
          )}
        </div>
      </aside>

      {/* ── Main ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center justify-between px-4 h-16 border-b border-bg-border bg-bg-secondary flex-shrink-0">
          <div className="flex items-center gap-3">
            <button onClick={toggleSidebar} className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors">
              {sidebarOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>

            {/* Live price ticker */}
            <div className="hidden md:flex items-center gap-4 overflow-hidden">
              {TICKER_SYMBOLS.map((sym) => {
                const p = prices[sym];
                return (
                  <div key={sym} className="flex items-center gap-1.5 text-xs">
                    <span className="text-text-muted font-mono">{sym.replace('/USDT','')}</span>
                    <span className="font-mono text-text-primary">
                      {p ? `$${p.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : '—'}
                    </span>
                    {p?.change_pct !== undefined && (
                      <span className={clsx('font-mono', p.change_pct >= 0 ? 'text-accent-green' : 'text-accent-red')}>
                        {p.change_pct >= 0 ? '+' : ''}{p.change_pct.toFixed(2)}%
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* WS status */}
            <div className={clsx('flex items-center gap-1.5 text-xs px-2 py-1 rounded-full border',
              connected
                ? 'text-accent-green border-accent-green/20 bg-accent-green/5'
                : 'text-text-muted border-bg-border bg-bg-elevated'
            )}>
              {connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
              <span className="hidden sm:inline">{connected ? 'Live' : 'Offline'}</span>
            </div>

            {/* Alerts bell */}
            <button
              onClick={() => setAlertsOpen(!alertsOpen)}
              className="relative p-2 rounded-lg text-text-secondary hover:text-text-primary hover:bg-bg-elevated transition-colors"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-accent-red rounded-full" />
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto bg-bg-primary bg-grid-pattern bg-grid">
          <div className="p-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
