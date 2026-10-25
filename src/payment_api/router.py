from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from payment_api.dependencies import get_session, verify_api_key
from payment_api.schemas import PaymentCreate, PaymentCreated
from payment_api.service import create_payment

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
