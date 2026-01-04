from sqlalchemy import Boolean, Column, Integer, String, Text, ForeignKey, DateTime, Float, TIMESTAMP, Date, Time
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    role = Column(Integer, default=0, nullable=False) 
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    doctor = relationship("Doctor", back_populates="user", uselist=False)  # 1-1 với doctor
    patient = relationship("Patient", back_populates="user", uselist=False)

class Doctor(Base):
    __tablename__ = "doctors"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    specialty = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String)
    hospital_id = Column(Integer, ForeignKey("hospitals.id"), nullable=True)
    bio = Column(Text)
    years_experience = Column(Integer)
    education = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    hospital = relationship("Hospital", back_populates="doctors")
    user = relationship("User", back_populates="doctor")

class Hospital(Base):
    __tablename__ = "hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    address = Column(String, nullable=False)
    city = Column(String)
    phone = Column(String)
    email = Column(String)
    specialties = Column(String)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    doctors = relationship("Doctor", back_populates="hospital")

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    # thêm UNIQUE để đảm bảo 1-1
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    full_name = Column(String, nullable=False)
    date_of_birth = Column(DateTime)
    gender = Column(String)
    phone = Column(String)
    address = Column(String)
    blood_type = Column(String)
    allergies = Column(Text)
    medical_history = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="patient", uselist=False)

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"))
    doctor_id = Column(Integer, ForeignKey("doctors.id", ondelete="CASCADE"))

    appointment_date = Column(Date, nullable=False)
    appointment_time = Column(Time, nullable=False)

    status = Column(String(30), default="pending")  
    note = Column(Text, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())

    # optional relations (không bắt buộc)
    patient = relationship("Patient", backref="appointments")
    doctor = relationship("Doctor", backref="appointments")