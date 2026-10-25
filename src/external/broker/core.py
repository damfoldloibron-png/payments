import logging

from faststream.rabbit import Channel, RabbitBroker

from config.app import RabbitSettings

logger = logging.getLogger(__name__)


def create_broker(cfg: RabbitSettings) -> RabbitBroker:
    logger.info("Create RabbitBroker")
    return RabbitBroker(
        cfg.rabbit_url,
        # prefetch ограничивает число неподтверждённых сообщений на consumer,
        # то есть число одновременно обрабатываемых платежей
        default_channel=Channel(prefetch_count=cfg.rabbit_prefetch_count),
    )
