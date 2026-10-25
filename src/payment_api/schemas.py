import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from payment_api.models import Currency, PaymentStatus


class PaymentCreate(BaseModel):
    amount: Decimal = Field(
        max_digits=18,
        decimal_places=2,
        description="Сумма платежа, до 2 знаков после запятой",
        examples=["1500.50"],
    )
    currency: Currency = Field(description="Валюта платежа", examples=["RUB"])
    description: str | None = Field(
        default=None,
        description="Описание платежа",
        examples=["Оплата заказа №123"],
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Произвольные данные платежа, например идентификатор заказа",
        examples=[{"order_id": "123"}],
    )
    webhook_url: str = Field(
        max_length=2048,
        description="URL, на который придёт уведомление о результате обработки",
        examples=["https://example.com/webhooks/payments"],
    )


class PaymentCreated(BaseModel):
    payment_id: uuid.UUID = Field(
        description="Идентификатор платежа",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    status: PaymentStatus = Field(description="Статус платежа", examples=["PENDING"])
    created_at: datetime = Field(
        description="Время создания платежа",
        examples=["2026-10-07T12:00:00Z"],
    )
