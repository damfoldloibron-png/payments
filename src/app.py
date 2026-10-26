import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from database.core import create_engine, create_sessionmaker
from exc_handler import setup_exception_handlers
from external.broker.core import create_broker
from external.broker.topology import declare_topology
from middleware import setup_middlewares
from outbox.cleanup import run_cleanup
from outbox.relay import run_relay
from routers import setup_routers

logger = logging.getLogger(__name__)


async def startup(app: FastAPI) -> None:
    logger.info("START Application")
    engine = create_engine(settings.database)
    broker = create_broker(settings.rabbit)
    app.state.engine, app.state.broker = engine, broker
    app.state.sessionmaker = create_sessionmaker(engine)
    app.state.relay_stop = (
        asyncio.Event()
    )  # Событие отмены, чтобы корректно завершить обработку задач в relay процессе
    await broker.connect()
    await declare_topology(broker, settings.retry.retry_delays)

    app.state.relay_task = asyncio.create_task(
        run_relay(app.state.sessionmaker, broker, settings.relay, app.state.relay_stop),
        name="outbox-relay",
    )
    app.state.cleanup_task = asyncio.create_task(
        run_cleanup(app.state.sessionmaker, settings.relay, app.state.relay_stop),
        name="outbox-cleanup",
    )


async def shutdown(app: FastAPI) -> None:
    app.state.relay_stop.set()
    relay_task = getattr(app.state, "relay_task", None)
    if relay_task is not None:
        await relay_task
    cleanup_task = getattr(app.state, "cleanup_task", None)
    if cleanup_task is not None:
        await cleanup_task
    await app.state.broker.stop()
    await app.state.engine.dispose()
    logger.info("FINISH Application")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    try:
        await startup(app)
        yield
    finally:
        await shutdown(app)


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, redirect_slashes=False)
    setup_routers(app=app)
    setup_exception_handlers(app=app)
    setup_middlewares(app=app)
    return app
