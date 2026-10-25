import uuid
from decimal import Decimal

import httpx
from pydantic import BaseModel

from config.app import WebhookSettings


class PaymentWebhook(BaseModel):
    # status и currency строками: external/ не зависит от моделей доменов
    payment_id: uuid.UUID
    status: str
    amount: Decimal
    currency: str


def create_webhook_client(cfg: WebhookSettings) -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=cfg.webhook_timeout)


async def send_webhook(
    client: httpx.AsyncClient, url: str, payload: PaymentWebhook
) -> None:
    response = await client.post(url, json=payload.model_dump(mode="json"))
    response.raise_for_status()
