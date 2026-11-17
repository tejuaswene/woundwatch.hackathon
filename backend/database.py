from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./woundwatch.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Patient(Base):
    __tablename__ = "patients"
    phone = Column(String, primary_key=True)
    name = Column(String, default="")
    age = Column(Integer, default=0)
    gender = Column(String, default="")
    surgery_type = Column(String, default="")
    surgery_date = Column(String, default="")
    doctor_id = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Doctor(Base):
    __tablename__ = "doctors"
    doctor_id = Column(String, primary_key=True)
    name = Column(String, default="")
    phone = Column(String, default="")
    specialization = Column(String, default="")
    hospital = Column(String, default="")
    password_hash = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class WoundPhoto(Base):
    __tablename__ = "wound_photos"
    id = Column(Integer, primary_key=True, autoincrement=True)
    patient_phone = Column(String, index=True)
    filename = Column(String)
    upload_time = Column(DateTime, default=datetime.utcnow)
    risk_level = Column(String, default="YELLOW")
    risk_score = Column(Float, default=0.0)
    redness_index = Column(Float, default=0.0)
    swelling_score = Column(Float, default=0.0)
    color_deviation = Column(Float, default=0.0)
    recommendation = Column(Text, default="")
    doctor_notes = Column(Text, default="")
    reviewed = Column(Boolean, default=False)
    reviewed_at = Column(DateTime, nullable=True)
    # Doctor review of this specific skin photo
    reviewed_by = Column(String, default="")          # doctor_id
    doctor_assessment = Column(String, default="")    # GREEN / YELLOW / RED (doctor's verdict)
    doctor_findings = Column(Text, default="")
    doctor_advice = Column(Text, default="")
    doctor_medications = Column(Text, default="")
    followup_date = Column(String, default="")


class OTPRecord(Base):
    __tablename__ = "otp_records"
    phone = Column(String, primary_key=True)
    otp = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    verified = Column(Boolean, default=False)


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, autoincrement=True)
    target_phone = Column(String, index=True)
    target_type = Column(String, default="patient")  # patient or doctor
    title = Column(String, default="")
    message = Column(Text, default="")
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    # GPS location (sent with SOS alerts)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location_accuracy = Column(Float, nullable=True)  # metres


def _migrate_columns():
    """Add new columns to existing tables (SQLite create_all does not alter tables)."""
    from sqlalchemy import inspect, text
    insp = inspect(engine)
    tables = insp.get_table_names()
    wanted = {
        "wound_photos": {
            "reviewed_by": "VARCHAR DEFAULT ''",
            "doctor_assessment": "VARCHAR DEFAULT ''",
            "doctor_findings": "TEXT DEFAULT ''",
            "doctor_advice": "TEXT DEFAULT ''",
            "doctor_medications": "TEXT DEFAULT ''",
            "followup_date": "VARCHAR DEFAULT ''",
        },
        "notifications": {
            "latitude": "FLOAT",
            "longitude": "FLOAT",
            "location_accuracy": "FLOAT",
        },
    }
    with engine.begin() as conn:
        for table, cols in wanted.items():
            if table not in tables:
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, ddl in cols.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db():
    Base.metadata.create_all(bind=engine)
    _migrate_columns()
    # Create default demo doctor
    db = SessionLocal()
    try:
        doc = db.query(Doctor).filter(Doctor.doctor_id == "DOC001").first()
        if not doc:
            demo_doc = Doctor(
                doctor_id="DOC001",
                name="Dr. Demo",
                phone="9999999999",
                specialization="General Surgery",
                hospital="City Hospital",
                password_hash="demo123"
            )
            db.add(demo_doc)
            db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
