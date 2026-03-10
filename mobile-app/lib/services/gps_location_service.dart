/*
GPS Location Service — Satellite-based positioning, no internet needed.

GPS receivers in smartphones talk directly to satellites in space.
A patient on a mountaintop with ZERO cell signal can still get:
  - Latitude / Longitude (accurate to about 3-5 meters)
  - Altitude above sea level
  - These coordinates are stored locally for emergency records

When the phone gets internet again, the app uploads the GPS-tagged
emergency so the doctor sees the exact location.

This is used for the SOS/emergency feature — when vitals are
dangerously abnormal, the app captures WHERE the patient is.
*/
library;

// Timers and async helpers
import 'dart:async';
// Lets us talk to the phone's native GPS through a platform channel
import 'package:flutter/services.dart';

// ============================================================================
// GPS Position Data — holds a single location reading
// ============================================================================

// Stores one GPS reading (latitude, longitude, altitude, accuracy)
class GpsPosition {
  // How far north or south the person is (e.g. 25.2 for Dubai)
  final double latitude;
  // How far east or west the person is (e.g. 55.3 for Dubai)
  final double longitude;
  // Height above sea level in meters (if available)
  final double? altitude;
  // How accurate the reading is in meters (lower = more accurate)
  final double? accuracy;
  // When this reading was taken
  final DateTime timestamp;

  // Create a GPS position, defaulting the timestamp to right now
  GpsPosition({
    required this.latitude,
    required this.longitude,
    this.altitude,
    this.accuracy,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  // Check if the person is at a high altitude (could indicate remote area)
  bool get isHighAltitude => altitude != null && altitude! > 1500;

  // Show the altitude as a readable label like "1200m above sea level"
  String get altitudeLabel {
    if (altitude == null) return 'Unknown';
    return '${altitude!.round()}m above sea level';
  }

  // Convert this position to a JSON map for saving or sending to the server
  Map<String, dynamic> toJson() => {
    'latitude': latitude,
    'longitude': longitude,
    'altitude': altitude,
    'accuracy': accuracy,
    'timestamp': timestamp.toIso8601String(),
  };
}

// ============================================================================
// GPS Location Service — gets the phone's current location
// ============================================================================

class GpsLocationService {
  // The last GPS reading we got (kept in case GPS is temporarily unavailable)
  GpsPosition? _lastPosition;

  // Whether the user has given us permission to use GPS
  bool _hasPermission = false;

  // The communication channel to the phone's native GPS system
  static const _channel = MethodChannel('adaptiv_health/gps');

  // ---- Public API ----

  // Get the last GPS reading (might be slightly outdated)
  GpsPosition? get lastPosition => _lastPosition;

  // Check if the user has allowed location access
  bool get hasPermission => _hasPermission;

  // Ask the user for permission to access their GPS location
  Future<bool> requestPermission() async {
    try {
      // Send the permission request to the phone's native side
      _hasPermission = await _requestPermissionNative();
      return _hasPermission;
    } catch (e) {
      // If something goes wrong, mark permission as not granted
      _hasPermission = false;
      return false;
    }
  }

  // Get a fresh GPS reading right now (works WITHOUT internet!)
  Future<GpsPosition?> getCurrentPosition() async {
    try {
      // Ask the phone's GPS for the current location
      final position = await _getPositionNative();
      if (position != null) {
        // Save it in case we need it later
        _lastPosition = position;
      }
      return position;
    } catch (e) {
      // GPS temporarily unavailable — return the last reading if we have one
      return _lastPosition;
    }
  }

  // Get the best available location for an emergency alert
  Future<GpsPosition?> getEmergencyPosition() async {
    // Try to get a fresh GPS reading first
    final current = await getCurrentPosition();
    if (current != null) return current;

    // If GPS isn't working right now, use the last saved position
    return _lastPosition;
  }

  // ---- Private: Native GPS Access ----

  // Request permission through the phone's native system
  Future<bool> _requestPermissionNative() async {
    try {
      // Call the native side to show the permission dialog
      final result = await _channel.invokeMethod<bool>('requestPermission');
      return result ?? false;
    } on MissingPluginException {
      // Running on desktop/emulator without GPS — assume granted for testing
      return true;
    }
  }

  // Get the current position through the phone's native GPS
  Future<GpsPosition?> _getPositionNative() async {
    try {
      // Call the native GPS plugin to get coordinates
      final result = await _channel.invokeMethod<Map>('getCurrentPosition');
      if (result != null) {
        // Convert the native response into our GpsPosition object
        return GpsPosition(
          latitude: (result['latitude'] as num).toDouble(),
          longitude: (result['longitude'] as num).toDouble(),
          altitude: (result['altitude'] as num?)?.toDouble(),
          accuracy: (result['accuracy'] as num?)?.toDouble(),
        );
      }
    } on MissingPluginException {
      // No real GPS available — return a fake position for development testing
      return _getMockPosition();
    }
    return null;
  }

  // Fake GPS position used only during development / testing
  GpsPosition? _getMockPosition() {
    // Returns a Dubai location as the default test position
    return GpsPosition(
      latitude: 25.2048,
      longitude: 55.2708,
      altitude: 5.0,
      accuracy: 10.0,
    );
  }
}
