# test/ — Automated Tests

Tests that verify the app works correctly. Run them with:

```bash
flutter test
```

## Files

| File | Purpose |
|------|---------|
| `widget_test.dart` | Basic smoke test — checks the app starts without crashing |
| `dark_mode_test.dart` | Verifies dark mode colors, theme switching, and accessibility contrast ratios |
| `cloud_sync_service_test.dart` | Tests the cloud sync logic — queuing, retry, and conflict resolution |

## Subfolders

| Folder | Purpose |
|--------|---------|
| `screens/` | Tests for individual screens — checks that buttons, forms, and navigation work correctly |
