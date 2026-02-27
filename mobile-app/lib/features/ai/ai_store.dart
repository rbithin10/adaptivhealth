import 'package:flutter/foundation.dart';
import 'ai_api.dart';

class AiStore extends ChangeNotifier {
  final AiApi api;
  AiStore(this.api);

  bool loading = false;
  String? error;

  Map<String, dynamic>? latestVitals;
  Map<String, dynamic>? latestRisk;
  Map<String, dynamic>? latestRecommendation;

  String? cachedRiskSummary;
  String? cachedWorkoutSummary;
  String? cachedProgressSummary;
  DateTime? lastNlUpdate;

  Future<void> loadHome() async {
    loading = true;
    error = null;
    notifyListeners();

    try {
      // In parallel-ish: call sequentially for simplicity
      latestVitals = await api.getLatestVitals();
      latestRisk = await api.getMyLatestRisk();
      latestRecommendation = await api.getMyLatestRecommendation();
    } catch (e) {
      error = _prettyError(e);
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> computeAiAndRefresh() async {
    loading = true;
    error = null;
    notifyListeners();

    try {
      await api.computeMyRiskAssessment();
      latestRisk = await api.getMyLatestRisk();
      latestRecommendation = await api.getMyLatestRecommendation();
    } catch (e) {
      error = _prettyError(e);
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> loadAICoachSummaries() async {
    loading = true;
    error = null;
    notifyListeners();

    try {
      final riskFuture = api.getNLRiskSummary().catchError((_) => '');
      final workoutFuture = api.getNLTodaysWorkout().catchError((_) => '');
      final progressFuture = api.getNLProgressSummary().catchError((_) => '');

      final results = await Future.wait([riskFuture, workoutFuture, progressFuture]);
      cachedRiskSummary = results[0];
      cachedWorkoutSummary = results[1];
      cachedProgressSummary = results[2];
      lastNlUpdate = DateTime.now();
    } catch (e) {
      error = _prettyError(e);
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<String> getRiskSummaryWithCache() async {
    if (_isCacheValid()) {
      return cachedRiskSummary ?? '';
    }
    await loadAICoachSummaries();
    return cachedRiskSummary ?? '';
  }

  bool _isCacheValid() {
    if (cachedRiskSummary == null || lastNlUpdate == null) return false;
    final elapsed = DateTime.now().difference(lastNlUpdate!);
    return elapsed.inMinutes < 5;
  }

  String _prettyError(Object e) {
    final msg = e.toString();
    // You can improve this later; keep it readable for now
    if (msg.contains('404')) return 'No data yet. Submit vitals first.';
    if (msg.contains('401')) return 'Session expired. Please login again.';
    return 'Something went wrong. $msg';
  }
}
