from sqlalchemy.ext.asyncio import AsyncSession

from external.broker.messages import PAYMENT_NEW_EVENT, PaymentNewMessage
from outbox.repository import OutboxRepository
from payment_api.models import Payment
from payment_api.repository import PaymentRepository
from payment_api.schemas import PaymentCreate


async def create_payment(
    session: AsyncSession, data: PaymentCreate, idempotency_key: str
) -> Payment:
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
        return payment
