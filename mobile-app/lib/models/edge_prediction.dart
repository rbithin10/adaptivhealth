/// Data models for edge AI predictions.
///
/// These lightweight classes hold the results from on-device TFLite
/// inference. They mirror the backend's risk prediction response but
/// are tagged with source='edge' for cloud sync conflict resolution.
library;

// Result of on-device risk prediction via TFLite Random Forest
class EdgeRiskPrediction {
  final double riskScore;       // 0.0 - 1.0 probability of high risk
  final String riskLevel;       // 'low', 'moderate', 'high'
  final double confidence;      // max(prob_low, prob_high)
  final int inferenceTimeMs;    // Milliseconds for inference
  final String modelVersion;    // e.g. '2.0'
  final String source;          // Always 'edge'
  final DateTime timestamp;

  EdgeRiskPrediction({
    required this.riskScore,
    required this.riskLevel,
    required this.confidence,
    required this.inferenceTimeMs,
    required this.modelVersion,
    this.source = 'edge',
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  // Convert to JSON for local storage and cloud sync
  Map<String, dynamic> toJson() => {
    'risk_score': riskScore,
    'risk_level': riskLevel,
    'confidence': confidence,
    'inference_time_ms': inferenceTimeMs,
    'model_version': modelVersion,
    'source': source,
    'timestamp': timestamp.toIso8601String(),
  };

  // Create from cached JSON
  factory EdgeRiskPrediction.fromJson(Map<String, dynamic> json) {
    return EdgeRiskPrediction(
      riskScore: (json['risk_score'] as num).toDouble(),
      riskLevel: json['risk_level'] as String,
      confidence: (json['confidence'] as num).toDouble(),
      inferenceTimeMs: json['inference_time_ms'] as int,
      modelVersion: json['model_version'] as String,
      source: json['source'] as String? ?? 'edge',
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }
}

// Threshold alert triggered by vital sign limits (no ML needed)
class ThresholdAlert {
  final String alertType;       // 'high_hr', 'low_hr', 'low_spo2', 'high_bp'
  final String severity;        // 'critical', 'warning', 'info'
  final String title;
  final String message;
  final List<String> actions;   // Recommended actions for the patient
  final double? triggerValue;   // The value that triggered the alert
  final double? threshold;      // The threshold that was exceeded
  final DateTime timestamp;

  ThresholdAlert({
    required this.alertType,
    required this.severity,
    required this.title,
    required this.message,
    required this.actions,
    this.triggerValue,
    this.threshold,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toJson() => {
    'alert_type': alertType,
    'severity': severity,
    'title': title,
    'message': message,
    'actions': actions,
    'trigger_value': triggerValue,
    'threshold': threshold,
    'timestamp': timestamp.toIso8601String(),
  };
}

// GPS emergency alert for offline/remote situations
class GpsEmergencyAlert {
  final double latitude;
  final double longitude;
  final double? altitude;       // Meters above sea level
  final double? accuracy;       // GPS accuracy in meters
  final String riskLevel;
  final double riskScore;
  final Map<String, dynamic> vitals;  // Snapshot of vitals at alert time
  final DateTime timestamp;
  final bool synced;            // Has this been sent to cloud?

  GpsEmergencyAlert({
    required this.latitude,
    required this.longitude,
    this.altitude,
    this.accuracy,
    required this.riskLevel,
    required this.riskScore,
    required this.vitals,
    this.synced = false,
    DateTime? timestamp,
  }) : timestamp = timestamp ?? DateTime.now();

  Map<String, dynamic> toJson() => {
    'latitude': latitude,
    'longitude': longitude,
    'altitude': altitude,
    'accuracy': accuracy,
    'risk_level': riskLevel,
    'risk_score': riskScore,
    'vitals': vitals,
    'timestamp': timestamp.toIso8601String(),
    'synced': synced,
  };

  factory GpsEmergencyAlert.fromJson(Map<String, dynamic> json) {
    return GpsEmergencyAlert(
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      altitude: (json['altitude'] as num?)?.toDouble(),
      accuracy: (json['accuracy'] as num?)?.toDouble(),
      riskLevel: json['risk_level'] as String,
      riskScore: (json['risk_score'] as num).toDouble(),
      vitals: Map<String, dynamic>.from(json['vitals'] as Map),
      synced: json['synced'] as bool? ?? false,
      timestamp: DateTime.parse(json['timestamp'] as String),
    );
  }
}
