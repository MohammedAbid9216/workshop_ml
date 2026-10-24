from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database.connection import get_db
from ..database.models import User
from ..services.order_payment import pay_order


router = APIRouter(
    prefix="/api/payments",
    tags=["Order Payments"],
)


class OrderPayment(BaseModel):
    order_id: int


@router.post("/order")
def order_payment(
    data: OrderPayment,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(403, "Only patients can pay for orders")

    if not user.patient:
        raise HTTPException(400, "Patient profile not found")

    try:
        return pay_order(
            db=db,
            patient_id=user.patient.id,
            order_id=data.order_id,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
