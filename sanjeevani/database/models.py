from datetime import datetime, date, time
from decimal import Decimal
from sqlalchemy import String, Integer, Boolean, DateTime, Date, Time, ForeignKey, Numeric, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .connection import Base

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    users = relationship("User", back_populates="role")
    permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))
    roles = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id"), primary_key=True)
    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    role = relationship("Role", back_populates="users")
    doctor = relationship("Doctor", back_populates="user", uselist=False)
    patient = relationship("Patient", back_populates="user", uselist=False)

class Specialty(Base):
    __tablename__ = "specialties"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    doctors = relationship("DoctorSpecialty", back_populates="specialty")

class Doctor(Base):
    __tablename__ = "doctors"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    registration_no: Mapped[str] = mapped_column(String(80), unique=True)
    experience_years: Mapped[int] = mapped_column(Integer, default=0)
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    user = relationship("User", back_populates="doctor")
    specialties = relationship("DoctorSpecialty", back_populates="doctor", cascade="all, delete-orphan")

class DoctorSpecialty(Base):
    __tablename__ = "doctor_specialties"
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), primary_key=True)
    specialty_id: Mapped[int] = mapped_column(ForeignKey("specialties.id"), primary_key=True)
    doctor = relationship("Doctor", back_populates="specialties")
    specialty = relationship("Specialty", back_populates="doctors")

class Patient(Base):
    __tablename__ = "patients"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    dob: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(20))
    blood_group: Mapped[str | None] = mapped_column(String(10))
    emergency_contact: Mapped[str | None] = mapped_column(String(120))
    user = relationship("User", back_populates="patient")

class Appointment(Base):
    __tablename__ = "appointments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"), index=True)
    appointment_date: Mapped[date] = mapped_column(Date)
    appointment_time: Mapped[time] = mapped_column(Time)
    consultation_fee: Mapped[Decimal] = mapped_column(Numeric(10,2))
    status: Mapped[str] = mapped_column(String(30), default="payment_pending")
    payment_status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__ = (UniqueConstraint("doctor_id", "appointment_date", "appointment_time", name="uq_doctor_slot"),)

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("medicine_orders.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10,2))
    gateway: Mapped[str] = mapped_column(String(40), default="mock")
    transaction_id: Mapped[str | None] = mapped_column(String(120), unique=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime)

class Medicine(Base):
    __tablename__ = "medicines"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    generic_name: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str | None] = mapped_column(String(100))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10,2))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
    reorder_level: Mapped[int] = mapped_column(Integer, default=10)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Prescription(Base):
    __tablename__ = "prescriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("medicine_orders.id"))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    prescription_id: Mapped[int] = mapped_column(
        ForeignKey("prescriptions.id"), index=True
    )
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id"), index=True
    )
    dosage: Mapped[str] = mapped_column(String(120))
    frequency: Mapped[str] = mapped_column(String(120))
    duration_days: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    instructions: Mapped[str | None] = mapped_column(Text)


class PatientAddress(Base):
    __tablename__ = "patient_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id"), index=True
    )
    label: Mapped[str] = mapped_column(String(50), default="Home")
    address_line: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(20))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10,7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10,7))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class MedicineOrder(Base):
    __tablename__ = "medicine_orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    prescription_id: Mapped[int | None] = mapped_column(ForeignKey("prescriptions.id"))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)
    medicine_total: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(10,2), default=0)
    status: Mapped[str] = mapped_column(String(40), default="payment_pending")
    address: Mapped[str] = mapped_column(Text)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(8,2))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MedicineOrderItem(Base):
    __tablename__ = "medicine_order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_orders.id"), index=True
    )
    medicine_id: Mapped[int] = mapped_column(
        ForeignKey("medicines.id"), index=True
    )
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10,2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(10,2))


class DeliveryPartner(Base):
    __tablename__ = "delivery_partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), unique=True
    )
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(30))
    vehicle_no: Mapped[str | None] = mapped_column(String(40))
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class DeliveryAssignment(Base):
    __tablename__ = "delivery_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("medicine_orders.id"), unique=True
    )
    delivery_partner_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_partners.id")
    )
    status: Mapped[str] = mapped_column(
        String(40), default="assigned"
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)


class DeliveryTrackingEvent(Base):
    __tablename__ = "delivery_tracking_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(
        ForeignKey("delivery_assignments.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(40))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(10,7))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(10,7))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(120))
    resource: Mapped[str | None] = mapped_column(String(120))
    resource_id: Mapped[str | None] = mapped_column(String(80))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
