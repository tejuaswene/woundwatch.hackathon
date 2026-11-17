from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, List
import os, shutil, json, io
from dotenv import load_dotenv

load_dotenv()

from database import init_db, get_db, Patient, Doctor, WoundPhoto, OTPRecord, Notification
from wound_analyzer import analyze_wound, validate_wound_image, generate_heatmap
from otp_service import send_otp as send_otp_svc, verify_otp as verify_otp_svc

app = FastAPI(title="WoundWatch API", version="3.1.0")

app.add_middleware(
    CORSMiddleware,
        allow_origins=["https://woundwatch-patient.vercel.app", "https://woundwatch-doctor.vercel.app", "http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
init_db()

# ==================== SEED DEMO DOCTOR ====================
def seed_demo_doctor():
    from database import SessionLocal
    db = SessionLocal()
    try:
        doc = db.query(Doctor).filter(Doctor.doctor_id == "DOC001").first()
        if not doc:
            doc = Doctor(
                doctor_id="DOC001",
                name="Dr. Demo",
                password_hash="demo123",
                specialization="General Surgery",
                hospital="WoundWatch Demo Hospital"
            )
            db.add(doc)
            db.commit()
            print("✅ Demo doctor DOC001 seeded")
        else:
            # Ensure password is correct
            if doc.password_hash != "demo123":
                doc.password_hash = "demo123"
                db.commit()
                print("✅ Demo doctor password fixed")
    finally:
        db.close()

seed_demo_doctor()

# ==================== AUTH ====================

@app.post("/auth/send-otp")
async def send_otp(phone: str = Form(...), db: Session = Depends(get_db)):
    result = send_otp_svc(phone)
    return result

@app.post("/auth/verify-otp")
async def verify_otp(phone: str = Form(...), otp: str = Form(...), db: Session = Depends(get_db)):
    result = verify_otp_svc(phone, otp)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    # Auto-create patient if not exists
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        patient = Patient(phone=phone)
        db.add(patient)
        db.commit()
    # FIX: Use `not patient.name` instead of `patient.name == ""` (handles None)
    return {"success": True, "phone": phone, "name": patient.name, "is_new": not patient.name}

# ==================== DOCTOR AUTH ====================

@app.post("/auth/doctor-login")
async def doctor_login(doctor_id: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor or doctor.password_hash != password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"success": True, "doctor_id": doctor.doctor_id, "name": doctor.name, "specialization": doctor.specialization, "hospital": doctor.hospital}

# ==================== PATIENT PROFILE ====================

@app.post("/api/patient-profile")
async def update_profile(
    phone: str = Form(...), name: str = Form(""), age: int = Form(0),
    gender: str = Form(""), surgery_type: str = Form(""), surgery_date: str = Form(""),
    doctor_id: str = Form(""), db: Session = Depends(get_db)
):
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        patient = Patient(phone=phone)
        db.add(patient)
    patient.name = name
    patient.age = age
    patient.gender = gender
    patient.surgery_type = surgery_type
    patient.surgery_date = surgery_date
    patient.doctor_id = doctor_id
    db.commit()
    return {"success": True, "message": "Profile updated"}

@app.get("/api/patient-profile/{phone}")
async def get_profile(phone: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "phone": patient.phone, "name": patient.name, "age": patient.age,
        "gender": patient.gender, "surgery_type": patient.surgery_type,
        "surgery_date": patient.surgery_date, "doctor_id": patient.doctor_id
    }

# ==================== WOUND PHOTOS ====================

@app.post("/api/upload-wound-photo")
async def upload_photo(
    phone: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db)
):
    allowed = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in allowed:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, WebP images allowed")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{phone}_{timestamp}_{file.filename}"
    filepath = os.path.join("uploads", filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # ===== VALIDATE: Is this actually a wound photo? =====
    validation = validate_wound_image(filepath)
    if not validation["valid"]:
        os.remove(filepath)
        raise HTTPException(status_code=400, detail=validation["reason"])

    result = analyze_wound(filepath)

    # Generate heatmap overlay (shown to doctor in review + included in PDF report)
    try:
        generate_heatmap(filepath, os.path.join("uploads", f"heatmap_{filename}"))
    except Exception as e:
        print(f"[WoundWatch] heatmap failed: {e}")

    photo = WoundPhoto(
        patient_phone=phone, filename=filename, risk_level=result["risk_level"],
        risk_score=result["risk_score"], redness_index=result["redness_index"],
        swelling_score=result["swelling_score"], color_deviation=result["color_deviation"],
        recommendation=result["recommendation"]
    )
    db.add(photo)
    db.commit()

    # Create notification for doctor if RED
    if result["risk_level"] == "RED":
        patient = db.query(Patient).filter(Patient.phone == phone).first()
        pname = patient.name if patient and patient.name else phone
        # FIX: Default to DOC001 if patient has no assigned doctor
        doctor_id = (patient.doctor_id if patient and patient.doctor_id else "DOC001")
        notif = Notification(
            target_phone=doctor_id,
            target_type="doctor",
            title="HIGH RISK Alert",
            message=f"Patient {pname} uploaded a wound photo with RED risk level (score: {result['risk_score']:.0%})"
        )
        db.add(notif)
        db.commit()

    return {
        "success": True, "filename": filename,
        "risk_level": result["risk_level"], "risk_score": result["risk_score"],
        "redness_index": result["redness_index"], "swelling_score": result["swelling_score"],
        "color_deviation": result["color_deviation"], "recommendation": result["recommendation"]
    }

def photo_to_dict(p: WoundPhoto) -> dict:
    return {
        "id": p.id, "filename": p.filename, "uploaded_at": str(p.upload_time),
        "risk_level": p.risk_level, "risk_score": p.risk_score,
        "redness_index": p.redness_index, "swelling_score": p.swelling_score,
        "color_deviation": p.color_deviation, "recommendation": p.recommendation,
        "doctor_notes": p.doctor_notes, "reviewed": bool(p.reviewed),
        "reviewed_at": str(p.reviewed_at) if p.reviewed_at else "",
        "reviewed_by": p.reviewed_by or "",
        "doctor_assessment": p.doctor_assessment or "",
        "doctor_findings": p.doctor_findings or "",
        "doctor_advice": p.doctor_advice or "",
        "doctor_medications": p.doctor_medications or "",
        "followup_date": p.followup_date or "",
        "report_available": bool(p.reviewed and p.doctor_assessment),
    }

@app.get("/api/patient-history/{phone}")
async def get_history(phone: str, db: Session = Depends(get_db)):
    photos = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.desc()).all()
    return [photo_to_dict(p) for p in photos]

# ==================== EMERGENCY SOS ====================

@app.post("/api/sos")
async def emergency_sos(
    phone: str = Form(...), message: str = Form("Emergency! Patient needs immediate attention."),
    latitude: str = Form(""), longitude: str = Form(""), accuracy: str = Form(""),
    db: Session = Depends(get_db)
):
    """Emergency SOS — patient alerts their doctor instantly (with GPS location if the phone shared it)"""
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    # Never block an SOS: fall back to the demo doctor if the patient record is missing
    pname = (patient.name if patient and patient.name else phone)
    doctor_id = (patient.doctor_id if patient and patient.doctor_id else "DOC001")

    # Parse GPS (optional — SOS still goes out without it)
    lat = lng = acc = None
    try:
        if latitude and longitude:
            lat, lng = float(latitude), float(longitude)
            if not (-90 <= lat <= 90 and -180 <= lng <= 180):
                lat = lng = None
            acc = float(accuracy) if accuracy else None
    except ValueError:
        lat = lng = acc = None
    if lat is not None:
        acc_txt = f" (±{acc:.0f} m)" if acc else ""
        location_info = f" | 📍 Location{acc_txt}: https://www.google.com/maps?q={lat:.6f},{lng:.6f}"
    else:
        location_info = " | 📍 Location not shared"

    # Get latest wound photo for context
    latest = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.desc()).first()
    latest_info = ""
    if latest:
        latest_info = f" | Latest scan: {latest.risk_level} ({latest.risk_score:.0%}) at {latest.upload_time.strftime('%d %b %I:%M %p')}"

    # Create EMERGENCY notification for the doctor
    notif = Notification(
        target_phone=doctor_id,
        target_type="doctor",
        title="🚨 EMERGENCY SOS",
        message=f"Patient {pname} ({phone}) triggered SOS! \"{message}\"{latest_info}{location_info}",
        latitude=lat, longitude=lng, location_accuracy=acc,
    )
    db.add(notif)

    # Also create a confirmation notification for the patient
    notif_patient = Notification(
        target_phone=phone,
        target_type="patient",
        title="SOS Sent",
        message=f"Your emergency alert has been sent to your doctor. They will be notified immediately. If this is a life-threatening emergency, call 112."
    )
    db.add(notif_patient)
    db.commit()

    return {"success": True, "message": "Emergency SOS sent to your doctor", "doctor_id": doctor_id,
            "location_shared": lat is not None}

