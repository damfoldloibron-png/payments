import uuid

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from payment_api.models import Payment, PaymentStatus
from payment_api.schemas import PaymentCreate


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def insert_or_none(
        self, data: PaymentCreate, idempotency_key: str
    ) -> Payment | None:
        """None означает дубль: платёж с таким ключом уже существует"""
        stmt = (
            insert(Payment)
            .values(
                amount=data.amount,
                currency=data.currency,
                description=data.description,
                metadata_json=data.metadata,
                webhook_url=data.webhook_url,
                idempotency_key=idempotency_key,
            )
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(Payment)
        )
        return await self._session.scalar(stmt)

    async def get_by_id(self, payment_id: uuid.UUID) -> Payment:
        """Бросает NoResultFound, если платёж не найден"""
        stmt = select(Payment).where(Payment.id == payment_id)
        return (await self._session.scalars(stmt)).one()

    async def get_by_idempotency_key(self, idempotency_key: str) -> Payment:
        """Бросает NoResultFound, если платёж с таким ключом не найден"""
        stmt = select(Payment).where(Payment.idempotency_key == idempotency_key)
        return (await self._session.scalars(stmt)).one()

    async def set_status(self, payment_id: uuid.UUID, status: PaymentStatus) -> bool:
        """Меняет статус, только если платёж ещё PENDING; True, если строка обновлена"""
        stmt = (
            update(Payment)
            .where(Payment.id == payment_id, Payment.status == PaymentStatus.PENDING)
            .values(status=status, processed_at=func.now())
            .execution_options(synchronize_session=False)
        )
        result = await self._session.execute(stmt)
        return result.rowcount == 1  # type: ignore
