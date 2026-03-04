/*
App-wide theme with Light Mode Support.

This defines the visual appearance for light mode.
Contains ThemeData for light mode only.
*/

import 'package:flutter/material.dart';
import 'colors.dart';

ThemeData buildAdaptivHealthTheme([Brightness brightness = Brightness.light]) {
  final isDark = brightness == Brightness.dark;

  final colorScheme = isDark
      ? const ColorScheme.dark(
          primary: AdaptivColors.primaryDarkMode,
          secondary: AdaptivColors.primaryDarkMode,
          error: AdaptivColors.criticalDarkMode,
          surface: AdaptivColors.surface900,
          onPrimary: AdaptivColors.textDark50,
          onSurface: AdaptivColors.textDark50,
        )
      : const ColorScheme.light(
          primary: AdaptivColors.primary,
          secondary: AdaptivColors.primary,
          error: AdaptivColors.critical,
          surface: AdaptivColors.white,
          onPrimary: AdaptivColors.white,
          onSurface: AdaptivColors.text900,
        );

  return ThemeData(
    useMaterial3: true,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: isDark ? AdaptivColors.background900 : AdaptivColors.primaryUltralight,
    appBarTheme: AppBarTheme(
      backgroundColor: isDark ? AdaptivColors.surface900 : AdaptivColors.primary,
      foregroundColor: isDark ? AdaptivColors.textDark50 : AdaptivColors.white,
    ),
  );
}
