import logging

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from config.app import DatabaseSettings

logger = logging.getLogger(__name__)


def create_engine(cfg: DatabaseSettings) -> AsyncEngine:
    engine = create_async_engine(
        cfg.sqlalchemy_url,
        echo=cfg.db_echo,
        pool_size=cfg.db_pool_size,
        max_overflow=cfg.db_max_overflow,
        pool_pre_ping=True,
    )

    logger.info("Start db engine")
    return engine


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    logger.debug("Create async sessionmaker")
    return async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
