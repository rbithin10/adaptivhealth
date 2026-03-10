# app/schemas/ — Request & Response Schemas

Each file defines Pydantic schemas that control what data the API accepts (requests) and what it sends back (responses). Think of them as contracts — they make sure data is always in the right format before it reaches the database or the user.

## Files

| File | What It Validates |
|------|------------------|
| `__init__.py` | Exports all schemas for easy importing |
| `activity.py` | Activity session data — exercise type, duration, intensity |
| `alert.py` | Alert creation and display — severity, message, patient link |
| `food_analysis.py` | Food photo upload input and AI nutrition analysis output |
| `medical_history.py` | Medical history entries — conditions, dates, notes |
| `medication_reminder.py` | Reminder schedules, dosage info, adherence records |
| `message.py` | Chat message content, sender/receiver, timestamps, read status |
| `nl.py` | Natural-language AI coach requests and responses |
| `nutrition.py` | Meal logs — food name, calories, macros, portion size |
| `recommendation.py` | Health recommendation details — type, priority, description |
| `rehab.py` | Rehab programme structures, exercise lists, progress updates |
| `risk_assessment.py` | Risk prediction input features and output scores |
| `user.py` | User registration, login, profile updates, role info |
| `vital_signs.py` | Vital sign readings — heart rate, BP, SpO₂, temperature, weight |
