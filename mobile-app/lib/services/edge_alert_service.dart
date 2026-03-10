/*
Edge Alert Service — Threshold-based alerts + GPS emergency SOS.

This service handles two critical offline-capable features:

1. THRESHOLD ALERTS: Pure math, no ML. If heart rate > 180 or SpO2 < 88,
   the patient needs an alert immediately — no model needed.

2. GPS EMERGENCY: When a critical alert fires, capture GPS coordinates
   (GPS works via satellite — no cell signal needed). Queue the
   emergency data locally. When connectivity returns, auto-sync
   to the cloud so the doctor sees the event with exact location.

GPS receivers in phones talk directly to satellites. A patient
hiking on a mountaintop with zero cell service can still get:
- Their exact latitude/longitude/altitude
- A locally-stored SOS record
- Auto-sync when they descend to cell coverage
*/
library;

// Converts objects to/from JSON text for saving to phone storage
import 'dart:convert';
// Saves small pieces of data to the phone that survive app restarts
import 'package:shared_preferences/shared_preferences.dart';
// Our data models for alerts and GPS emergency records
import '../models/edge_prediction.dart';

// ============================================================================
// Alert Thresholds — the danger levels that trigger alerts
// ============================================================================

// Holds all the numbers that define "dangerous" vital signs
class AlertThresholds {
  // Heart rate above this = CRITICAL danger (default: 180 BPM)
  final int hrCriticalHigh;
  // Heart rate above this = warning (default: 150 BPM)
  final int hrWarningHigh;
  // Heart rate below this = CRITICAL danger (default: 40 BPM)
  final int hrCriticalLow;
  // Heart rate below this = warning (default: 50 BPM)
  final int hrWarningLow;
  // Blood oxygen below this = CRITICAL danger (default: 88%)
  final int spo2Critical;
  // Blood oxygen below this = warning (default: 92%)
  final int spo2Warning;
  // Blood pressure top number above this = CRITICAL (default: 180)
  final int bpSystolicCritical;
  // Blood pressure top number above this = warning (default: 160)
  final int bpSystolicWarning;

  // Default threshold values based on medical guidelines
  const AlertThresholds({
    this.hrCriticalHigh = 180,
    this.hrWarningHigh = 150,
    this.hrCriticalLow = 40,
    this.hrWarningLow = 50,
    this.spo2Critical = 88,
    this.spo2Warning = 92,
    this.bpSystolicCritical = 180,
    this.bpSystolicWarning = 160,
  });

  // Create thresholds from a JSON settings file (with safe defaults)
  factory AlertThresholds.fromJson(Map<String, dynamic> json) {
    return AlertThresholds(
      hrCriticalHigh: json['hr_critical_high'] as int? ?? 180,
      hrWarningHigh: json['hr_warning_high'] as int? ?? 150,
      hrCriticalLow: json['hr_critical_low'] as int? ?? 40,
      hrWarningLow: json['hr_warning_low'] as int? ?? 50,
      spo2Critical: json['spo2_critical'] as int? ?? 88,
      spo2Warning: json['spo2_warning'] as int? ?? 92,
      bpSystolicCritical: json['bp_systolic_critical'] as int? ?? 180,
      bpSystolicWarning: json['bp_systolic_warning'] as int? ?? 160,
    );
  }
}

// ============================================================================
// Edge Alert Service — checks vitals against danger thresholds
// ============================================================================

class EdgeAlertService {
  // The threshold values we compare vitals against
  AlertThresholds thresholds;

  // Queue of GPS emergency alerts waiting to be uploaded to the cloud
  final List<GpsEmergencyAlert> _pendingEmergencies = [];

  // Tracks when each alert type last fired to prevent alert storms
  final Map<String, DateTime> _lastAlertTime = {};
  // Minimum 2 minutes between repeated alerts of the same type
  static const _alertCooldown = Duration(minutes: 2);

  // Create the service with custom thresholds or use safe medical defaults
  EdgeAlertService({AlertThresholds? thresholds})
      : thresholds = thresholds ?? const AlertThresholds();

