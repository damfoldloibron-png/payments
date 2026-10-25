import uuid

from pydantic import BaseModel

PAYMENT_NEW_EVENT = "payment.new"
PAYMENT_NEW_ROUTING_KEY = "payments.new"


class PaymentNewMessage(BaseModel):
    payment_id: uuid.UUID
    idempotency_key: str
