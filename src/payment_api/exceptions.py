import uuid


class PaymentNotFound(Exception):
    def __init__(self, payment_id: uuid.UUID) -> None:
        super().__init__(f"Payment {payment_id} not found")
        self.payment_id = payment_id
