import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from payment_api.dependencies import get_session, verify_api_key
from payment_api.schemas import PaymentCreate, PaymentCreated, PaymentDetails
from payment_api.service import create_payment, get_payment

router = APIRouter(prefix="/api/v1", dependencies=[Depends(verify_api_key)])


@router.post(
    "/payments",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Создать платёж",
    responses={401: {"description": "Отсутствует или неверен заголовок X-API-Key"}},
)
async def create_payment_endpoint(
    body: PaymentCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[
        str,
        Header(
            alias="Idempotency-Key",
            max_length=255,
            description="Ключ идемпотентности",
        ),
    ],
) -> PaymentCreated:
    payment = await create_payment(session, body, idempotency_key)
    return PaymentCreated(
        payment_id=payment.id,
        status=payment.status,
        created_at=payment.created_at,
    )


@router.get(
    "/payments/{payment_id}",
    summary="Получить платёж",
    responses={
        401: {"description": "Отсутствует или неверен заголовок X-API-Key"},
        404: {"description": "Платёж не найден"},
    },
)
async def get_payment_endpoint(
    payment_id: uuid.UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PaymentDetails:
    payment = await get_payment(session, payment_id)
    return PaymentDetails(
        payment_id=payment.id,
        amount=payment.amount,
        currency=payment.currency,
        description=payment.description,
        metadata=payment.metadata_json,
        status=payment.status,
        webhook_url=payment.webhook_url,
        idempotency_key=payment.idempotency_key,
        created_at=payment.created_at,
        processed_at=payment.processed_at,
    )
