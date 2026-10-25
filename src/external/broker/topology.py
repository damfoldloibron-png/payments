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


async def declare_topology(broker: RabbitBroker) -> None:
    """
    Объявляет обменники, очереди и привязки
    """
    payments = await broker.declare_exchange(PAYMENTS_EXCHANGE)
    dlx = await broker.declare_exchange(PAYMENTS_DLX_EXCHANGE)

    payments_new = await broker.declare_queue(PAYMENTS_NEW)
    await payments_new.bind(payments, routing_key=PAYMENTS_NEW.routing())

    payments_dlq = await broker.declare_queue(PAYMENTS_DLQ)
    await payments_dlq.bind(dlx, routing_key=PAYMENTS_DLQ.routing())
