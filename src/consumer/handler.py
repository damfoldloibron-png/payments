import logging

import httpx
from faststream import AckPolicy
from faststream.rabbit import RabbitBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from consumer.payment_gateway import charge
from consumer.service import process_payment
from external.broker.messages import PaymentNewMessage
from external.broker.topology import PAYMENTS_EXCHANGE, PAYMENTS_NEW
from external.webhook.client import PaymentWebhook, send_webhook

logger = logging.getLogger(__name__)


def register_handlers(
    broker: RabbitBroker,
    sessionmaker: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient,
) -> None:
    @broker.subscriber(
        PAYMENTS_NEW, PAYMENTS_EXCHANGE, ack_policy=AckPolicy.REJECT_ON_ERROR
    )
    async def handle_payment_new(message: PaymentNewMessage) -> None:
        logger.info(
            "Получено payment.new payment_id=%s idem_key=%s",
            message.payment_id,
            message.idempotency_key,
        )
        payment = await process_payment(sessionmaker, message.payment_id, charge)
        logger.info(
            "Платёж обработан payment_id=%s status=%s", payment.id, payment.status
        )
        await send_webhook(
            http_client,
            payment.webhook_url,
            PaymentWebhook(
                payment_id=payment.id,
                status=payment.status,
                amount=payment.amount,
                currency=payment.currency,
            ),
        )
        logger.info("Webhook отправлен payment_id=%s", payment.id)
