import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from ..database.models import MedicineOrder, Payment


def pay_order(db: Session, patient_id: int, order_id: int):
    order = (
        db.query(MedicineOrder)
        .filter(
            MedicineOrder.id == order_id,
            MedicineOrder.patient_id == patient_id,
        )
        .with_for_update()
        .first()
    )

    if not order:
        raise ValueError("Order not found")

    if order.status != "pending_payment":
        raise ValueError("Order is not awaiting payment")

    amount = Decimal(str(order.grand_total))

    transaction_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"

    payment = Payment(
        patient_id=patient_id,
        order_id=order.id,
        amount=amount,
        gateway="mock",
        transaction_id=transaction_id,
        status="paid",
        paid_at=datetime.now(timezone.utc),
    )

    order.status = "confirmed"

    db.add(payment)
    db.commit()

    db.refresh(payment)
    db.refresh(order)

    return {
        "success": True,
        "payment_id": payment.id,
        "transaction_id": transaction_id,
        "order_id": order.id,
        "amount": float(amount),
        "payment_status": payment.status,
        "order_status": order.status,
    }
