import logging

import httpx
from faststream import AckPolicy
from faststream.rabbit import RabbitBroker, RabbitMessage
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from consumer.payment_gateway import GatewayError, charge
from consumer.service import fail_payment, process_payment
from external.broker.messages import PaymentNewMessage
from external.broker.topology import (
    PAYMENTS_EXCHANGE,
    PAYMENTS_NEW,
    PAYMENTS_RETRY_EXCHANGE,
    retry_routing_key,
)
from external.webhook.client import PaymentWebhook, send_webhook
from payment_api.models import Payment

logger = logging.getLogger(__name__)

ATTEMPT_HEADER = "x-attempt"


async def schedule_retry(
    broker: RabbitBroker,
    message: PaymentNewMessage,
    attempt: int,
    message_id: str | None,
) -> None:
    """Кладёт копию сообщения в retry-очередь текущей попытки"""
    await broker.publish(
        message.model_dump(mode="json"),
        exchange=PAYMENTS_RETRY_EXCHANGE,
        routing_key=retry_routing_key(attempt),
        headers={ATTEMPT_HEADER: attempt + 1},
        persist=True,
        message_id=message_id,
    )


async def notify(http_client: httpx.AsyncClient, payment: Payment) -> None:
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
    logger.info("Webhook отправлен payment_id=%s status=%s", payment.id, payment.status)


def register_handlers(
    broker: RabbitBroker,
    sessionmaker: async_sessionmaker[AsyncSession],
    http_client: httpx.AsyncClient,
    max_attempts: int,
) -> None:
    @broker.subscriber(
        PAYMENTS_NEW, PAYMENTS_EXCHANGE, ack_policy=AckPolicy.REJECT_ON_ERROR
    )
    async def handle_payment_new(
        message: PaymentNewMessage, msg: RabbitMessage
    ) -> None:
        attempt = int(msg.headers.get(ATTEMPT_HEADER, 1))
        logger.info(
            "Получено payment.new payment_id=%s idem_key=%s попытка=%s",
            message.payment_id,
            message.idempotency_key,
            attempt,
        )
        try:
            payment = await process_payment(sessionmaker, message.payment_id, charge)
            logger.info(
                "Платёж обработан payment_id=%s status=%s", payment.id, payment.status
            )
            await notify(http_client, payment)
        except NoResultFound:
            # Платежа нет: повтор не поможет, сразу в DLQ
            logger.error(
                "Платеж не найден payment_id=%s, отправлен в DLQ", message.payment_id
            )
            raise
        except Exception as exc:
            if attempt < max_attempts:
                logger.warning(
                    "Попытка %s не удалась payment_id=%s: %r, повтор запланирован",
                    attempt,
                    message.payment_id,
                    exc,
                )
                await schedule_retry(broker, message, attempt, msg.message_id)
                return
            # Попытки закончились, сообщение уйдёт в DLQ. FAILED и вебхук только при
            # ошибке шлюза; при ошибке БД итог у шлюза неизвестен, оставляем PENDING
            if isinstance(exc, GatewayError):
                failed = await fail_payment(sessionmaker, message.payment_id)
                await notify(http_client, failed)
            logger.exception(
                "Платеж не обработан payment_id=%s, отправвлен в DLQ. %r",
                message.payment_id,
                exc,
            )
            raise
