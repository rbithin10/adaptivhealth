# app/models/ — Database Models

Each file here defines one or more database tables using SQLAlchemy. These models describe the shape of the data stored in PostgreSQL — columns, types, and relationships between tables.

## Files

| File | What It Stores |
|------|---------------|
| `__init__.py` | Imports all models so the database knows about every table |
| `activity.py` | Exercise and activity sessions — type, duration, calories burned |
| `alert.py` | Clinical alerts — e.g. "heart rate too high" or "missed medication" |
| `auth_credential.py` | Login credentials — hashed passwords and password-reset tokens |
| `medical_history.py` | Past medical conditions, surgeries, family history |
| `medication_adherence.py` | Medication reminders and whether the patient took them on time |
| `message.py` | Chat messages between patients and clinicians |
| `nutrition.py` | Daily food/nutrition log entries |
| `recommendation.py` | AI-generated health recommendations for each patient |
| `rehab.py` | Cardiac rehab programmes, phases, exercises, and progress logs |
| `risk_assessment.py` | ML risk-prediction results — score, contributing factors, timestamps |
| `token_blocklist.py` | Revoked JWT tokens — prevents logged-out tokens from being reused |
| `user.py` | User accounts — name, email, role (patient / clinician / admin), profile info |
| `vital_signs.py` | Recorded vitals — heart rate, blood pressure, oxygen level, temperature, etc. |
