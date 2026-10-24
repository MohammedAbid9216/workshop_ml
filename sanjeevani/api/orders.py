from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database.connection import get_db
from ..database.models import (
    User,
    PatientAddress,
    MedicineOrder,
)
from ..services.order import create_order


router = APIRouter(
    prefix="/api/orders",
    tags=["Orders"],
)


class AddressCreate(BaseModel):
    label: str = Field(min_length=1, max_length=50)
    address_line: str = Field(min_length=3, max_length=255)
    city: str = Field(min_length=2, max_length=100)
    state: str = Field(min_length=2, max_length=100)
    postal_code: str = Field(min_length=4, max_length=20)
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False


class OrderCreate(BaseModel):
    prescription_id: int
    address_id: int
    distance_km: Decimal = Field(ge=0, le=100)


@router.post("/addresses")
def add_address(
    data: AddressCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(403, "Only patients can add addresses")

    patient = user.patient

    if not patient:
        raise HTTPException(400, "Patient profile not found")

    if data.is_default:
        db.query(PatientAddress).filter(
            PatientAddress.patient_id == patient.id
        ).update({"is_default": False})

    address = PatientAddress(
        patient_id=patient.id,
        label=data.label,
        address_line=data.address_line,
        city=data.city,
        state=data.state,
        postal_code=data.postal_code,
        latitude=data.latitude,
        longitude=data.longitude,
        is_default=data.is_default,
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    return {
        "success": True,
        "address_id": address.id,
    }


@router.get("/addresses")
def addresses(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(403, "Only patients can view addresses")

    patient = user.patient

    return [
        {
            "id": a.id,
            "label": a.label,
            "address": a.address_line,
            "city": a.city,
            "state": a.state,
            "postal_code": a.postal_code,
            "is_default": a.is_default,
        }
        for a in db.query(PatientAddress)
        .filter(PatientAddress.patient_id == patient.id)
        .all()
    ]


@router.post("")
def create_medicine_order(
    data: OrderCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(403, "Only patients can create orders")

    patient = user.patient

    if not patient:
        raise HTTPException(400, "Patient profile not found")

    try:
        order = create_order(
            db=db,
            patient_id=patient.id,
            prescription_id=data.prescription_id,
            address_id=data.address_id,
            distance_km=data.distance_km,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {
        "success": True,
        "order_id": order.id,
        "prescription_id": order.prescription_id,
        "medicine_total": float(order.medicine_total),
        "delivery_fee": float(order.delivery_fee),
        "grand_total": float(order.grand_total),
        "status": order.status,
        "next_step": "payment_required",
    }


@router.get("/mine")
def my_orders(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(403, "Only patients can view orders")

    patient = user.patient

    return [
        {
            "id": o.id,
            "prescription_id": o.prescription_id,
            "medicine_total": float(o.medicine_total),
            "delivery_fee": float(o.delivery_fee),
            "grand_total": float(o.grand_total),
            "status": o.status,
            "address": o.address,
            "distance_km": float(o.distance_km or 0),
            "created_at": o.created_at,
        }
        for o in db.query(MedicineOrder)
        .filter(MedicineOrder.patient_id == patient.id)
        .order_by(MedicineOrder.id.desc())
        .all()
    ]