# ==================== DOCTOR ENDPOINTS ====================

@app.get("/api/patients")
async def get_patients(db: Session = Depends(get_db)):
    patients = db.query(Patient).all()
    result = []
    for p in patients:
        latest = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == p.phone).order_by(WoundPhoto.upload_time.desc()).first()
        total = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == p.phone).count()
        unreviewed = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == p.phone, WoundPhoto.reviewed == False).count()
        result.append({
            "phone": p.phone, "name": p.name, "age": p.age, "gender": p.gender,
            "surgery_type": p.surgery_type, "surgery_date": p.surgery_date,
            "latest_risk": latest.risk_level if latest else "NONE",
            "latest_score": latest.risk_score if latest else 0,
            "last_scan": str(latest.upload_time) if latest else "",
            "total_photos": total, "unreviewed": unreviewed
        })
    risk_order = {"RED": 0, "YELLOW": 1, "GREEN": 2, "NONE": 3}
    result.sort(key=lambda x: risk_order.get(x["latest_risk"], 3))
    return result

@app.get("/api/patient-detail/{phone}")
async def get_patient_detail(phone: str, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    photos = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.desc()).all()
    # Collect doctor notes from notifications
    notes = db.query(Notification).filter(
        Notification.target_phone == phone,
        Notification.target_type == "patient",
        Notification.title == "Doctor Review"
    ).order_by(Notification.created_at.desc()).all()
    return {
        "patient": {
            "phone": patient.phone, "name": patient.name, "age": patient.age,
            "gender": patient.gender, "surgery_type": patient.surgery_type,
            "surgery_date": patient.surgery_date
        },
        "photos": [photo_to_dict(p) for p in photos],
        "notes": [
            {"note": n.message, "doctor_id": "Doctor", "created_at": str(n.created_at)}
            for n in notes
        ]
    }

