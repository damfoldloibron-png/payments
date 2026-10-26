import asyncio
import os
import time
from collections import Counter

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.timeout(600)]

COUNT = int(os.getenv("TEST_LOAD_COUNT", "100"))
# На один платеж: при prefetch_count=10 пачка в 100 платежей идет ~40 с
PAYMENT_TIMEOUT = float(os.getenv("TEST_LOAD_TIMEOUT", "180"))
SEND_CONCURRENCY = 20
MIN_SUCCESS_RATE = 0.95



async def test_bulk_payments(create_payment, wait_final) -> None:
    """
    тест на пропускную способность, батчем отправляются 100 платежей из COUNT
    """
    semaphore = asyncio.Semaphore(SEND_CONCURRENCY)

    async def process_one() -> str:
        async with semaphore:
            created = await create_payment()
        assert created.status_code == 202
        payment = await wait_final(
            created.json()["payment_id"], timeout=PAYMENT_TIMEOUT, interval=1.0
        )
        return str(payment["status"])

    started = time.monotonic()
    statuses = Counter(await asyncio.gather(*(process_one() for _ in range(COUNT))))
    elapsed = time.monotonic() - started

    success_rate = statuses["SUCCEEDED"] / COUNT
    print(
        f"\nПлатежей: {COUNT}, время: {elapsed:.1f} с, "
        f"скорость: {COUNT / elapsed:.1f} платежей/с, "
        f"SUCCEEDED: {statuses['SUCCEEDED']}, FAILED: {statuses['FAILED']}, "
        f"успех: {success_rate:.0%}"
    )
    assert success_rate >= MIN_SUCCESS_RATE
