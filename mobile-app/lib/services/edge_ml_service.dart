/*
Edge ML Service — on-device cardiac risk prediction.

Uses a trained RandomForest model (100 decision trees, 97.5% accuracy)
that was exported from the Python backend. Runs entirely offline using
pure Dart math — no internet, no native plugins, works on all platforms.

The model takes 17 health features (heart rate, blood oxygen, age, etc.)
and predicts whether the patient is at low, moderate, or high cardiac risk.

If the model files fail to load, this service gracefully falls back
to threshold-only alerts (handled by EdgeAiStore).
*/
library;

// Converts JSON text into Dart objects
import 'dart:convert';
// Gives us debugging tools and kDebugMode flag
import 'package:flutter/foundation.dart';
// Lets us load files bundled inside the app (like the AI model)
import 'package:flutter/services.dart' show rootBundle;
// Our data model for AI risk predictions
import '../models/edge_prediction.dart';

// The AI engine that runs cardiac risk predictions on the phone itself
class EdgeMLService {
  // Whether the AI model has been loaded and is ready to use
  bool _isReady = false;
  // Version label for the loaded model (e.g. "2.0-rf" for RandomForest)
  String _modelVersion = 'unknown';

  // The average value for each feature — used to center inputs before prediction  
  List<double> _scalerMean = [];
  // The spread value for each feature — used to normalize inputs before prediction
  List<double> _scalerScale = [];
  // The names of the 17 features the model expects, in order
  List<String> _featureColumns = [];

  // The 100 decision trees that make up the RandomForest model
  List<Map<String, dynamic>> _treesData = [];
  // How many trees are in the forest (should be 100 for the real model)
  int _nEstimators = 0;

  // Risk score above this = "high" risk (80%)
  final double _highThreshold = 0.80;
  // Risk score above this = "moderate" risk (50%)
  final double _moderateThreshold = 0.50;

  // ---- Public API ----

  // Whether the AI model is loaded and ready to make predictions
  bool get isReady => _isReady;
  // The version of the loaded AI model
  String get modelVersion => _modelVersion;

  // Load the AI model files from the app bundle (call once after login)
  Future<void> initialize() async {
    try {
      // --- Load the StandardScaler parameters (mean + scale for each feature) ---
      final rawScalerJson = await rootBundle.loadString(
        'assets/ml_models/scaler_params.json',
      );
      // Python sometimes exports "NaN" which Dart can't parse — replace with 0.0
      final scalerJson = rawScalerJson.replaceAll('NaN', '0.0');
      // Parse the JSON into a Dart map
      final scaler = json.decode(scalerJson) as Map<String, dynamic>;
      // Extract the list of mean values (one per feature)
      _scalerMean = List<double>.from(
        (scaler['mean'] as List).map((v) => (v as num).toDouble()),
      );
      // Extract the list of scale values (one per feature)
      _scalerScale = List<double>.from(
        (scaler['scale'] as List).map((v) => (v as num).toDouble()),
      );
      // Extract the ordered list of feature names
      _featureColumns = List<String>.from(scaler['feature_columns'] as List);

      // --- Load the decision tree forest (100 trees exported from Python) ---
      final rawTreeJson = await rootBundle.loadString(
        'assets/ml_models/tree_ensemble.json',
      );
      // Replace Python's "NaN" with -2.0 (a sentinel value trees never reach)
      final treeJson = rawTreeJson.replaceAll('NaN', '-2.0');
      // Parse the JSON into the tree structure
      final ensemble = json.decode(treeJson) as Map<String, dynamic>;
      // Store each tree's data (feature thresholds, branches, leaf values)
      _treesData = List<Map<String, dynamic>>.from(ensemble['trees'] as List);
      // Count how many trees we loaded
      _nEstimators = _treesData.length;

      // The real model has 100 trees; a stub/placeholder has just 1
      if (_nEstimators > 1) {
        _modelVersion = '2.0-rf';
        _isReady = true;
      }
    } catch (e, stack) {
      // If anything goes wrong, disable the AI model gracefully
      _isReady = false;
      if (kDebugMode) {
        debugPrint('[EdgeML] initialize() failed: $e\n$stack');
      }
    }
  }

  // Run the AI model on a set of vital signs and return a risk prediction
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
    // Can't predict if the model hasn't been loaded yet
    if (!_isReady) return null;

    // Start a timer to measure how fast the prediction runs
    final stopwatch = Stopwatch()..start();

