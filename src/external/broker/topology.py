from collections.abc import Sequence

from faststream.rabbit import ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from external.broker.messages import PAYMENT_NEW_ROUTING_KEY

PAYMENTS_DLQ_KEY = "payments.dlq"

PAYMENTS_EXCHANGE = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)
PAYMENTS_DLX_EXCHANGE = RabbitExchange(
    "payments.dlx", type=ExchangeType.DIRECT, durable=True
)

PAYMENTS_NEW = RabbitQueue(
    "payments.new",
    durable=True,
    routing_key=PAYMENT_NEW_ROUTING_KEY,
    arguments={
        "x-dead-letter-exchange": PAYMENTS_DLX_EXCHANGE.name,
        "x-dead-letter-routing-key": PAYMENTS_DLQ_KEY,
    },
)
PAYMENTS_DLQ = RabbitQueue(
    "payments.dlq",
    durable=True,
    routing_key=PAYMENTS_DLQ_KEY,
)

PAYMENTS_RETRY_EXCHANGE = RabbitExchange(
    "payments.retry", type=ExchangeType.DIRECT, durable=True
)


def retry_routing_key(level: int) -> str:
    return f"payments.retry.{level}"


def build_retry_queues(delays: Sequence[float]) -> list[RabbitQueue]:
    """По очереди на каждую задержку: по истечении TTL сообщение идёт в payments.new"""
    return [
        RabbitQueue(
            retry_routing_key(level),
            durable=True,
            routing_key=retry_routing_key(level),
            arguments={
                "x-message-ttl": int(delay * 1000),
                "x-dead-letter-exchange": PAYMENTS_EXCHANGE.name,
                "x-dead-letter-routing-key": PAYMENT_NEW_ROUTING_KEY,
            },
        )
        for level, delay in enumerate(delays, start=1)
    ]


async def declare_topology(broker: RabbitBroker, retry_delays: Sequence[float]) -> None:
    """
    Объявляет обменники, очереди и привязки
    """
    payments = await broker.declare_exchange(PAYMENTS_EXCHANGE)
    dlx = await broker.declare_exchange(PAYMENTS_DLX_EXCHANGE)

    payments_new = await broker.declare_queue(PAYMENTS_NEW)
    await payments_new.bind(payments, routing_key=PAYMENTS_NEW.routing())

    payments_dlq = await broker.declare_queue(PAYMENTS_DLQ)
    await payments_dlq.bind(dlx, routing_key=PAYMENTS_DLQ.routing())

    retry_exchange = await broker.declare_exchange(PAYMENTS_RETRY_EXCHANGE)
    for queue in build_retry_queues(retry_delays):
        retry_queue = await broker.declare_queue(queue)
        await retry_queue.bind(retry_exchange, routing_key=queue.routing())
