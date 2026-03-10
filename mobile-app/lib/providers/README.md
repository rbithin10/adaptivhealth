# providers/ — State Managers

These files keep track of important app-wide data (like who's logged in, what theme is active, and the latest health readings). When data changes, all screens that depend on it automatically refresh.

## Files

| File | Purpose |
|------|---------|
| `auth_provider.dart` | Tracks login status, stores the current user's profile, handles sign-in and sign-out |
| `chat_provider.dart` | Manages the list of chat messages with the AI health coach and the doctor messaging thread |
| `theme_provider.dart` | Remembers the user's theme choice (light, dark, or system default) and saves it between app launches |
| `vitals_provider.dart` | Holds the latest vital signs (heart rate, blood pressure, SpO2, etc.) and tells screens to update when new readings arrive |
