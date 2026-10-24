from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database.connection import get_db
from ..database.models import User
from ..services.payment import pay


router = APIRouter(
    prefix="/api/payments",
    tags=["Payments"],
)


class AppointmentPayment(BaseModel):
    appointment_id: int


@router.post("/appointment")
def appointment_payment(
    data: AppointmentPayment,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(
            status_code=403,
            detail="Only patients can pay for appointments",
        )

    patient = user.patient

    if patient is None:
        raise HTTPException(
            status_code=400,
            detail="Patient profile not found",
        )

    try:
        return pay(
            db=db,
            patient_id=patient.id,
            appointment_id=data.appointment_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )
