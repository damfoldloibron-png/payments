import asyncio
import os
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest
import pytest_asyncio

from config import settings

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
# Любой существующий адрес, отвечающий 200 на POST: доставку webhook тесты не проверяют
WEBHOOK_URL = os.getenv("TEST_WEBHOOK_URL", "https://httpbin.org/post")
FINAL_STATUSES = {"SUCCEEDED", "FAILED"}

CreatePayment = Callable[..., Awaitable[httpx.Response]]
WaitFinal = Callable[..., Awaitable[dict[str, Any]]]


@pytest_asyncio.fixture(scope="session")
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"X-API-Key": settings.api.api_key},
        timeout=30,
    ) as http_client:
        yield http_client


@pytest.fixture
def payment_body() -> dict[str, Any]:
    return {
        "amount": "1500.50",
        "currency": "RUB",
        "description": "Тестовый платеж",
        "metadata": {"source": "tests"},
        "webhook_url": WEBHOOK_URL,
    }


@pytest.fixture
def create_payment(
    client: httpx.AsyncClient, payment_body: dict[str, Any]
) -> CreatePayment:
    async def _create(key: str | None = None, **overrides: Any) -> httpx.Response:
        return await client.post(
            "/api/v1/payments",
            json={**payment_body, **overrides},
            headers={"Idempotency-Key": key or f"test-{uuid.uuid4()}"},
        )

    return _create


@pytest.fixture
def wait_final(client: httpx.AsyncClient) -> WaitFinal:
    async def _wait(
        payment_id: str, timeout: float = 40.0, interval: float = 0.5
    ) -> dict[str, Any]:
        """Опрашивает GET, пока платеж не получит финальный статус"""
        deadline = time.monotonic() + timeout
        while True:
            response = await client.get(f"/api/v1/payments/{payment_id}")
            response.raise_for_status()
            payment: dict[str, Any] = response.json()
            if payment["status"] in FINAL_STATUSES:
                return payment
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"Платеж {payment_id} не завершен за {timeout} с, "
                    f"статус {payment['status']}"
                )
            await asyncio.sleep(interval)

    return _wait
