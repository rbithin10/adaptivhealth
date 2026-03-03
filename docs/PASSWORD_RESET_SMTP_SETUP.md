# Password Reset SMTP Setup

Production setup guide for password reset email delivery in AdaptivHealth backend.

## What changed

- `POST /api/v1/reset-password` now sends reset emails through SMTP when configured.
- Response remains enumeration-safe and always returns:
  - `{"message": "If the email exists, a reset link has been sent"}`
- Reset tokens are never returned in API responses.
- Dev fallback token logging is available only when explicitly enabled.

## Required environment variables

Add these to the backend `.env`:

- `SMTP_HOST` (example: `smtp.sendgrid.net`)
- `SMTP_PORT` (usually `587` for STARTTLS or `465` for SSL)
- `SMTP_USERNAME` (SendGrid SMTP uses `apikey`)
- `SMTP_PASSWORD` (SendGrid API key, or SMTP password)
- `SMTP_FROM_EMAIL` (verified sender)
- `SMTP_FROM_NAME` (optional, default: `Adaptiv Health`)
- `SMTP_USE_TLS` (`true` for port 587)
- `SMTP_USE_SSL` (`false` for STARTTLS, `true` for 465)
- `FRONTEND_BASE_URL` (example: `https://app.example.com`)
- `PASSWORD_RESET_PATH` (default: `/reset-password`)
- `PASSWORD_RESET_DEV_TOKEN_LOGGING` (`false` in production)

## SendGrid (SMTP-compatible) example

```env
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=SG.xxxxxxxxxxxxxxxxxxxxx
SMTP_FROM_EMAIL=no-reply@yourdomain.com
SMTP_FROM_NAME=Adaptiv Health
SMTP_USE_TLS=true
SMTP_USE_SSL=false

FRONTEND_BASE_URL=https://adaptivhealth.example.com
PASSWORD_RESET_PATH=/reset-password
PASSWORD_RESET_DEV_TOKEN_LOGGING=false
```

## Reset link contract

Backend generates links as:

`{FRONTEND_BASE_URL}{PASSWORD_RESET_PATH}?token=<jwt>`

Example:

`https://adaptivhealth.example.com/reset-password?token=eyJ...`

## Development fallback behavior

If SMTP is not configured:

- API still returns safe generic success message.
- Token logging occurs only when `PASSWORD_RESET_DEV_TOKEN_LOGGING=true`.
- Recommended local-only setup:

```env
PASSWORD_RESET_DEV_TOKEN_LOGGING=true
```

Never enable this in production.

## Troubleshooting

### 1) No email received

- Verify `SMTP_FROM_EMAIL` is a verified sender/domain in your provider.
- Confirm `SMTP_USERNAME` and `SMTP_PASSWORD` are valid.
- Check provider blocks/rate limits and spam folder.

### 2) TLS/SSL handshake errors

- Use `SMTP_PORT=587` with `SMTP_USE_TLS=true` and `SMTP_USE_SSL=false`.
- Use `SMTP_PORT=465` with `SMTP_USE_SSL=true` and `SMTP_USE_TLS=false`.
- Do not enable both SSL and TLS simultaneously.

### 3) Reset link opens wrong frontend

- Verify `FRONTEND_BASE_URL` and `PASSWORD_RESET_PATH` values.
- Ensure your frontend route matches the path exactly.

### 4) Need local testing without SMTP

- Leave SMTP vars unset.
- Set `PASSWORD_RESET_DEV_TOKEN_LOGGING=true`.
- Use token from backend logs for `POST /api/v1/reset-password/confirm`.

## Verification checklist

- Request reset for an existing user (`POST /api/v1/reset-password`).
- Confirm inbox receives an email with tokenized reset link.
- Open reset link and submit new password using existing confirm flow.
- Verify old password fails and new password succeeds.
- Verify endpoint response never includes token.
