#!/usr/bin/env python
"""
Create the initial admin user.
Usage: docker compose exec backend python scripts/create_admin.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal, init_db
from app.models.models import User, UserSettings, UserRole
from app.core.security import hash_password
from app.core.config import settings


async def create_admin():
    await init_db()
    async with AsyncSessionLocal() as session:
        existing = await session.execute(
            select(User).where(User.email == settings.FIRST_SUPERUSER_EMAIL)
        )
        if existing.scalar_one_or_none():
            print(f"✅ Admin already exists: {settings.FIRST_SUPERUSER_EMAIL}")
            return

        admin = User(
            email=settings.FIRST_SUPERUSER_EMAIL,
            username="admin",
            hashed_password=hash_password(settings.FIRST_SUPERUSER_PASSWORD),
            full_name="Administrator",
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True,
        )
        session.add(admin)
        await session.flush()
        session.add(UserSettings(user_id=admin.id))
        await session.commit()
        print(f"✅ Admin created: {settings.FIRST_SUPERUSER_EMAIL}")
        print(f"   Password: {settings.FIRST_SUPERUSER_PASSWORD}")
        print("   ⚠️  Change the password immediately after first login!")


if __name__ == "__main__":
    asyncio.run(create_admin())
