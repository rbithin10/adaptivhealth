# Dark Mode Quick Reference for Developers

**Date**: February 22, 2026  
**Status**: ✅ All 9 screens updated and ready

---

## 🎯 One-Line Summary
All AdaptivHealth Flutter screens now support dark mode with WCAG AA accessibility. Theme toggles from Profile → Theme Settings.

---

## ✅ What's Already Done (Don't Repeat!)

These 9 screens are **COMPLETE and dark mode ready**:
1. ✅ Profile Screen — Theme Settings integrated
2. ✅ Login Screen — Full dark mode support  
3. ✅ Home Screen — Theme-aware background
4. ✅ Health/Vitals Screen — Dynamic colors
5. ✅ Fitness Screen — Brightness-aware layout
6. ✅ Messaging Screen — Theme support
7. ✅ Notifications Screen — Dark mode ready
8. ✅ Nutrition Screen — Theme-aware UI
9. ✅ Splash Screen — Complete example

---

## 🛠️ If You Need to Update Another Screen

### Step 1: Import Brightness
```dart
@override
Widget build(BuildContext context) {
  final brightness = MediaQuery.of(context).platformBrightness;
  // Now brightness is either Brightness.light or Brightness.dark
}
```

### Step 2: Replace Hard-Coded Colors
```dart
// ❌ Before (WRONG - breaks in dark mode)
backgroundColor: Colors.white,
title: Text('Hello', style: TextStyle(color: Colors.black)),

// ✅ After (CORRECT - works in both themes)
backgroundColor: AdaptivColors.getBackgroundColor(brightness),
title: Text('Hello', style: TextStyle(
  color: AdaptivColors.getTextColor(brightness),
)),
```

### Step 3: Use Helper Methods
```dart
// Text colors
AdaptivColors.getTextColor(brightness)              // Primary text
AdaptivColors.getSecondaryTextColor(brightness)     // Secondary text

// Backgrounds
AdaptivColors.getBackgroundColor(brightness)        // Full background
AdaptivColors.getSurfaceColor(brightness)           // Cards/surfaces

// Clinical colors
AdaptivColors.getRiskColorForBrightness('high', brightness)
AdaptivColors.getRiskColorForBrightness('moderate', brightness)
AdaptivColors.getRiskColorForBrightness('low', brightness)
```

### Step 4: Verify Tap Targets
```dart
// Ensure buttons are at least 48x48 pixels
SizedBox(
  width: 48,
  height: 48,
  child: IconButton(icon: Icon(Icons.favorite), onPressed: () {}),
)
```

### Step 5: Add Semantics (Optional but Good)
```dart
Semantics(
  heading: true,
  label: 'Screen Title',
  child: Text('Screen Title'),
)
```

### Step 6: Test
```bash
flutter run
# Toggle dark mode and verify colors change
```

---

## 🎨 Available Colors

### Light Mode (Brightness.light)
```dart
Background: AdaptivColors.getBackgroundColor() → Colors.white or #F9FAFB
Text:       AdaptivColors.getTextColor()       → Colors.black or #212121
Alert:      Colors.red, orange, green
```

### Dark Mode (Brightness.dark)
```dart
Background: AdaptivColors.getBackgroundColor() → #121212
Text:       AdaptivColors.getTextColor()       → #E8E8E8
Alert:      Lighter variants (#FF6B6B, #FFC933, #4CAF50)
```

---

## 🧪 Running Tests

```bash
cd mobile-app
flutter test test/dark_mode_test.dart
```

Expected: 10+ tests pass ✅

---

## 📖 Documentation

| File | Purpose |
|------|---------|
| `DARK_MODE_GUIDE.md` | Complete reference (1000+ lines) |
| `DARK_MODE_BEST_PRACTICES.dart` | Common mistakes + patterns |
| `THEME_INTEGRATION_EXAMPLE.dart` | Copy-paste code |
| `DARK_MODE_IMPLEMENTATION.md` | Status + checklist |

---

## 🚀 Profile Screen Theme Settings

When users want to change theme:
1. Open app
2. Profile tab (bottom right)
3. Scroll down to "Display Settings"
4. Tap "Theme"
5. Choose: Light / Dark / System
6. Change applies instantly
7. Preference persists on restart

