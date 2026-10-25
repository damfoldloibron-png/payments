import asyncio
import logging
import random
from typing import Any

logger = logging.getLogger(__name__)

MIN_DELAY = 2.0
MAX_DELAY = 5.0
FAILURE_RATE = 0.1


class GatewayError(Exception):
    """Техническая ошибка платёжного шлюза"""


async def charge(idempotency_key: str, *args: Any, **kwargs: Any) -> None:
    # Реальному провайдеру передаются ключ идемпотентности и другие данные платежа,
    # считаем, что провайдер обрабатывает платежи идемпотентно
    # и можем доставить событие несколько раз
    await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    if random.random() < FAILURE_RATE:
        logger.exception("Ошибка платежного шлюза idem_key=%s", idempotency_key)
        raise GatewayError(f"Шлюз не обработал платёж idem_key={idempotency_key}")
