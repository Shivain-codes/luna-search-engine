"""Repository for admin users, API keys, settings, and audit events."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from luna_shared.models import AdminUser, APIKey, AuditEvent, Setting


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # Users
    async def get_user_by_email(self, email: str) -> AdminUser | None:
        result = await self.session.execute(
            select(AdminUser).where(AdminUser.email == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_user(self, user_id: uuid.UUID) -> AdminUser | None:
        return await self.session.get(AdminUser, user_id)

    async def create_user(
        self, *, email: str, hashed_password: str, role: str, full_name: str | None = None
    ) -> AdminUser:
        user = AdminUser(
            email=email.lower(),
            hashed_password=hashed_password,
            role=role,
            full_name=full_name,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def touch_login(self, user: AdminUser) -> None:
        user.last_login = datetime.now(UTC)
        await self.session.flush()

    # API keys
    async def create_api_key(
        self,
        *,
        name: str,
        key_hash: str,
        key_prefix: str,
        user_id: uuid.UUID,
        rate_limit: int = 1000,
        expires_at: datetime | None = None,
    ) -> APIKey:
        api_key = APIKey(
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=user_id,
            rate_limit=rate_limit,
            expires_at=expires_at,
        )
        self.session.add(api_key)
        await self.session.flush()
        return api_key

    async def list_api_keys(self, user_id: uuid.UUID | None = None) -> list[APIKey]:
        stmt = select(APIKey).order_by(APIKey.created_at.desc())
        if user_id:
            stmt = stmt.where(APIKey.user_id == user_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_api_key_by_hash(self, key_hash: str) -> APIKey | None:
        result = await self.session.execute(
            select(APIKey).where(APIKey.key_hash == key_hash)
        )
        return result.scalar_one_or_none()

    async def revoke_api_key(self, key_id: uuid.UUID) -> bool:
        api_key = await self.session.get(APIKey, key_id)
        if not api_key:
            return False
        api_key.is_active = False
        await self.session.flush()
        return True

    # Settings
    async def get_setting(self, key: str) -> Setting | None:
        return await self.session.get(Setting, key)

    async def list_settings(self, category: str | None = None) -> list[Setting]:
        stmt = select(Setting)
        if category:
            stmt = stmt.where(Setting.category == category)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def upsert_setting(
        self,
        *,
        key: str,
        value: str,
        description: str | None = None,
        category: str = "general",
        updated_by: uuid.UUID | None = None,
    ) -> Setting:
        setting = await self.get_setting(key)
        if setting is None:
            setting = Setting(key=key, value=value, description=description, category=category)
            self.session.add(setting)
        else:
            setting.value = value
            if description is not None:
                setting.description = description
        setting.updated_by = updated_by
        await self.session.flush()
        return setting

    # Audit
    async def audit(
        self,
        *,
        action: str,
        actor_id: uuid.UUID | None,
        actor_role: str | None,
        target_type: str | None = None,
        target_id: str | None = None,
        outcome: str = "success",
        reason: str | None = None,
        request_id: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            action=action,
            actor_id=actor_id,
            actor_role=actor_role,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            reason=reason,
            request_id=request_id,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_audit(self, limit: int = 50) -> list[AuditEvent]:
        result = await self.session.execute(
            select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
        )
        return list(result.scalars().all())


__all__ = ["AdminRepository"]
