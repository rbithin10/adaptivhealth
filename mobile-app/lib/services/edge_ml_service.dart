/// Edge ML Service — on-device cardiac risk prediction.
///
/// Uses the trained RandomForest (100 trees, 97.5% accuracy) exported from
/// risk_model.pkl via convert_to_tflite.py.  Runs entirely offline using a
/// pure-Dart decision-tree walk — no native plugins, works on all platforms.
///
/// Feature engineering MUST match backend app/services/ml_prediction.py
/// engineer_features() exactly — 9 raw inputs + 8 derived = 17 total.
///
/// ARCHITECTURE:
///   Vital reading → engineerFeatures() → scaleFeatures() → treeEnsemble() → risk score
///
/// FALLBACK:
///   If assets fail to load, _isReady stays false and EdgeAiStore falls back
///   to threshold-only alerts.

import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart' show rootBundle;
import '../models/edge_prediction.dart';

class EdgeMLService {
  bool _isReady = false;
  String _modelVersion = 'unknown';

  List<double> _scalerMean = [];
  List<double> _scalerScale = [];
  List<String> _featureColumns = [];

  List<Map<String, dynamic>> _treesData = [];
  int _nEstimators = 0;

  final double _highThreshold = 0.80;
  final double _moderateThreshold = 0.50;

  // ---- Public API ----

  bool get isReady => _isReady;
  String get modelVersion => _modelVersion;

  /// Load model assets from the bundle. Call once after login.
  Future<void> initialize() async {
    try {
      // Load StandardScaler params (mean + scale)
      final rawScalerJson = await rootBundle.loadString(
        'assets/ml_models/scaler_params.json',
      );
      // Python export may include bare NaN (invalid JSON for Dart decoder).
      // Replace with 0.0 so parsing succeeds; scaling step already guards for
      // zero/invalid scales and this keeps edge inference operational.
      final scalerJson = rawScalerJson.replaceAll('NaN', '0.0');
      final scaler = json.decode(scalerJson) as Map<String, dynamic>;
      _scalerMean = List<double>.from(
        (scaler['mean'] as List).map((v) => (v as num).toDouble()),
      );
      _scalerScale = List<double>.from(
        (scaler['scale'] as List).map((v) => (v as num).toDouble()),
      );
      _featureColumns = List<String>.from(scaler['feature_columns'] as List);

      // Load decision tree ensemble (100 trees from risk_model.pkl).
      // Python's json.dump writes bare NaN for leaf-node thresholds, which
      // is not valid JSON. Replace with -2.0 (sklearn's TREE_UNDEFINED) before
      // parsing — the tree walk exits before reading any leaf's threshold.
      final rawTreeJson = await rootBundle.loadString(
        'assets/ml_models/tree_ensemble.json',
      );
      final treeJson = rawTreeJson.replaceAll('NaN', '-2.0');
      final ensemble = json.decode(treeJson) as Map<String, dynamic>;
      _treesData = List<Map<String, dynamic>>.from(ensemble['trees'] as List);
      _nEstimators = _treesData.length;

      // Sanity check: stub has 1 tree, real model has 100
      if (_nEstimators > 1) {
        _modelVersion = '2.0-rf';
        _isReady = true;
      }
    } catch (e, stack) {
      _isReady = false;
      if (kDebugMode) {
        debugPrint('[EdgeML] initialize() failed: $e\n$stack');
      }
    }
  }

  /// Run risk prediction on a vital reading window.
  /// Returns null if the model is not loaded yet.
  EdgeRiskPrediction? predictRisk({
    required int age,
    required int baselineHr,
    required int maxSafeHr,
    required int avgHeartRate,
    required int peakHeartRate,
    required int minHeartRate,
    required int avgSpo2,
    required int durationMinutes,
    required int recoveryTimeMinutes,
    String activityType = 'walking',
  }) {
    if (!_isReady) return null;

    final stopwatch = Stopwatch()..start();

    try {
      // Step 1: Engineer the 17 features
      final features = engineerFeatures(
        age: age, baselineHr: baselineHr, maxSafeHr: maxSafeHr,
        avgHeartRate: avgHeartRate, peakHeartRate: peakHeartRate,
        minHeartRate: minHeartRate, avgSpo2: avgSpo2,
        durationMinutes: durationMinutes,
        recoveryTimeMinutes: recoveryTimeMinutes,
        activityType: activityType,
      );

      // Step 2: Build ordered feature vector
      final featureArray =
          _featureColumns.map((col) => features[col] ?? 0.0).toList();

      // Step 3: StandardScaler normalization
      final scaled = _scaleFeatures(featureArray);

      // Step 4: Walk all 100 trees and average high-risk probability
      final riskScore = _runEnsemble(scaled);

      stopwatch.stop();

      final confidence = 0.5 + (riskScore - 0.5).abs();
      final riskLevel = riskScore >= _highThreshold
          ? 'high'
          : riskScore >= _moderateThreshold
              ? 'moderate'
              : 'low';

      return EdgeRiskPrediction(
        riskScore: riskScore,
        riskLevel: riskLevel,
        confidence: confidence,
        inferenceTimeMs: stopwatch.elapsedMilliseconds,
        modelVersion: _modelVersion,
      );
    } catch (e) {
      stopwatch.stop();
      _isReady = false;
      return null;
    }
  }