    try {
      // Step 1: Calculate the 17 features the AI model expects
      final features = engineerFeatures(
        age: age, baselineHr: baselineHr, maxSafeHr: maxSafeHr,
        avgHeartRate: avgHeartRate, peakHeartRate: peakHeartRate,
        minHeartRate: minHeartRate, avgSpo2: avgSpo2,
        durationMinutes: durationMinutes,
        recoveryTimeMinutes: recoveryTimeMinutes,
        activityType: activityType,
      );

      // Step 2: Put features in the exact order the model expects
      final featureArray =
          _featureColumns.map((col) => features[col] ?? 0.0).toList();

      // Step 3: Normalize each feature to be on the same scale
      final scaled = _scaleFeatures(featureArray);

      // Step 4: Run every tree and average their risk scores
      final riskScore = _runEnsemble(scaled);

      stopwatch.stop();

      // Calculate how confident the model is (closer to 0 or 1 = more confident)
      final confidence = 0.5 + (riskScore - 0.5).abs();
      // Convert the numeric score to a human-readable risk level
      final riskLevel = riskScore >= _highThreshold
          ? 'high'
          : riskScore >= _moderateThreshold
              ? 'moderate'
              : 'low';

      // Return the complete prediction result
      return EdgeRiskPrediction(
        riskScore: riskScore,
        riskLevel: riskLevel,
        confidence: confidence,
        inferenceTimeMs: stopwatch.elapsedMilliseconds,
        modelVersion: _modelVersion,
      );
    } catch (e) {
      stopwatch.stop();
      // If prediction fails, disable the model to prevent repeated errors
      _isReady = false;
      return null;
    }
  }

  // ---- Feature Engineering (MUST match the Python backend exactly) ----

  // Calculate the 17 features the AI model needs from raw vital signs
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
    // What percentage of their maximum safe heart rate did they reach?
    final hrPctOfMax =
        maxSafeHr > 0 ? peakHeartRate / maxSafeHr.toDouble() : 0.0;
    // How much higher is their current heart rate versus their resting baseline?
    final hrElevation = (avgHeartRate - baselineHr).toDouble();
    // The spread between highest and lowest heart rate during the session
    final hrRange = (peakHeartRate - minHeartRate).toDouble();
    // How intense was the session? (longer + harder = higher number)
    final durationIntensity = durationMinutes * hrPctOfMax;
    // How long did recovery take relative to the session? (higher = slower recovery)
    final recoveryEfficiency = durationMinutes > 0
        ? recoveryTimeMinutes / durationMinutes.toDouble()
        : 0.0;
    // How far below normal (98%) is their blood oxygen?
    final spo2Deviation = (98 - avgSpo2).toDouble();
    // Age-based risk factor (older = higher risk, normalized to 70)
    final ageRiskFactor = age / 70.0;

    // Convert activity names to intensity levels (1=light, 2=moderate, 3=high)
    const activityMapping = {
      'walking': 1, 'yoga': 1,
      'jogging': 2, 'cycling': 2,
      'swimming': 3,
    };
    final activityIntensity = (activityMapping[activityType] ?? 2).toDouble();

    // Return all 17 features as a named map
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

  // ---- Private: walk all 100 decision trees and average their votes ----

  double _runEnsemble(List<double> scaledInput) {
    // If no trees loaded, return a neutral 50% score
    if (_nEstimators == 0) return 0.5;

    // Sum up the "high risk" probability from each tree
    double totalHighProb = 0.0;
    for (final tree in _treesData) {
      // Each tree has: which feature to check at each node, the threshold,
      // which child to go to if less/greater, and the final probabilities
      final feats   = tree['feature']        as List;
      final threshs = tree['threshold']      as List;
      final left    = tree['children_left']  as List;
      final right   = tree['children_right'] as List;
      final vals    = tree['value']          as List;

      // Start at the root of the tree and walk down
      int node = 0;
      // Keep going until we reach a leaf node (leaf = no more children)
      while ((left[node] as int) != -1) {
        // Which feature does this node check?
        final fi = feats[node] as int;
        // What's the threshold for this node's decision?
        final th = (threshs[node] as num).toDouble();
        // Go left if feature value <= threshold, right otherwise
        node = (fi >= 0 && fi < scaledInput.length && scaledInput[fi] <= th)
            ? left[node] as int
            : right[node] as int;
      }

      // At the leaf: read the probability of "high risk" (class 1)
      final probs = (vals[node] as List)[0] as List;
      totalHighProb += probs.length > 1
          ? (probs[1] as num).toDouble()
          : (probs[0] as num).toDouble();
    }

    // Average all tree votes and clamp between 0.0 and 1.0
    return (totalHighProb / _nEstimators).clamp(0.0, 1.0);
  }

  // ---- Private: normalize raw features using StandardScaler ----

  List<double> _scaleFeatures(List<double> features) {
    // Create an output array filled with zeros
    final scaled = List<double>.filled(features.length, 0.0);
    for (int i = 0; i < features.length; i++) {
      if (i < _scalerMean.length && i < _scalerScale.length) {
        final s = _scalerScale[i];
        // Subtract the mean and divide by the scale (standard normalization)
        scaled[i] = s != 0.0 ? (features[i] - _scalerMean[i]) / s : 0.0;
      }
    }
    return scaled;
  }

  // Clean up when the service is no longer needed
  void dispose() {
    _isReady = false;
  }
}
