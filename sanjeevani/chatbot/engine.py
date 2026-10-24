from sqlalchemy.orm import Session

from .buttons import button, main_menu, back_button
from .intents import detect_intent
from .responses import (
    welcome,
    out_of_scope,
    help_response,
    appointment_start,
    prescription_start,
    medicine_start,
    tracking_start,
    clinic_services,
)
from .scope import is_clinic_scope
from .state import get_state, update_state, reset_state


def _appointment_flow(
    text: str,
    patient_id: int,
    db: Session,
):
    from datetime import date, timedelta
    from sqlalchemy import text as sql_text

    state = get_state(patient_id)

    # STEP 1: Load specialties from MySQL.
    if text == "appointment" or (
        state.step == "start" and not text.startswith("specialty:")
    ):
        rows = db.execute(
            sql_text("""
                SELECT id, name
                FROM specialties
                ORDER BY name
            """)
        ).mappings().all()

        if not rows:
            return {
                "message": "Abhi koi specialty available nahi hai.",
                "buttons": main_menu(),
            }

        update_state(
            patient_id,
            intent="appointment",
            step="specialty",
        )

        return {
            "message": "Specialty select karein.",
            "buttons": [
                button(f"🩺 {row['name']}", f"specialty:{row['id']}")
                for row in rows
            ] + back_button(),
        }

    # STEP 2: Load doctors for selected specialty.
    if text.startswith("specialty:"):
        try:
            specialty_id = int(text.split(":", 1)[1])
        except ValueError:
            return {"message": "Invalid specialty. Dobara select karein.",
                    "buttons": back_button()}

        rows = db.execute(
            sql_text("""
                SELECT d.id, u.full_name AS doctor_name,
                       d.experience_years, d.consultation_fee
                FROM doctors d
                JOIN users u ON u.id = d.user_id
                JOIN doctor_specialties ds ON ds.doctor_id = d.id
                JOIN specialties s ON s.id = ds.specialty_id
                WHERE s.id = :sid AND d.available = 1
                ORDER BY u.full_name
            """),
            {"sid": specialty_id},
        ).mappings().all()

        if not rows:
            return {
                "message": "Is specialty mein abhi available doctor nahi hai.",
                "buttons": back_button(),
            }

        update_state(
            patient_id,
            step="doctor",
            specialty_id=specialty_id,
        )

        return {
            "message": "Available doctor select karein.",
            "buttons": [
                button(
                    f"{r['doctor_name'] if r['doctor_name'].lower().startswith('dr.') else 'Dr. ' + r['doctor_name']} • ₹{r['consultation_fee']}",
                    f"doctor:{r['id']}",
                )
                for r in rows
            ] + back_button(),
        }

    # STEP 3: Load real dates that have available slots.
    if text.startswith("doctor:"):
        try:
            doctor_id = int(text.split(":", 1)[1])
        except ValueError:
            return {"message": "Invalid doctor selection.",
                    "buttons": back_button()}

        specialty_id = state.data.get("specialty_id")
        valid_doctor = db.execute(
            sql_text("""
                SELECT d.id
                FROM doctors d
                JOIN doctor_specialties ds ON ds.doctor_id = d.id
                WHERE d.id = :did
                  AND d.available = 1
                  AND ds.specialty_id = :sid
            """),
            {"did": doctor_id, "sid": specialty_id},
        ).first()

        if not valid_doctor:
            return {
                "message": "Doctor selection valid nahi hai. Specialty dobara choose karein.",
                "buttons": back_button(),
            }

        today = date.today()
        rows = db.execute(
            sql_text("""
                SELECT DISTINCT slot_date
                FROM doctor_slots
                WHERE doctor_id = :did
                  AND status = 'available'
                  AND slot_date >= :today
                ORDER BY slot_date
                LIMIT 7
            """),
            {"did": doctor_id, "today": today},
        ).mappings().all()

        if not rows:
            return {
                "message": "Is doctor ke liye abhi koi available date nahi hai.",
                "buttons": back_button(),
            }

        update_state(patient_id, step="date", doctor_id=doctor_id)

        return {
            "message": "Appointment date select karein.",
            "buttons": [
                button(
                    f"📅 {r['slot_date'].strftime('%d %b %Y')}",
                    f"date:{r['slot_date'].isoformat()}",
                )
                for r in rows
            ] + back_button(),
        }

    # STEP 4: Load available slots for selected date.
    if text.startswith("date:"):
        selected_date = text.split(":", 1)[1]
        try:
            parsed_date = date.fromisoformat(selected_date)
        except ValueError:
            return {"message": "Invalid date. Dobara select karein.",
                    "buttons": back_button()}

        doctor_id = state.data.get("doctor_id")
        if not doctor_id or parsed_date < date.today():
            return {
                "message": "Date selection invalid ya expired hai.",
                "buttons": back_button(),
            }

        rows = db.execute(
            sql_text("""
                SELECT id, slot_time
                FROM doctor_slots
                WHERE doctor_id = :did
                  AND slot_date = :selected_date
                  AND status = 'available'
                ORDER BY slot_time
            """),
            {"did": doctor_id, "selected_date": parsed_date},
        ).mappings().all()

        if not rows:
            return {
                "message": "Is date par koi available slot nahi hai.",
                "buttons": back_button(),
            }

        update_state(patient_id, step="slot", appointment_date=selected_date)

        def display_time(value):
            if isinstance(value, timedelta):
                seconds = int(value.total_seconds())
                hour, minute = seconds // 3600, (seconds % 3600) // 60
            else:
                hour, minute = value.hour, value.minute
            suffix = "AM" if hour < 12 else "PM"
            return f"{hour % 12 or 12}:{minute:02d} {suffix}"

        return {
            "message": "Available slot select karein.",
            "buttons": [
                button(f"🕐 {display_time(r['slot_time'])}", f"slot:{r['id']}")
                for r in rows
            ] + back_button(),
        }

    # STEP 5: Revalidate selected slot before showing summary.
    if text.startswith("slot:"):
        try:
            slot_id = int(text.split(":", 1)[1])
        except ValueError:
            return {"message": "Invalid slot selection.",
                    "buttons": back_button()}

        doctor_id = state.data.get("doctor_id")
        selected_date = state.data.get("appointment_date")

        if not doctor_id or not selected_date:
            reset_state(patient_id)
            return welcome()

        slot = db.execute(
            sql_text("""
                SELECT ds.id, ds.slot_date, ds.slot_time,
                       d.consultation_fee, u.full_name AS doctor_name
                FROM doctor_slots ds
                JOIN doctors d ON d.id = ds.doctor_id
                JOIN users u ON u.id = d.user_id
                WHERE ds.id = :slot_id
                  AND ds.doctor_id = :did
                  AND ds.slot_date = :selected_date
                  AND ds.status = 'available'
                  AND d.available = 1
            """),
            {
                "slot_id": slot_id,
                "did": doctor_id,
                "selected_date": selected_date,
            },
        ).mappings().first()

        if not slot:
            return {
                "message": "Ye slot ab available nahi hai. Date dobara select karein.",
                "buttons": [
                    button("🔄 Choose Date", f"doctor:{doctor_id}"),
                    *back_button(),
                ],
            }

        def display_time(value):
            if isinstance(value, timedelta):
                seconds = int(value.total_seconds())
                hour, minute = seconds // 3600, (seconds % 3600) // 60
            else:
                hour, minute = value.hour, value.minute
            suffix = "AM" if hour < 12 else "PM"
            return f"{hour % 12 or 12}:{minute:02d} {suffix}"

        update_state(
            patient_id,
            step="confirmation",
            slot_id=slot_id,
            slot=display_time(slot["slot_time"]),
        )

        return {
            "message": (
                "Appointment summary (abhi booking create nahi hui):\n\n"
                f"👨‍⚕️ Doctor: {slot['doctor_name'] if slot['doctor_name'].lower().startswith('dr.') else 'Dr. ' + slot['doctor_name']}\n"
                f"📅 Date: {slot['slot_date']}\n"
                f"🕐 Time: {display_time(slot['slot_time'])}\n"
                f"💰 Consultation Fee: ₹{slot['consultation_fee']}\n\n"
                "Confirm karein to appointment reserve hogi; payment next step hai."
            ),
            "buttons": [
                button("✅ Confirm & Book", "appointment:pay"),
                button("🔄 Choose Another Date", f"doctor:{doctor_id}"),
                button("Cancel", "cancel"),
            ],
        }

    return {
        "message": "Appointment option select karein.",
        "buttons": back_button(),
    }


