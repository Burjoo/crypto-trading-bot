"""Exchange management endpoints — connect, list, test, and remove exchange accounts."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.core.security import encrypt_api_key
from app.models.models import Exchange, ExchangeName, User
from app.services.exchange_service import ExchangeService

router = APIRouter()
exchange_svc = ExchangeService()


class AddExchangeRequest(BaseModel):
    name: ExchangeName
    label: str = Field(..., min_length=1, max_length=100)
    api_key: str = Field(..., min_length=1)
    api_secret: str = Field(..., min_length=1)
    passphrase: Optional[str] = None   # Coinbase Pro only
    is_paper_trading: bool = True


@router.get("")
async def list_exchanges(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Exchange).where(Exchange.user_id == current_user.id)
    )
    exchanges = result.scalars().all()
    return {
        "exchanges": [
            {
                "id": e.id,
                "name": e.name,
                "label": e.label,
                "is_paper_trading": e.is_paper_trading,
                "is_active": e.is_active,
                "last_sync_at": e.last_sync_at,
                "created_at": e.created_at,
                # Never return raw keys
                "api_key_hint": "****" + e.encrypted_api_key[-4:] if e.encrypted_api_key else None,
            }
            for e in exchanges
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_exchange(
    payload: AddExchangeRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add and encrypt an exchange API key pair."""
    # Test connectivity before saving
    if not payload.is_paper_trading:
        try:
            await exchange_svc.fetch_balance(
                exchange_name=payload.name,
                api_key_enc=encrypt_api_key(payload.api_key),
                api_secret_enc=encrypt_api_key(payload.api_secret),
                passphrase_enc=encrypt_api_key(payload.passphrase) if payload.passphrase else None,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Exchange connection test failed: {str(exc)}"
            )

    exchange = Exchange(
        user_id=current_user.id,
        name=payload.name,
        label=payload.label,
        encrypted_api_key=encrypt_api_key(payload.api_key),
        encrypted_api_secret=encrypt_api_key(payload.api_secret),
        encrypted_passphrase=encrypt_api_key(payload.passphrase) if payload.passphrase else None,
        is_paper_trading=payload.is_paper_trading,
    )
    db.add(exchange)
    await db.commit()
    await db.refresh(exchange)
    return {"message": "Exchange connected", "exchange_id": exchange.id}


@router.get("/{exchange_id}/balance")
async def get_balance(
    exchange_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exchange = await db.get(Exchange, exchange_id)
    if not exchange or exchange.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Exchange not found")

    if exchange.is_paper_trading:
        return {"mode": "paper", "balance": {"USDT": {"free": 10000, "used": 0, "total": 10000}}}

    try:
        balance = await exchange_svc.fetch_balance(
            exchange.name, exchange.encrypted_api_key, exchange.encrypted_api_secret,
            exchange.encrypted_passphrase,
        )
        return {"mode": "live", "balance": balance}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{exchange_id}/symbols")
async def get_symbols(
    exchange_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    quote: str = "USDT",
):
    exchange = await db.get(Exchange, exchange_id)
    if not exchange or exchange.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Exchange not found")
    try:
        symbols = await exchange_svc.get_supported_symbols(exchange.name, quote)
        return {"symbols": symbols[:200]}  # cap at 200
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/{exchange_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_exchange(
    exchange_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    exchange = await db.get(Exchange, exchange_id)
    if not exchange or exchange.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Exchange not found")
    await db.delete(exchange)
    await db.commit()
