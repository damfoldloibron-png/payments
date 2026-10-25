import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from exc_handler import setup_exception_handlers
from middleware import setup_middlewares
from routers import setup_routers

logger = logging.getLogger(__name__)


async def startup():
    logger.info("START Application")


async def shutdown():
    logger.info("FINISH Application")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup()
    yield
    await shutdown()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan, redirect_slashes=False)
    setup_routers(app=app)
    setup_exception_handlers(app=app)
    setup_middlewares(app=app)
    return app
