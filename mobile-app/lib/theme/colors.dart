/*
App color palette with Light Mode Support.

These colors are used everywhere so the app looks consistent.
Red means high risk, amber means caution, green means safe.

DARK MODE: Colors automatically adapt based on theme.
Use AdaptivColors.getForBrightness() or access light/dark variants directly.

Design System Reference:
- Primary Blue: #0066FF (Actions, CTA buttons)
- Success Green: #00C853 (Safe zone, completed actions)
- Warning Yellow: #FFB300 (Caution, moderate alerts)
- Alert Red: #FF3B30 (Critical, dangerous levels)
*/

import 'package:flutter/material.dart';

class AdaptivColors {
  // Private constructor
  AdaptivColors._();

  // Primary brand colors (Updated to design spec)
  static const Color primary = Color(0xFF0066FF);      // Actions, CTA buttons
  static const Color primaryDark = Color(0xFF0052CC);  // Hover states
  static const Color primaryLight = Color(0xFFD6E8FF); // Light backgrounds
  static const Color primaryUltralight = Color(0xFFEBF4FF); // Very light

  // Clinical status: Critical (High Risk)
  static const Color critical = Color(0xFFFF3B30);     // Updated to design spec
  static const Color criticalBg = Color(0xFFFEF2F2);
  static const Color criticalBorder = Color(0xFFFCA5A5);
  static const Color criticalText = Color(0xFF991B1B);
  static const Color criticalUltralight = Color(0xFFFEF2F2);
  static const Color criticalLight = Color(0xFFFCA5A5);

  // Clinical status: Warning (Moderate Risk)
  static const Color warning = Color(0xFFFFB300);      // Updated to design spec
  static const Color warningBg = Color(0xFFFFFBEB);
  static const Color warningBorder = Color(0xFFFCD34D);
  static const Color warningText = Color(0xFF92400E);

  // Clinical status: Stable (Low Risk / Safe Zone)
  static const Color stable = Color(0xFF10B981);
  static const Color stableBg = Color(0xFFECFDF5);
  static const Color stableBorder = Color(0xFF6EE7B7);
  static const Color stableText = Color(0xFF065F46);

  // Dark mode: text
  static const Color textDark50 = Color(0xFFF9FAFB);
  static const Color textDark100 = Color(0xFFD1D5DB);

  // Dark mode: surfaces and backgrounds
  static const Color surface900 = Color(0xFF1F2937);
  static const Color background900 = Color(0xFF111827);
  static const Color borderDark = Color(0xFF374151);

  // Dark mode: primary
  static const Color primaryDarkMode = Color(0xFF3B82F6);

  // Dark mode: clinical status colors (WCAG AA on dark backgrounds)
  static const Color criticalDarkMode = Color(0xFFF87171);
  static const Color warningDarkMode = Color(0xFFFBBF24);
  static const Color stableDarkMode = Color(0xFF34D399);

  // Dark mode: clinical background colors
  static const Color criticalBgDark = Color(0xFF7F1D1D);
  static const Color warningBgDark = Color(0xFF78350F);
  static const Color stableBgDark = Color(0xFF064E3B);

  // Dark mode: clinical text colors
  static const Color criticalTextDark = Color(0xFFFCA5A5);
  static const Color warningTextDark = Color(0xFFFDE68A);
  static const Color stableTextDark = Color(0xFF6EE7B7);

  // Heart Rate Zones (from design spec)
  static const Color zoneResting = Color(0xFF4CAF50);      // 50-70 BPM - Green
  static const Color zoneLightActivity = Color(0xFF8BC34A); // 70-100 BPM - Light Green
  static const Color zoneModerate = Color(0xFFFFC107);      // 100-140 BPM - Yellow
  static const Color zoneHard = Color(0xFFFF9800);          // 140-170 BPM - Orange
  static const Color zoneMaximum = Color(0xFFF44336);       // 170+ BPM - Red

  // HR Zone aliases (for widget compatibility)
  static const Color hrResting = zoneResting;
  static const Color hrLight = zoneLightActivity;
  static const Color hrModerate = zoneModerate;
  static const Color hrHard = zoneHard;
  static const Color hrMaximum = zoneMaximum;

  // Neutral palette
  static const Color text900 = Color(0xFF212121);    // Primary text (updated)
  static const Color text700 = Color(0xFF424242);    // Secondary text
  static const Color text600 = Color(0xFF666666);    // Tertiary text alt
  static const Color text500 = Color(0xFF999999);    // Tertiary text (caption)
  static const Color text400 = Color(0xFFBDBDBD);    // Disabled text
  static const Color text50 = Color(0xFFFAFAFA);     // Very light text
  static const Color neutral300 = Color(0xFFD1D5DB); // Neutral shade
  static const Color neutral400 = Color(0xFF9CA3AF); // Neutral shade
  static const Color border300 = Color(0xFFE0E0E0);  // Borders, dividers
  static const Color surface100 = Color(0xFFF5F5F5); // Card backgrounds
  static const Color background50 = Color(0xFFF9FAFB); // Page background
  static const Color white = Color(0xFFFFFFFF);      // White surfaces

