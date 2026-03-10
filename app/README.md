# app/ — Backend Application Package

The core Python backend for AdaptivHealth, built with FastAPI. Handles user authentication, vital signs tracking, AI risk assessment, messaging, rehab programmes, and more.

## Folder Structure

| Folder | Purpose |
|--------|---------|
| `api/` | API route handlers — one file per feature area (auth, vitals, alerts, etc.) |
| `models/` | SQLAlchemy database models — define the database tables and their columns |
| `schemas/` | Pydantic validation schemas — define what data the API accepts and returns |
| `services/` | Business logic — ML predictions, anomaly detection, encryption, email, etc. |

## Root Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package initialiser with project metadata |
| `main.py` | FastAPI app entry point — creates the app, registers routes, sets up CORS |
| `config.py` | Environment configuration — database URLs, JWT secrets, API keys, feature flags |
| `database.py` | Database connection setup — SQLAlchemy engine, session factory, table creation |
| `rate_limiter.py` | Request rate limiting — prevents abuse by limiting how often endpoints can be called |
