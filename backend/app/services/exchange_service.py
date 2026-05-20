"""
Exchange Service — CCXT-based integration for Binance, Bybit, Coinbase Pro.
Handles: balance fetching, OHLCV data, order execution, position management.
API keys are decrypted on-demand and never cached in memory.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

import ccxt.async_support as ccxt

from app.core.security import decrypt_api_key

logger = logging.getLogger(__name__)

# Supported exchanges and their CCXT class names
EXCHANGE_MAP: dict[str, type] = {
    "binance": ccxt.binance,
    "bybit": ccxt.bybit,
    "coinbasepro": ccxt.coinbasepro,
}


class ExchangeService:
    """
    Provides a unified async interface to multiple exchanges via CCXT.
    Each method creates a short-lived exchange instance (connection pooling
    is handled by aiohttp within CCXT).
    """

    def _build_client(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        passphrase_enc: Optional[str] = None,
        sandbox: bool = False,
    ) -> ccxt.Exchange:
        """Build and configure a CCXT exchange client."""
        exchange_cls = EXCHANGE_MAP.get(exchange_name.lower())
        if not exchange_cls:
            raise ValueError(f"Unsupported exchange: {exchange_name}")

        config: dict[str, Any] = {
            "apiKey": decrypt_api_key(api_key_enc),
            "secret": decrypt_api_key(api_secret_enc),
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }

        if passphrase_enc:
            config["password"] = decrypt_api_key(passphrase_enc)

        client = exchange_cls(config)

        if sandbox and hasattr(client, "set_sandbox_mode"):
            client.set_sandbox_mode(True)

        return client

    async def fetch_balance(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        passphrase_enc: Optional[str] = None,
    ) -> dict:
        """Fetch account balance from exchange."""
        client = self._build_client(exchange_name, api_key_enc, api_secret_enc, passphrase_enc)
        try:
            balance = await client.fetch_balance()
            # Return only non-zero balances
            return {
                asset: {
                    "free": data["free"],
                    "used": data["used"],
                    "total": data["total"],
                }
                for asset, data in balance.items()
                if isinstance(data, dict)
                and data.get("total", 0) and data["total"] > 0
                and asset not in ("info", "timestamp", "datetime", "free", "used", "total")
            }
        finally:
            await client.close()

    async def fetch_ohlcv(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
        since: Optional[int] = None,  # Unix ms
    ) -> list[dict]:
        """
        Fetch OHLCV candles for backtesting or strategy calculations.
        Returns list of dicts: {timestamp, open, high, low, close, volume}
        """
        client = self._build_client(exchange_name, api_key_enc, api_secret_enc)
        try:
            await client.load_markets()
            raw = await client.fetch_ohlcv(symbol, timeframe, since=since, limit=limit)
            return [
                {
                    "timestamp": candle[0],  # Unix ms
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                }
                for candle in raw
            ]
        finally:
            await client.close()

    async def fetch_ticker(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        symbol: str,
    ) -> dict:
        """Fetch current ticker data (price, 24h change, volume, etc.)"""
        client = self._build_client(exchange_name, api_key_enc, api_secret_enc)
        try:
            ticker = await client.fetch_ticker(symbol)
            return {
                "symbol": symbol,
                "last": ticker.get("last"),
                "bid": ticker.get("bid"),
                "ask": ticker.get("ask"),
                "high_24h": ticker.get("high"),
                "low_24h": ticker.get("low"),
                "volume_24h": ticker.get("baseVolume"),
                "change_24h": ticker.get("change"),
                "change_pct_24h": ticker.get("percentage"),
            }
        finally:
            await client.close()

    async def fetch_open_orders(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        symbol: Optional[str] = None,
    ) -> list[dict]:
        """Fetch open orders."""
        client = self._build_client(exchange_name, api_key_enc, api_secret_enc)
        try:
            orders = await client.fetch_open_orders(symbol)
            return [
                {
                    "id": o["id"],
                    "symbol": o["symbol"],
                    "side": o["side"],
                    "type": o["type"],
                    "price": o["price"],
                    "amount": o["amount"],
                    "filled": o["filled"],
                    "status": o["status"],
                    "timestamp": o["timestamp"],
                }
                for o in orders
            ]
        finally:
            await client.close()

    async def create_market_order(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        symbol: str,
        side: str,
        amount: float,
    ) -> dict:
        """Execute a market order (live trading only)."""
        client = self._build_client(exchange_name, api_key_enc, api_secret_enc)
        try:
            order = await client.create_market_order(symbol, side, amount)
            return {
                "order_id": order["id"],
                "symbol": order["symbol"],
                "side": order["side"],
                "amount": order["amount"],
                "price": order.get("average") or order.get("price"),
                "status": order["status"],
                "timestamp": order["timestamp"],
            }
        finally:
            await client.close()

    async def create_limit_order(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        symbol: str,
        side: str,
        amount: float,
        price: float,
    ) -> dict:
        """Execute a limit order."""
        client = self._build_client(exchange_name, api_key_enc, api_secret_enc)
        try:
            order = await client.create_limit_order(symbol, side, amount, price)
            return {
                "order_id": order["id"],
                "symbol": order["symbol"],
                "side": order["side"],
                "amount": order["amount"],
                "price": order["price"],
                "status": order["status"],
            }
        finally:
            await client.close()

    async def cancel_order(
        self,
        exchange_name: str,
        api_key_enc: str,
        api_secret_enc: str,
        order_id: str,
        symbol: str,
    ) -> dict:
        """Cancel an open order."""
        client = self._build_client(exchange_name, api_key_enc, api_secret_enc)
        try:
            result = await client.cancel_order(order_id, symbol)
            return {"cancelled": True, "order_id": result.get("id")}
        finally:
            await client.close()

    async def fetch_public_ohlcv(
        self,
        exchange_name: str,
        symbol: str,
        timeframe: str = "1h",
        limit: int = 500,
    ) -> list[dict]:
        """
        Fetch public OHLCV data without authentication.
        Used for backtesting when no exchange key is configured.
        """
        exchange_cls = EXCHANGE_MAP.get(exchange_name.lower(), ccxt.binance)
        client = exchange_cls({"enableRateLimit": True})
        try:
            await client.load_markets()
            raw = await client.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [
                {
                    "timestamp": candle[0],
                    "open": candle[1],
                    "high": candle[2],
                    "low": candle[3],
                    "close": candle[4],
                    "volume": candle[5],
                }
                for candle in raw
            ]
        finally:
            await client.close()

    async def get_supported_symbols(
        self, exchange_name: str, quote_currency: str = "USDT"
    ) -> list[str]:
        """Return list of supported trading pairs for a given quote currency."""
        exchange_cls = EXCHANGE_MAP.get(exchange_name.lower(), ccxt.binance)
        client = exchange_cls({"enableRateLimit": True})
        try:
            markets = await client.load_markets()
            return [
                symbol for symbol in markets
                if symbol.endswith(f"/{quote_currency}")
                and markets[symbol].get("active", True)
            ]
        finally:
            await client.close()
