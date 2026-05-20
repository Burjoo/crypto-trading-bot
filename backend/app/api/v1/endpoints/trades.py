"""Trade history endpoints."""
from __future__ import annotations
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models.models import Trade, TradeStatus, User

router = APIRouter()


@router.get("")
async def list_trades(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    query = select(Trade).where(Trade.user_id == current_user.id)
    if status:
        query = query.where(Trade.status == status)
    if symbol:
        query = query.where(Trade.symbol == symbol)
    query = query.order_by(desc(Trade.opened_at)).limit(limit).offset(offset)

    trades = (await db.execute(query)).scalars().all()
    return {
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "status": t.status,
                "order_type": t.order_type,
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "stop_loss_price": t.stop_loss_price,
                "take_profit_price": t.take_profit_price,
                "pnl_usdt": t.pnl_usdt,
                "pnl_pct": t.pnl_pct,
                "commission_usdt": t.commission_usdt,
                "is_paper_trade": t.is_paper_trade,
                "entry_reason": t.entry_reason,
                "exit_reason": t.exit_reason,
                "opened_at": t.opened_at,
                "closed_at": t.closed_at,
                "bot_id": t.bot_id,
            }
            for t in trades
        ],
        "total": len(trades),
    }


@router.get("/{trade_id}")
async def get_trade(
    trade_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    trade = await db.get(Trade, trade_id)
    if not trade or trade.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "status": trade.status,
        "entry_price": trade.entry_price,
        "exit_price": trade.exit_price,
        "quantity": trade.quantity,
        "pnl_usdt": trade.pnl_usdt,
        "pnl_pct": trade.pnl_pct,
        "entry_reason": trade.entry_reason,
        "exit_reason": trade.exit_reason,
        "opened_at": trade.opened_at,
        "closed_at": trade.closed_at,
    }
