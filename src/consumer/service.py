import logging
import uuid
from collections.abc import Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from payment_api.models import Payment, PaymentStatus
from payment_api.repository import PaymentRepository

logger = logging.getLogger(__name__)


async def process_payment(
    sessionmaker: async_sessionmaker[AsyncSession],
    payment_id: uuid.UUID,
    charge: Callable[..., Awaitable[None]],
) -> Payment:
    """Обрабатывает платёж и возвращает его актуальное состояние из БД"""

    async with sessionmaker() as session:
        payment = await PaymentRepository(session).get_by_id(payment_id)
        # Читаем в 1 сессии, чтобы не держать соединение с БД пока платеж выполняется

    if payment.status != PaymentStatus.PENDING:
        return payment

    await charge(payment.idempotency_key)  # Эмуляция платежа

    async with sessionmaker() as session, session.begin():
        repository = PaymentRepository(session)
        updated = await repository.set_status(payment_id, PaymentStatus.SUCCEEDED)
        # Перечитываем: при дубле сообщения статус мог записать другой обработчик
        payment = await repository.get_by_id(payment_id)

    if updated:
        logger.info("Платёж payment_id=%s успешно обработан", payment_id)
    else:
        logger.info(
            "Платёж payment_id=%s уже обработан другим обработчиком", payment_id
        )
    return payment
