import asyncio
import contextlib
import logging

from aio_pika.exceptions import DeliveryError
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from config.app import RelaySettings
from external.broker.topology import PAYMENTS_EXCHANGE
from outbox.repository import OutboxRepository

logger = logging.getLogger(__name__)


async def relay_once(
    sessionmaker: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
    cfg: RelaySettings,
) -> int:
    """Публикует одну пачку событий и возвращает число отправленных"""
    async with sessionmaker() as session, session.begin():
        outbox = OutboxRepository(session)
        published: list[int] = []
        for event in await outbox.fetch_unpublished(cfg.relay_batch_size):
            try:
                await broker.publish(
                    event.payload,
                    exchange=PAYMENTS_EXCHANGE,
                    routing_key=event.routing_key,
                    persist=True,
                    message_id=str(event.id),
                    timeout=cfg.relay_publish_timeout,
                )
            except DeliveryError as exc:
                logger.error("Брокер отверг событие outbox id=%s: %s", event.id, exc)
                continue
            except Exception:
                logger.exception(
                    "Брокер недоступен, пачка прервана на событии outbox id=%s",
                    event.id,
                )
                break
            published.append(event.id)

        if published:
            await outbox.mark_published(published)
    return len(published)


async def run_relay(
    sessionmaker: async_sessionmaker[AsyncSession],
    broker: RabbitBroker,
    cfg: RelaySettings,
    stop: asyncio.Event,
) -> None:
    while not stop.is_set():
        try:
            sent = await relay_once(sessionmaker, broker, cfg)
        except Exception as exc:
            logger.exception("Ошибка итерации relay exc=%s", exc)
            sent = 0
        if sent < cfg.relay_batch_size:
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(stop.wait(), cfg.relay_poll_interval)
