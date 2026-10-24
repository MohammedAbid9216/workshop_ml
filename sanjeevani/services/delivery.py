from datetime import datetime, timezone
from sqlalchemy.orm import Session

from ..database.models import (
    MedicineOrder,
    DeliveryPartner,
    DeliveryAssignment,
    DeliveryTrackingEvent,
)

ALLOWED_TRANSITIONS = {
    "assigned": {"picked_up", "failed"},
    "picked_up": {"out_for_delivery", "failed"},
    "out_for_delivery": {"delivered", "failed"},
    "delivered": set(),
    "failed": set(),
}

ORDER_STATUS = {
    "assigned": "assigned",
    "picked_up": "packed",
    "out_for_delivery": "out_for_delivery",
    "delivered": "delivered",
    "failed": "delivery_failed",
}


def assign_delivery(db: Session, order_id: int, delivery_partner_id: int):
    order = db.get(MedicineOrder, order_id)

    if not order:
        raise ValueError("Order not found")

    if order.status not in {"confirmed", "packed", "assigned"}:
        raise ValueError("Order is not ready for delivery")

    partner = db.get(DeliveryPartner, delivery_partner_id)

    if not partner or not partner.available:
        raise ValueError("Delivery partner not available")

    existing = (
        db.query(DeliveryAssignment)
        .filter(DeliveryAssignment.order_id == order_id)
        .first()
    )

    if existing:
        raise ValueError("Delivery is already assigned")

    assignment = DeliveryAssignment(
        order_id=order_id,
        delivery_partner_id=delivery_partner_id,
        status="assigned",
        assigned_at=datetime.now(timezone.utc),
    )

    order.status = "assigned"
    partner.available = False

    db.add(assignment)
    db.flush()

    db.add(
        DeliveryTrackingEvent(
            assignment_id=assignment.id,
            status="assigned",
            note="Delivery partner assigned",
        )
    )

    db.commit()
    db.refresh(assignment)

    return {
        "success": True,
        "assignment_id": assignment.id,
        "order_id": order.id,
        "delivery_partner_id": partner.id,
        "status": assignment.status,
    }


def update_delivery_status(
    db: Session,
    assignment_id: int,
    status: str,
    user_id: int,
    latitude=None,
    longitude=None,
    note=None,
):
    assignment = db.get(DeliveryAssignment, assignment_id)

    if not assignment:
        raise ValueError("Delivery assignment not found")

    partner = db.get(
        DeliveryPartner,
        assignment.delivery_partner_id,
    )

    if not partner or partner.user_id != user_id:
        raise ValueError("You are not assigned to this delivery")

    status = status.strip().lower()

    if status not in ALLOWED_TRANSITIONS:
        raise ValueError("Invalid delivery status")

    if status not in ALLOWED_TRANSITIONS.get(assignment.status, set()):
        raise ValueError(
            f"Cannot move delivery from "
            f"{assignment.status} to {status}"
        )

    now = datetime.now(timezone.utc)

    assignment.status = status

    if status == "picked_up":
        assignment.picked_up_at = now

    elif status == "delivered":
        assignment.delivered_at = now
        partner.available = True

    order = db.get(MedicineOrder, assignment.order_id)

    if order:
        order.status = ORDER_STATUS[status]

    db.add(
        DeliveryTrackingEvent(
            assignment_id=assignment.id,
            status=status,
            latitude=latitude,
            longitude=longitude,
            note=note,
        )
    )

    db.commit()
    db.refresh(assignment)

    return {
        "success": True,
        "assignment_id": assignment.id,
        "order_id": assignment.order_id,
        "status": assignment.status,
        "order_status": order.status if order else None,
    }


def get_order_tracking(
    db: Session,
    patient_id: int,
    order_id: int,
):
    order = (
        db.query(MedicineOrder)
        .filter(
            MedicineOrder.id == order_id,
            MedicineOrder.patient_id == patient_id,
        )
        .first()
    )

    if not order:
        raise ValueError("Order not found")

    assignment = (
        db.query(DeliveryAssignment)
        .filter(DeliveryAssignment.order_id == order_id)
        .first()
    )

    events = []
    partner = None

    if assignment:
        partner = db.get(
            DeliveryPartner,
            assignment.delivery_partner_id,
        )

        rows = (
            db.query(DeliveryTrackingEvent)
            .filter(
                DeliveryTrackingEvent.assignment_id
                == assignment.id
            )
            .order_by(DeliveryTrackingEvent.created_at.asc())
            .all()
        )

        events = [
            {
                "status": row.status,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "note": row.note,
                "created_at": row.created_at,
            }
            for row in rows
        ]

    return {
        "success": True,
        "order_id": order.id,
        "order_status": order.status,
        "assignment": (
            {
                "assignment_id": assignment.id,
                "status": assignment.status,
                "delivery_partner": partner.name if partner else None,
                "phone": partner.phone if partner else None,
                "vehicle_no": partner.vehicle_no if partner else None,
            }
            if assignment
            else None
        ),
        "tracking": events,
    }
