/**
 * useWebSocket — connects to the backend WS feeds and exposes live data.
 * Reconnects automatically with exponential back-off.
 */
import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuthStore } from '../store';

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000';

interface PriceMap { [symbol: string]: { price: number; change_pct: number } }
interface PortfolioUpdate { total_pnl_usdt: number; today_pnl_usdt: number; open_positions: number }

export function usePriceFeed() {
  const [prices, setPrices] = useState<PriceMap>({});
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE}/ws/prices`);
    wsRef.current = ws;

    ws.onopen = () => { setConnected(true); retryRef.current = 0; };

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'price_update') {
          setPrices((prev) => ({ ...prev, ...msg.data }));
        }
      } catch { /* ignore */ }
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = Math.min(1000 * 2 ** retryRef.current, 30_000);
      retryRef.current++;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => { connect(); return () => wsRef.current?.close(); }, [connect]);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'ping' }));
    }
  }, []);

  return { prices, connected, sendPing };
}

export function usePortfolioFeed() {
  const token = useAuthStore((s) => s.accessToken);
  const [update, setUpdate] = useState<PortfolioUpdate | null>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!token) return;
    const ws = new WebSocket(`${WS_BASE}/ws/portfolio?token=${token}`);
    wsRef.current = ws;

    ws.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === 'portfolio_update') setUpdate(msg.data);
        if (msg.type === 'alert') setAlerts((prev) => [msg.data, ...prev.slice(0, 49)]);
      } catch { /* ignore */ }
    };

    return () => ws.close();
  }, [token]);

  return { update, alerts };
}