**Developer Note**: The `ThemeSettingsDialog` is already created. You don't need to build it—just integrate the `ListTile` from the example!

---

## 🔍 Debugging Dark Mode Issues

### Problem: Colors not changing
**Solution**: Check that `brightness` is being read from `MediaQuery`
```dart
// ❌ WRONG - brightness not read
Widget build(BuildContext context) => Scaffold(
  backgroundColor: AdaptivColors.getBackgroundColor(brightness), // ERROR: brightness undefined
);

// ✅ RIGHT - brightness read first  
Widget build(BuildContext context) {
  final brightness = MediaQuery.of(context).platformBrightness;
  return Scaffold(
    backgroundColor: AdaptivColors.getBackgroundColor(brightness),
  );
}
```

### Problem: Theme not toggling
**Solution**: Verify `ThemeProvider` is in `main.dart` with `ChangeNotifierProvider`

### Problem: Low contrast warnings
**Solution**: Use `AdaptivColors` helpers—they're WCAG AA verified

### Problem: Tap target too small
**Solution**: Wrap buttons in `SizedBox(width: 48, height: 48, child: ...)`

---

## ✨ One-Screen Migration Example

**Before** (Light mode only):
```dart
class MyScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.white,
      appBar: AppBar(
        backgroundColor: Colors.white,
        title: Text('My Screen', style: TextStyle(color: Colors.black)),
      ),
      body: Center(
        child: Text('Hello', style: TextStyle(color: Colors.black)),
      ),
    );
  }
}
```

**After** (Dark mode + Light mode):
```dart
class MyScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    return Scaffold(
      backgroundColor: AdaptivColors.getBackgroundColor(brightness),
      appBar: AppBar(
        backgroundColor: AdaptivColors.getSurfaceColor(brightness),
        title: Text(
          'My Screen',
          style: TextStyle(color: AdaptivColors.getTextColor(brightness)),
        ),
      ),
      body: Center(
        child: Text(
          'Hello',
          style: TextStyle(color: AdaptivColors.getTextColor(brightness)),
        ),
      ),
    );
  }
}
```

**Lines Changed**: 4 replacements, ~2 minutes ⚡

---

## 📊 Coverage Status

| Component | Status |
|-----------|--------|
| Core Theme System | ✅ Complete |
| Color Palettes | ✅ Complete |
| Helper Methods | ✅ Complete |
| Profile Screen | ✅ Complete |
| Login Screen | ✅ Complete |
| Home Screen | ✅ Complete |
| Health Screen | ✅ Complete |
| Fitness Screen | ✅ Complete |
| Messaging Screen | ✅ Complete |
| Notifications Screen | ✅ Complete |
| Nutrition Screen | ✅ Complete |
| Widget Tests | ✅ Complete |
| WCAG AA Compliance | ✅ Complete |
| Documentation | ✅ Complete |

**Total**: 14/14 items complete ✅

---

## 🎓 Learning Path

**5 min**: Read this quick reference  
**10 min**: Check out `THEME_INTEGRATION_EXAMPLE.dart`  
**15 min**: Review one completely migrated screen (e.g., `login_screen.dart`)  
**10 min**: Run the tests and see them pass  
**20 min**: Migrate your own screen using the pattern  

**Total**: ~60 minutes to understand and implement on a new screen

---

## 💡 Pro Tips

1. **Reuse patterns** — Copy the Login/Profile screen structure for new screens
2. **Test early** — Toggle dark mode while developing to catch issues
3. **Use helpers** — `AdaptivColors.get*()` methods are pre-tested for WCAG AA
4. **Tap targets** — Always wrap buttons in `SizedBox(48, 48)` or larger
5. **Semantics** — Add `Semantics(button: true)` to interactive elements

---

## 🆘 Need More Help?

1. **Color questions** → See `lib/theme/colors.dart` (all variants listed)
2. **Pattern questions** → See `THEME_INTEGRATION_EXAMPLE.dart`
3. **Best practice questions** → See `DARK_MODE_BEST_PRACTICES.dart`
4. **Test writing** → See `test/dark_mode_test.dart`

---

**Status**: ✅ Ready to Deploy  
**Questions?** Refer to `DARK_MODE_GUIDE.md` for detailed answers

---

*Last Updated: February 22, 2026*