  // ---- Feature Engineering (MUST match backend exactly) ----

  /// Compute the 17 features the model expects.
  /// Direct port of app/services/ml_prediction.py engineer_features().
  Map<String, double> engineerFeatures({
    required int age,
    required int baselineHr,
    required int maxSafeHr,
    required int avgHeartRate,
    required int peakHeartRate,
    required int minHeartRate,
    required int avgSpo2,
    required int durationMinutes,
    required int recoveryTimeMinutes,
    String activityType = 'walking',
  }) {
    final hrPctOfMax =
        maxSafeHr > 0 ? peakHeartRate / maxSafeHr.toDouble() : 0.0;
    final hrElevation = (avgHeartRate - baselineHr).toDouble();
    final hrRange = (peakHeartRate - minHeartRate).toDouble();
    final durationIntensity = durationMinutes * hrPctOfMax;
    final recoveryEfficiency = durationMinutes > 0
        ? recoveryTimeMinutes / durationMinutes.toDouble()
        : 0.0;
    final spo2Deviation = (98 - avgSpo2).toDouble();
    final ageRiskFactor = age / 70.0;

    const activityMapping = {
      'walking': 1, 'yoga': 1,
      'jogging': 2, 'cycling': 2,
      'swimming': 3,
    };
    final activityIntensity = (activityMapping[activityType] ?? 2).toDouble();

    return {
      'age': age.toDouble(),
      'baseline_hr': baselineHr.toDouble(),
      'max_safe_hr': maxSafeHr.toDouble(),
      'avg_heart_rate': avgHeartRate.toDouble(),
      'peak_heart_rate': peakHeartRate.toDouble(),
      'min_heart_rate': minHeartRate.toDouble(),
      'avg_spo2': avgSpo2.toDouble(),
      'duration_minutes': durationMinutes.toDouble(),
      'recovery_time_minutes': recoveryTimeMinutes.toDouble(),
      'hr_pct_of_max': hrPctOfMax,
      'hr_elevation': hrElevation,
      'hr_range': hrRange,
      'duration_intensity': durationIntensity,
      'recovery_efficiency': recoveryEfficiency,
      'spo2_deviation': spo2Deviation,
      'age_risk_factor': ageRiskFactor,
      'activity_intensity': activityIntensity,
    };
  }

  // ---- Private: ensemble inference ----

  double _runEnsemble(List<double> scaledInput) {
    if (_nEstimators == 0) return 0.5;

    double totalHighProb = 0.0;
    for (final tree in _treesData) {
      final feats   = tree['feature']        as List;
      final threshs = tree['threshold']      as List;
      final left    = tree['children_left']  as List;
      final right   = tree['children_right'] as List;
      final vals    = tree['value']          as List;

      int node = 0;
      while ((left[node] as int) != -1) {
        final fi = feats[node] as int;
        final th = (threshs[node] as num).toDouble();
        node = (fi >= 0 && fi < scaledInput.length && scaledInput[fi] <= th)
            ? left[node] as int
            : right[node] as int;
      }

      // vals[node] == [[prob_class0, prob_class1]]
      final probs = (vals[node] as List)[0] as List;
      totalHighProb += probs.length > 1
          ? (probs[1] as num).toDouble()
          : (probs[0] as num).toDouble();
    }

    return (totalHighProb / _nEstimators).clamp(0.0, 1.0);
  }

  // ---- Private: scaling ----

  List<double> _scaleFeatures(List<double> features) {
    final scaled = List<double>.filled(features.length, 0.0);
    for (int i = 0; i < features.length; i++) {
      if (i < _scalerMean.length && i < _scalerScale.length) {
        final s = _scalerScale[i];
        scaled[i] = s != 0.0 ? (features[i] - _scalerMean[i]) / s : 0.0;
      }
    }
    return scaled;
  }

  void dispose() {
    _isReady = false;
  }
}
