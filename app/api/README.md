# app/api/ — API Route Handlers

Each file in this folder defines a group of API endpoints for one feature area. Routes handle incoming requests, validate data, call the right service, and return responses.

## Files

| File | What It Does |
|------|-------------|
| `__init__.py` | Registers all route files with the main app |
| `activity.py` | Log and retrieve physical activity / exercise sessions |
| `advanced_ml.py` | Advanced machine-learning insights — risk timelines, feature importance, scenario analysis |
| `alert.py` | Create, list, and manage clinical alerts for patients |
| `auth.py` | Sign up, log in, log out, refresh tokens, reset passwords |
| `consent.py` | Patient consent management — grant, revoke, and check data-sharing permissions |
| `food_analysis.py` | Upload a food photo and get AI-powered nutritional breakdown |
| `medical_history.py` | Add and view a patient's medical history and conditions |
| `medication_reminder.py` | Set up and manage medication reminders and adherence tracking |
| `messages.py` | Secure messaging between patients and clinicians |
| `nl_endpoints.py` | Natural-language AI coach — chat with the health assistant |
| `nutrition.py` | Log meals, view nutrition summaries, and track daily intake |
| `predict.py` | Run the ML risk-prediction model and get a cardiac risk score |
| `rehab.py` | Cardiac rehab programme management — phases, exercises, progress |
| `user.py` | View and update user profiles, upload profile photos |
| `vital_signs.py` | Record and retrieve vital signs — heart rate, blood pressure, SpO₂, etc. |
