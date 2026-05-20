"""Trading journal endpoints."""
from __future__ import annotations
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models.models import JournalEntry, User

router = APIRouter()


class JournalCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    trade_id: Optional[str] = None
    notes: Optional[str] = None
    emotion: Optional[str] = None
    mistakes: Optional[str] = None
    lessons: Optional[str] = None
    setup_quality: Optional[int] = Field(None, ge=1, le=10)
    tags: list[str] = Field(default_factory=list)
    screenshot_urls: list[str] = Field(default_factory=list)


@router.get("")
async def list_entries(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 20,
    offset: int = 0,
):
    result = await db.execute(
        select(JournalEntry)
        .where(JournalEntry.user_id == current_user.id)
        .order_by(desc(JournalEntry.created_at))
        .limit(limit).offset(offset)
    )
    entries = result.scalars().all()
    return {
        "entries": [
            {
                "id": e.id,
                "title": e.title,
                "trade_id": e.trade_id,
                "emotion": e.emotion,
                "setup_quality": e.setup_quality,
                "tags": e.tags,
                "created_at": e.created_at,
            }
            for e in entries
        ]
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: JournalCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    entry = JournalEntry(
        user_id=current_user.id,
        **payload.model_dump()
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"message": "Entry created", "id": entry.id}


@router.get("/analytics")
async def journal_analytics(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Analyze journal entries: emotion distribution, quality scores, tag frequency."""
    result = await db.execute(
        select(JournalEntry).where(JournalEntry.user_id == current_user.id)
    )
    entries = result.scalars().all()

    emotion_counts: dict[str, int] = {}
    tag_counts: dict[str, int] = {}
    quality_scores = []

    for e in entries:
        if e.emotion:
            emotion_counts[e.emotion] = emotion_counts.get(e.emotion, 0) + 1
        for tag in (e.tags or []):
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
        if e.setup_quality:
            quality_scores.append(e.setup_quality)

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0

    return {
        "total_entries": len(entries),
        "emotion_distribution": emotion_counts,
        "top_tags": sorted(tag_counts.items(), key=lambda x: -x[1])[:10],
        "avg_setup_quality": round(avg_quality, 1),
    }


@router.get("/{entry_id}")
async def get_entry(
    entry_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    entry = await db.get(JournalEntry, entry_id)
    if not entry or entry.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Entry not found")
    return {
        "id": entry.id,
        "title": entry.title,
        "trade_id": entry.trade_id,
        "notes": entry.notes,
        "emotion": entry.emotion,
        "mistakes": entry.mistakes,
        "lessons": entry.lessons,
        "setup_quality": entry.setup_quality,
        "tags": entry.tags,
        "screenshot_urls": entry.screenshot_urls,
        "created_at": entry.created_at,
        "updated_at": entry.updated_at,
    }


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    entry = await db.get(JournalEntry, entry_id)
    if not entry or entry.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Entry not found")
    await db.delete(entry)
    await db.commit()
