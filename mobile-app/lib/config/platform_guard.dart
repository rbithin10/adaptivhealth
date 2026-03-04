/*
Platform-safe helpers for checking the current OS.

dart:io's Platform class throws "Unsupported operation: Platform._operatingSystem"
when called on Flutter Web. All code that needs to branch on the OS must use
these helpers instead of importing dart:io directly.

Usage:
  import '../config/platform_guard.dart';
  if (isAndroid) { ... }
  if (isIOS) { ... }
  if (isWeb) { ... }
*/

import 'package:flutter/foundation.dart' show kIsWeb;
// Conditional import so dart:io is only loaded on non-web targets.
import 'dart:io' show Platform;

/// True when running on Android device/emulator (never true on web).
bool get isAndroid => !kIsWeb && Platform.isAndroid;

/// True when running on iOS device/simulator (never true on web).
bool get isIOS => !kIsWeb && Platform.isIOS;

/// True when running as a Flutter Web application.
bool get isWeb => kIsWeb;

/// True when running on a mobile platform (iOS or Android).
bool get isMobile => isAndroid || isIOS;

/// Safe read of the OS version string — returns empty string on web.
String get safeOsVersion => kIsWeb ? '' : Platform.operatingSystemVersion;
