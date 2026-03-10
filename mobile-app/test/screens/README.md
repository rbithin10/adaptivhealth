# screens/ — Screen Tests

Widget tests for individual app screens. Each test creates the screen, interacts with it, and verifies the expected behavior.

## Files

| File | Purpose |
|------|---------|
| `core_tabs_smoke_test.dart` | Checks that the main tab bar navigation (Home, Health, Profile, etc.) loads without errors |
| `home_screen_test.dart` | Tests the home dashboard — verifies vitals display, quick actions, and AI recommendations render |
| `login_screen_test.dart` | Tests the login form — email/password validation, error messages, and successful sign-in flow |
| `onboarding_screen_test.dart` | Tests the health profile wizard — step navigation, form fields, and completion |
