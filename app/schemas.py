from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date, time

class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class User(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    role: int
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class DoctorBase(BaseModel):
    full_name: str
    specialty: str
    email: EmailStr
    phone: Optional[str] = None
    hospital_id: Optional[int] = None
    bio: Optional[str] = None
    years_experience: Optional[int] = None
    education: Optional[str] = None

class DoctorCreate(DoctorBase):
    pass

class Doctor(DoctorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class HospitalBase(BaseModel):
    name: str
    address: str
    city: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    specialties: Optional[str] = None
    description: Optional[str] = None
    latitude: Optional[float] = None  
    longitude: Optional[float] = None  

class HospitalCreate(HospitalBase):
    pass

class Hospital(HospitalBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PatientBase(BaseModel):
    full_name: str
    date_of_birth: Optional[datetime] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    blood_type: Optional[str] = None
    allergies: Optional[str] = None
    medical_history: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class Patient(PatientBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class AppointmentCreate(BaseModel):
    doctor_id: int
    appointment_date: date
    appointment_time: time
    note: Optional[str] = None