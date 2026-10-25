from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from outbox.models import Outbox


class OutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, event_type: str, payload: dict[str, Any]) -> None:
        self._session.add(Outbox(event_type=event_type, payload=payload))
