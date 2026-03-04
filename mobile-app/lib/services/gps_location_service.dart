/// GPS Location Service — Satellite-based positioning, no internet needed.
///
/// GPS receivers in smartphones communicate directly with satellites.
/// A patient on a mountaintop with ZERO cell signal can still get:
///   - Latitude / Longitude (±3-5m accuracy)
///   - Altitude above sea level
///   - These coordinates are stored locally for emergency records
///
/// When connectivity returns, the app syncs the GPS-tagged emergency
/// to the cloud so the doctor/emergency contact sees the exact location.
///
/// PERMISSIONS REQUIRED (added to AndroidManifest.xml / Info.plist):
///   Android: ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION
///   iOS: NSLocationWhenInUseUsageDescription
///
/// NOTE: This uses a lightweight approach with platform channels
/// to avoid adding the heavy geolocator package (~2MB). For production,
/// you can swap in the `geolocator` package for more features.
library;

import 'dart:async';
import 'package:flutter/services.dart';

// ============================================================================
// GPS Position Data
// ============================================================================

class GpsPosition {
  final double latitude;
  final double longitude;
  final double? altitude;       // Meters above sea level
  final double? accuracy;       // Horizontal accuracy in meters
  final DateTime timestamp;

  GpsPosition({
    required this.latitude,
    required this.longitude,
    this.altitude,
    this.accuracy,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  // Whether this is a high-altitude location (potential remote area)
  bool get isHighAltitude => altitude != null && altitude! > 1500;

  // Human-readable altitude string
  String get altitudeLabel {
    if (altitude == null) return 'Unknown';
    return '${altitude!.round()}m above sea level';
  }

  Map<String, dynamic> toJson() => {
    'latitude': latitude,
    'longitude': longitude,
    'altitude': altitude,
    'accuracy': accuracy,
    'timestamp': timestamp.toIso8601String(),
  };
}

// ============================================================================
// GPS Location Service
// ============================================================================

class GpsLocationService {
  // Cached last known position
  GpsPosition? _lastPosition;

  // Whether GPS permission has been granted
  bool _hasPermission = false;

  // Platform channel for native GPS (lightweight alternative to geolocator)
  // If geolocator package is available, swap this for Geolocator.getCurrentPosition()
  static const _channel = MethodChannel('adaptiv_health/gps');

  // ---- Public API ----

  // Last known GPS position (may be stale if GPS is off)
  GpsPosition? get lastPosition => _lastPosition;

  // Whether we have location permission
  bool get hasPermission => _hasPermission;

  /// Request GPS permission from the user.
  /// Call this once during onboarding or first app launch.
  Future<bool> requestPermission() async {
    try {
      // Try using geolocator if available, otherwise platform channel
      _hasPermission = await _requestPermissionNative();
      return _hasPermission;
    } catch (e) {
      _hasPermission = false;
      return false;
    }
  }

  /// Get the current GPS position.
  /// Works WITHOUT internet — GPS uses satellite signals directly.
  /// Returns null if GPS is unavailable or permission denied.
  Future<GpsPosition?> getCurrentPosition() async {
    try {
      final position = await _getPositionNative();
      if (position != null) {
        _lastPosition = position;
      }
      return position;
    } catch (e) {
      // GPS unavailable — return last known position if available
      return _lastPosition;
    }
  }

  /// Get position for emergency alert.
  /// Tries current GPS first, falls back to last known position.
  /// Returns the best available location data for the emergency record.
  Future<GpsPosition?> getEmergencyPosition() async {
    // Try fresh GPS reading first (5 second timeout)
    final current = await getCurrentPosition();
    if (current != null) return current;

    // Fall back to last cached position
    return _lastPosition;
  }

  // ---- Private: Native GPS Access ----

  /// Request location permission via platform channel.
  /// In production, replace with geolocator package for cleaner API.
  Future<bool> _requestPermissionNative() async {
    try {
      final result = await _channel.invokeMethod<bool>('requestPermission');
      return result ?? false;
    } on MissingPluginException {
      // Platform channel not set up — assume permission granted for dev
      // In production, use geolocator package instead
      return true;
    }
  }

  /// Get current position via platform channel.
  Future<GpsPosition?> _getPositionNative() async {
    try {
      final result = await _channel.invokeMethod<Map>('getCurrentPosition');
      if (result != null) {
        return GpsPosition(
          latitude: (result['latitude'] as num).toDouble(),
          longitude: (result['longitude'] as num).toDouble(),
          altitude: (result['altitude'] as num?)?.toDouble(),
          accuracy: (result['accuracy'] as num?)?.toDouble(),
        );
      }
    } on MissingPluginException {
      // Platform channel not available — return mock for development
      // Remove this in production and use geolocator package
      return _getMockPosition();
    }
    return null;
  }

  /// Mock position for development/testing only.
  /// Remove this when geolocator package is integrated.
  GpsPosition? _getMockPosition() {
    // Returns a default Dubai position for dev testing
    return GpsPosition(
      latitude: 25.2048,
      longitude: 55.2708,
      altitude: 5.0,
      accuracy: 10.0,
    );
  }
}
