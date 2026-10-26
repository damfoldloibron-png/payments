import asyncio
import logging

from faststream import FastStream

from config import settings
from config.log_conf import setup_logging
from consumer.handler import register_handlers
from database.core import create_engine, create_sessionmaker
from external.broker.core import create_broker
from external.broker.topology import declare_topology
from external.webhook.client import create_webhook_client

logger = logging.getLogger(__name__)


def create_app() -> FastStream:
    broker = create_broker(settings.rabbit)
    engine = create_engine(settings.database)
    sessionmaker = create_sessionmaker(engine)
    http_client = create_webhook_client(settings.webhook)
    register_handlers(
        broker, sessionmaker, http_client, settings.retry.retry_max_attempts
    )

    async def declare() -> None:
        await broker.connect()
        await declare_topology(broker, settings.retry.retry_delays)
        logger.info("Консьюмер запущен")

    async def dispose_engine() -> None:
        await http_client.aclose()
        await engine.dispose()
        logger.info("Консьюмер остановлен")

    return FastStream(
        broker, on_startup=[declare], after_shutdown=[dispose_engine], logger=logger
    )


if __name__ == "__main__":
    setup_logging()
    asyncio.run(create_app().run())
