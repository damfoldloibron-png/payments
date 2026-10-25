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
from routers import setup_routers

logger = logging.getLogger(__name__)


async def startup(app: FastAPI) -> None:
    logger.info("START Application")
    engine = create_engine(settings.database)
    broker = create_broker(settings.rabbit)
    app.state.engine, app.state.broker = engine, broker
    app.state.sessionmaker = create_sessionmaker(engine)
    await broker.connect()
    await declare_topology(broker)


async def shutdown(app: FastAPI) -> None:
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
