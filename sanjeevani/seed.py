from sqlalchemy.orm import Session
from .database.connection import Base, engine, SessionLocal
from .database.models import *
from .auth import hash_password
from decimal import Decimal

def seed():
    Base.metadata.create_all(engine); db=SessionLocal()
    roles={}
    for name in ["super_admin","doctor","reception_staff","pharmacy_staff","delivery_staff","patient"]:
        r=db.query(Role).filter_by(name=name).first() or Role(name=name); db.add(r); db.flush(); roles[name]=r
    codes=["admin.dashboard.view","admin.users.manage","doctor.dashboard.view","doctor.patients.view","doctor.prescriptions.write","staff.appointments.manage","pharmacy.inventory.manage","delivery.assigned.manage"]
    perms={}
    for code in codes:
        p=db.query(Permission).filter_by(code=code).first() or Permission(code=code); db.add(p); db.flush(); perms[code]=p
    role_codes={"super_admin":codes,"doctor":["doctor.dashboard.view","doctor.patients.view","doctor.prescriptions.write"],"reception_staff":["staff.appointments.manage"],"pharmacy_staff":["pharmacy.inventory.manage"],"delivery_staff":["delivery.assigned.manage"]}
    for rn,pcs in role_codes.items():
        for code in pcs:
            if not db.query(RolePermission).filter_by(role_id=roles[rn].id,permission_id=perms[code].id).first(): db.add(RolePermission(role_id=roles[rn].id,permission_id=perms[code].id))
    accounts=[("admin@sanjeevani.local","Admin User","super_admin"),("doctor@sanjeevani.local","Dr. Rahul Sharma","doctor"),("staff@sanjeevani.local","Reception Staff","reception_staff"),("pharmacy@sanjeevani.local","Pharmacy Staff","pharmacy_staff"),("delivery@sanjeevani.local","Delivery Staff","delivery_staff"),("patient@sanjeevani.local","Demo Patient","patient")]
    for email,name,role in accounts:
        if not db.query(User).filter_by(email=email).first(): db.add(User(email=email,full_name=name,password_hash=hash_password("ChangeMe123!"),role_id=roles[role].id))
    db.flush()
    doctor_user=db.query(User).filter_by(email="doctor@sanjeevani.local").first(); patient_user=db.query(User).filter_by(email="patient@sanjeevani.local").first()
    if not db.query(Doctor).filter_by(user_id=doctor_user.id).first(): db.add(Doctor(user_id=doctor_user.id,registration_no="RJ-MED-10001",experience_years=12,consultation_fee=Decimal("700.00")))
    if not db.query(Patient).filter_by(user_id=patient_user.id).first(): db.add(Patient(user_id=patient_user.id,gender="Male",blood_group="O+"))
    if not db.query(Medicine).first():
        db.add_all([Medicine(name="Paracetamol 500mg",generic_name="Paracetamol",category="Analgesic",unit_price=Decimal("20"),stock_qty=200),Medicine(name="Cetirizine 10mg",generic_name="Cetirizine",category="Antihistamine",unit_price=Decimal("35"),stock_qty=120),Medicine(name="Omeprazole 20mg",generic_name="Omeprazole",category="GI",unit_price=Decimal("55"),stock_qty=90)])
    db.commit(); db.close()
if __name__=="__main__": seed(); print("Sanjeevani seed complete")
