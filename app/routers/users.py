from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.models import User, Doctor, Patient, Appointment

router = APIRouter(prefix="/users", tags=["Users"])

# Pydantic model cho body JSON khi update role
class RoleUpdate(BaseModel):
    role: int

# ==== Hàm migrate chung ====
def migrate_role(user_id: int, new_role: int, db: Session):
    """Migrate role fully, xử lý xóa/tạo Doctor/Patient và tránh FK errors"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # --- Xử lý role cũ → admin ---
    if new_role == 2:  # admin
        # Xóa Doctor
        doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
        if doctor:
            # Xóa appointment liên quan doctor trước
            db.query(Appointment).filter(Appointment.doctor_id == doctor.id).delete()
            db.delete(doctor)
        # Xóa Patient
        patient = db.query(Patient).filter(Patient.user_id == user_id).first()
        if patient:
            # Xóa appointment liên quan patient trước
            db.query(Appointment).filter(Appointment.patient_id == patient.id).delete()
            db.delete(patient)

    # --- Xử lý role cũ → doctor ---
    elif new_role == 1:  # doctor
        # Xóa tất cả dữ liệu liên quan patient
        patient = db.query(Patient).filter(Patient.user_id == user_id).first()
        if patient:
            db.query(Appointment).filter(Appointment.patient_id == patient.id).delete()
            db.delete(patient)
        # Tạo Doctor nếu chưa có
        doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
        if not doctor:
            doctor = Doctor(
                user_id=user_id,
                full_name=user.full_name,
                specialty="Chưa xác định",
                email=user.email or "no-email@example.com"
            )
            db.add(doctor)

    # --- Xử lý role cũ → patient ---
    elif new_role == 0:  # patient
        # Xóa tất cả dữ liệu liên quan doctor
        doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
        if doctor:
            db.query(Appointment).filter(Appointment.doctor_id == doctor.id).delete()
            db.delete(doctor)
        # Tạo Patient nếu chưa có
        patient = db.query(Patient).filter(Patient.user_id == user_id).first()
        if not patient:
            patient = Patient(
                user_id=user_id,
                full_name=user.full_name,
                created_at=datetime.utcnow()
            )
            db.add(patient)

    db.commit()
    db.refresh(user)
    return user
# ==== Kết thúc migrate ====

@router.get("/")
def get_users(search: str = "", db: Session = Depends(get_db)):
    query = db.query(User)
    if search:
        query = query.filter(
            User.full_name.ilike(f"%{search}%") |
            User.email.ilike(f"%{search}%")
        )
    return query.all()

@router.get("/count")
def get_user_count(db: Session = Depends(get_db)):
    return {"count": db.query(User).count()}

@router.put("/{user_id}/role")
def update_role(user_id: int, payload: RoleUpdate = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.role == payload.role:
        return {"message": f"User role is already {payload.role}"}

    # migrate dữ liệu
    migrate_role(user_id, payload.role, db)

    # cập nhật role user
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return {"message": f"User role updated to {payload.role}"}

@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    # Xóa doctor hoặc patient liên quan trước
    doctor = db.query(Doctor).filter(Doctor.user_id == user_id).first()
    if doctor:
        db.delete(doctor)

    patient = db.query(Patient).filter(Patient.user_id == user_id).first()
    if patient:
        db.delete(patient)

    # Cuối cùng mới xóa user
    db.delete(user)
    db.commit()
    return {"message": "User deleted"}