  // Background shades
  static const Color bg100 = Color(0xFFF5F5F5);      // Light background
  static const Color bg200 = Color(0xFFEEEEEE);      // Slightly darker
  static const Color primaryBg = Color(0xFFE3F2FD); // Primary tint background

  // Chart colors
  static const Color chartTeal = Color(0xFF14B8A6);
  static const Color chartBlue = Color(0xFF0EA5E9);
  static const Color chartSuccess = Color(0xFF10B981);

  // Helper methods for risk levels
  static Color getRiskColor(String riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'high':
      case 'critical':
        return critical;
      case 'moderate':
      case 'warning':
        return warning;
      case 'low':
      case 'stable':
      default:
        return stable;
    }
  }

  static Color getRiskBgColor(String riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'high':
      case 'critical':
        return criticalBg;
      case 'moderate':
      case 'warning':
        return warningBg;
      case 'low':
      case 'stable':
      default:
        return stableBg;
    }
  }

  static Color getRiskTextColor(String riskLevel) {
    switch (riskLevel.toLowerCase()) {
      case 'high':
      case 'critical':
        return criticalText;
      case 'moderate':
      case 'warning':
        return warningText;
      case 'low':
      case 'stable':
      default:
        return stableText;
    }
  }

  /// Get HR zone color based on heart rate
  static Color getHRZoneColor(int heartRate) {
    if (heartRate < 70) return zoneResting;
    if (heartRate < 100) return zoneLightActivity;
    if (heartRate < 140) return zoneModerate;
    if (heartRate < 170) return zoneHard;
    return zoneMaximum;
  }

  /// Get HR zone label based on heart rate
  static String getHRZoneLabel(int heartRate) {
    if (heartRate < 70) return 'Resting';
    if (heartRate < 100) return 'Light';
    if (heartRate < 140) return 'Moderate';
    if (heartRate < 170) return 'Hard';
    return 'Maximum';
  }

  // =============================================================================
  // DARK MODE HELPERS
  // =============================================================================

  /// Get text color based on brightness (WCAG AA compliant)
  static Color getTextColor(Brightness brightness) {
    return brightness == Brightness.dark ? textDark50 : text900;
  }

  /// Get secondary text color based on brightness
  static Color getSecondaryTextColor(Brightness brightness) {
    return brightness == Brightness.dark ? textDark100 : text700;
  }

  /// Get surface/background color based on brightness
  static Color getSurfaceColor(Brightness brightness) {
    return brightness == Brightness.dark ? surface900 : white;
  }

  /// Get page background color based on brightness
  static Color getBackgroundColor(Brightness brightness) {
    return brightness == Brightness.dark ? background900 : background50;
  }

  /// Get border color based on brightness
  static Color getBorderColor(Brightness brightness) {
    return brightness == Brightness.dark ? borderDark : border300;
  }

  /// Get primary color based on brightness
  static Color getPrimaryColor(Brightness brightness) {
    return brightness == Brightness.dark ? primaryDarkMode : primary;
  }

  /// Get risk color based on risk level and brightness (WCAG AA compliant)
  static Color getRiskColorForBrightness(String riskLevel, Brightness brightness) {
    switch (riskLevel.toLowerCase()) {
      case 'high':
      case 'critical':
        return brightness == Brightness.dark ? criticalDarkMode : critical;
      case 'moderate':
      case 'warning':
        return brightness == Brightness.dark ? warningDarkMode : warning;
      case 'low':
      case 'stable':
      default:
        return brightness == Brightness.dark ? stableDarkMode : stable;
    }
  }

  /// Get risk background color based on risk level and brightness
  static Color getRiskBgColorForBrightness(String riskLevel, Brightness brightness) {
    switch (riskLevel.toLowerCase()) {
      case 'high':
      case 'critical':
        return brightness == Brightness.dark ? criticalBgDark : criticalBg;
      case 'moderate':
      case 'warning':
        return brightness == Brightness.dark ? warningBgDark : warningBg;
      case 'low':
      case 'stable':
      default:
        return brightness == Brightness.dark ? stableBgDark : stableBg;
    }
  }

  /// Get risk text color based on risk level and brightness
  static Color getRiskTextColorForBrightness(String riskLevel, Brightness brightness) {
    switch (riskLevel.toLowerCase()) {
      case 'high':
      case 'critical':
        return brightness == Brightness.dark ? criticalTextDark : criticalText;
      case 'moderate':
      case 'warning':
        return brightness == Brightness.dark ? warningTextDark : warningText;
      case 'low':
      case 'stable':
      default:
        return brightness == Brightness.dark ? stableTextDark : stableText;
    }
  }
}
