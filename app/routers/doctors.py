from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from .. import models, schemas, auth
from ..database import get_db

router = APIRouter(prefix="/api/doctors", tags=["doctors"])

@router.get("/", response_model=List[schemas.Doctor])
def get_doctors(
    skip: int = 0,
    limit: int = 100,
    specialty: str | None = None,
    hospital_id: int | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Doctor)
    
    if specialty:
        query = query.filter(models.Doctor.specialty.contains(specialty))
    if hospital_id:
        query = query.filter(models.Doctor.hospital_id == hospital_id)
    
    doctors = query.offset(skip).limit(limit).all()
    return doctors


# =========================================================
# 📊 Endpoint: Đếm tổng số bác sĩ
# =========================================================
@router.get("/count-all")
def get_doctors_count(db: Session = Depends(get_db)):
    count = db.query(models.Doctor).count()
    return {"total_doctors": count}

@router.get("/{doctor_id}", response_model=schemas.Doctor)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

@router.post("/", response_model=schemas.Doctor)
def create_doctor(
    doctor: schemas.DoctorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_doctor = models.Doctor(**doctor.dict())
    db.add(db_doctor)
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

@router.put("/{doctor_id}", response_model=schemas.Doctor)
def update_doctor(
    doctor_id: int,
    doctor: schemas.DoctorCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not db_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    for key, value in doctor.dict().items():
        setattr(db_doctor, key, value)
    
    db.commit()
    db.refresh(db_doctor)
    return db_doctor

@router.delete("/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_active_user)
):
    db_doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    if not db_doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    db.delete(db_doctor)
    db.commit()
    return {"message": "Doctor deleted successfully"}



 