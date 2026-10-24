from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database.connection import get_db
from ..database.models import (
    User,
    Appointment,
    Prescription,
    PrescriptionItem,
    Medicine,
)


router = APIRouter(
    prefix="/api/prescriptions",
    tags=["Prescriptions"],
)


class PrescriptionItemInput(BaseModel):
    medicine_id: int
    dosage: str = Field(min_length=1, max_length=120)
    frequency: str = Field(min_length=1, max_length=120)
    duration_days: int = Field(gt=0, le=365)
    quantity: int = Field(gt=0, le=1000)
    instructions: str | None = None


class PrescriptionCreate(BaseModel):
    appointment_id: int
    notes: str | None = None
    items: list[PrescriptionItemInput] = Field(min_length=1)


@router.post("")
def create_prescription(
    data: PrescriptionCreate,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "doctor":
        raise HTTPException(
            status_code=403,
            detail="Only doctors can create prescriptions",
        )

    doctor = user.doctor

    if doctor is None:
        raise HTTPException(
            status_code=400,
            detail="Doctor profile not found",
        )

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.id == data.appointment_id,
            Appointment.doctor_id == doctor.id,
        )
        .first()
    )

    if appointment is None:
        raise HTTPException(
            status_code=404,
            detail="Appointment not found for this doctor",
        )

    if appointment.status != "confirmed":
        raise HTTPException(
            status_code=400,
            detail="Prescription can only be created for a confirmed appointment",
        )

    existing = (
        db.query(Prescription)
        .filter(Prescription.appointment_id == appointment.id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Prescription already exists for this appointment",
        )

    prescription = Prescription(
        patient_id=appointment.patient_id,
        doctor_id=doctor.id,
        appointment_id=appointment.id,
        notes=data.notes,
    )

    db.add(prescription)
    db.flush()

    response_items = []

    for item in data.items:
        medicine = db.get(Medicine, item.medicine_id)

        if medicine is None or not medicine.active:
            raise HTTPException(
                status_code=404,
                detail=f"Medicine {item.medicine_id} not found",
            )

        prescription_item = PrescriptionItem(
            prescription_id=prescription.id,
            medicine_id=medicine.id,
            dosage=item.dosage,
            frequency=item.frequency,
            duration_days=item.duration_days,
            quantity=item.quantity,
            instructions=item.instructions,
        )

        db.add(prescription_item)

        response_items.append({
            "medicine_id": medicine.id,
            "medicine": medicine.name,
            "dosage": item.dosage,
            "frequency": item.frequency,
            "duration_days": item.duration_days,
            "quantity": item.quantity,
            "instructions": item.instructions,
        })

    db.commit()
    db.refresh(prescription)

    return {
        "success": True,
        "prescription_id": prescription.id,
        "appointment_id": appointment.id,
        "patient_id": appointment.patient_id,
        "doctor_id": doctor.id,
        "notes": prescription.notes,
        "items": response_items,
    }


@router.get("/mine")
def my_prescriptions(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if user.role.name != "patient":
        raise HTTPException(
            status_code=403,
            detail="Only patients can view their prescriptions",
        )

    patient = user.patient

    if patient is None:
        raise HTTPException(
            status_code=400,
            detail="Patient profile not found",
        )

    prescriptions = (
        db.query(Prescription)
        .filter(Prescription.patient_id == patient.id)
        .order_by(Prescription.created_at.desc())
        .all()
    )

    result = []

    for prescription in prescriptions:
        items = (
            db.query(PrescriptionItem, Medicine)
            .join(
                Medicine,
                Medicine.id == PrescriptionItem.medicine_id,
            )
            .filter(
                PrescriptionItem.prescription_id == prescription.id
            )
            .all()
        )

        result.append({
            "id": prescription.id,
            "doctor_id": prescription.doctor_id,
            "appointment_id": prescription.appointment_id,
            "notes": prescription.notes,
            "created_at": prescription.created_at.isoformat(),
            "items": [
                {
                    "medicine_id": medicine.id,
                    "medicine": medicine.name,
                    "dosage": item.dosage,
                    "frequency": item.frequency,
                    "duration_days": item.duration_days,
                    "quantity": item.quantity,
                    "instructions": item.instructions,
                }
                for item, medicine in items
            ],
        })

    return result


@router.get("/{prescription_id}")
def prescription_detail(
    prescription_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    prescription = db.get(Prescription, prescription_id)

    if prescription is None:
        raise HTTPException(
            status_code=404,
            detail="Prescription not found",
        )

    if user.role.name == "patient":
        if user.patient is None or prescription.patient_id != user.patient.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot access this prescription",
            )

    elif user.role.name == "doctor":
        if user.doctor is None or prescription.doctor_id != user.doctor.id:
            raise HTTPException(
                status_code=403,
                detail="You cannot access this prescription",
            )

    else:
        raise HTTPException(
            status_code=403,
            detail="Permission denied",
        )

    items = (
        db.query(PrescriptionItem, Medicine)
        .join(
            Medicine,
            Medicine.id == PrescriptionItem.medicine_id,
        )
        .filter(PrescriptionItem.prescription_id == prescription.id)
        .all()
    )

    return {
        "id": prescription.id,
        "patient_id": prescription.patient_id,
        "doctor_id": prescription.doctor_id,
        "appointment_id": prescription.appointment_id,
        "notes": prescription.notes,
        "created_at": prescription.created_at.isoformat(),
        "items": [
            {
                "medicine_id": medicine.id,
                "medicine": medicine.name,
                "dosage": item.dosage,
                "frequency": item.frequency,
                "duration_days": item.duration_days,
                "quantity": item.quantity,
                "instructions": item.instructions,
            }
            for item, medicine in items
        ],
    }
