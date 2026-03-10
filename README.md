# Adaptiv Health

A comprehensive cardiac-rehabilitation health monitoring platform with a **FastAPI backend**, **React clinician dashboard**, and **Flutter patient mobile app**.

---

## Overview

Adaptiv Health is a clinical-grade health monitoring system designed for:
- **Patients** — Track heart rate, blood pressure, nutrition, rehab progress, and recovery via the mobile app
- **Clinicians** — Monitor patients, assess risk, manage alerts, and message patients via the web dashboard
- **Backend** — Secure data management with ML-powered risk prediction, anomaly detection, and AI coaching

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Flutter 3.13+
- PostgreSQL 12+

### 1. Configure Environment
```bash
cp .env.example .env        # Edit with your database URL, secret key, etc.
cp web-dashboard/.env.example web-dashboard/.env
```

### 2. Start the Backend
```bash
pip install -r requirements.txt
python start_server.py
```
Backend runs on `http://localhost:8080`. API docs at `/docs`.

### 3. Start the Web Dashboard
```bash
cd web-dashboard
npm install
npm start
```
Dashboard runs on `http://localhost:3000`.

### 4. Start the Mobile App
```bash
cd mobile-app
flutter pub get
flutter run
```

---

## Features

### Patient Mobile App (Flutter) — 16 Screens
- Real-time heart rate monitoring with animated ring display
- Vital signs tracking (SpO2, blood pressure, HRV)
- AI-powered health recommendations and coaching
- Guided workout sessions with HR zone management
- Recovery scoring and breathing exercises
- Nutrition tracking and recipe library
- Rehab programme management
- Device pairing (BLE) and health platform integrations (Fitbit, Apple Health, Google Fit)
- Doctor messaging with read receipts
- Dark mode support
- Onboarding flow and notifications

### Clinician Web Dashboard (React) — 8 Pages
- Patient roster with search and filtering
- Individual patient vitals, history, and medical profile
- Risk assessment with ML prediction explainability
- Advanced ML panel (anomaly detection, trend forecasting)
- Alert management and clinical recommendations
- Patient-clinician messaging
- Admin panel (user management)
- Professional medical UI (WCAG 2.1 AA compliant)

### Backend API (FastAPI) — 16 Route Modules
- JWT authentication with token refresh and blocklist
- Vital signs recording and retrieval
- ML risk prediction with explainability
- Anomaly detection and trend forecasting
- Natural language AI coaching endpoints
- Nutrition tracking and food analysis
- Rehab programme management
- Patient-clinician messaging
- Activity tracking and alerts
- Medical history and consent management
- Medication reminders
- Rate limiting and CORS

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Patient (Mobile)                       │
│  Flutter App — 16 screens, BLE, Fitbit, health APIs     │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS (JWT Auth)
┌────────────────────▼────────────────────────────────────┐
│                  Backend (FastAPI)                       │
│  16 API modules, 14 DB models, 11 services              │
│  Database: PostgreSQL  │  ML: scikit-learn / TFLite      │
└────────────────────┬────────────────────────────────────┘
                     │ HTTPS (JWT Auth)
┌────────────────────▼────────────────────────────────────┐
│              Clinician (Web Dashboard)                   │
│  React/TypeScript — 8 pages, MUI theme, Axios client    │
└─────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
AdaptivHealth/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # Application entry point
│   ├── config.py                 # Environment configuration
│   ├── database.py               # SQLAlchemy database setup
│   ├── rate_limiter.py           # Request rate limiting
│   ├── api/                      # Route handlers (16 modules)
│   ├── models/                   # SQLAlchemy models (14 files)
│   ├── schemas/                  # Pydantic schemas (14 files)
│   └── services/                 # Business logic & ML (16 files)
│
├── web-dashboard/                # React Clinician Dashboard
│   └── src/
│       ├── pages/                # 8 pages + tests
│       ├── components/           # Reusable UI components
│       ├── services/             # API client (Axios)
│       ├── theme/                # Colours, typography, MUI theme
│       └── types/                # TypeScript interfaces
│
├── mobile-app/                   # Flutter Patient App
│   └── lib/
│       ├── screens/              # 16 screens + home sub-widgets
│       ├── providers/            # State management (Provider)
│       ├── services/             # API, BLE, health, notifications
│       ├── widgets/              # Shared reusable widgets
│       └── theme/                # Design tokens
│
├── ml_models/                    # Trained ML model + training scripts
├── tests/                        # Backend test suite (34 test files, pytest)
├── migrations/                   # SQL migration scripts (14 files)
├── scripts/                      # DB setup, migration, deploy utilities
├── docs/                         # Technical documentation
│
├── .env.example                  # Environment variable template
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container build
├── start_server.py               # Server launcher
└── start.bat                     # Windows quick start
```

---

## API Endpoints

### Authentication
- `POST /auth/register` — Create account
- `POST /auth/login` — Login, returns JWT
- `POST /auth/refresh` — Refresh access token
- `POST /auth/request-password-reset` — Request password reset email
- `POST /auth/reset-password` — Reset password with token

### Vital Signs
- `GET /vitals/latest` — Current HR, SpO2, BP
- `GET /vitals/history` — Historical data (24h/7d/30d)
- `POST /vitals/submit` — Submit a reading

### Risk Prediction
- `POST /predictions/risk` — ML risk assessment with explainability

### Messaging
- `GET /messages/` — Conversation history
- `POST /messages/` — Send message

### Recommendations, Nutrition, Rehab, Alerts, Activity
- See full API docs at `http://localhost:8080/docs`

---

## Security

- JWT token authentication (HS256) with refresh and token blocklist
- NIST-approved password hashing (pbkdf2_sha256, 600k iterations)
- Optional AES-256-GCM encryption for PHI fields
- SQL injection prevention (SQLAlchemy ORM)
- CORS configuration and rate limiting
- HTTPS support (SSL certificates included for deployment)
- Secure token storage on mobile (flutter_secure_storage)

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| **Mobile App** | Flutter, Dart, Provider, Dio |
| **Web Dashboard** | React 18, TypeScript, MUI, Axios |
| **Backend** | FastAPI, Python, Pydantic |
| **Database** | PostgreSQL, SQLAlchemy |
| **ML** | scikit-learn, TensorFlow Lite |
| **Auth** | JWT (HS256), pbkdf2_sha256 |
| **Deployment** | Docker, Nginx, AWS RDS |

---

## Testing

```bash
# Backend tests
pytest

# Web dashboard tests
cd web-dashboard && npm test

# Flutter tests
cd mobile-app && flutter test
```

---

## Deployment

```bash
# Backend (Docker)
docker build -t adaptiv-health .
docker run -p 8080:8080 --env-file .env adaptiv-health

# Web dashboard
cd web-dashboard && npm run build
# Serve the build/ directory

# Mobile app
flutter build apk --release          # Android
flutter build appbundle --release     # Google Play
flutter build ios --release           # iOS
```

---

## Environment Variables

See [.env.example](.env.example) for all required and optional variables including:
- `DATABASE_URL` — PostgreSQL connection string
- `SECRET_KEY` — JWT signing secret
- `GEMINI_API_KEY` — Google Gemini for AI features
- `SMTP_*` — Email configuration for password resets
- `PHI_ENCRYPTION_KEY` — Optional field-level encryption

---

**Version**: 1.0.0
