from decimal import Decimal
from sqlalchemy.orm import Session

from ..database.models import (
    Medicine,
    MedicineOrder,
    MedicineOrderItem,
    PatientAddress,
    Prescription,
    PrescriptionItem,
)


def calculate_delivery_fee(distance_km: Decimal) -> Decimal:
    distance = float(distance_km)

    if distance <= 3:
        return Decimal("30.00")
    if distance <= 7:
        return Decimal("50.00")
    if distance <= 12:
        return Decimal("80.00")
    if distance <= 20:
        return Decimal("120.00")

    return Decimal("180.00")


def create_order(
    db: Session,
    patient_id: int,
    prescription_id: int,
    address_id: int,
    distance_km: Decimal,
):
    prescription = (
        db.query(Prescription)
        .filter(
            Prescription.id == prescription_id,
            Prescription.patient_id == patient_id,
        )
        .first()
    )

    if not prescription:
        raise ValueError("Prescription not found")

    if prescription.order_id:
        raise ValueError("Prescription already has an order")

    address = (
        db.query(PatientAddress)
        .filter(
            PatientAddress.id == address_id,
            PatientAddress.patient_id == patient_id,
        )
        .first()
    )

    if not address:
        raise ValueError("Delivery address not found")

    items = (
        db.query(PrescriptionItem)
        .filter(PrescriptionItem.prescription_id == prescription_id)
        .all()
    )

    if not items:
        raise ValueError("Prescription has no medicines")

    medicine_total = Decimal("0.00")

    order = MedicineOrder(
        patient_id=patient_id,
        prescription_id=prescription_id,
        delivery_fee=Decimal("0.00"),
        medicine_total=Decimal("0.00"),
        grand_total=Decimal("0.00"),
        status="pending_payment",
        address=(
            f"{address.address_line}, {address.city}, "
            f"{address.state} - {address.postal_code}"
        ),
        distance_km=distance_km,
    )

    db.add(order)
    db.flush()

    for prescription_item in items:
        medicine = db.get(Medicine, prescription_item.medicine_id)

        if not medicine or not medicine.active:
            raise ValueError(
                f"Medicine {prescription_item.medicine_id} unavailable"
            )

        if medicine.stock_qty < prescription_item.quantity:
            raise ValueError(
                f"Insufficient stock for {medicine.name}"
            )

        unit_price = Decimal(str(medicine.unit_price))
        line_total = unit_price * prescription_item.quantity

        medicine_total += line_total

        medicine.stock_qty -= prescription_item.quantity

        db.add(
            MedicineOrderItem(
                order_id=order.id,
                medicine_id=medicine.id,
                quantity=prescription_item.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )

    delivery_fee = calculate_delivery_fee(distance_km)
    grand_total = medicine_total + delivery_fee

    order.medicine_total = medicine_total
    order.delivery_fee = delivery_fee
    order.grand_total = grand_total

    prescription.order_id = order.id

    db.commit()
    db.refresh(order)

    return order