  /// Check vitals against thresholds and return alerts (if any).
  /// This is pure math — runs in <1ms, zero ML, zero network.
  List<ThresholdAlert> checkVitals({
    required int heartRate,
    int? spo2,
    int? bpSystolic,
  }) {
    // Collect any alerts we need to return
    final alerts = <ThresholdAlert>[];
    // Snapshot the current time for cooldown tracking
    final now = DateTime.now();

    // ---- Heart Rate Checks ----

    // Check if heart rate is CRITICALLY high (e.g. above 180 BPM)
    if (heartRate >= thresholds.hrCriticalHigh) {
      // Only fire if we haven't just sent the same alert recently
      if (_canAlert('hr_critical_high', now)) {
        alerts.add(ThresholdAlert(
          alertType: 'high_heart_rate',
          severity: 'critical',
          title: 'Dangerously High Heart Rate',
          message: 'Your heart rate is $heartRate BPM — this is dangerously high. '
              'Stop all activity immediately.',
          actions: [
            'Stop all physical activity NOW',
            'Sit or lie down immediately',
            'Call emergency services if you feel chest pain or dizziness',
            'Take slow, deep breaths',
          ],
          triggerValue: heartRate.toDouble(),
          threshold: thresholds.hrCriticalHigh.toDouble(),
        ));
      }
    // If not critical, check if heart rate is a warning level (e.g. above 150)
    } else if (heartRate >= thresholds.hrWarningHigh) {
      if (_canAlert('hr_warning_high', now)) {
        alerts.add(ThresholdAlert(
          alertType: 'high_heart_rate',
          severity: 'warning',
          title: 'Heart Rate Elevated',
          message: 'Your heart rate is $heartRate BPM — higher than recommended. '
              'Consider slowing down.',
          actions: [
            'Reduce your activity intensity',
            'Take slow, deep breaths for 2 minutes',
            'Drink water',
            'If it does not come down in 10 minutes, contact your doctor',
          ],
          triggerValue: heartRate.toDouble(),
          threshold: thresholds.hrWarningHigh.toDouble(),
        ));
      }
    }

    // Check if heart rate is CRITICALLY low (e.g. below 40 BPM)
    if (heartRate <= thresholds.hrCriticalLow && heartRate > 0) {
      if (_canAlert('hr_critical_low', now)) {
        alerts.add(ThresholdAlert(
          alertType: 'low_heart_rate',
          severity: 'critical',
          title: 'Dangerously Low Heart Rate',
          message: 'Your heart rate is $heartRate BPM — this is abnormally low. '
              'Seek medical attention.',
          actions: [
            'Sit or lie down immediately',
            'Do not stand up quickly',
            'Call emergency services if you feel faint',
          ],
          triggerValue: heartRate.toDouble(),
          threshold: thresholds.hrCriticalLow.toDouble(),
        ));
      }
    // If not critical, check if heart rate is a warning-low (e.g. below 50)
    } else if (heartRate <= thresholds.hrWarningLow && heartRate > 0) {
      if (_canAlert('hr_warning_low', now)) {
        alerts.add(ThresholdAlert(
          alertType: 'low_heart_rate',
          severity: 'warning',
          title: 'Heart Rate Low',
          message: 'Your heart rate is $heartRate BPM — lower than expected.',
          actions: [
            'Sit or lie down if you feel dizzy',
            'Avoid sudden movements',
            'Contact your healthcare provider if symptoms persist',
          ],
          triggerValue: heartRate.toDouble(),
          threshold: thresholds.hrWarningLow.toDouble(),
        ));
      }
    }

    // ---- Blood Oxygen (SpO2) Checks ----

    // Only check if SpO2 data was provided and is a real reading
    if (spo2 != null && spo2 > 0) {
      // Check if blood oxygen is CRITICALLY low (e.g. below 88%)
      if (spo2 <= thresholds.spo2Critical) {
        if (_canAlert('spo2_critical', now)) {
          alerts.add(ThresholdAlert(
            alertType: 'low_spo2',
            severity: 'critical',
            title: 'Critically Low Blood Oxygen',
            message: 'Your blood oxygen is $spo2% — this is dangerously low. '
                'Your body may not be getting enough oxygen.',
            actions: [
              'Sit upright immediately to help breathing',
              'Take slow, deep breaths',
              'Call emergency services if you feel short of breath',
              'Do NOT ignore this — low oxygen can be life-threatening',
            ],
            triggerValue: spo2.toDouble(),
            threshold: thresholds.spo2Critical.toDouble(),
          ));
        }
      // If not critical, check if SpO2 is at warning level (e.g. below 92%)
      } else if (spo2 <= thresholds.spo2Warning) {
        if (_canAlert('spo2_warning', now)) {
          alerts.add(ThresholdAlert(
            alertType: 'low_spo2',
            severity: 'warning',
            title: 'Blood Oxygen Below Normal',
            message: 'Your blood oxygen is $spo2% — slightly below normal range.',
            actions: [
              'Sit upright to help your breathing',
              'Take slow, deep breaths',
              'Monitor closely — if it drops further, seek help',
            ],
            triggerValue: spo2.toDouble(),
            threshold: thresholds.spo2Warning.toDouble(),
          ));
        }
      }
    }

    // ---- Blood Pressure Checks ----

    // Only check if blood pressure data was provided and is a real reading
    if (bpSystolic != null && bpSystolic > 0) {
      // Check if blood pressure is CRITICALLY high (e.g. above 180 mmHg)
      if (bpSystolic >= thresholds.bpSystolicCritical) {
        if (_canAlert('bp_critical', now)) {
          alerts.add(ThresholdAlert(
            alertType: 'high_blood_pressure',
            severity: 'critical',
            title: 'Dangerously High Blood Pressure',
            message: 'Your systolic BP is $bpSystolic mmHg — seek medical help.',
            actions: [
              'Sit down and relax immediately',
              'Avoid caffeine, salt, and physical activity',
              'Contact your healthcare provider urgently',
            ],
            triggerValue: bpSystolic.toDouble(),
            threshold: thresholds.bpSystolicCritical.toDouble(),
          ));
        }
      // If not critical, check if blood pressure is at warning level
      } else if (bpSystolic >= thresholds.bpSystolicWarning) {
        if (_canAlert('bp_warning', now)) {
          alerts.add(ThresholdAlert(
            alertType: 'high_blood_pressure',
            severity: 'warning',
            title: 'Blood Pressure Elevated',
            message: 'Your systolic BP is $bpSystolic mmHg — worth monitoring.',
            actions: [
              'Sit and relax for 5 minutes',
              'Retake reading in 15 minutes',
              'Avoid caffeine and salty foods',
            ],
            triggerValue: bpSystolic.toDouble(),
            threshold: thresholds.bpSystolicWarning.toDouble(),
          ));
        }
      }
    }

    // Return all the alerts we found (could be empty if vitals are fine)
    return alerts;
  }

