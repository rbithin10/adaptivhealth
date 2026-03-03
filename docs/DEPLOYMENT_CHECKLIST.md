# AdaptivHealth — Deployment Checklist

> **Purpose**: Step-by-step guide for deploying AdaptivHealth to production (AWS).
> **Last updated**: March 2, 2026

---

## Pre-Deployment

### 1. Environment Variables

Copy `.env.example` to `.env` on the production server and set ALL required values:

| Variable | Required | Production Value |
|----------|----------|-----------------|
| `DATABASE_URL` | YES | `postgresql://user:pass@rds-host:5432/adaptivhealth` |
| `SECRET_KEY` | YES | Random 64+ char string (`openssl rand -hex 32`) |
| `ENVIRONMENT` | YES | `production` |
| `DEBUG` | YES | `false` |
| `PHI_ENCRYPTION_KEY` | YES | Base64-encoded 32-byte key (`python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"`) |
| `GEMINI_API_KEY` | Recommended | Google AI Studio key for document extraction |
| `SMTP_HOST` | Recommended | e.g., `smtp.sendgrid.net` |
| `SMTP_PORT` | Recommended | `587` |
| `SMTP_USERNAME` | Recommended | e.g., `apikey` (SendGrid) |
| `SMTP_PASSWORD` | Recommended | SendGrid API key or SMTP password |
| `SMTP_FROM_EMAIL` | Recommended | `noreply@adaptivhealth.com` |
| `FRONTEND_BASE_URL` | YES | `https://dashboard.adaptivhealth.com` |
| `PASSWORD_RESET_DEV_TOKEN_LOGGING` | YES | `false` (NEVER true in production) |
| `ALLOWED_ORIGINS` | YES | `["https://dashboard.adaptivhealth.com"]` |
| `AWS_ACCESS_KEY_ID` | If using S3 | IAM credentials |
| `AWS_SECRET_ACCESS_KEY` | If using S3 | IAM credentials |
| `AWS_REGION` | If using S3 | `me-central-1` |

### 2. Database Setup

```bash
# 1. Ensure PostgreSQL (RDS) is running and accessible
# 2. Run migration tracker setup + all pending migrations
python scripts/apply_migrations.py

# 3. Create admin account
python scripts/create_admin.py

# 4. Verify database health
python -c "from app.database import check_db_connection; print('OK' if check_db_connection() else 'FAIL')"
```

### 3. Security Checklist

- [ ] `ENVIRONMENT=production` is set (guards dev token logging, prevents DB drop)
- [ ] `DEBUG=false` (disables SQL echo logging)
- [ ] `SECRET_KEY` is unique, random, 64+ characters
- [ ] `PHI_ENCRYPTION_KEY` is set (AES-256-GCM for medical data)
- [ ] `PASSWORD_RESET_DEV_TOKEN_LOGGING=false`
- [ ] TrustedHostMiddleware has specific hosts (no `"*"`)
- [ ] CORS `ALLOWED_ORIGINS` lists only production frontend URL
- [ ] HTTPS enforced (ALB/CloudFront terminates TLS)
- [ ] `.env` file is NOT committed to git

---

## Backend Deployment (FastAPI)

### AWS EC2 / ECS

```bash
# Install dependencies
pip install -r requirements.txt

# Start with Uvicorn (production)
uvicorn app.main:app --host 0.0.0.0 --port 8080 --workers 4

# Or with Gunicorn + Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8080
```

### Health Check

```bash
# Backend health endpoint
curl https://api.adaptivhealth.com/api/v1/health
# Expected: {"status": "healthy", "database": "connected"}
```

### Post-Deploy Verification

- [ ] `GET /docs` returns Swagger UI
- [ ] `POST /api/v1/login` works with admin credentials
- [ ] `POST /api/v1/vitals` accepts vitals (authenticated)
- [ ] `POST /api/v1/predictions/risk` returns risk score
- [ ] Rate limits active: login (5/min), register (3/min), vitals (60/min)
- [ ] Password reset email sends (if SMTP configured)

---

## Web Dashboard Deployment (React)

### Build

```bash
cd web-dashboard

# Set production API URL
echo "REACT_APP_API_URL=https://api.adaptivhealth.com" > .env.production

# Build
npm ci
npm run build
```

### Deploy to S3 + CloudFront (or equivalent)

```bash
# Upload build/ to S3
aws s3 sync build/ s3://adaptivhealth-dashboard --delete

# Invalidate CloudFront cache (replace with your distribution ID from AWS Console → CloudFront → Distributions)
aws cloudfront create-invalidation --distribution-id "$CLOUDFRONT_DISTRIBUTION_ID" --paths "/*"
```

### Post-Deploy Verification

- [ ] Dashboard loads at `https://dashboard.adaptivhealth.com`
- [ ] Login works (clinician + admin accounts)
- [ ] Patient list loads with real data
- [ ] Patient detail page shows vitals, risk assessment, medical profile
- [ ] Password reset flow works end-to-end (request → email → reset page → new login)

---

## Mobile App Deployment (Flutter)

### Android (APK / AAB)

```bash
cd mobile-app

# Update API base URL in lib/services/api_client.dart
# Point to production: https://api.adaptivhealth.com

# Build release APK
flutter build apk --release

# Or build App Bundle for Play Store
flutter build appbundle --release
```

### iOS

```bash
cd mobile-app

# Build for iOS
flutter build ios --release

# Archive and upload via Xcode
open ios/Runner.xcworkspace
# Product → Archive → Distribute
```

### Post-Deploy Verification

- [ ] App installs and launches
- [ ] Registration + onboarding completes (7 steps)
- [ ] BLE device pairing works (Polar H10 or similar)
- [ ] Vitals appear on home screen
- [ ] Edge AI risk assessment runs locally (~10ms)
- [ ] Cloud sync uploads vitals every 15 minutes
- [ ] Notifications appear for threshold violations
- [ ] Messaging with clinician works

---

## Monitoring

### Logs

- Backend: `uvicorn` stdout/stderr → CloudWatch or log file
- Structured logging via `structlog` — filter by `logger` name

### Key Metrics to Watch

| Metric | Alert Threshold |
|--------|----------------|
| API response time (p95) | > 500ms |
| Error rate (5xx) | > 1% |
| Database connections | > 25 (pool_size=10, max_overflow=20) |
| Rate limit hits | Sudden spike = possible attack |
| Failed login attempts | > 50/hour = brute force |

---

## Rollback

```bash
# Backend: restart previous container/process
# Dashboard: deploy previous S3 build
aws s3 sync s3://adaptivhealth-dashboard-backup build/

# Database: migrations are additive (ALTER TABLE ADD)
# No destructive rollback needed for current migrations
```
