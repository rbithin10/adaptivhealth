# services/ — Backend Communication

This folder contains the code that talks to the backend server. All API calls go through here.

## Files

| File | Purpose |
|------|---------|
| `api.ts` | The main API client — handles login, user management, vital signs, risk assessments, alerts, messaging, medical profiles, ML features, and more. Automatically attaches the login token and handles session refresh. |
