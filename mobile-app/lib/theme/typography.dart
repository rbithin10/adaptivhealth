/*
Text styles used across the app.

Design System Reference:
- Primary Font: Inter (body text, labels)
- Monospace Font: JetBrains Mono (numeric values like HR, SpO2, BP)

We keep all fonts and sizes here so screens look consistent.

DARK MODE: Primary hierarchy styles (screenTitle, cardTitle, body, etc.) have no
hardcoded color so they inherit the theme's onSurface color, which is
brightness-aware. Muted/secondary styles (bodySmall, caption, label, overline,
heroUnit) expose xxxFor(brightness) helpers when a brightness-aware muted tint
is needed, and fall back to a mid-gray for legacy light-mode usage.
*/

import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'colors.dart';

class AdaptivTypography {
  // Private constructor
  AdaptivTypography._();

  // Base text style using Inter (modern, clean, medical-grade).
  // color is optional — omit it to inherit from DefaultTextStyle (theme-aware).
  static TextStyle _baseStyle(
    double fontSize,
    FontWeight fontWeight,
    double lineHeight, {
    Color? color,
  }) {
    return GoogleFonts.inter(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: lineHeight,
      letterSpacing: fontSize < 14 ? 0.3 : 0.0,
    );
  }

  // Monospace style for numeric values using JetBrains Mono.
  static TextStyle _monoStyle(
    double fontSize,
    FontWeight fontWeight,
    double lineHeight, {
    Color? color,
  }) {
    return GoogleFonts.jetBrainsMono(
      fontSize: fontSize,
      fontWeight: fontWeight,
      color: color,
      height: lineHeight,
    );
  }

  // ==========================================================================
  // PRIMARY HIERARCHY — no hardcoded color, inherits from theme onSurface.
  // ==========================================================================

  // Screen-level title (H1)
  static final TextStyle screenTitle = _baseStyle(28, FontWeight.w600, 1.3);

  // Section headers within a screen (H2)
  static final TextStyle sectionTitle = _baseStyle(20, FontWeight.w600, 1.4);

  // Card headers (H3)
  static final TextStyle cardTitle = _baseStyle(16, FontWeight.w600, 1.4);

  // Regular body text (Body Large)
  static final TextStyle body = _baseStyle(16, FontWeight.w400, 1.5);

  // The big heart rate number (Value Display - Monospace)
  static final TextStyle heroNumber = _monoStyle(32, FontWeight.w700, 1.0);

  // Compact metric value (for vital cards)
  static final TextStyle metricValue = _monoStyle(28, FontWeight.w700, 1.0);

  // Small metric value (for secondary displays)
  static final TextStyle metricValueSmall = _monoStyle(20, FontWeight.w600, 1.0);

  // Subtitle 1 (for section headers)
  static final TextStyle subtitle1 = _baseStyle(18, FontWeight.w600, 1.4);

  // Subtitle 2 (smaller subtitle)
  static final TextStyle subtitle2 = _baseStyle(16, FontWeight.w500, 1.4);

  // ==========================================================================
  // MUTED / SECONDARY STYLES — light-mode defaults kept for back-compat;
  // use xxxFor(brightness) when rendering on a brightness-aware surface.
  // ==========================================================================

  // Smaller body text (Body Small) — mid-gray in light mode
  static final TextStyle bodySmall = _baseStyle(
    14, FontWeight.w400, 1.5, color: const Color(0xFF666666),
  );

  // Small metadata (Caption)
  static final TextStyle caption = _baseStyle(
    12, FontWeight.w400, 1.4, color: const Color(0xFF999999),
  );

  // Unit label next to numbers (BPM, %)
  static final TextStyle heroUnit = _baseStyle(
    12, FontWeight.w400, 1.0, color: const Color(0xFF666666),
  );

  // Overline / badge text
  static final TextStyle overline = _baseStyle(
    11, FontWeight.w500, 1.4, color: const Color(0xFF666666),
  );

  // Label text (for form labels, card labels)
  static final TextStyle label = _baseStyle(
    12, FontWeight.w500, 1.4, color: const Color(0xFF666666),
  );

  // ==========================================================================
  // FIXED-COLOR STYLES (intentional — not theme-aware)
  // ==========================================================================

  // Button text — always white (used on colored button backgrounds)
  static final TextStyle button = _baseStyle(
    14, FontWeight.w600, 1.4, color: const Color(0xFFFFFFFF),
  );

  // ==========================================================================
  // BRIGHTNESS-AWARE HELPERS for muted styles
  // Call these when rendering muted text on a brightness-sensitive surface.
  // ==========================================================================

  /// Body Small with proper muted color for the given brightness.
  static TextStyle bodySmallFor(Brightness b) => bodySmall.copyWith(
    color: b == Brightness.dark ? AdaptivColors.textDark100 : const Color(0xFF666666),
  );

  /// Caption with proper muted color for the given brightness.
  static TextStyle captionFor(Brightness b) => caption.copyWith(
    color: b == Brightness.dark ? AdaptivColors.textDark100 : const Color(0xFF999999),
  );

  /// Hero unit label with proper muted color for the given brightness.
  static TextStyle heroUnitFor(Brightness b) => heroUnit.copyWith(
    color: b == Brightness.dark ? AdaptivColors.textDark100 : const Color(0xFF666666),
  );

  /// Overline / badge text with brightness-aware muted color.
  static TextStyle overlineFor(Brightness b) => overline.copyWith(
    color: b == Brightness.dark ? AdaptivColors.textDark100 : const Color(0xFF666666),
  );

  /// Label text with brightness-aware muted color.
  static TextStyle labelFor(Brightness b) => label.copyWith(
    color: b == Brightness.dark ? AdaptivColors.textDark100 : const Color(0xFF666666),
  );
}
