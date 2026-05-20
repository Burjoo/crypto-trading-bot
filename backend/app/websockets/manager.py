"""
WebSocket Connection Manager.

Manages client connections, rooms (channels), and broadcasting.
Supports:
  - Price feed channel (live market data for all connected clients)
  - Per-user portfolio channel (PnL, positions, bot status)
  - Per-user alert channel (notifications)
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Central WebSocket connection manager.

    Channels:
      - "prices"          : broadcast to ALL connected clients
      - "user:{user_id}"  : broadcast only to connections authenticated as user_id
      - "bot:{bot_id}"    : broadcast bot-specific updates
    """

    def __init__(self):
        # channel_name → list of WebSocket connections
        self._channels: dict[str, list[WebSocket]] = defaultdict(list)
        # websocket → set of channels it's subscribed to
        self._subscriptions: dict[WebSocket, set[str]] = {}
        self._lock = asyncio.Lock()

    # ── Connection Lifecycle ──────────────────────────────────────────────────

    async def connect(self, websocket: WebSocket, channel: str) -> None:
        """Accept a WebSocket connection and subscribe it to a channel."""
        await websocket.accept()

        async with self._lock:
            self._channels[channel].append(websocket)
            if websocket not in self._subscriptions:
                self._subscriptions[websocket] = set()
            self._subscriptions[websocket].add(channel)

        logger.info("WS connected: channel=%s total=%d", channel, len(self._channels[channel]))

    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket from all channels it was subscribed to."""
        async with self._lock:
            channels = self._subscriptions.pop(websocket, set())
            for channel in channels:
                try:
                    self._channels[channel].remove(websocket)
                except ValueError:
                    pass
                if not self._channels[channel]:
                    del self._channels[channel]

        logger.debug("WS disconnected from channels: %s", channels)

    # ── Messaging ─────────────────────────────────────────────────────────────

    async def send_personal(self, websocket: WebSocket, data: Any) -> None:
        """Send a message to a single WebSocket."""
        try:
            await websocket.send_text(json.dumps(data, default=str))
        except Exception as exc:
            logger.debug("WS send_personal failed: %s", exc)
            await self.disconnect(websocket)

    async def broadcast_to_channel(self, channel: str, data: Any) -> None:
        """Broadcast a message to all connections in a channel."""
        payload = json.dumps(data, default=str)
        dead: list[WebSocket] = []

        async with self._lock:
            connections = list(self._channels.get(channel, []))

        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        # Cleanup dead connections
        for ws in dead:
            await self.disconnect(ws)

    async def broadcast_to_user(self, user_id: str, data: Any) -> None:
        """Send a message to all connections authenticated as a specific user."""
        await self.broadcast_to_channel(f"user:{user_id}", data)

    async def broadcast_prices(self, prices: dict) -> None:
        """Broadcast live price updates to all subscribed clients."""
        await self.broadcast_to_channel(
            "prices",
            {
                "type": "price_update",
                "data": prices,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def broadcast_portfolio_update(
        self, user_id: str, portfolio_data: dict
    ) -> None:
        """Push a portfolio/PnL update to a specific user."""
        await self.broadcast_to_user(
            user_id,
            {
                "type": "portfolio_update",
                "data": portfolio_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def broadcast_trade_update(
        self, user_id: str, trade_data: dict
    ) -> None:
        """Notify a user's connections about a new trade event."""
        await self.broadcast_to_user(
            user_id,
            {
                "type": "trade_update",
                "data": trade_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def broadcast_bot_status(
        self, user_id: str, bot_id: str, status: str, message: Optional[str] = None
    ) -> None:
        """Notify a user about a bot status change."""
        await self.broadcast_to_user(
            user_id,
            {
                "type": "bot_status",
                "data": {
                    "bot_id": bot_id,
                    "status": status,
                    "message": message,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def broadcast_alert(self, user_id: str, alert: dict) -> None:
        """Push a new alert to a user."""
        await self.broadcast_to_user(
            user_id,
            {
                "type": "alert",
                "data": alert,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    # ── Stats ─────────────────────────────────────────────────────────────────

    def connection_count(self, channel: Optional[str] = None) -> int:
        if channel:
            return len(self._channels.get(channel, []))
        return sum(len(conns) for conns in self._channels.values())

    def channel_list(self) -> list[str]:
        return list(self._channels.keys())


# Global singleton — imported by route handlers
ws_manager = ConnectionManager()


# ── WebSocket Handler Helpers ─────────────────────────────────────────────────

async def handle_price_feed(
    websocket: WebSocket,
    symbols: list[str] | None = None,
):
    """
    Handle a price feed WebSocket connection.
    Client can send: {"action": "subscribe", "symbols": ["BTC/USDT", "ETH/USDT"]}
    """
    await ws_manager.connect(websocket, "prices")
    try:
        # Send initial connection acknowledgement
        await ws_manager.send_personal(
            websocket,
            {"type": "connected", "message": "Connected to price feed", "symbols": symbols or []},
        )

        # Keep connection alive, receiving client messages
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                data = json.loads(message)
                # Handle subscription changes
                if data.get("action") == "ping":
                    await ws_manager.send_personal(websocket, {"type": "pong"})
            except asyncio.TimeoutError:
                # Send heartbeat
                await ws_manager.send_personal(websocket, {"type": "heartbeat"})
            except WebSocketDisconnect:
                break
    finally:
        await ws_manager.disconnect(websocket)


async def handle_portfolio_feed(websocket: WebSocket, user_id: str):
    """Handle a per-user portfolio WebSocket connection."""
    channel = f"user:{user_id}"
    await ws_manager.connect(websocket, channel)
    try:
        await ws_manager.send_personal(
            websocket,
            {"type": "connected", "message": f"Connected to portfolio feed"},
        )
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                data = json.loads(message)
                if data.get("action") == "ping":
                    await ws_manager.send_personal(websocket, {"type": "pong"})
            except asyncio.TimeoutError:
                await ws_manager.send_personal(websocket, {"type": "heartbeat"})
            except WebSocketDisconnect:
                break
    finally:
        await ws_manager.disconnect(websocket)
