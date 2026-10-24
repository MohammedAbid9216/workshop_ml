
from datetime import date, time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from mysql.connector import IntegrityError, Error

from booking.database import get_db_connection

router = APIRouter(prefix="/api/booking", tags=["Appointment Booking"])


class BookingRequest(BaseModel):
    patient_id: int = Field(gt=0)
    doctor_id: int = Field(gt=0)
    appointment_date: date
    appointment_time: time


@router.get("/doctors")
def list_doctors():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id AS doctor_id, name AS doctor_name,
                   specialty, experience_years
            FROM doctors
            WHERE is_active = 1
            ORDER BY name
        """)
        return {"doctors": cursor.fetchall()}
    except Error:
        raise HTTPException(status_code=500, detail="Could not load doctors.")
    finally:
        cursor.close()
        conn.close()

@router.get("/slots")
def list_slots(doctor_id: int, slot_date: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT s.id AS slot_id, TIME_FORMAT(s.slot_time, '%H:%i') AS slot_time
            FROM doctor_slots s
            JOIN doctors d ON d.id = s.doctor_id
            WHERE s.doctor_id = %s
              AND s.slot_date = %s
              AND s.is_booked = 0
              AND s.slot_date >= CURDATE()
              AND d.is_active = 1
            ORDER BY s.slot_time
        """, (doctor_id, slot_date))
        return {"slots": cursor.fetchall()}
    except Error:
        raise HTTPException(status_code=500, detail="Could not load available slots.")
    finally:
        cursor.close()
        conn.close()

@router.post("/book")
def book_appointment(payload: BookingRequest):
    if payload.appointment_date < date.today():
        raise HTTPException(400, "Past appointments cannot be booked.")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        conn.start_transaction()

        # Verify that the patient belongs to an active patient account.
        cursor.execute("""
            SELECT p.id
            FROM patients p
            JOIN users u ON u.id = p.user_id
            JOIN roles r ON r.id = u.role_id
            WHERE p.id = %s
              AND u.active = 1
              AND r.name = 'patient'
            FOR UPDATE
        """, (payload.patient_id,))
        patient = cursor.fetchone()

        if not patient:
            conn.rollback()
            raise HTTPException(404, "Patient account not found.")

        # Lock the exact slot so concurrent requests cannot book it twice.
        cursor.execute("""
            SELECT s.id, s.doctor_id, s.slot_date, s.slot_time,
                   d.consultation_fee
            FROM doctor_slots s
            JOIN doctors d ON d.id = s.doctor_id
            JOIN users du ON du.id = d.user_id
            WHERE s.doctor_id = %s
              AND s.slot_date = %s
              AND s.slot_time = %s
              AND s.status = 'available'
              AND s.slot_date >= CURDATE()
              AND d.available = 1
              AND du.active = 1
            FOR UPDATE
        """, (
            payload.doctor_id,
            payload.appointment_date,
            payload.appointment_time,
        ))
        slot = cursor.fetchone()

        if not slot:
            conn.rollback()
            raise HTTPException(
                409, "That slot is unavailable. Please choose another slot."
            )

        cursor.execute("""
            INSERT INTO appointments (
                patient_id, doctor_id, appointment_date,
                appointment_time, consultation_fee,
                status, payment_status, created_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            payload.patient_id,
            slot["doctor_id"],
            slot["slot_date"],
            slot["slot_time"],
            slot["consultation_fee"],
            "pending_payment",
            "pending",
        ))

        appointment_id = cursor.lastrowid

        cursor.execute("""
            UPDATE doctor_slots
            SET status = 'booked'
            WHERE id = %s AND status = 'available'
        """, (slot["id"],))

        if cursor.rowcount != 1:
            conn.rollback()
            raise HTTPException(
                409, "Slot was just taken. Please select another time."
            )

        conn.commit()

        return {
            "success": True,
            "appointment_id": appointment_id,
            "patient_id": payload.patient_id,
            "doctor_id": slot["doctor_id"],
            "date": slot["slot_date"].isoformat(),
            "time": str(slot["slot_time"]),
            "fee": str(slot["consultation_fee"]),
            "status": "pending_payment",
            "payment_status": "pending",
            "message": "Appointment created; payment is still pending.",
        }

    except HTTPException:
        raise
    except IntegrityError:
        conn.rollback()
        raise HTTPException(
            409, "This appointment conflicts with an existing booking."
        )
    except Error:
        conn.rollback()
        raise HTTPException(500, "Booking failed. Please try again.")
    finally:
        cursor.close()
        conn.close()
