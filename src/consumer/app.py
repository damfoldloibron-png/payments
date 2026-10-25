import asyncio

from faststream import FastStream

from config import settings
from config.log_conf import setup_logging
from external.broker.core import create_broker
from external.broker.topology import declare_topology


def create_app() -> FastStream:
    broker = create_broker(settings.rabbit)

    async def declare() -> None:
        await declare_topology(broker)

    return FastStream(broker, after_startup=[declare])


if __name__ == "__main__":
    setup_logging()
    asyncio.run(create_app().run())
