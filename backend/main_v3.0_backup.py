from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from datetime import datetime
import os, shutil, json
from dotenv import load_dotenv

load_dotenv()

from database import init_db, get_db, Patient, Doctor, WoundPhoto, OTPRecord, Notification
from wound_analyzer import analyze_wound, validate_wound_image, generate_heatmap
from otp_service import send_otp as send_otp_svc, verify_otp as verify_otp_svc

app = FastAPI(title="WoundWatch API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
init_db()

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
        # Delete the invalid file
        os.remove(filepath)
        raise HTTPException(status_code=400, detail=validation["reason"])
    # =====================================================

    result = analyze_wound(filepath)

    # Generate heatmap overlay
    heatmap_path = os.path.join("uploads", f"heatmap_{filename}")
    generate_heatmap(filepath, heatmap_path)

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
        notif = Notification(
            target_phone=patient.doctor_id if patient else "",
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

@app.get("/api/patient-history/{phone}")
async def get_history(phone: str, db: Session = Depends(get_db)):
    photos = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.desc()).all()
    return [
        {
            "id": p.id, "filename": p.filename, "upload_time": str(p.upload_time),
            "risk_level": p.risk_level, "risk_score": p.risk_score,
            "redness_index": p.redness_index, "swelling_score": p.swelling_score,
            "color_deviation": p.color_deviation, "recommendation": p.recommendation,
            "doctor_notes": p.doctor_notes, "reviewed": p.reviewed
        }
        for p in photos
    ]

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
            "latest_upload": str(latest.upload_time) if latest else "",
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
    photos = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.asc()).all()
    return {
        "patient": {
            "phone": patient.phone, "name": patient.name, "age": patient.age,
            "gender": patient.gender, "surgery_type": patient.surgery_type,
            "surgery_date": patient.surgery_date
        },
        "photos": [
            {
                "id": p.id, "filename": p.filename, "upload_time": str(p.upload_time),
                "risk_level": p.risk_level, "risk_score": p.risk_score,
                "redness_index": p.redness_index, "swelling_score": p.swelling_score,
                "color_deviation": p.color_deviation, "recommendation": p.recommendation,
                "doctor_notes": p.doctor_notes, "reviewed": p.reviewed
            }
            for p in photos
        ]
    }

