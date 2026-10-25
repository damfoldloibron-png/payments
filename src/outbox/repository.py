from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from outbox.models import Outbox


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event_type: str, routing_key: str, payload: dict[str, Any]) -> None:
        self._session.add(
            Outbox(event_type=event_type, routing_key=routing_key, payload=payload)
        )

    async def fetch_unpublished(self, limit: int) -> Sequence[Outbox]:
        """Берёт пачку неотправленных записей"""
        stmt = (
            select(Outbox)
            .where(Outbox.published_at.is_(None))
            .order_by(Outbox.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        return (await self._session.scalars(stmt)).all()

    async def mark_published(self, ids: Sequence[int]) -> None:
        stmt = update(Outbox).where(Outbox.id.in_(ids)).values(published_at=func.now())
        await self._session.execute(stmt)
