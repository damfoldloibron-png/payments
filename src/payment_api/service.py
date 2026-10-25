import logging
import uuid

from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from external.broker.messages import PAYMENT_NEW_EVENT, PaymentNewMessage
from outbox.repository import OutboxRepository
from payment_api.exceptions import PaymentNotFound
from payment_api.models import Payment
from payment_api.repository import PaymentRepository
from payment_api.schemas import PaymentCreate

logger = logging.getLogger(__name__)


async def create_payment(
    session: AsyncSession, data: PaymentCreate, idempotency_key: str
) -> Payment:
    logger.debug("Создание платежа idem_key=%s", idempotency_key)
    payments = PaymentRepository(session)
    outbox = OutboxRepository(session)
    async with session.begin():
        payment = await payments.insert_or_none(data, idempotency_key)
        if payment is None:
            return await payments.get_by_idempotency_key(idempotency_key)
        message = PaymentNewMessage(
            payment_id=payment.id, idempotency_key=idempotency_key
        )
        outbox.add(PAYMENT_NEW_EVENT, message.model_dump(mode="json"))
        logger.debug("Платеж создан idem_key=%s", idempotency_key)
        return payment


async def get_payment(session: AsyncSession, payment_id: uuid.UUID) -> Payment:
    try:
        return await PaymentRepository(session).get_by_id(payment_id)
    except NoResultFound as exc:
        logger.exception("Платеж не найден id=%s", payment_id)
        raise PaymentNotFound(payment_id) from exc
