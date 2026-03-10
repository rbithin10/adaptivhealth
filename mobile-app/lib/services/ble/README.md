# ble/ — Bluetooth Low Energy

Handles connecting to Bluetooth medical devices like heart rate monitors, pulse oximeters, blood pressure cuffs, and thermometers.

## Files

| File | Purpose |
|------|---------|
| `ble_service.dart` | The main Bluetooth manager — scans for devices, connects, auto-reconnects, and receives live health data |
| `ble_health_parser.dart` | Translates raw Bluetooth data bytes into human-readable health values (heart rate in BPM, SpO2 percentage, etc.) |
| `ble_permission_handler.dart` | Asks the user for Bluetooth and location permissions (required by Android/iOS to use Bluetooth) |
