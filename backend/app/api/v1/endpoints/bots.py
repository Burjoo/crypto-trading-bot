"""
Bot Management Endpoints.
Create, configure, start, stop, and monitor trading bots.
"""
from __future__ import annotations

from typing import Annotated, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_db, get_current_user
from app.models.models import Bot, BotStatus, Exchange, Strategy, Trade, TradeStatus, User
from app.websockets.manager import ws_manager

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class CreateBotRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    exchange_id: str
    strategy_type: str
    strategy_params: dict = Field(default_factory=dict)
    symbol: str = Field(..., min_length=3, max_length=20)
    timeframe: str = Field(default="1h")
    position_size_usdt: float = Field(gt=0, le=100_000)
    max_open_trades: int = Field(default=1, ge=1, le=10)
    stop_loss_pct: Optional[float] = Field(None, gt=0, le=50)
    take_profit_pct: Optional[float] = Field(None, gt=0, le=100)
    trailing_stop_pct: Optional[float] = Field(None, gt=0, le=50)
    max_daily_loss_usdt: Optional[float] = Field(None, gt=0)


class UpdateBotRequest(BaseModel):
    name: Optional[str] = None
    position_size_usdt: Optional[float] = Field(None, gt=0)
    stop_loss_pct: Optional[float] = Field(None, gt=0, le=50)
    take_profit_pct: Optional[float] = Field(None, gt=0, le=100)
    trailing_stop_pct: Optional[float] = Field(None, gt=0, le=50)
    max_daily_loss_usdt: Optional[float] = Field(None, gt=0)
    max_open_trades: Optional[int] = Field(None, ge=1, le=10)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _bot_to_dict(bot: Bot) -> dict:
    win_rate = (
        round(bot.winning_trades / bot.total_trades * 100, 1)
        if bot.total_trades > 0 else 0.0
    )
    return {
        "id": bot.id,
        "name": bot.name,
        "symbol": bot.symbol,
        "timeframe": bot.timeframe,
        "status": bot.status,
        "position_size_usdt": bot.position_size_usdt,
        "stop_loss_pct": bot.stop_loss_pct,
        "take_profit_pct": bot.take_profit_pct,
        "trailing_stop_pct": bot.trailing_stop_pct,
        "max_daily_loss_usdt": bot.max_daily_loss_usdt,
        "max_open_trades": bot.max_open_trades,
        "total_trades": bot.total_trades,
        "winning_trades": bot.winning_trades,
        "win_rate_pct": win_rate,
        "total_pnl_usdt": round(bot.total_pnl_usdt, 2),
        "paper_balance_usdt": round(bot.paper_balance_usdt, 2),
        "last_tick_at": bot.last_tick_at,
        "error_message": bot.error_message,
        "created_at": bot.created_at,
        "exchange_id": bot.exchange_id,
        "strategy_id": bot.strategy_id,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("")
async def list_bots(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: Optional[str] = None,
):
    """List all bots for the current user."""
    query = select(Bot).where(Bot.user_id == current_user.id)
    if status_filter:
        query = query.where(Bot.status == status_filter)
    query = query.order_by(Bot.created_at.desc())

    result = await db.execute(query)
    bots = result.scalars().all()
    return {"bots": [_bot_to_dict(b) for b in bots], "total": len(bots)}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_bot(
    payload: CreateBotRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new trading bot."""
    from app.core.config import settings

    # Check bot limit
    count_result = await db.execute(
        select(func.count(Bot.id)).where(Bot.user_id == current_user.id)
    )
    if count_result.scalar() >= settings.MAX_BOTS_PER_USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.MAX_BOTS_PER_USER} bots allowed per user",
        )

    # Verify exchange belongs to user
    exchange = await db.get(Exchange, payload.exchange_id)
    if not exchange or exchange.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Exchange not found")

    # Create or find strategy
    strategy_result = await db.execute(
        select(Strategy).where(
            Strategy.strategy_type == payload.strategy_type,
            Strategy.created_by == current_user.id,
        )
    )
    strategy = strategy_result.scalar_one_or_none()
    if not strategy:
        strategy = Strategy(
            name=f"{payload.strategy_type.replace('_', ' ').title()} — {payload.symbol}",
            strategy_type=payload.strategy_type,
            parameters=payload.strategy_params,
            created_by=current_user.id,
        )
        db.add(strategy)
        await db.flush()

    bot = Bot(
        user_id=current_user.id,
        exchange_id=payload.exchange_id,
        strategy_id=strategy.id,
        name=payload.name,
        symbol=payload.symbol,
        timeframe=payload.timeframe,
        position_size_usdt=payload.position_size_usdt,
        max_open_trades=payload.max_open_trades,
        stop_loss_pct=payload.stop_loss_pct,
        take_profit_pct=payload.take_profit_pct,
        trailing_stop_pct=payload.trailing_stop_pct,
        max_daily_loss_usdt=payload.max_daily_loss_usdt,
        paper_balance_usdt=10_000.0,
    )
    db.add(bot)
    await db.commit()
    await db.refresh(bot)

    return {"message": "Bot created", "bot": _bot_to_dict(bot)}


@router.get("/{bot_id}")
async def get_bot(
    bot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single bot by ID."""
    bot = await db.get(Bot, bot_id)
    if not bot or bot.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")
    return _bot_to_dict(bot)


@router.patch("/{bot_id}")
async def update_bot(
    bot_id: str,
    payload: UpdateBotRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update bot configuration. Bot must be stopped first."""
    bot = await db.get(Bot, bot_id)
    if not bot or bot.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")

    if bot.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Stop the bot before updating configuration")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(bot, field, value)

    await db.commit()
    return {"message": "Bot updated", "bot": _bot_to_dict(bot)}


@router.post("/{bot_id}/start")
async def start_bot(
    bot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Start a trading bot."""
    bot = await db.get(Bot, bot_id)
    if not bot or bot.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")

    if bot.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Bot is already running")

    bot.status = BotStatus.RUNNING
    bot.error_message = None
    await db.commit()

    # Notify via WebSocket
    await ws_manager.broadcast_bot_status(current_user.id, bot_id, "running")

    return {"message": f"Bot '{bot.name}' started", "status": "running"}


@router.post("/{bot_id}/stop")
async def stop_bot(
    bot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Stop a running bot."""
    bot = await db.get(Bot, bot_id)
    if not bot or bot.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")

    bot.status = BotStatus.STOPPED
    await db.commit()

    await ws_manager.broadcast_bot_status(current_user.id, bot_id, "stopped")

    return {"message": f"Bot '{bot.name}' stopped", "status": "stopped"}


@router.delete("/{bot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot(
    bot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a bot (must be stopped)."""
    bot = await db.get(Bot, bot_id)
    if not bot or bot.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")

    if bot.status == BotStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Stop the bot before deleting")

    await db.delete(bot)
    await db.commit()


@router.get("/{bot_id}/trades")
async def get_bot_trades(
    bot_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 50,
    offset: int = 0,
):
    """Get trade history for a specific bot."""
    bot = await db.get(Bot, bot_id)
    if not bot or bot.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Bot not found")

    result = await db.execute(
        select(Trade)
        .where(Trade.bot_id == bot_id)
        .order_by(Trade.opened_at.desc())
        .limit(limit)
        .offset(offset)
    )
    trades = result.scalars().all()

    return {
        "bot_id": bot_id,
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "status": t.status,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "pnl_usdt": t.pnl_usdt,
                "pnl_pct": t.pnl_pct,
                "exit_reason": t.exit_reason,
                "opened_at": t.opened_at,
                "closed_at": t.closed_at,
            }
            for t in trades
        ],
    }
