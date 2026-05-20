"""
Telegram Notification Service.
Sends formatted alerts for trade events, errors, and daily summaries.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """
    Sends Telegram messages via Bot API.
    All methods are async and silently fail if Telegram is not configured.
    """

    BASE_URL = "https://api.telegram.org/bot{token}/sendMessage"

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.enabled = settings.telegram_enabled

    async def _send(self, text: str, parse_mode: str = "HTML") -> bool:
        """Low-level message sender."""
        if not self.enabled:
            logger.debug("Telegram not configured — skipping alert")
            return False

        import aiohttp

        url = self.BASE_URL.format(token=self.token)
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("Telegram API error %d: %s", resp.status, body)
                        return False
                    return True
        except Exception as exc:
            logger.warning("Telegram send failed: %s", exc)
            return False

    # ── Public Alert Methods ──────────────────────────────────────────────────

    async def send_trade_opened(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        quantity: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        bot_name: str,
        is_paper: bool = True,
    ) -> bool:
        mode = "📄 PAPER" if is_paper else "🔴 LIVE"
        side_emoji = "🟢 BUY" if side == "buy" else "🔴 SELL"
        sl_text = f"${stop_loss:.4f}" if stop_loss else "N/A"
        tp_text = f"${take_profit:.4f}" if take_profit else "N/A"

        text = (
            f"<b>{mode} — Trade Opened</b>\n\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"📊 Symbol: <b>{symbol}</b>\n"
            f"Direction: {side_emoji}\n"
            f"💰 Entry: <b>${entry_price:.4f}</b>\n"
            f"📦 Qty: {quantity:.6f}\n"
            f"🛑 Stop Loss: {sl_text}\n"
            f"🎯 Take Profit: {tp_text}\n"
            f"🕐 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self._send(text)

    async def send_trade_closed(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        exit_price: float,
        pnl_usdt: float,
        pnl_pct: float,
        exit_reason: str,
        bot_name: str,
        is_paper: bool = True,
    ) -> bool:
        mode = "📄 PAPER" if is_paper else "🔴 LIVE"
        pnl_emoji = "✅" if pnl_usdt >= 0 else "❌"
        pnl_sign = "+" if pnl_usdt >= 0 else ""
        reason_map = {
            "stop_loss": "🛑 Stop Loss",
            "take_profit": "🎯 Take Profit",
            "signal": "📈 Strategy Signal",
            "trailing_stop": "⬇️ Trailing Stop",
            "manual": "👤 Manual Close",
        }
        reason_text = reason_map.get(exit_reason, exit_reason)

        text = (
            f"<b>{mode} — Trade Closed {pnl_emoji}</b>\n\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"📊 Symbol: <b>{symbol}</b>\n"
            f"💰 Entry: ${entry_price:.4f} → Exit: ${exit_price:.4f}\n"
            f"📈 PnL: <b>{pnl_sign}${pnl_usdt:.2f} ({pnl_sign}{pnl_pct:.2f}%)</b>\n"
            f"Reason: {reason_text}\n"
            f"🕐 Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self._send(text)

    async def send_stop_loss_hit(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        loss_usdt: float,
        bot_name: str,
    ) -> bool:
        text = (
            f"<b>🛑 Stop Loss Triggered</b>\n\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"📊 Symbol: <b>{symbol}</b>\n"
            f"Entry: ${entry_price:.4f} → SL: ${stop_price:.4f}\n"
            f"💸 Loss: <b>-${abs(loss_usdt):.2f}</b>\n"
            f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self._send(text)

    async def send_bot_error(
        self, bot_name: str, error: str
    ) -> bool:
        text = (
            f"<b>⚠️ Bot Error</b>\n\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"Error: <code>{error[:500]}</code>\n"
            f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self._send(text)

    async def send_daily_summary(
        self,
        username: str,
        date: str,
        total_pnl: float,
        total_trades: int,
        win_rate: float,
        active_bots: int,
        portfolio_value: float,
    ) -> bool:
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"
        pnl_sign = "+" if total_pnl >= 0 else ""

        text = (
            f"<b>📊 Daily Summary — {date}</b>\n"
            f"👤 {username}\n\n"
            f"{pnl_emoji} Daily PnL: <b>{pnl_sign}${total_pnl:.2f}</b>\n"
            f"🔄 Trades: {total_trades}\n"
            f"🎯 Win Rate: {win_rate:.1f}%\n"
            f"🤖 Active Bots: {active_bots}\n"
            f"💼 Portfolio: <b>${portfolio_value:,.2f}</b>"
        )
        return await self._send(text)

    async def send_max_loss_warning(
        self, bot_name: str, daily_loss: float, max_loss: float
    ) -> bool:
        text = (
            f"<b>🚨 Max Daily Loss Reached — Bot Paused</b>\n\n"
            f"🤖 Bot: <code>{bot_name}</code>\n"
            f"📉 Daily Loss: ${abs(daily_loss):.2f}\n"
            f"🔒 Limit: ${max_loss:.2f}\n"
            f"Bot has been automatically paused.\n"
            f"🕐 {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        return await self._send(text)
