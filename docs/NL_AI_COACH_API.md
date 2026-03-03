# Natural Language AI Coach API

## Overview

AdaptivHealth uses a **Natural Language (NL) first** architecture.

- Primary path: deterministic NL builders convert model/clinical outputs into clear patient-facing text.
- Secondary path: Gemini is used only for gap-fill scenarios (open-ended chat, image analysis, or explicit cloud enhancement).

This preserves clinical consistency while still supporting flexible AI assistance.

---

## Architecture Policy

### 1) NL-first (default)
Used for core summaries and guidance:
- Risk summary
- Today’s workout guidance
- Alert explanation
- Progress summary

These responses are built from structured backend data (risk assessments, vitals, alerts, activity sessions, recommendations) and rendered using internal NL builder functions.

### 2) Gemini as gap-fill (optional)
Gemini is used when:
- User asks open-ended questions in chat that do not match a known NL intent.
- User uses image-based chat analysis.
- A caller explicitly requests cloud enhancement for advanced ML risk summary (`use_cloud_ai=true`).

---

## Route Map

## Base: `/api/v1/nl` (AI Coach)
Implemented in `app/api/nl_endpoints.py`, router prefix set in `app/main.py`.

### GET `/api/v1/nl/risk-summary`
- Purpose: Patient-friendly summary of latest risk + recent vitals/alerts.
- Source: NL builder (`build_risk_summary_text`) with real DB data.
- Auth: Required (`get_current_user`).

### GET `/api/v1/nl/todays-workout`
- Purpose: Daily workout explanation in plain language.
- Source: NL builder (`build_todays_workout_text`) + recommendation/risk context.
- Auth: Required.

### GET `/api/v1/nl/alert-explanation`
- Purpose: Explain why an alert happened and what to do next.
- Source: NL builder (`build_alert_explanation_text`) + alert/activity/vitals context.
- Auth: Required.

### GET `/api/v1/nl/progress-summary`
- Purpose: Motivational period-over-period progress interpretation.
- Source: NL builder (`build_progress_summary_text`) + trend computation.
- Auth: Required.

### POST `/api/v1/nl/chat`
- Purpose: Conversational AI coach.
- Source policy:
  1. Template NL response for known intents.
  2. Gemini fallback for unmatched/open-ended prompts.
  3. Generic fallback if Gemini unavailable.
- Auth: Required.
- Rate limit: 10 requests/min per user (in-memory limiter).

### POST `/api/v1/nl/chat-with-image`
- Purpose: Multimodal coaching analysis (food, medication, edema, general).
- Source: Gemini Vision.
- Auth: Required.
- Gemini key required: returns 503 if missing.

---

## Base: `/api/v1` (Advanced ML NL helpers)
Implemented in `app/api/advanced_ml.py`.

### GET `/api/v1/risk-summary/natural-language`
- Purpose: Clinician/dashboard plain-language summary of latest risk assessment.
- Default behavior: internal NL template (`format_risk_summary`).
- Optional cloud enhancement: `use_cloud_ai=true` attempts Gemini enhancement.
- If Gemini enhancement fails, endpoint gracefully falls back to internal NL summary.

### POST `/api/v1/alerts/natural-language`
- Purpose: Convert technical alert fields to patient-friendly phrasing.
- Source: internal template generator (`generate_natural_language_alert`).
- Note: This is deterministic NL output, not mandatory Gemini.

---

## What NL Makes Human-Interpretable

NL layer translates model/system outputs such as:
- `risk_score`, `risk_level`, `risk_factors_json`
- Vitals aggregates (HR, SpO2)
- Alert severity/context
- Activity adherence/progress trends
- Recommendation intensity and safe ranges

into short, readable coaching language for patients/clinicians.

This is exactly the “AI model output to human-interpretable explanation” role.

---

## Client Usage

### Mobile App
- Uses `/api/v1/nl/*` summaries and `/api/v1/nl/chat`.
- File: `mobile-app/lib/services/api_client.dart`
- UI entry point: floating coach chat (`mobile-app/lib/widgets/floating_chatbot.dart`).

### Web Dashboard
- Uses advanced ML NL endpoints in patient detail panel:
  - `/risk-summary/natural-language`
  - `/alerts/natural-language`
- Files:
  - `web-dashboard/src/services/api.ts`
  - `web-dashboard/src/pages/PatientDetailPage.tsx`

---

## Operational Notes

- Required for Gemini paths: `GEMINI_API_KEY` (aliases supported in config).
- Without Gemini key:
  - `/api/v1/nl/chat` still works for template-matched intents.
  - `/api/v1/nl/chat-with-image` returns 503.
  - `/api/v1/risk-summary/natural-language?use_cloud_ai=true` falls back to template summary.

---

## Summary

AdaptivHealth NL is **not** Gemini takeover.

- Core coaching interpretation is provided by internal NL logic over your model outputs.
- Gemini is a controlled augmentation layer for conversational/image gaps and optional enhancement.