@app.post("/api/doctor-notes")
async def add_doctor_notes(
    photo_id: int = Form(...), notes: str = Form(...), db: Session = Depends(get_db)
):
    photo = db.query(WoundPhoto).filter(WoundPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    photo.doctor_notes = notes
    photo.reviewed = True
    photo.reviewed_at = datetime.utcnow()
    db.commit()
    # Notify patient
    notif = Notification(
        target_phone=photo.patient_phone, target_type="patient",
        title="Doctor Review",
        message=f"Your doctor has reviewed your wound photo and added notes."
    )
    db.add(notif)
    db.commit()
    return {"success": True, "message": "Notes saved"}

# ==================== NOTIFICATIONS ====================

@app.get("/api/notifications/{phone}")
async def get_notifications(phone: str, target_type: str = "patient", db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(
        Notification.target_phone == phone, Notification.target_type == target_type
    ).order_by(Notification.created_at.desc()).limit(20).all()
    return [
        {"id": n.id, "title": n.title, "message": n.message, "read": n.read, "created_at": str(n.created_at)}
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
        "total_patients": total_patients, "total_photos": total_photos,
        "red": red, "yellow": yellow, "green": green,
        "unreviewed": unreviewed,
        "alert_rate": round(red / total_photos * 100, 1) if total_photos > 0 else 0
    }

# ==================== EMERGENCY SOS ====================

@app.post("/api/sos")
async def emergency_sos(
    phone: str = Form(...), message: str = Form("Emergency! Patient needs immediate attention."),
    db: Session = Depends(get_db)
):
    """Emergency SOS — patient alerts their doctor instantly"""
    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    pname = patient.name or phone

    # Get latest wound photo for context
    latest = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.desc()).first()
    latest_info = ""
    if latest:
        latest_info = f" | Latest scan: {latest.risk_level} ({latest.risk_score:.0%}) at {latest.upload_time.strftime('%d %b %I:%M %p')}"

    # Create EMERGENCY notification for the doctor
    notif = Notification(
        target_phone=patient.doctor_id if patient.doctor_id else "DOC001",
        target_type="doctor",
        title="🚨 EMERGENCY SOS",
        message=f"Patient {pname} ({phone}) triggered SOS! \"{message}\"{latest_info}"
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

    return {"success": True, "message": "Emergency SOS sent to your doctor", "doctor_id": patient.doctor_id or "DOC001"}

# ==================== PDF REPORT ====================

@app.get("/api/report/{phone}")
async def generate_report(phone: str, db: Session = Depends(get_db)):
    """Generate a PDF wound history report for a patient"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from fastapi.responses import FileResponse
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    patient = db.query(Patient).filter(Patient.phone == phone).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    photos = db.query(WoundPhoto).filter(WoundPhoto.patient_phone == phone).order_by(WoundPhoto.upload_time.desc()).all()

    pdf_path = os.path.join("uploads", f"report_{phone}.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title2', parent=styles['Title'], fontSize=22, textColor=colors.HexColor('#2F2B6E'), spaceAfter=6)
    subtitle_style = ParagraphStyle('Sub', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#8C8AAE'), spaceAfter=16)
    heading_style = ParagraphStyle('H2', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2F2B6E'), spaceBefore=16, spaceAfter=8)
    normal_style = ParagraphStyle('Norm', parent=styles['Normal'], fontSize=10, spaceAfter=4)
    small_style = ParagraphStyle('Small', parent=styles['Normal'], fontSize=8, textColor=colors.gray)

    elements = []

    # Header
    elements.append(Paragraph("WoundWatch Report", title_style))
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y, %I:%M %p')}", subtitle_style))

    # Patient Info
    elements.append(Paragraph("Patient Information", heading_style))
    pdata = [
        ['Name', patient.name or 'N/A', 'Phone', patient.phone],
        ['Age', str(patient.age or 'N/A'), 'Gender', patient.gender or 'N/A'],
        ['Surgery', patient.surgery_type or 'N/A', 'Date', patient.surgery_date or 'N/A'],
    ]
    ptable = Table(pdata, colWidths=[70, 140, 70, 140])
    ptable.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2F2B6E')),
        ('TEXTCOLOR', (2, 0), (2, -1), colors.HexColor('#2F2B6E')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8E7F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7F6FB')),
    ]))
    elements.append(ptable)

    # Summary Stats
    elements.append(Paragraph("Summary", heading_style))
    total = len(photos)
    red_count = sum(1 for p in photos if p.risk_level == 'RED')
    yellow_count = sum(1 for p in photos if p.risk_level == 'YELLOW')
    green_count = sum(1 for p in photos if p.risk_level == 'GREEN')
    reviewed_count = sum(1 for p in photos if p.reviewed)

    sdata = [
        ['Total Uploads', str(total), 'Reviewed', str(reviewed_count)],
        ['🟢 Green', str(green_count), '🟡 Yellow', str(yellow_count)],
        ['🔴 Red (Alerts)', str(red_count), 'Latest Risk', photos[0].risk_level if photos else 'N/A'],
    ]
    stable = Table(sdata, colWidths=[100, 110, 100, 110])
    stable.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E8E7F0')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7F6FB')),
    ]))
    elements.append(stable)

    # Photo History
    elements.append(Paragraph("Wound Photo History", heading_style))
    for p in photos:
        risk_color = '#D64545' if p.risk_level == 'RED' else '#E89B2C' if p.risk_level == 'YELLOW' else '#2BA84A'
        upload_dt = p.upload_time.strftime('%d %b %Y, %I:%M %p') if p.upload_time else 'N/A'

        elements.append(Paragraph(
            f'<font color="{risk_color}"><b>{p.risk_level}</b></font> — {upload_dt} — '
            f'Score: {(p.risk_score*100):.0f}% | Redness: {p.redness_index:.0f} | Swelling: {p.swelling_score:.0f}',
            normal_style
        ))

        # Add wound image if exists
        img_path = os.path.join("uploads", p.filename)
        if os.path.exists(img_path):
            try:
                rl_img = RLImage(img_path, width=120, height=90)
                elements.append(rl_img)
            except Exception:
                pass

        elements.append(Paragraph(f"Recommendation: {p.recommendation}", small_style))

        if p.reviewed and p.doctor_notes:
            elements.append(Paragraph(f'<font color="#2BA84A"><b>Doctor Notes:</b></font> {p.doctor_notes}', normal_style))

        elements.append(Spacer(1, 8))

    # Footer
    elements.append(Spacer(1, 20))
    elements.append(Paragraph(
        '<font color="#8C8AAE">This report is AI-generated and should not replace professional medical advice. '
        'Please consult your doctor for diagnosis and treatment.</font>',
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER)
    ))

    doc.build(elements)
    return FileResponse(pdf_path, filename=f"WoundWatch_Report_{patient.name or phone}.pdf", media_type="application/pdf")

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
        "emergency": "Go to ER immediately if: heavy bleeding that won't stop, fever above 102°F, severe pain not relieved by medicine, wound opening up, or red streaks spreading from wound.",
        "default": "I can help with: pain management, fever concerns, redness monitoring, medicine schedule, diet tips, bathing care, wound discharge, stitches care, exercise limits, and emergency signs. What would you like to know?"
    },
    "hi": {
        "pain": "सर्जरी के बाद 3-5 दिन तक हल्का दर्द सामान्य है। निर्धारित दर्द निवारक लें। अगर दर्द अचानक बढ़े या धड़के, तो डॉक्टर से संपर्क करें।",
        "fever": "1-2 दिन तक हल्का बुखार (99°F/37.2°C तक) सामान्य है। अगर बुखार 100.4°F/38°C से ऊपर जाए या 48 घंटे से ज्यादा रहे, तो डॉक्टर को दिखाएं।",
        "redness": "घाव के आसपास कुछ लालिमा सामान्य है। अगर लालिमा घाव के किनारे से 2 सेमी से ज्यादा फैले या गर्म लगे, तो संक्रमण हो सकता है।",
        "medicine": "सभी एंटीबायोटिक्स निर्धारित अनुसार लें, भले ही आप बेहतर महसूस करें। खुराक न छोड़ें। पेट खराबी से बचने के लिए दर्द निवारक खाने के साथ लें।",
        "diet": "ठीक होने के लिए प्रोटीन युक्त भोजन (अंडे, दाल, चिकन, पनीर) खाएं। रोज 8+ गिलास पानी पिएं। 1 सप्ताह तक मसालेदार और तैलीय भोजन से बचें।",
        "bath": "48 घंटे तक घाव को सूखा रखें। उसके बाद शावर ले सकते हैं पर भिगोएं नहीं। धीरे से थपथपाकर सुखाएं। घाव पर सीधे साबुन न लगाएं।",
        "discharge": "साफ या हल्का पीला स्राव सामान्य है। अगर स्राव गाढ़ा, हरा, बदबूदार या बढ़ रहा है, तो तुरंत डॉक्टर को दिखाएं।",
        "stitches": "टांके न खींचें और न खुजलाएं। आमतौर पर 7-14 दिनों में निकाले जाते हैं। क्षेत्र साफ और सूखा रखें।",
        "exercise": "2-4 सप्ताह तक भारी सामान न उठाएं। पहले दिन से हल्की सैर की सलाह दी जाती है।",
        "emergency": "तुरंत ER जाएं अगर: भारी रक्तस्राव जो रुके नहीं, 102°F से ऊपर बुखार, दवा से राहत न मिलने वाला तेज दर्द, घाव खुल रहा हो।",
        "default": "मैं इनमें मदद कर सकता हूं: दर्द, बुखार, लालिमा, दवाई, खानपान, नहाना, स्राव, टांके, व्यायाम, आपातकाल। क्या जानना चाहेंगे?"
    },
    "od": {
        "pain": "ଅପରେସନ ପରେ ୫-୭ ଦିନ ହାଲୁକା ଯନ୍ତ୍ରଣା ସ୍ୱାଭାବିକ। ଡାକ୍ତର ଦେଇଥିବା ଔଷଧ ଖାଇନ୍ତୁ। ଯଦି ଯନ୍ତ୍ରଣା ହଠାତ୍ ବଢ଼ିଯାଇ, ଡାକ୍ତରଙ୍କୁ କୁହନ୍ତୁ।",
        "fever": "୧-୨ ଦିନ ହାଲୁକା ଜ୍ୱର (99°F ପର୍ଯ୍ଣନ୍ତ) ସ୍ୱାଭାବିକ। ଯଦି ଜ୍ୱର 100.4°F ଉପରେ ଯାଇ, ଡାକ୍ତରଙ୍କୁ ଦେଖାନ୍ତୁ।",
        "redness": "ଘା ଚାରିପଟେ ଅଳ୍ପ ଲାଲ ହେବା ସ୍ୱାଭାବିକ। ଯଦି ଲାଲ 2 ସେମି ରୁ ବେଶି ବିସ୍ତାର ହୁଇ, ସଙ୍କ୍ରମଣ ହୋଇପାରେ।",
        "medicine": "ସବୁ ଆଣ୍ଟିବାୟୋଟିକ ନିୟମିତ ଖାଇନ୍ତୁ। ଭଲ ଲାଗିଲେ ମଧ୍ୟ ବନ୍ଦ କରନ୍ତୁ ନାହିଁ।",
        "diet": "ଭଲ ହେବା ପାଇଁ ପ୍ରୋଟିନ ଯୁକ୍ତ ଖାଦ୍ୟ ଖାଇନ୍ତୁ - ଅଣ୍ଡା, ଡାଲି, ମାଛ। ଦିନକୁ ୮ ଗ୍ଲାସରୁ ବେଶି ପାଣି ପିଅନ୍ତୁ।",
        "bath": "48 ଘଣ୍ଟା ପର୍ଯ୍ଣନ୍ତ ଘା ଶୁଖିଲା ରଖନ୍ତୁ। ତା ପରେ ସ୍ନାନ କରିପାରିବେ, କିନ୍ତୁ ଘା ଭିଜାନ୍ତୁ ନାହିଁ।",
        "discharge": "ସଫା କିମ୍ବା ହାଲୁକା ହଳଦିଆ ସ୍ରାବ ସ୍ୱାଭାବିକ। ଯଦି ସ୍ରାବ ସବୁଜ, ଦୁର୍ଗନ୍ଧ, ବା ବଢ଼ୁଥି, ତୁରନ୍ତ ଡାକ୍ତରଙ୍କୁ ଦେଖାନ୍ତୁ।",
        "stitches": "ଟାଙ୍କା ଟାଣନ୍ତୁ ନାହିଁ। ସାଧାରଣତଃ 7-14 ଦିନରେ ବାହାର କରାଯାଇ।",
        "exercise": "2-4 ସପ୍ତାହ ପର୍ଯ୍ଣନ୍ତ ଭାରୀ ଜିନିଷ ଉଠାନ୍ତୁ ନାହିଁ। ପ୍ରଥମ ଦିନଠାରୁ ହାଲୁକା ଚାଲିବା ଭଲ।",
        "emergency": "ତୁରନ୍ତ ଡାକ୍ତରଖାନା ଯାଇନ୍ତୁ ଯଦି: ରକ୍ତସ୍ରାବ ବନ୍ଦ ହେଉନାହିଁ, 102°F ଉପରେ ଜ୍ୱର, ଅସହ୍ୟ ଯନ୍ତ୍ରଣା, ଘା ଖୋଲିଯାଉଥି।",
        "default": "ମୁଁ ସାହାଯ୍ୟ କରିପାରିବି: ଯନ୍ତ୍ରଣା, ଜ୍ୱର, ଲାଲ, ଔଷଧ, ଖାଦ୍ୟ, ସ୍ନାନ, ସ୍ରାବ, ଟାଙ୍କା, ବ୍ୟାୟାମ, ଜରୁରୀ। କଣ ଜାଣିବାକୁ ଚାହାନ୍ତି?"
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

@app.get("/")
async def root():
    return {"app": "WoundWatch API", "version": "3.0.0", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
