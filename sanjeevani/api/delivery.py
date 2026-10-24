from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database.connection import get_db
from ..database.models import User, DeliveryPartner
from ..services.delivery import (
    assign_delivery,
    update_delivery_status,
    get_order_tracking,
)

router = APIRouter(
    prefix="/api/delivery",
    tags=["Delivery"],
)


class AssignDelivery(BaseModel):
    order_id: int
    delivery_partner_id: int


class DeliveryStatusUpdate(BaseModel):
    assignment_id: int
    status: str
    latitude: Optional[float] = Field(
        default=None,
        ge=-90,
        le=90,
    )
    longitude: Optional[float] = Field(
        default=None,
        ge=-180,
        le=180,
    )
    note: Optional[str] = None


def can_manage_delivery(user: User):
    return user.role.name in {
        "super_admin",
        "reception_staff",
        "pharmacy_staff",
    }


@router.get("/partners")
def delivery_partners(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_delivery(user):
        raise HTTPException(403, "Permission denied")

    rows = (
        db.query(DeliveryPartner)
        .filter(DeliveryPartner.available == True)
        .all()
    )

    return {
        "success": True,
        "partners": [
            {
                "id": row.id,
                "name": row.name,
                "phone": row.phone,
                "vehicle_no": row.vehicle_no,
                "available": row.available,
            }
            for row in rows
        ],
    }


@router.post("/assign")
def assign(
    data: AssignDelivery,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not can_manage_delivery(user):
        raise HTTPException(403, "Permission denied")

    try:
        return assign_delivery(
            db,
            data.order_id,
            data.delivery_partner_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.post("/status")
def status_update(
    data: DeliveryStatusUpdate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "delivery_staff":
        raise HTTPException(
            403,
            "Only delivery partners can update delivery status",
        )

    try:
        return update_delivery_status(
            db=db,
            assignment_id=data.assignment_id,
            status=data.status,
            user_id=user.id,
            latitude=data.latitude,
            longitude=data.longitude,
            note=data.note,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/track/{order_id}")
def track_order(
    order_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient" or not user.patient:
        raise HTTPException(
            403,
            "Only patients can track their orders",
        )

    try:
        return get_order_tracking(
            db,
            user.patient.id,
            order_id,
        )
    except ValueError as exc:
        raise HTTPException(404, str(exc))
