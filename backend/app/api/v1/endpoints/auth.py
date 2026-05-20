"""
Authentication endpoints: register, login, refresh token, profile management.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.models import User, UserSettings

router = APIRouter()


# ─── Schemas ──────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=100)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(None, max_length=100)
    telegram_chat_id: str | None = Field(None, max_length=50)
    telegram_alerts_enabled: bool | None = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new user account."""
    # Check uniqueness
    existing = await db.execute(
        select(User).where(
            (User.email == payload.email) | (User.username == payload.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
    )
    db.add(user)
    await db.flush()  # get user.id

    # Create default settings
    db.add(UserSettings(user_id=user.id))
    await db.commit()
    await db.refresh(user)

    return {
        "message": "Account created successfully",
        "user_id": user.id,
        "email": user.email,
        "username": user.username,
    }


@router.post("/login", response_model=LoginResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Authenticate with username/email + password. Returns JWT tokens."""
    # Support login with email OR username
    result = await db.execute(
        select(User).where(
            (User.email == form_data.username) | (User.username == form_data.username)
        )
    )
    user: User | None = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    return LoginResponse(
        access_token=create_access_token(user.id, extra_claims={"role": user.role}),
        refresh_token=create_refresh_token(user.id),
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "avatar_url": user.avatar_url,
        },
    )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(
    payload: RefreshRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Exchange a refresh token for a new access + refresh token pair."""
    user_id = verify_token(payload.refresh_token, token_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return LoginResponse(
        access_token=create_access_token(user.id, extra_claims={"role": user.role}),
        refresh_token=create_refresh_token(user.id),
        user={
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
        },
    )


@router.get("/me")
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    """Return the authenticated user's profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "avatar_url": current_user.avatar_url,
        "telegram_chat_id": current_user.telegram_chat_id,
        "telegram_alerts_enabled": current_user.telegram_alerts_enabled,
        "created_at": current_user.created_at,
        "last_login_at": current_user.last_login_at,
    }


@router.patch("/me")
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update the authenticated user's profile."""
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.telegram_chat_id is not None:
        current_user.telegram_chat_id = payload.telegram_chat_id
    if payload.telegram_alerts_enabled is not None:
        current_user.telegram_alerts_enabled = payload.telegram_alerts_enabled

    await db.commit()
    return {"message": "Profile updated successfully"}


@router.post("/change-password", status_code=status.HTTP_200_OK)
async def change_password(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    old_password: str = "",
    new_password: str = "",
):
    """Change password after verifying the old one."""
    if not verify_password(old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    if len(new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    current_user.hashed_password = hash_password(new_password)
    await db.commit()
    return {"message": "Password changed successfully"}
