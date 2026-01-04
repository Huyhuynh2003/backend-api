from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Appointment, Patient, Doctor
from ..schemas import AppointmentCreate
from ..auth import get_current_user
from ..services.email_service import send_appointment_email
from typing import List
from datetime import date

router = APIRouter(tags=["Appointments"])

@router.post("/")
def book_appointment(
    data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    print("CURRENT USER:", current_user.id, current_user.role)

    if current_user.role != 0:
        raise HTTPException(status_code=403, detail="Only patients can book appointments")

    patient = current_user.patient
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Check slot bị trùng
    exist = db.query(Appointment).filter(
        Appointment.doctor_id == data.doctor_id,
        Appointment.appointment_date == data.appointment_date,
        Appointment.appointment_time == data.appointment_time
    ).first()

    if exist:
        raise HTTPException(status_code=400, detail="Bác sĩ đang bận vào thời gian này")

    appointment = Appointment(
        patient_id=patient.id,
        doctor_id=data.doctor_id,
        appointment_date=data.appointment_date,
        appointment_time=data.appointment_time,
        note=data.note
    )

    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return {
        "message": "Đặt lịch thành công",
        "appointment_id": appointment.id
    }

@router.get("/me")
def get_my_appointments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != 0:
        raise HTTPException(status_code=403, detail="Only patients")

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    data = db.query(
    Appointment.id,
    Appointment.appointment_date,
    Appointment.appointment_time,
    Appointment.status,
    Appointment.note,
    Doctor.full_name.label("doctor_name")
    ).join(
        Doctor, Appointment.doctor_id == Doctor.id
    ).filter(
        Appointment.patient_id == patient.id
    ).order_by(
        Appointment.appointment_date.desc()
    ).all()

    # Convert tuple -> dict
    result = [
        {
            "id": d[0],
            "appointment_date": d[1],
            "appointment_time": d[2],
            "status": d[3],
            "note": d[4],
            "doctor_name": d[5],
        }
        for d in data
    ]

    return result


@router.get("/doctor")
def get_doctor_appointments(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != 1:
        raise HTTPException(status_code=403, detail="Only doctors")

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    # Join Patient để lấy tên bệnh nhân
    data = db.query(
    Appointment.id,
    Appointment.appointment_date,
    Appointment.appointment_time,
    Appointment.status,
    Appointment.note,
    Patient.full_name.label("patient_name")
    ).join(
        Patient, Appointment.patient_id == Patient.id
    ).filter(
        Appointment.doctor_id == doctor.id
    ).order_by(
        Appointment.appointment_date.asc()
    ).all()

    # Chuyển tuple / Row thành dict
    result = [
        {
            "id": a.id,
            "appointment_date": a.appointment_date,
            "appointment_time": a.appointment_time,
            "status": a.status,
            "note": a.note,
            "patient_name": a.patient_name
        }
        for a in data
    ]

    return result


@router.put("/{appointment_id}/status")
async def update_status(
    appointment_id: int,
    status: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != 1:
        raise HTTPException(status_code=403, detail="Only doctors")

    if status not in ["confirmed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Invalid status")

    doctor = db.query(Doctor).filter(Doctor.user_id == current_user.id).first()

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.doctor_id == doctor.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    old_status = appointment.status

    if old_status != status:
        appointment.status = status
        db.commit()
        db.refresh(appointment)

        patient = db.query(Patient).filter(
            Patient.id == appointment.patient_id
        ).first()

        background_tasks.add_task(
            send_appointment_email,
            patient.user.email,
            patient.full_name,
            doctor.full_name,
            appointment.appointment_date,
            appointment.appointment_time,
            status,
            appointment.note
        )

    return {"message": f"Appointment {status}"}

@router.delete("/{appointment_id}")
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != 0:
        raise HTTPException(status_code=403, detail="Only patients")

    patient = db.query(Patient).filter(Patient.user_id == current_user.id).first()

    appointment = db.query(Appointment).filter(
        Appointment.id == appointment_id,
        Appointment.patient_id == patient.id
    ).first()

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    db.delete(appointment)
    db.commit()

    return {"message": "Appointment cancelled"}

@router.get("/busy-times", response_model=List[str])
def get_busy_times(
    doctor_id: int = Query(...),
    date: date = Query(...),
    db: Session = Depends(get_db)
):
    """
    Lấy các giờ đã được đặt của 1 bác sĩ trong 1 ngày cụ thể
    """

    appointments = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_date == date,
        Appointment.status != "cancelled"
    ).all()

    # Chuyển TIME -> "HH:MM"
    busy_times = [
        appt.appointment_time.strftime("%H:%M") 
        for appt in appointments
        if appt.appointment_time
    ]

    return busy_times