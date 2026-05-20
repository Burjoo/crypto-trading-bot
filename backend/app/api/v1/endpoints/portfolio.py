"""Portfolio summary endpoint."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models.models import Bot, BotStatus, Trade, TradeStatus, User

router = APIRouter()


@router.get("/summary")
async def portfolio_summary(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    # All-time closed trades
    all_trades = (await db.execute(
        select(Trade).where(Trade.user_id == current_user.id, Trade.status == TradeStatus.CLOSED)
    )).scalars().all()

    # Today's trades
    today_trades = [t for t in all_trades if t.closed_at and t.closed_at >= today_start]

    total_pnl = sum(t.pnl_usdt or 0 for t in all_trades)
    today_pnl = sum(t.pnl_usdt or 0 for t in today_trades)
    wins = [t for t in all_trades if (t.pnl_usdt or 0) > 0]
    win_rate = round(len(wins) / len(all_trades) * 100, 1) if all_trades else 0.0

    # Active bots
    bots_result = await db.execute(
        select(Bot).where(Bot.user_id == current_user.id)
    )
    bots = bots_result.scalars().all()
    active_bots = [b for b in bots if b.status == BotStatus.RUNNING]

    # Open trades
    open_trades = (await db.execute(
        select(Trade).where(Trade.user_id == current_user.id, Trade.status == TradeStatus.OPEN)
    )).scalars().all()

    # Equity over last 30 days (daily PnL rolling sum)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_trades = [t for t in all_trades if t.closed_at and t.closed_at >= thirty_days_ago]
    daily_map: dict[str, float] = {}
    for t in recent_trades:
        day = t.closed_at.strftime("%Y-%m-%d")
        daily_map[day] = daily_map.get(day, 0) + (t.pnl_usdt or 0)
    equity_history = [{"date": k, "pnl": round(v, 2)} for k, v in sorted(daily_map.items())]

    return {
        "total_pnl_usdt": round(total_pnl, 2),
        "today_pnl_usdt": round(today_pnl, 2),
        "total_trades": len(all_trades),
        "today_trades": len(today_trades),
        "win_rate_pct": win_rate,
        "active_bots": len(active_bots),
        "total_bots": len(bots),
        "open_positions": len(open_trades),
        "paper_balance_total": round(sum(b.paper_balance_usdt for b in bots), 2),
        "equity_history": equity_history,
        "bot_summary": [
            {
                "id": b.id,
                "name": b.name,
                "symbol": b.symbol,
                "status": b.status,
                "total_pnl_usdt": round(b.total_pnl_usdt, 2),
                "total_trades": b.total_trades,
            }
            for b in bots
        ],
    }
