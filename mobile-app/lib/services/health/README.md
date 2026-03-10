# health/ — Phone Health Platform Integration

Reads and writes health data from the phone's built-in health system (Apple HealthKit on iPhone, Google Health Connect on Android).

## Files

| File | Purpose |
|------|---------|
| `health_service.dart` | Requests permission to access health data, reads heart rate and step history, and writes workout records back to the phone's health app |
