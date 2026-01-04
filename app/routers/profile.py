from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Doctor, Patient
from app.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/profile", tags=["Profile"])

class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: str | None = None
    address: str | None = None
    specialty: str | None = None

@router.get("")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {
        "user": current_user,
        "patient": db.query(Patient).filter_by(user_id=current_user.id).first(),
        "doctor": db.query(Doctor).filter_by(user_id=current_user.id).first(),
    }

@router.put("")
def update_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if payload.full_name:
        current_user.full_name = payload.full_name
    if payload.email:
        current_user.email = payload.email

    if current_user.role == 0:
        patient = db.query(Patient).filter_by(user_id=current_user.id).first()
        if patient and payload.address:
            patient.address = payload.address

    if current_user.role == 1:
        doctor = db.query(Doctor).filter_by(user_id=current_user.id).first()
        if doctor and payload.specialty:
            doctor.specialty = payload.specialty

    db.commit()
    return {"message": "Profile updated"}
