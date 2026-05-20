"""Alerts and notifications endpoints."""
from __future__ import annotations
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models.models import Alert, User

router = APIRouter()


@router.get("")
async def list_alerts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    unread_only: bool = False,
    limit: int = 30,
):
    query = select(Alert).where(Alert.user_id == current_user.id)
    if unread_only:
        query = query.where(Alert.is_read == False)
    query = query.order_by(desc(Alert.created_at)).limit(limit)
    alerts = (await db.execute(query)).scalars().all()
    return {
        "alerts": [
            {
                "id": a.id,
                "type": a.alert_type,
                "title": a.title,
                "message": a.message,
                "is_read": a.is_read,
                "sent_via_telegram": a.sent_via_telegram,
                "created_at": a.created_at,
            }
            for a in alerts
        ],
        "unread_count": sum(1 for a in alerts if not a.is_read),
    }


@router.post("/{alert_id}/read")
async def mark_read(
    alert_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    alert = await db.get(Alert, alert_id)
    if not alert or alert.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    await db.commit()
    return {"message": "Marked as read"}


@router.post("/read-all")
async def mark_all_read(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await db.execute(
        update(Alert)
        .where(Alert.user_id == current_user.id, Alert.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All alerts marked as read"}