def _handle_action(
    text: str,
    patient_id: int,
    db: Session,
):
    if text == "back":
        reset_state(patient_id)
        return welcome()

    if text == "cancel":
        state = get_state(patient_id)
        appointment_id = state.data.get("appointment_id")
        message = "Workflow cancel kar diya gaya."

        if appointment_id:
            from sqlalchemy import text as sql_text
            from ..database.models import Appointment

            appointment = (
                db.query(Appointment)
                .filter(
                    Appointment.id == appointment_id,
                    Appointment.patient_id == patient_id,
                )
                .with_for_update()
                .first()
            )

            if (
                appointment
                and appointment.status == "pending_payment"
                and appointment.payment_status != "paid"
            ):
                db.execute(
                    sql_text("""
                        UPDATE doctor_slots
                        SET status = 'available'
                        WHERE doctor_id = :doctor_id
                          AND slot_date = :slot_date
                          AND slot_time = :slot_time
                          AND status = 'booked'
                    """),
                    {
                        "doctor_id": appointment.doctor_id,
                        "slot_date": appointment.appointment_date,
                        "slot_time": appointment.appointment_time,
                    },
                )
                appointment.status = "cancelled"
                appointment.payment_status = "cancelled"
                db.commit()
                message = (
                    f"Appointment #{appointment.id} cancel ho gayi; "
                    "slot release kar diya gaya."
                )
            else:
                db.rollback()
                message = (
                    "Appointment cancel nahi hui. Sirf pending-payment "
                    "appointment cancel ho sakti hai."
                )

        reset_state(patient_id)
        return {"message": message, "buttons": main_menu()}

    if text == "appointment":
        return _appointment_flow(text, patient_id, db)

    if text.startswith("specialty:") or text.startswith("doctor:"):
        return _appointment_flow(text, patient_id, db)

    if text.startswith("date:") or text.startswith("slot:"):
        return _appointment_flow(text, patient_id, db)

    if text == "appointment:pay":
        state = get_state(patient_id)
        slot_id = state.data.get("slot_id")
        doctor_id = state.data.get("doctor_id")
        selected_date = state.data.get("appointment_date")

        if not slot_id or not doctor_id or not selected_date:
            reset_state(patient_id)
            return {
                "message": "Appointment session expire ho gaya. Dobara start karein.",
                "buttons": main_menu(),
            }

        from datetime import date, time, timedelta
        from sqlalchemy import text as sql_text
        from ..database.models import Appointment

        slot = db.execute(
            sql_text("""
                SELECT slot_date, slot_time, status
                FROM doctor_slots
                WHERE id = :slot_id
                  AND doctor_id = :doctor_id
                  AND slot_date = :selected_date
                FOR UPDATE
            """),
            {
                "slot_id": slot_id,
                "doctor_id": doctor_id,
                "selected_date": selected_date,
            },
        ).mappings().first()

        if not slot or slot["status"] != "available":
            db.rollback()
            return {
                "message": "Ye slot ab available nahi hai. Please date dobara choose karein.",
                "buttons": [
                    button("Choose Another Date", f"doctor:{doctor_id}"),
                    *back_button(),
                ],
            }

        if isinstance(slot["slot_time"], timedelta):
            seconds = int(slot["slot_time"].total_seconds())
            slot_time = time(seconds // 3600, (seconds % 3600) // 60)
        else:
            slot_time = slot["slot_time"]

        appointment = (
            db.query(Appointment)
            .filter(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == slot["slot_date"],
                Appointment.appointment_time == slot_time,
                Appointment.status.in_(["pending", "pending_payment", "confirmed"]),
            )
            .first()
        )

        if appointment:
            db.rollback()
            return {
                "message": "Ye slot kisi appointment ke liye already reserved hai. Choose another slot.",
                "buttons": [
                    button("Choose Another Date", f"doctor:{doctor_id}"),
                    *back_button(),
                ],
            }

        doctor = db.execute(
            sql_text("""
                SELECT consultation_fee
                FROM doctors
                WHERE id = :doctor_id AND available = 1
            """),
            {"doctor_id": doctor_id},
        ).mappings().first()

        if not doctor:
            db.rollback()
            return {
                "message": "Doctor abhi available nahi hai.",
                "buttons": main_menu(),
            }

        # patient_id comes from the authenticated API's patient profile.
        if not patient_id:
            db.rollback()
            return {
                "message": "Patient profile verify nahi ho paayi. Please login again.",
                "buttons": main_menu(),
            }

        appointment = Appointment(
            patient_id=patient_id,
            doctor_id=doctor_id,
            appointment_date=slot["slot_date"],
            appointment_time=slot_time,
            consultation_fee=doctor["consultation_fee"],
            status="pending_payment",
            payment_status="pending",
        )
        db.add(appointment)
        db.flush()

        slot_update = db.execute(
            sql_text("""
                UPDATE doctor_slots
                SET status = 'booked'
                WHERE id = :slot_id
                  AND doctor_id = :doctor_id
                  AND status = 'available'
            """),
            {"slot_id": slot_id, "doctor_id": doctor_id},
        )

        if slot_update.rowcount != 1:
            db.rollback()
            return {
                "message": "Slot reserve nahi ho saka. Please doosra slot choose karein.",
                "buttons": [
                    button("Choose Another Date", f"doctor:{doctor_id}"),
                    *back_button(),
                ],
            }

        db.commit()
        db.refresh(appointment)

        update_state(
            patient_id,
            step="payment_pending",
            appointment_id=appointment.id,
        )

        return {
            "message": (
                f"Appointment #{appointment.id} create ho gayi hai, "
                "lekin abhi payment pending hai.\n"
                f"Consultation fee: ₹{appointment.consultation_fee}"
            ),
            "buttons": [
                button("💳 Pay Consultation Fee", f"payment:appointment:{appointment.id}"),
                button("Cancel", "cancel"),
            ],
        }

    if text.startswith("payment:appointment:"):
        try:
            appointment_id = int(text.rsplit(":", 1)[1])
        except ValueError:
            return {"message": "Invalid appointment ID.", "buttons": main_menu()}

        # The authenticated API supplies patient_id on every request.
        # The payment service must verify appointment ownership and status.
        from ..services.payment import pay

        try:
            result = pay(
                db=db,
                patient_id=patient_id,
                appointment_id=appointment_id,
            )
        except ValueError as exc:
            db.rollback()
            return {
                "message": f"Payment complete nahi hui: {exc}",
                "buttons": main_menu(),
            }

        reset_state(patient_id)
        return {
            "message": (
                f"✅ Payment successful!\n"
                f"Appointment ID: #{result['appointment_id']}\n"
                f"Amount paid: ₹{result['amount']}\n"
                "Appointment confirmed."
            ),
            "buttons": main_menu(),
        }

    if text == "prescription":
        update_state(
            patient_id,
            intent="prescription",
            step="selection",
        )
        return prescription_start()

    if text == "medicine_order":
        update_state(
            patient_id,
            intent="medicine_order",
            step="selection",
        )
        return medicine_start()

    if text == "order_tracking":
        update_state(
            patient_id,
            intent="order_tracking",
            step="selection",
        )
        return tracking_start()

    if text == "clinic":
        reset_state(patient_id)
        return clinic_services()

    if text == "help":
        return help_response()

    if text.startswith("prescription:"):
        return {
            "message": (
                "Prescription request received. "
                "Ab patient-specific prescription data DB se fetch hogi."
            ),
            "buttons": main_menu(),
        }

    if text.startswith("medicine:"):
        return {
            "message": (
                "Medicine order workflow start ho gaya. "
                "Prescription select karne ke baad address, "
                "delivery fee aur payment process hoga."
            ),
            "buttons": main_menu(),
        }

    if text.startswith("orders:"):
        return {
            "message": (
                "Aapke orders DB se fetch karke current delivery "
                "status yahan show kiya jayega."
            ),
            "buttons": main_menu(),
        }

    return None


def chatbot_response(
    *,
    text: str,
    patient_id: int,
    db: Session,
):
    text = text.strip()

    if not text:
        return welcome()

    state = get_state(patient_id)

    # Button/action messages must be handled before intent detection.
    action_response = _handle_action(
        text,
        patient_id,
        db,
    )

    if action_response:
        return action_response

    if not is_clinic_scope(
        text,
        active_workflow=state.step != "start",
    ):
        return out_of_scope()

    intent = detect_intent(text)

    if intent == "appointment":
        return _appointment_flow(
            text,
            patient_id,
            db,
        )

    if intent == "prescription":
        update_state(
            patient_id,
            intent="prescription",
            step="selection",
        )
        return prescription_start()

    if intent == "medicine_order":
        update_state(
            patient_id,
            intent="medicine_order",
            step="selection",
        )
        return medicine_start()

    if intent == "order_tracking":
        update_state(
            patient_id,
            intent="order_tracking",
            step="selection",
        )
        return tracking_start()

    if intent == "my_appointments":
        return {
            "message": "Aapki appointments DB se fetch ki jayengi.",
            "buttons": [
                button("Upcoming", "appointments:upcoming"),
                button("Past", "appointments:past"),
                *back_button(),
            ],
        }

    if intent == "clinic":
        return clinic_services()

    if intent == "help":
        return help_response()

    return {
        "message": (
            "Main aapki request ko clinic workflow se match nahi kar paaya. "
            "Appointment, prescription, medicine ya order ke baare mein poochhein."
        ),
        "buttons": main_menu(),
    }
