import asyncio
import contextlib
import logging
from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.app import RelaySettings
from outbox.repository import OutboxRepository

logger = logging.getLogger(__name__)


async def cleanup_once(
    sessionmaker: async_sessionmaker[AsyncSession], cfg: RelaySettings
) -> int:
    """Удаляет опубликованные записи старше срока хранения, возвращает их число"""
    older_than = timedelta(hours=cfg.outbox_retention_hours)
    total = 0
    while True:
        async with sessionmaker() as session, session.begin():
            deleted = await OutboxRepository(session).delete_published(
                older_than, cfg.outbox_cleanup_batch
            )
        total += deleted
        if deleted < cfg.outbox_cleanup_batch:
            return total


async def run_cleanup(
    sessionmaker: async_sessionmaker[AsyncSession],
    cfg: RelaySettings,
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        try:
            deleted = await cleanup_once(sessionmaker, cfg)
            if deleted:
                logger.info("Очистка outbox: удалено записей %s", deleted)
        except Exception as exc:
            logger.exception("Ошибка очистки outbox exc=%s", exc)
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), cfg.outbox_cleanup_interval)
