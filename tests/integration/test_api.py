import asyncio
import uuid
from decimal import Decimal
from typing import Any

import httpx
import pytest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("headers", [{}, {"X-API-Key": "wrong"}])
async def test_requires_valid_api_key(
    client: httpx.AsyncClient, headers: dict[str, str]
) -> None:
    """
    тест валидности ключа авторизации, 401 возврат
    """
    async with httpx.AsyncClient(base_url=client.base_url) as anonymous:
        response = await anonymous.get(
            f"/api/v1/payments/{uuid.uuid4()}", headers=headers
        )
    assert response.status_code == 401


async def test_create_and_get_payment(create_payment, wait_final) -> None:
    """
    тест создания платежа и ожидание его завершения
    """
    created = await create_payment()
    assert created.status_code == 202
    body = created.json()
    assert body["status"] == "PENDING"

    payment = await wait_final(body["payment_id"])
    assert payment["status"] == "SUCCEEDED"
    assert payment["processed_at"] is not None
    assert payment["currency"] == "RUB"
    assert Decimal(str(payment["amount"])) == Decimal("1500.50")


async def test_repeat_with_same_key_returns_same_payment(create_payment) -> None:
    """
    тест идемпотентности, состояние не меняется
    """
    key = f"test-{uuid.uuid4()}"
    first = await create_payment(key)
    second = await create_payment(key)
    assert first.status_code == second.status_code == 202
    assert first.json()["payment_id"] == second.json()["payment_id"]
