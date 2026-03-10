# app/services/ — Business Logic & AI Services

This is where the heavy lifting happens. Each service file contains the logic that sits between the API routes and the database — processing data, running ML models, sending emails, encrypting messages, and more.

## Files

| File | What It Does |
|------|-------------|
| `__init__.py` | Package initialiser |
| `anomaly_detection.py` | Detects unusual patterns in a patient's vital signs (sudden spikes, drops) |
| `auth_service.py` | Handles password hashing, JWT token creation/verification, login logic |
| `baseline_optimization.py` | Calculates personalised "normal" baselines for each patient's vitals |
| `chat_service.py` | Powers the AI health coach — talks to the Gemini language model |
| `document_extraction.py` | Extracts health data from uploaded documents (PDFs, images) |
| `email_service.py` | Sends emails — password resets, notifications, verification links |
| `encryption.py` | Encrypts and decrypts sensitive message content |
| `explainability.py` | Explains ML predictions in plain language — "why is my risk score high?" |
| `ml_prediction.py` | Runs the cardiac risk prediction model and returns a score |
| `natural_language_alerts.py` | Turns raw clinical data into human-readable alert messages |
| `nl_builders.py` | Builds structured prompts for the natural-language AI coach |
| `recommendation_ranking.py` | Ranks and prioritises health recommendations for each patient |
| `rehab_service.py` | Manages rehab programme logic — phase progression, exercise assignment |
| `retraining_pipeline.py` | Re-trains the ML model with new patient data to keep predictions accurate |
| `trend_forecasting.py` | Projects future vital-sign trends based on historical readings |
