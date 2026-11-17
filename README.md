# WoundWatch v3 - Separate Patient & Doctor Apps

## Architecture
```
Backend (FastAPI)     → localhost:8000
Patient App (React)   → localhost:3000  (mobile-first PWA)
Doctor Dashboard (React) → localhost:3001  (desktop-first)
```

## Quick Start (Windows)

### Terminal 1 - Backend:
```
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn main:app --reload --port 8000
```

### Terminal 2 - Patient App:
```
cd patient-app
npm install
npm start
```

### Terminal 3 - Doctor Dashboard:
```
cd doctor-app
npm install
set PORT=3001 && npm start
```

## Access
- Patient App: http://localhost:3000 (Demo OTP: 1234)
- Doctor Dashboard: http://localhost:3001 (ID: DOC001, Pass: demo123)
- API Docs: http://localhost:8000/docs

## Patient App Features
- Phone OTP login
- Profile setup (name, age, surgery type)
- Upload wound photo with camera
- AI wound analysis (OpenCV LAB color)
- History with risk score chart
- Trilingual chatbot (EN/HI/OD)
- Notification center
- Emergency SOS button
- Mobile-first bottom navigation

## Doctor Dashboard Features
- Doctor ID/password login
- Stats overview (patients, scans, alerts)
- Risk distribution bar chart
- Patient list with risk filtering & search
- Patient detail page with photo timeline
- Risk score trend chart
- Add notes to patient photos
- Notification system (RED risk alerts)
- Desktop sidebar navigation
"# WoundWatch-" 
