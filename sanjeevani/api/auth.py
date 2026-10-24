from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from ..database.connection import get_db
from ..database.models import User, Role
from ..auth import verify_password, create_token, hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class Login(BaseModel):
    email: str
    password: str


class Register(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=72)
    phone: str | None = Field(default=None, max_length=30)


@router.post("/register", status_code=201)
def register(data: Register, db: Session = Depends(get_db)):
    name = data.full_name.strip()
    email = data.email.strip().lower()
    password = data.password

    if len(name) < 2:
        raise HTTPException(422, "Please enter your full name")

    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        raise HTTPException(422, "Enter a valid email address")

    if len(password.encode("utf-8")) > 72:
        raise HTTPException(422, "Password must be at most 72 bytes")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "An account with this email already exists")

    patient_role = db.query(Role).filter(Role.name == "patient").first()
    if not patient_role:
        patient_role = Role(name="patient")
        db.add(patient_role)
        db.flush()

    try:
        user = User(
            full_name=name,
            email=email,
            phone=data.phone.strip() if data.phone and data.phone.strip() else None,
            password_hash=hash_password(password),
            role_id=patient_role.id,
            active=True,
        )
        db.add(user)
        db.flush()

        existing_patients = db.execute(
            text("""
                SELECT id FROM patients
                WHERE LOWER(TRIM(email)) = :email
            """),
            {"email": email},
        ).fetchall()

        if len(existing_patients) > 1:
            raise HTTPException(
                409,
                "Multiple patient profiles use this email. Contact clinic support."
            )

        if not existing_patients:
            db.execute(
                text("""
                    INSERT INTO patients (name, phone, email)
                    VALUES (:name, :phone, :email)
                """),
                {"name": name, "phone": user.phone, "email": email},
            )

        db.commit()

        return {
            "message": "Account created successfully. Please log in.",
            "email": user.email,
        }
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "An account with this email already exists"
        )
    except Exception:
        db.rollback()
        raise


@router.post("/login")
def login(data: Login, db: Session = Depends(get_db)):
    email = data.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")

    if not user.active:
        raise HTTPException(403, "This account is inactive")

    return {
        "access_token": create_token(user.id),
        "token_type": "bearer",
        "role": user.role.name,
        "name": user.full_name,
    }
