/// Edge Alert Service — Threshold-based alerts + GPS emergency SOS.
///
/// This service handles two critical offline-capable features:
///
/// 1. THRESHOLD ALERTS: Pure math, no ML. If HR > 180 or SpO2 < 88,
///    the patient needs an alert immediately — no model needed.
///
/// 2. GPS EMERGENCY: When a critical alert fires, capture GPS coordinates
///    (GPS works via satellite — no cell signal needed). Queue the
///    emergency data locally. When connectivity returns, auto-sync
///    to the cloud so the doctor sees the event with exact location.
///
/// WHY GPS WITHOUT NETWORK?
///   GPS receivers in phones talk directly to satellites. A patient
///   hiking on a mountaintop with zero cell service can still get:
///   - Their exact latitude/longitude/altitude
///   - A locally-stored SOS record
///   - Auto-sync when they descend to cell coverage
///   The app can also trigger the phone's native SOS (if available)
///   or compose an SMS (SMS works on weaker signal than data).
library;

import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/edge_prediction.dart';

// ============================================================================
// Alert Thresholds (configurable, loaded from edge_model_metadata.json)
// ============================================================================

class AlertThresholds {
  final int hrCriticalHigh;
  final int hrWarningHigh;
  final int hrCriticalLow;
  final int hrWarningLow;
  final int spo2Critical;
  final int spo2Warning;
  final int bpSystolicCritical;
  final int bpSystolicWarning;

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
// Edge Alert Service
// ============================================================================

class EdgeAlertService {
  AlertThresholds thresholds;

  // Queue of emergency alerts waiting to sync to cloud
  final List<GpsEmergencyAlert> _pendingEmergencies = [];

  // Prevent alert storms — cooldown per alert type
  final Map<String, DateTime> _lastAlertTime = {};
  static const _alertCooldown = Duration(minutes: 2);

  EdgeAlertService({AlertThresholds? thresholds})
      : thresholds = thresholds ?? const AlertThresholds();

  /// Check vitals against thresholds and return alerts (if any).
  /// This is pure math — runs in <1ms, zero ML, zero network.
  List<ThresholdAlert> checkVitals({
    required int heartRate,
    int? spo2,
    int? bpSystolic,
  }) {
    final alerts = <ThresholdAlert>[];
    final now = DateTime.now();

    // ---- Heart Rate Checks ----
    if (heartRate >= thresholds.hrCriticalHigh) {
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

    // ---- SpO2 Checks ----
    if (spo2 != null && spo2 > 0) {
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
    if (bpSystolic != null && bpSystolic > 0) {
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
    final alert = GpsEmergencyAlert(
      latitude: latitude,
      longitude: longitude,
      altitude: altitude,
      accuracy: accuracy,
      riskLevel: riskLevel,
      riskScore: riskScore,
      vitals: vitals,
    );

    // Queue for cloud sync
    _pendingEmergencies.add(alert);

    // Persist to local storage (survives app restart)
    await _savePendingEmergencies();

    return alert;
  }

  /// Get all pending emergencies that haven't been synced to cloud
  List<GpsEmergencyAlert> get pendingEmergencies =>
      List.unmodifiable(_pendingEmergencies);

  /// Mark an emergency as synced (called after successful cloud upload)
  Future<void> markEmergencySynced(int index) async {
    if (index >= 0 && index < _pendingEmergencies.length) {
      _pendingEmergencies.removeAt(index);
      await _savePendingEmergencies();
    }
  }

  /// Load pending emergencies from local storage (call at app startup)
  Future<void> loadPendingEmergencies() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonStr = prefs.getString('pending_gps_emergencies');
      if (jsonStr != null) {
        final list = json.decode(jsonStr) as List;
        _pendingEmergencies.clear();
        for (final item in list) {
          _pendingEmergencies.add(
            GpsEmergencyAlert.fromJson(Map<String, dynamic>.from(item as Map)),
          );
        }
      }
    } catch (_) {
      // Silently fail — don't crash app for storage issues
    }
  }

  // ---- Private Helpers ----

  /// Prevent alert storms: only one alert per type every 2 minutes
  bool _canAlert(String type, DateTime now) {
    final last = _lastAlertTime[type];
    if (last != null && now.difference(last) < _alertCooldown) {
      return false;
    }
    _lastAlertTime[type] = now;
    return true;
  }

  /// Persist pending emergencies to SharedPreferences
  Future<void> _savePendingEmergencies() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonStr = json.encode(
        _pendingEmergencies.map((e) => e.toJson()).toList(),
      );
      await prefs.setString('pending_gps_emergencies', jsonStr);
    } catch (_) {
      // Best effort persistence
    }
  }
}
