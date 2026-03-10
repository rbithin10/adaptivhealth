# services/ — Backend & Device Services

These files handle communication with the server, Bluetooth devices, health platforms, and on-device AI. They do the "behind the scenes" work so screens can just display the data.

## Files

| File | Purpose |
|------|---------|
| `api_client.dart` | Talks to the backend server — sends login requests, fetches vitals, posts alerts, etc. |
| `chat_store.dart` | Stores chat messages in memory for the AI coach conversation |
| `alert_polling_service.dart` | Periodically checks the server for new health alerts or notifications |
| `notification_service.dart` | Schedules and displays local push notifications on the device |
| `medication_reminder_service.dart` | Manages medication reminder schedules and sends timely notifications |
| `mock_vitals_service.dart` | Generates fake health readings for testing when no real device is connected |
| `cloud_sync_service.dart` | Syncs locally stored health data with the cloud server when internet is available |
| `edge_ai_store.dart` | Manages the on-device AI system — loads the ML model, runs predictions, stores results |
| `edge_alert_service.dart` | Checks vital signs against safety thresholds and triggers alerts if something is wrong |
| `edge_ml_service.dart` | Runs the TensorFlow Lite machine learning model on the device for risk prediction |
| `gps_location_service.dart` | Gets the user's GPS location for emergency SOS alerts |

## Subfolders

| Folder | Purpose |
|--------|---------|
| `ble/` | Bluetooth Low Energy — connects to heart rate monitors, blood pressure cuffs, and other medical devices |
| `fitbit/` | Fitbit integration — pulls step count, heart rate, and sleep data from Fitbit's API |
| `health/` | Apple HealthKit and Google Health Connect integration — reads/writes health data from the phone's built-in health app |