@app.post("/api/doctor-notes")
async def add_doctor_notes(
    photo_id: int = Form(None), phone: str = Form(None),
    doctor_id: str = Form(None), notes: str = Form(...),
    db: Session = Depends(get_db)
):
    # Support both old photo_id style and new phone+doctor_id style
    if photo_id:
        photo = db.query(WoundPhoto).filter(WoundPhoto.id == photo_id).first()
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        photo.doctor_notes = notes
        photo.reviewed = True
        photo.reviewed_at = datetime.utcnow()
        target_phone = photo.patient_phone
    elif phone:
        target_phone = phone
    else:
        raise HTTPException(status_code=400, detail="Provide photo_id or phone")

    db.commit()

    # Notify patient
    notif = Notification(
        target_phone=target_phone, target_type="patient",
        title="Doctor Review",
        message=notes
    )
    db.add(notif)
    db.commit()
    return {"success": True, "message": "Notes saved"}

# ==================== DOCTOR PHOTO REVIEW ====================

@app.post("/api/review-photo")
async def review_photo(
    photo_id: int = Form(...), doctor_id: str = Form(...),
    assessment: str = Form(...),            # GREEN / YELLOW / RED
    findings: str = Form(""), advice: str = Form(""),
    medications: str = Form(""), followup_date: str = Form(""),
    db: Session = Depends(get_db)
):
    assessment = assessment.upper().strip()
    if assessment not in ("GREEN", "YELLOW", "RED"):
        raise HTTPException(status_code=400, detail="assessment must be GREEN, YELLOW or RED")
    if not findings.strip():
        raise HTTPException(status_code=400, detail="Please write your findings")
    photo = db.query(WoundPhoto).filter(WoundPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    first_review = not photo.reviewed
    photo.reviewed = True
    photo.reviewed_at = datetime.utcnow()
    photo.reviewed_by = doctor_id
    photo.doctor_assessment = assessment
    photo.doctor_findings = findings.strip()
    photo.doctor_advice = advice.strip()
    photo.doctor_medications = medications.strip()
    photo.followup_date = followup_date.strip()
    photo.doctor_notes = findings.strip()

    taken = photo.upload_time.strftime("%d %b") if photo.upload_time else "your photo"
    verb = "reviewed" if first_review else "updated the review of"
    db.add(Notification(
        target_phone=photo.patient_phone, target_type="patient",
        title="Report Ready" if assessment != "RED" else "Report Ready - Please visit hospital",
        message=f"{doctor.name} {verb} your wound photo from {taken}. Download your PDF report from History."
    ))
    db.commit()
    return {"success": True, "message": "Review saved", "photo": photo_to_dict(photo)}

@app.get("/api/review-report/{photo_id}")
async def review_report(photo_id: int, phone: Optional[str] = None, inline: bool = False,
                        db: Session = Depends(get_db)):
    """PDF report for one doctor-reviewed wound photo. Patient passes ?phone= to download their own."""
    photo = db.query(WoundPhoto).filter(WoundPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    if phone and phone != photo.patient_phone:
        raise HTTPException(status_code=403, detail="This report belongs to another patient")
    if not (photo.reviewed and photo.doctor_assessment):
        raise HTTPException(status_code=400, detail="Doctor has not reviewed this photo yet")
    try:
        from report_pdf import build_review_report
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed. Run: pip install reportlab")

    patient = db.query(Patient).filter(Patient.phone == photo.patient_phone).first() or Patient(phone=photo.patient_phone)
    doctor = db.query(Doctor).filter(Doctor.doctor_id == photo.reviewed_by).first()
    buf = build_review_report(patient, photo, doctor, upload_dir="uploads")

    pname = (patient.name or photo.patient_phone).replace(" ", "_")
    day = photo.upload_time.strftime("%Y%m%d") if photo.upload_time else "photo"
    filename = f"WoundWatch_Review_{pname}_{day}_{photo.id}.pdf"
    disp = "inline" if inline else "attachment"
    return StreamingResponse(buf, media_type="application/pdf", headers={
        "Content-Disposition": f'{disp}; filename="{filename}"',
        "Access-Control-Expose-Headers": "Content-Disposition",
    })

# ==================== NOTIFICATIONS ====================

@app.get("/api/notifications/{phone}")
async def get_notifications(phone: str, target_type: str = "patient", db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(
        Notification.target_phone == phone, Notification.target_type == target_type
    ).order_by(Notification.created_at.desc()).limit(30).all()
    return [
        {"id": n.id, "title": n.title, "message": n.message, "read": n.read, "created_at": str(n.created_at),
         "latitude": n.latitude, "longitude": n.longitude, "location_accuracy": n.location_accuracy,
         "maps_url": (f"https://www.google.com/maps?q={n.latitude:.6f},{n.longitude:.6f}"
                      if n.latitude is not None and n.longitude is not None else None)}
        for n in notifs
    ]

@app.post("/api/notifications/read/{notif_id}")
async def mark_read(notif_id: int, db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if notif:
        notif.read = True
        db.commit()
    return {"success": True}

# ==================== STATS ====================

@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    total_patients = db.query(Patient).count()
    total_photos = db.query(WoundPhoto).count()
    red = db.query(WoundPhoto).filter(WoundPhoto.risk_level == "RED").count()
    yellow = db.query(WoundPhoto).filter(WoundPhoto.risk_level == "YELLOW").count()
    green = db.query(WoundPhoto).filter(WoundPhoto.risk_level == "GREEN").count()
    unreviewed = db.query(WoundPhoto).filter(WoundPhoto.reviewed == False).count()
    return {
        "total_patients": total_patients, "total_scans": total_photos,
        "red": red, "yellow": yellow, "green": green,
        "high_risk": red, "healthy": green,
        "unreviewed": unreviewed,
        "alert_rate": round(red / total_photos * 100, 1) if total_photos > 0 else 0
    }

# ==================== CHATBOT ====================

CHAT_RESPONSES = {
    "en": {
        "pain": "Mild pain is normal for 3-5 days after surgery. Take prescribed painkillers. If pain suddenly increases or throbs, contact your doctor.",
        "fever": "Low fever (up to 99°F/37.2°C) is normal for 1-2 days. If fever exceeds 100.4°F/38°C or lasts more than 48 hours, see your doctor.",
        "redness": "Some redness around the wound is normal. If redness spreads beyond 2cm from the wound edge or feels hot, it may be infected.",
        "medicine": "Take all antibiotics as prescribed, even if you feel better. Do not skip doses. Take painkillers with food to avoid stomach upset.",
        "diet": "Eat protein-rich food (eggs, dal, chicken, paneer) for healing. Drink 8+ glasses of water daily. Avoid spicy and oily food for 1 week.",
        "bath": "Keep the wound dry for 48 hours. After that, you can shower but don't soak. Pat dry gently. Don't apply soap directly on the wound.",
        "discharge": "Clear or slightly yellow discharge is normal. If discharge is thick, green, foul-smelling, or increasing, see your doctor immediately.",
        "stitches": "Don't pull or scratch stitches. They are usually removed in 7-14 days. Keep the area clean and dry. Report any loosening to your doctor.",
        "exercise": "Avoid heavy lifting for 2-4 weeks. Light walking is encouraged from day 1. Gradually increase activity as advised by your doctor.",
        "clean": "Clean wound gently with normal saline or clean water. Pat dry. Apply prescribed ointment and fresh dressing. Wash hands before and after.",
        "dressing": "Change dressing once daily or when it gets wet/dirty. Use sterile gauze and medical tape. Don't use cotton wool directly on wound.",
        "infection": "Signs of infection: increasing pain, spreading redness, warmth, swelling, pus/discharge, fever, red streaks. See doctor if you notice any.",
        "emergency": "Go to ER immediately if: heavy bleeding that won't stop, fever above 102°F, severe pain not relieved by medicine, wound opening up, or red streaks spreading from wound.",
        "default": "I can help with: pain management, fever concerns, redness monitoring, medicine schedule, diet tips, bathing care, wound discharge, stitches care, exercise limits, cleaning, dressing changes, infection signs, and emergency signs. What would you like to know?"
    },
    "hi": {
        "pain": "सर्जरी के बाद 3-5 दिन तक हल्का दर्द सामान्य है। निर्धारित दर्द निवारक लें। अगर दर्द अचानक बढ़े या धड़के, तो डॉक्टर से संपर्क करें।",
        "fever": "1-2 दिन तक हल्का बुखार (99°F/37.2°C तक) सामान्य है। अगर बुखार 100.4°F/38°C से ऊपर जाए या 48 घंटे से ज्यादा रहे, तो डॉक्टर को दिखाएं।",
        "redness": "घाव के आसपास कुछ लालिमा सामान्य है। अगर लालिमा घाव के किनारे से 2 सेमी से ज्यादा फैले या गर्म लगे, तो संक्रमण हो सकता है।",
        "medicine": "सभी एंटीबायोटिक्स निर्धारित अनुसार लें, भले ही आप बेहतर महसूस करें। खुराक न छोड़ें।",
        "diet": "ठीक होने के लिए प्रोटीन युक्त भोजन (अंडे, दाल, चिकन, पनीर) खाएं। रोज 8+ गिलास पानी पिएं। 1 सप्ताह तक मसालेदार और तैलीय भोजन से बचें।",
        "bath": "48 घंटे तक घाव को सूखा रखें। उसके बाद शावर ले सकते हैं पर भिगोएं नहीं। धीरे से थपथपाकर सुखाएं।",
        "discharge": "साफ या हल्का पीला स्राव सामान्य है। अगर स्राव गाढ़ा, हरा, बदबूदार या बढ़ रहा है, तो तुरंत डॉक्टर को दिखाएं।",
        "stitches": "टांके न खींचें और न खुजलाएं। आमतौर पर 7-14 दिनों में निकाले जाते हैं।",
        "exercise": "2-4 सप्ताह तक भारी सामान न उठाएं। पहले दिन से हल्की सैर की सलाह दी जाती है।",
        "clean": "घाव को साधारण नमक के पानी से धीरे से साफ करें। सूखा करें। निर्धारित मलहम और ताजी पट्टी लगाएं।",
        "dressing": "रोज एक बार या जब पट्टी गीली/गंदी हो तब बदलें। स्टराइल गॉज और मेडिकल टेप उपयोग करें।",
        "infection": "संक्रमण के लक्षण: बढ़ता दर्द, फैलती लालिमा, गर्मी, सूजन, मवाद, बुखार, लाल धारियां। कोई भी दिखे तो डॉक्टर को दिखाएं।",
        "emergency": "तुरंत ER जाएं अगर: भारी रक्तस्राव जो रुके नहीं, 102°F से ऊपर बुखार, अति तेज दर्द, घाव खुल रहा हो।",
        "default": "मैं इनमें मदद कर सकता हूं: दर्द, बुखार, लालिमा, दवाई, खानपान, नहाना, स्राव, टांके, व्यायाम, सफाई, पट्टी, संक्रमण, आपातकाल। क्या जानना चाहेंगे?"
    },
    "od": {
        "pain": "ଅପରେସନ ପରେ ୩-୫ ଦିନ ହାଲୁକା ଯନ୍ତ୍ରଣା ସ୍ୱାଭାବିକ। ଡାକ୍ତର ଦେଇଥିବା ଔଷଧ ଖାଆନ୍ତୁ। ଯଦି ଯନ୍ତ୍ରଣା ହଠାତ୍ ବଢ଼ିଯାଏ, ଡାକ୍ତରଙ୍କୁ କୁହନ୍ତୁ।",
        "fever": "୧-୨ ଦିନ ହାଲୁକା ଜ୍ୱର (୯୯°F ପର୍ଯ୍ୟନ୍ତ) ସ୍ୱାଭାବିକ। ଯଦି ଜ୍ୱର ୧୦୦.୪°F ଉପରେ ଯାଏ, ଡାକ୍ତରଙ୍କୁ ଦେଖାନ୍ତୁ।",
        "redness": "ଘା ଚାରିପଟେ ଅଳ୍ପ ଲାଲ ହେବା ସ୍ୱାଭାବିକ। ଯଦି ଲାଲ ୨ ସେମି ରୁ ବେଶି ବିସ୍ତାର ହୁଏ, ସଂକ୍ରମଣ ହୋଇପାରେ।",
        "medicine": "ସବୁ ଆଣ୍ଟିବାୟୋଟିକ ନିୟମିତ ଖାଆନ୍ତୁ। ଭଲ ଲାଗିଲେ ମଧ୍ୟ ବନ୍ଦ କରନ୍ତୁ ନାହିଁ।",
        "diet": "ଭଲ ହେବା ପାଇଁ ପ୍ରୋଟିନ ଯୁକ୍ତ ଖାଦ୍ୟ ଖାଆନ୍ତୁ - ଅଣ୍ଡା, ଡାଲି, ମାଛ। ଦିନକୁ ୮ ଗ୍ଲାସରୁ ବେଶି ପାଣି ପିଅନ୍ତୁ।",
        "bath": "୪୮ ଘଣ୍ଟା ପର୍ଯ୍ୟନ୍ତ ଘା ଶୁଖିଲା ରଖନ୍ତୁ। ତା ପରେ ସ୍ନାନ କରିପାରିବେ, କିନ୍ତୁ ଘା ଭିଜାନ୍ତୁ ନାହିଁ।",
        "discharge": "ସଫା କିମ୍ବା ହାଲୁକା ହଳଦିଆ ସ୍ରାବ ସ୍ୱାଭାବିକ। ଯଦି ସ୍ରାବ ସବୁଜ, ଦୁର୍ଗନ୍ଧ, ବା ବଢ଼ୁଛି, ତୁରନ୍ତ ଡାକ୍ତରଙ୍କୁ ଦେଖାନ୍ତୁ।",
        "stitches": "ଟାଙ୍କା ଟାଣନ୍ତୁ ନାହିଁ। ସାଧାରଣତଃ ୭-୧୪ ଦିନରେ ବାହାର କରାଯାଏ।",
        "exercise": "୨-୪ ସପ୍ତାହ ପର୍ଯ୍ୟନ୍ତ ଭାରୀ ଜିନିଷ ଉଠାନ୍ତୁ ନାହିଁ। ପ୍ରଥମ ଦିନଠାରୁ ହାଲୁକା ଚାଲିବା ଭଲ।",
        "clean": "ଘାକୁ ସାଧାରଣ ଲୁଣ ପାଣି ସହ ଧୀରେ ସଫା କରନ୍ତୁ। ଶୁଖାନ୍ତୁ। ନିର୍ଧାରିତ ମଲମ ଓ ନୂଆ ବନ୍ଧନୀ ଲଗାନ୍ତୁ।",
        "dressing": "ଦିନକୁ ଥରେ ବା ଭିଜିଲେ ବନ୍ଧନୀ ବଦଳାନ୍ତୁ। ଷ୍ଟେରାଇଲ ଗଜ ଓ ମେଡିକାଲ ଟେପ ବ୍ୟବହାର କରନ୍ତୁ।",
        "infection": "ସଂକ୍ରମଣ ଲକ୍ଷଣ: ବଢ଼ୁଥିବା ଯନ୍ତ୍ରଣା, ବିସ୍ତାର ହେଉଥିବା ଲାଲ, ଗରମ, ସୁଜନ, ପୂଜ, ଜ୍ୱର। କୌଣସି ଦେଖିଲେ ଡାକ୍ତରଙ୍କୁ ଦେଖାନ୍ତୁ।",
        "emergency": "ତୁରନ୍ତ ଡାକ୍ତରଖାନା ଯାଆନ୍ତୁ ଯଦି: ରକ୍ତସ୍ରାବ ବନ୍ଦ ହେଉନାହିଁ, ୧୦୨°F ଉପରେ ଜ୍ୱର, ଅସହ୍ୟ ଯନ୍ତ୍ରଣା, ଘା ଖୋଲିଯାଉଛି।",
        "default": "ମୁଁ ସାହାଯ୍ୟ କରିପାରିବି: ଯନ୍ତ୍ରଣା, ଜ୍ୱର, ଲାଲ, ଔଷଧ, ଖାଦ୍ୟ, ସ୍ନାନ, ସ୍ରାବ, ଟାଙ୍କା, ବ୍ୟାୟାମ, ସଫାଇ, ବନ୍ଧନୀ, ସଂକ୍ରମଣ, ଜରୁରୀ। କଣ ଜାଣିବାକୁ ଚାହାନ୍ତି?"
    }
}

@app.post("/api/chat")
async def chat(phone: str = Form(...), message: str = Form(...), lang: str = Form("en")):
    msg = message.lower()
    responses = CHAT_RESPONSES.get(lang, CHAT_RESPONSES["en"])
    reply = responses["default"]
    for keyword, response in responses.items():
        if keyword != "default" and keyword in msg:
            reply = response
            break
    return {"reply": reply, "lang": lang}

# ==================== PDF REPORT ====================

@app.get("/api/report/{phone}")
async def generate_report(phone: str, db: Session = Depends(get_db)):
    """Generate a PDF wound history report for a patient"""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
    except ImportError:
        raise HTTPException(status_code=500, detail="reportlab not installed. Run: pip install reportlab")

    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    photos = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.asc()).all()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=20*mm, rightMargin=20*mm, topMargin=25*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#2F2B6E'), spaceAfter=4)
    subtitle_style = ParagraphStyle('Subtitle', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#7F79B6'), spaceAfter=16, alignment=TA_CENTER)
    heading_style = ParagraphStyle('Heading', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2F2B6E'), spaceBefore=16, spaceAfter=8)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#333333'), spaceAfter=4)
    risk_colors = {'GREEN': colors.HexColor('#2BA84A'), 'YELLOW': colors.HexColor('#E89B2C'), 'RED': colors.HexColor('#D64545')}

    elements = []

    # Header
    elements.append(Paragraph("WoundWatch - Patient Report", title_style))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%d %B %Y, %I:%M %p')}", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#E8E7F0'), spaceAfter=12))

    # Patient Info
    elements.append(Paragraph("Patient Information", heading_style))
    p_info = [
        ["Name", patient.name or "N/A"],
        ["Phone", patient.phone],
        ["Age / Gender", f"{patient.age or 'N/A'} / {patient.gender or 'N/A'}"],
        ["Surgery Type", patient.surgery_type or "N/A"],
        ["Surgery Date", patient.surgery_date or "N/A"],
    ]
    t = Table(p_info, colWidths=[120, 340])
    t.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2F2B6E')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#444444')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#EEEEEE')),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Scan History
    elements.append(Paragraph(f"Wound Scan History ({len(photos)} scans)", heading_style))
    if photos:
        header = ["#", "Date", "AI Risk", "Score", "Redness", "Swelling", "Color Dev", "Doctor"]
        data = [header]
        for i, p in enumerate(photos):
            dt = p.upload_time.strftime('%d %b %Y') if p.upload_time else 'N/A'
            data.append([
                str(i + 1), dt, p.risk_level or 'N/A',
                f"{(p.risk_score or 0)*100:.0f}%",
                f"{(p.redness_index or 0):.0f}",
                f"{(p.swelling_score or 0):.0f}",
                f"{(p.color_deviation or 0):.0f}",
                (p.doctor_assessment or "Pending") if p.reviewed else "Pending"
            ])
        scan_table = Table(data, colWidths=[24, 70, 52, 45, 52, 52, 58, 55])
        style_cmds = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2F2B6E')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F7FF')]),
        ]
        # Color-code risk cells
        for i, p in enumerate(photos):
            rc = risk_colors.get(p.risk_level, colors.gray)
            style_cmds.append(('TEXTCOLOR', (2, i+1), (2, i+1), rc))
            style_cmds.append(('FONTNAME', (2, i+1), (2, i+1), 'Helvetica-Bold'))
            if p.reviewed and p.doctor_assessment:
                style_cmds.append(('TEXTCOLOR', (7, i+1), (7, i+1), risk_colors.get(p.doctor_assessment, colors.gray)))
                style_cmds.append(('FONTNAME', (7, i+1), (7, i+1), 'Helvetica-Bold'))
        scan_table.setStyle(TableStyle(style_cmds))
        elements.append(scan_table)
    else:
        elements.append(Paragraph("No scans recorded yet.", body_style))

    elements.append(Spacer(1, 12))

    # Latest recommendation
    if photos:
        latest = photos[-1]
        elements.append(Paragraph("Latest Recommendation", heading_style))
        from xml.sax.saxutils import escape as _esc
        elements.append(Paragraph(_esc(latest.recommendation or "Continue monitoring"), body_style))
        if latest.doctor_notes:
            elements.append(Spacer(1, 6))
            elements.append(Paragraph(f"<b>Doctor Notes:</b> {_esc(latest.doctor_notes)}", body_style))
        if latest.doctor_advice:
            elements.append(Paragraph(f"<b>Doctor Advice:</b> {_esc(latest.doctor_advice)}", body_style))
        if latest.followup_date:
            elements.append(Paragraph(f"<b>Next follow-up:</b> {_esc(latest.followup_date)}", body_style))

    # Footer
    elements.append(Spacer(1, 24))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#E8E7F0'), spaceAfter=8))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#AAAAAA'), alignment=TA_CENTER)
    elements.append(Paragraph("WoundWatch — Post-Surgical Wound Infection Detection System", footer_style))
    elements.append(Paragraph("This report is AI-generated. Always consult your healthcare provider.", footer_style))

    doc.build(elements)
    buf.seek(0)

    pname = (patient.name or phone).replace(' ', '_')
    filename = f"WoundWatch_Report_{pname}_{datetime.now().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(buf, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{filename}"'
    })

@app.get("/")
async def root():
    return {"app": "WoundWatch API", "version": "3.1.0", "docs": "/docs"}
