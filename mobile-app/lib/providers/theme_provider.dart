/*
Theme Provider.

Controls whether the app uses light mode, dark mode, or follows the phone's setting.
The user's choice is saved to the phone so it's remembered next time they open the app.
*/

import 'package:flutter/material.dart';
// SharedPreferences lets us save small settings to the phone's local storage
import 'package:shared_preferences/shared_preferences.dart';

// This class keeps track of the current theme (light/dark/system).
// All screens listen to it and re-draw when the theme changes.
class ThemeProvider extends ChangeNotifier {
  // The key we use to store the theme choice on the phone (like a label on a storage box)
  static const _key = 'theme_mode';

  // Start with "system" — meaning follow whatever the phone is set to
  ThemeMode _themeMode = ThemeMode.system;
  // Let other parts of the app read the current theme
  ThemeMode get themeMode => _themeMode;

  // Quick check: is the app currently in dark mode?
  bool get isDark => _themeMode == ThemeMode.dark;

  // When this provider is created, immediately load the saved theme from storage
  ThemeProvider() {
    _load();
  }

  // Read the saved theme preference from the phone's storage
  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    // Read the stored value — will be 'dark', 'light', or null (not set yet)
    final value = prefs.getString(_key);
    if (value == 'dark') {
      _themeMode = ThemeMode.dark;
    } else if (value == 'light') {
      _themeMode = ThemeMode.light;
    } else {
      // If nothing was saved, follow the phone's system setting
      _themeMode = ThemeMode.system;
    }
    // Tell all screens to redraw with the loaded theme
    notifyListeners();
  }

  // Switch between light and dark mode, and save the choice
  Future<void> toggleTheme() async {
    // If it's dark, switch to light — and vice versa
    _themeMode = isDark ? ThemeMode.light : ThemeMode.dark;
    final prefs = await SharedPreferences.getInstance();
    // Save the new theme to the phone so it's remembered next time
    await prefs.setString(_key, _themeMode == ThemeMode.dark ? 'dark' : 'light');
    // Tell all screens to redraw with the new theme
    notifyListeners();
  }
}
