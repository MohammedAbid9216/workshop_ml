from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database.connection import get_db
from ..database.models import User


router = APIRouter(
    prefix="/api/appointments",
    tags=["Appointments"],
)


class Book(BaseModel):
    doctor_id: int
    slot_id: int
    appointment_date: date


@router.post("")
def book(
    data: Book,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    if not user.role or user.role.name != "patient":
        raise HTTPException(
            status_code=403,
            detail="Only patients can book appointments.",
        )

    if not user.email:
        raise HTTPException(
            status_code=400,
            detail="Your account does not have an email address.",
        )

    try:
        # Resolve the patient using the authenticated account email.
        # Never accept patient_id from the browser.
        patients = db.execute(
            text("""
                SELECT id
                FROM patients
                WHERE LOWER(TRIM(email)) = LOWER(TRIM(:email))
            """),
            {"email": user.email},
        ).mappings().all()

        if len(patients) != 1:
            raise HTTPException(
                status_code=400,
                detail=(
                    "A unique patient profile matching your account email "
                    "was not found. Please contact clinic support."
                ),
            )

        patient_id = patients[0]["id"]

        # Lock and validate the exact slot in the same transaction.
        slot = db.execute(
            text("""
                SELECT
                    s.id AS slot_id,
                    s.doctor_id,
                    s.slot_date,
                    TIME_FORMAT(s.slot_time, '%H:%i') AS slot_time,
                    d.name AS doctor_name
                FROM doctor_slots s
                JOIN doctors d ON d.id = s.doctor_id
                WHERE s.id = :slot_id
                  AND s.doctor_id = :doctor_id
                  AND s.slot_date = :slot_date
                  AND s.is_booked = 0
                  AND d.is_active = 1
                  AND (
                      s.slot_date > CURDATE()
                      OR (
                          s.slot_date = CURDATE()
                          AND s.slot_time > CURTIME()
                      )
                  )
                FOR UPDATE
            """),
            {
                "slot_id": data.slot_id,
                "doctor_id": data.doctor_id,
                "slot_date": data.appointment_date,
            },
        ).mappings().first()

        if slot is None:
            raise HTTPException(
                status_code=409,
                detail="This slot is unavailable. Please choose another time.",
            )

        result = db.execute(
            text("""
                INSERT INTO appointments
                    (patient_id, doctor_id, slot_id, status)
                VALUES
                    (:patient_id, :doctor_id, :slot_id, 'booked')
            """),
            {
                "patient_id": patient_id,
                "doctor_id": data.doctor_id,
                "slot_id": data.slot_id,
            },
        )

        appointment_id = result.lastrowid

        updated = db.execute(
            text("""
                UPDATE doctor_slots
                SET is_booked = 1
                WHERE id = :slot_id
                  AND is_booked = 0
            """),
            {"slot_id": data.slot_id},
        )

        if updated.rowcount != 1:
            raise HTTPException(
                status_code=409,
                detail="This slot was just taken. Please choose another.",
            )

        db.commit()

        return {
            "success": True,
            "appointment_id": appointment_id,
            "doctor": slot["doctor_name"],
            "appointment_date": str(slot["slot_date"]),
            "appointment_time": str(slot["slot_time"]),
            "consultation_fee": None,
            "payment_status": "not_configured",
            "status": "booked",
        }

    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This slot conflicts with an existing booking.",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Appointment booking failed. Please try again.",
        )
