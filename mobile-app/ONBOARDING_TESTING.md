# Onboarding Testing Guide

## Problem Fixed ✅

**ROOT CAUSE:** The onboarding flag was stored device-wide, not per-user. If anyone completed onboarding on the device, new users wouldn't see it.

**SOLUTION:** Onboarding is now **user-specific** - stored per email address. Each account maintains its own onboarding completion status.

The onboarding flow has been enhanced with:
1. ✅ **User-specific onboarding state** (stored as `onboarding_complete_user@example.com`)
2. ✅ Debug logging to trace the onboarding state
3. ✅ Developer utility to reset onboarding flag for testing
4. ✅ Error handling and fallback behavior

## How to Test Onboarding

### Method 1: Create a Fresh Account (RECOMMENDED FOR TESTING THE FIX)

1. Run the app: `flutter run`
2. Click **"Create Account"** / **"Register"**
3. Fill in the registration form with a **NEW email address**
4. Submit registration
5. Log in with the new account
6. **✅ Onboarding should now appear!**

### Method 2: Using the Developer Utility

1. Run the app: `flutter run`
2. Log in with any account
3. Navigate to **Profile** screen (bottom tab)
4. Scroll down to find **"Developer Utilities (DEV ONLY)"** section
5. Tap **"Reset Onboarding"** button
6. Log out
7. Log back in → Onboarding should now appear!

### Method 3: Clear App Data

**Android:**
- Settings > Apps > Adaptiv Health > Storage > Clear data

**iOS:**
- Uninstall and reinstall the app

**Web (Chrome/Edge):**
1. Open Developer Tools (F12)
2. Application tab > Local Storage
3. Clear all storage
4. Refresh page

**Flutter DevTools:**
1. Run app in debug mode
2. Open Flutter DevTools
3. Go to "App" tab
4. Find "shared_preferences"
5. Delete the "onboarding_complete" key

## Debug Output Explained

When you run the app with `flutter run`, you'll see debug output in the terminal:

```
DEBUG: Onboarding completed: false
DEBUG: Will show onboarding: true
DEBUG: State updated - isLoggedIn: true, showOnboarding: true
DEBUG BUILD: Showing OnboardingScreen
```

This tells you:
- Whether onboarding was previously completed
- Whether onboarding will be shown
- Which screen is being displayed

If you see:
```
DEBUG: Onboarding completed: true
DEBUG: Will show onboarding: false
DEBUG BUILD: Showing HomeScreen
```

It means the user has already completed onboarding. Use the "Reset Onboarding" button in Profile screen.

## Common Issues

### Issue: "Onboarding still not showing after reset"

**Solution:** Make sure you log out and log back in after resetting. The onboarding check only happens during login.

### Issue: "I don't see the Developer Utilities section"

**Solution:** Make sure you're on the Profile screen (bottom navigation tab, rightmost icon).

### Issue: "The app closes immediately after login"

**Solution:** Check the terminal for error messages. There might be a critical issue with the API or network.

## For Production Builds

The "Developer Utilities" section and all debug print statements should be:
1. Wrapped in `kDebugMode` checks, OR
2. Removed before releasing to production

Example:
```dart
if (kDebugMode) {
  print('DEBUG: Onboarding completed: $completed');
}
```

This ensures debug output doesn't appear in production builds.

## Technical Details

### Onboarding State Storage

- **Storage:** `SharedPreferences` (local device storage)
- **Key Pattern:** `onboarding_complete_{email}` (e.g., `onboarding_complete_john@example.com`)
- **Value:** `true` (completed) or missing (not completed)
- **Scope:** Per-user (each email has its own completion state)

### Why User-Specific?

Previously, onboarding was device-wide. If User A completed onboarding, User B logging in on the same device wouldn't see it. Now each user account has its own onboarding state.

**Example:**
- User `alice@example.com` completes onboarding → Key `onboarding_complete_alice@example.com = true`
- User `bob@example.com` logs in → Key `onboarding_complete_bob@example.com` doesn't exist → Shows onboarding
- User `alice@example.com` logs back in → Key exists → Skips onboarding ✅

### Flow

1. User logs in → `_handleLoginSuccess()` called
2. Fetch user profile to get email address
3. Check `SharedPreferences` for key `onboarding_complete_{email}`
4. If missing or `false` → show Onboarding Screen
5. If `true` → show Home Screen
6. When user completes onboarding → set `onboarding_complete_{email} = true`

### Files Modified

- `mobile-app/lib/main.dart` - Added debug logging
- `mobile-app/lib/screens/onboarding_screen.dart` - Added debug logging
- `mobile-app/lib/screens/profile_screen.dart` - Added developer utilities
- `mobile-app/lib/dev_utils/reset_onboarding.dart` - New utility file

## Need Help?

If onboarding still doesn't show after trying all methods:
1. Check terminal for error messages
2. Verify the backend is running (`python start_server.py`)
3. Check that login is successful (look for "access_token" in debug output)
4. Try running with verbose logging: `flutter run -v`