  // ---- GPS Emergency SOS ----

  /// Create a GPS emergency alert with the patient's location.
  /// GPS works via satellite — NO cell signal or internet needed.
  /// The alert is stored locally and auto-synced when connectivity returns.
  Future<GpsEmergencyAlert> createGpsEmergency({
    required double latitude,
    required double longitude,
    double? altitude,
    double? accuracy,
    required String riskLevel,
    required double riskScore,
    required Map<String, dynamic> vitals,
  }) async {
    // Build the emergency record with GPS location and health data
    final alert = GpsEmergencyAlert(
      latitude: latitude,
      longitude: longitude,
      altitude: altitude,
      accuracy: accuracy,
      riskLevel: riskLevel,
      riskScore: riskScore,
      vitals: vitals,
    );

    // Add to the queue waiting to be uploaded to the cloud
    _pendingEmergencies.add(alert);

    // Save to phone storage so it survives app restarts
    await _savePendingEmergencies();

    return alert;
  }

  // Get a read-only copy of emergencies waiting to be synced
  List<GpsEmergencyAlert> get pendingEmergencies =>
      List.unmodifiable(_pendingEmergencies);

  // Remove an emergency from the queue after it was successfully uploaded
  Future<void> markEmergencySynced(int index) async {
    if (index >= 0 && index < _pendingEmergencies.length) {
      _pendingEmergencies.removeAt(index);
      // Update the saved list on the phone
      await _savePendingEmergencies();
    }
  }

  // Load any unsent emergencies from phone storage (called when app starts)
  Future<void> loadPendingEmergencies() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      // Read the JSON string of saved emergencies
      final jsonStr = prefs.getString('pending_gps_emergencies');
      if (jsonStr != null) {
        // Parse the JSON text back into a list of alert objects
        final list = json.decode(jsonStr) as List;
        _pendingEmergencies.clear();
        for (final item in list) {
          _pendingEmergencies.add(
            GpsEmergencyAlert.fromJson(Map<String, dynamic>.from(item as Map)),
          );
        }
      }
    } catch (_) {
      // Don't crash the app over a storage issue — just skip loading
    }
  }

  // ---- Private Helpers ----

  // Prevents alert storms: only allow one alert per type every 2 minutes
  bool _canAlert(String type, DateTime now) {
    // Check when this alert type last fired
    final last = _lastAlertTime[type];
    // If it fired recently (within cooldown period), block the new alert
    if (last != null && now.difference(last) < _alertCooldown) {
      return false;
    }
    // Record that we're firing this alert type right now
    _lastAlertTime[type] = now;
    return true;
  }

  // Save the pending emergencies list to phone storage
  Future<void> _savePendingEmergencies() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      // Convert all emergency objects to JSON text
      final jsonStr = json.encode(
        _pendingEmergencies.map((e) => e.toJson()).toList(),
      );
      // Write the JSON text to SharedPreferences storage
      await prefs.setString('pending_gps_emergencies', jsonStr);
    } catch (_) {
      // Best effort — if save fails, emergencies are still in memory
    }
  }
}
