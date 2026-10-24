import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from ..database.models import Appointment, Payment


class MockPaymentGateway:
    def charge(self, amount, patient_id, purpose):
        return {
            "success": True,
            "transaction_id": f"MOCK-{uuid.uuid4().hex[:12].upper()}",
            "amount": str(amount),
            "purpose": purpose,
        }


def pay(db: Session, patient_id: int, appointment_id: int):
    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == appointment_id,
            Appointment.patient_id == patient_id,
        )
        .with_for_update()
        .first()
    )

    if appointment is None:
        raise ValueError("Appointment not found")

    if appointment.status != "pending_payment":
        raise ValueError("Appointment is not awaiting payment")

    if appointment.payment_status == "paid":
        raise ValueError("Appointment is already paid")

    amount = Decimal(str(appointment.consultation_fee))

    result = MockPaymentGateway().charge(
        amount,
        patient_id,
        "appointment",
    )

    if not result["success"]:
        from sqlalchemy import text as sql_text

        appointment.payment_status = "failed"
        appointment.status = "cancelled"

        db.execute(
            sql_text("""
                UPDATE doctor_slots
                SET status = 'available'
                WHERE doctor_id = :doctor_id
                  AND slot_date = :slot_date
                  AND slot_time = :slot_time
                  AND status = 'booked'
            """),
            {
                "doctor_id": appointment.doctor_id,
                "slot_date": appointment.appointment_date,
                "slot_time": appointment.appointment_time,
            },
        )

        db.commit()
        raise ValueError("Payment failed; appointment cancelled and slot released")

    payment = Payment(
        patient_id=patient_id,
        appointment_id=appointment.id,
        amount=amount,
        gateway="mock",
        transaction_id=result["transaction_id"],
        status="paid",
        paid_at=datetime.now(timezone.utc),
    )

    appointment.payment_status = "paid"
    appointment.status = "confirmed"

    db.add(payment)
    db.commit()
    db.refresh(payment)
    db.refresh(appointment)

    return {
        "success": True,
        "payment_id": payment.id,
        "transaction_id": payment.transaction_id,
        "appointment_id": appointment.id,
        "amount": float(payment.amount),
        "payment_status": appointment.payment_status,
        "appointment_status": appointment.status,
    }
