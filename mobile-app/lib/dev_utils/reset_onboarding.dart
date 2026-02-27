/*
Developer utility to reset onboarding flag for testing.

NOTE: Onboarding is now USER-SPECIFIC (stored per email address).
Each user account maintains their own onboarding completion status.

USAGE IN YOUR APP (for testing only):
import 'dev_utils/reset_onboarding.dart';
import 'screens/onboarding_screen.dart';

// Reset for a specific user
await clearOnboardingFlag('user@example.com');

// Or reset for all users
await clearOnboardingFlag();

ALTERNATIVE - Using Flutter DevTools:
1. Run your app in debug mode
2. Open Flutter DevTools
3. Go to "App" tab
4. Find "shared_preferences"
5. Delete keys starting with "onboarding_complete_"

ALTERNATIVE - Clear app data:
- Android: Settings > Apps > Adaptiv Health > Storage > Clear data
- iOS: Uninstall and reinstall the app
- Web: Clear browser local storage
*/

import 'package:shared_preferences/shared_preferences.dart';

// Note: The actual functions are now in onboarding_screen.dart
// This file exists as documentation for developers
