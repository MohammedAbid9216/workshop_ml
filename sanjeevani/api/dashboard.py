from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..auth import current_user
from ..database.connection import get_db
from ..database.models import User, Patient, Doctor, Appointment, MedicineOrder, Payment
router=APIRouter(prefix="/api/dashboard",tags=["Dashboards"])
@router.get("/summary")
def summary(user:User=Depends(current_user),db:Session=Depends(get_db)):
    role=user.role.name
    if role=="super_admin":
        return {"role":role,"cards":{"patients":db.query(func.count(Patient.id)).scalar(),"doctors":db.query(func.count(Doctor.id)).scalar(),"appointments":db.query(func.count(Appointment.id)).scalar(),"orders":db.query(func.count(MedicineOrder.id)).scalar(),"payments":db.query(func.count(Payment.id)).scalar()}}
    if role=="doctor":
        d=user.doctor
        return {"role":role,"cards":{"today_appointments":db.query(func.count(Appointment.id)).filter(Appointment.doctor_id==d.id).scalar(),"total_appointments":db.query(func.count(Appointment.id)).filter(Appointment.doctor_id==d.id).scalar()}}
    return {"role":role,"cards":{"appointments":db.query(func.count(Appointment.id)).scalar(),"orders":db.query(func.count(MedicineOrder.id)).scalar()}}
