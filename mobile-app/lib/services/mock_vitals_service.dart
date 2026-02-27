// DEV ONLY: Mock vitals generator for demos. This simulates a wearable device; do not use in production.

import 'dart:async';
import 'dart:math';

import 'api_client.dart';
import 'edge_ai_store.dart';

// ---------------------------------------------------------------------------
// Scenario enum — 4 realistic physiological scenarios
// ---------------------------------------------------------------------------

enum MockScenario {
  rest,       // Resting baseline: HR ~68, SpO2 97-99%, calm BP, high HRV
  workout,    // Full workout: warmup → steady → peak → cooldown (90 ticks)
  sleep,      // NREM/REM cycling: bradycardia, autonomic BP dip, high HRV
  emergency,  // Critical event: HR>180, SpO2<90, BP>160 → all 3 alert types
}

// ---------------------------------------------------------------------------
// VitalReading — extended with BP, HRV, scenario, phase
// ---------------------------------------------------------------------------

class VitalReading {
  final DateTime timestamp;
  final int heartRate;
  final int spo2;
  final int bloodPressureSystolic;
  final int bloodPressureDiastolic;
  final double? hrv;        // RMSSD in ms (heart rate variability)
  final MockScenario scenario;
  final String phase;       // 'rest', 'warmup', 'steady', 'peak', 'cooldown',
                            // 'nrem1', 'nrem2', 'deep_sleep', 'rem',
                            // 'critical', 'recovery', 'post_event'

  const VitalReading({
    required this.timestamp,
    required this.heartRate,
    required this.spo2,
    required this.bloodPressureSystolic,
    required this.bloodPressureDiastolic,
    this.hrv,
    required this.scenario,
    required this.phase,
  });
}

// ---------------------------------------------------------------------------
// Internal data bundle (avoids Dart record syntax for broader compatibility)
// ---------------------------------------------------------------------------

class _Vitals {
  final int hr;
  final int spo2;
  final int bpSys;
  final int bpDia;
  final double hrv;
  final String phase;

  const _Vitals(this.hr, this.spo2, this.bpSys, this.bpDia, this.hrv, this.phase);
}

// ---------------------------------------------------------------------------
// MockVitalsService
// ---------------------------------------------------------------------------

class MockVitalsService {
  final ApiClient _apiClient;
  final EdgeAiStore _edgeAiStore;
  final Random _random = Random();

  final StreamController<VitalReading> _controller =
      StreamController<VitalReading>.broadcast();

  Timer? _timer;
  MockScenario _scenario = MockScenario.rest;
  int _scenarioTick = 0;      // increments each interval tick
  String _currentPhase = 'rest';
  double _cooldownStartHr = 160; // HR at start of cooldown (set during workout peak)

  int? _cachedAge;
  int? _cachedBaselineHr;
  int? _cachedMaxSafeHr;

  MockVitalsService({
    required ApiClient apiClient,
    required EdgeAiStore edgeAiStore,
  })  : _apiClient = apiClient,
        _edgeAiStore = edgeAiStore;

  Stream<VitalReading> get stream => _controller.stream;
  bool get isRunning => _timer != null;
  MockScenario get currentScenario => _scenario;
  String get currentPhase => _currentPhase;

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  Future<void> start({
    Duration interval = const Duration(seconds: 5),
    MockScenario scenario = MockScenario.rest,
  }) async {
    if (isRunning) return;

    _scenario = scenario;
    _scenarioTick = 0;
    _currentPhase = _initialPhase(scenario);
    await _loadPatientContext();

    _timer = Timer.periodic(interval, (_) {
      _emitReading();
    });

    await _emitReading();
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
  }

  /// Switch scenario mid-stream (resets tick counter to start of new scenario).
  void setScenario(MockScenario scenario) {
    _scenario = scenario;
    _scenarioTick = 0;
    _currentPhase = _initialPhase(scenario);
  }

  Future<void> dispose() async {
    stop();
    await _controller.close();
  }

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  String _initialPhase(MockScenario scenario) {
    switch (scenario) {
      case MockScenario.rest:
        return 'rest';
      case MockScenario.workout:
        return 'warmup';
      case MockScenario.sleep:
        return 'nrem1';
      case MockScenario.emergency:
        return 'critical';
    }
  }

  Future<void> _loadPatientContext() async {
    try {
      final user = await _apiClient.getCurrentUser();
      final age = _toInt(user['age']);
      final baseline = _toInt(user['baseline_hr'] ?? user['resting_hr']);

      _cachedAge = age != null && age > 0 ? age : 35;
      _cachedBaselineHr = baseline != null && baseline > 0 ? baseline : 72;
      _cachedMaxSafeHr = 220 - (_cachedAge ?? 35);
    } catch (_) {
      _cachedAge = 35;
      _cachedBaselineHr = 72;
      _cachedMaxSafeHr = 185;
    }
  }

  Future<void> _emitReading() async {
    final baseline = _cachedBaselineHr ?? 72;
    final maxHr = _cachedMaxSafeHr ?? 185;

    final v = _generateVitals(baseline, maxHr);
    _currentPhase = v.phase;

    final reading = VitalReading(
      timestamp: DateTime.now(),
      heartRate: v.hr,
      spo2: v.spo2,
      bloodPressureSystolic: v.bpSys,
      bloodPressureDiastolic: v.bpDia,
      hrv: v.hrv,
      scenario: _scenario,
      phase: v.phase,
    );

    _controller.add(reading);
    _scenarioTick++;

    // Pass ALL vitals to Edge AI (threshold checks + TFLite risk prediction)
    await _edgeAiStore.processVitals(
      heartRate: reading.heartRate,
      spo2: reading.spo2,
      bpSystolic: reading.bloodPressureSystolic,
      bpDiastolic: reading.bloodPressureDiastolic,
      age: _cachedAge,
      baselineHr: _cachedBaselineHr,
      maxSafeHr: _cachedMaxSafeHr,
      activityType: _activityType(v.phase),
    );

    try {
      await _apiClient.submitVitalSigns(
        heartRate: reading.heartRate,
        spo2: reading.spo2,
        systolicBp: reading.bloodPressureSystolic,
        diastolicBp: reading.bloodPressureDiastolic,
        hrv: reading.hrv,
        timestamp: reading.timestamp,
      );
    } catch (_) {
      // Keep simulator running even if backend submit fails.
    }
  }

  // ---------------------------------------------------------------------------
  // Vital sign generation — routes to per-scenario logic
  // ---------------------------------------------------------------------------

  _Vitals _generateVitals(int baseline, int maxHr) {
    switch (_scenario) {
      case MockScenario.rest:
        return _restVitals(baseline);
      case MockScenario.workout:
        return _workoutVitals(baseline, maxHr);
      case MockScenario.sleep:
        return _sleepVitals(baseline);
      case MockScenario.emergency:
        return _emergencyVitals(baseline);
    }
  }

  // ---------------------------------------------------------------------------
  // REST scenario
  // Calm resting state: HR near baseline, high HRV, normal BP.
  // ---------------------------------------------------------------------------

  _Vitals _restVitals(int baseline) {
    final hr = _clampInt(_gaussInt(baseline, 5), 50, 100);
    final spo2 = _clampInt(_gaussInt(98, 1), 95, 100);
    final bpSys = _clampInt(_gaussInt(112, 5), 100, 130);
    final bpDia = _clampInt(_gaussInt(72, 3), 60, 85);
    final hrv = _clampDouble(_gaussDouble(42, 4), 25, 65);
    return _Vitals(hr, spo2, bpSys, bpDia, hrv, 'rest');
  }

  // ---------------------------------------------------------------------------
  // WORKOUT scenario (90-tick cycle ≈ 7.5 min real time at 5-s interval)
  //
  // Ticks  0- 9: warmup   — HR rises linearly from baseline to ~100 BPM
  // Ticks 10-29: steady   — HR Gaussian around 82% max (WARNING zone near 150)
  // Ticks 30-39: peak     — HR Gaussian around 90% max (crosses 150+ → alert)
  // Ticks 40-89: cooldown — exponential decay back to baseline
  // Loops back at tick 90.
  // ---------------------------------------------------------------------------

  _Vitals _workoutVitals(int baseline, int maxHr) {
    final tick = _scenarioTick % 90;

    int hr;
    double hrv;
    String phase;

    if (tick < 10) {
      // Warmup: linear rise
      final progress = tick / 10.0;
      final target = baseline + (100 - baseline) * progress;
      hr = _clampInt(_gaussInt(target, 4), baseline, 115);
      hrv = _clampDouble(_gaussDouble(35, 3), 20, 50);
      phase = 'warmup';
    } else if (tick < 30) {
      // Steady: 80–85% max HR
      final steadyTarget = maxHr * 0.82;
      hr = _clampInt(_gaussInt(steadyTarget, 6), 100, 160);
      hrv = _clampDouble(_gaussDouble(22, 3), 10, 35);
      phase = 'steady';
    } else if (tick < 40) {
      // Peak: 88–93% max HR — crosses WARNING threshold (>150 BPM)
      final peakTarget = maxHr * 0.90;
      hr = _clampInt(_gaussInt(peakTarget, 4), 148, maxHr - 3);
      hrv = _clampDouble(_gaussDouble(12, 2), 5, 20);
      phase = 'peak';
      // Record peak HR for exponential decay in cooldown
      if (tick == 30) _cooldownStartHr = hr.toDouble();
    } else {
      // Cooldown: exponential decay  τ = 10 ticks ≈ 50 s (realistic cardiac recovery)
      final t = (tick - 40).toDouble();
      final decayHr = baseline + (_cooldownStartHr - baseline) * exp(-t / 10.0);
      hr = _clampInt(_gaussInt(decayHr, 3), baseline - 5, maxHr);
      final recoveryFraction = (t / 50.0).clamp(0.0, 1.0);
      hrv = _clampDouble(_gaussDouble(12 + 28 * recoveryFraction, 3), 5, 50);
      phase = 'cooldown';
    }

    final spo2 = _spo2FromHr(hr);
    final bpSys = _bpSysFromHr(hr, baseline);
    final bpDia = _bpDiaFromHr(hr, baseline);

    return _Vitals(hr, spo2, bpSys, bpDia, hrv, phase);
  }

  // ---------------------------------------------------------------------------
  // SLEEP scenario — 18-tick NREM/REM cycles
  //
  // Each 18-tick cycle ≈ 90-min sleep cycle (compressed to 1.5 real minutes):
  //   NREM1 (ticks 0–3):   light sleep, HR ~58
  //   NREM2 (ticks 4–8):   true sleep, HR ~54
  //   NREM3 (ticks 9–12):  deep sleep, HR ~50, highest HRV
  //   REM   (ticks 13–17): REM sleep, HR ~62, more variable
  // ---------------------------------------------------------------------------

  _Vitals _sleepVitals(int baseline) {
    final cyclePos = _scenarioTick % 18;

    int hrMean;
    double spo2Mean;
    double hrvMean;
    int bpSysMean;
    int bpDiaMean;
    String phase;

    if (cyclePos < 4) {
      hrMean = (baseline * 0.84).round();
      spo2Mean = 96.5;
      hrvMean = 42;
      bpSysMean = 108;
      bpDiaMean = 66;
      phase = 'nrem1';
    } else if (cyclePos < 9) {
      hrMean = (baseline * 0.77).round();
      spo2Mean = 96.0;
      hrvMean = 52;
      bpSysMean = 104;
      bpDiaMean = 63;
      phase = 'nrem2';
    } else if (cyclePos < 13) {
      hrMean = (baseline * 0.70).round();  // deep sleep: ~50 BPM at baseline 72
      spo2Mean = 95.0;
      hrvMean = 60;
      bpSysMean = 100;
      bpDiaMean = 60;
      phase = 'deep_sleep';
    } else {
      // REM: slightly elevated HR, more variable than NREM
      hrMean = (baseline * 0.87).round();
      spo2Mean = 95.8;
      hrvMean = 33;
      bpSysMean = 106;
      bpDiaMean = 65;
      phase = 'rem';
    }

    final hr = _clampInt(_gaussInt(hrMean.toDouble(), 3), 40, 80);
    final spo2 = _clampInt(_gaussInt(spo2Mean, 0.6), 88, 100);
    final bpSys = _clampInt(_gaussInt(bpSysMean.toDouble(), 4), 88, 125);
    final bpDia = _clampInt(_gaussInt(bpDiaMean.toDouble(), 3), 50, 80);
    final hrv = _clampDouble(_gaussDouble(hrvMean, 4), 20, 80);

    return _Vitals(hr, spo2, bpSys, bpDia, hrv, phase);
  }

  // ---------------------------------------------------------------------------
  // EMERGENCY scenario
  //
  // Ticks  0-23: critical — HR 181-200, SpO2 85-89, BP 162-185
  //              → triggers all 3 backend alert types simultaneously
  // Ticks 24-47: recovery — exponential decay back to baseline
  // Ticks 48+:   post-event rest
  // ---------------------------------------------------------------------------

  _Vitals _emergencyVitals(int baseline) {
    if (_scenarioTick < 24) {
      // Critical phase: cross ALL backend thresholds
      // Backend: HR > 180 → CRITICAL, SpO2 < 90 → CRITICAL, BP > 160 → WARNING
      final hr = _clampInt(_gaussInt(188, 4), 181, 200);
      final spo2 = _clampInt(_gaussInt(87, 1), 84, 89);
      final bpSys = _clampInt(_gaussInt(172, 5), 162, 185);
      final bpDia = _clampInt(_gaussInt(102, 4), 90, 115);
      final hrv = _clampDouble(_gaussDouble(6, 1.5), 3, 12);
      return _Vitals(hr, spo2, bpSys, bpDia, hrv, 'critical');
    } else if (_scenarioTick < 48) {
      // Recovery: exponential decay toward baseline
      final t = (_scenarioTick - 24).toDouble();
      final hr = _clampInt(
        _gaussInt(baseline + (188 - baseline) * exp(-t / 8), 3),
        baseline - 5, 195,
      );
      final spo2 = _clampInt(
        (87 + 10 * (1 - exp(-t / 6))).round(),
        87, 100,
      );
      final bpSys = _clampInt(
        (172 - 55 * (1 - exp(-t / 8))).round() + _gaussInt(0, 4),
        115, 180,
      );
      final bpDia = _clampInt(
        (102 - 22 * (1 - exp(-t / 8))).round() + _gaussInt(0, 3),
        65, 110,
      );
      final hrv = _clampDouble(
        _gaussDouble(6 + 30 * (1 - exp(-t / 10)), 2),
        5, 45,
      );
      return _Vitals(hr, spo2, bpSys, bpDia, hrv, 'recovery');
    } else {
      // Settled back to rest after event completes
      return _restVitals(baseline).withPhase('post_event');
    }
  }

  // ---------------------------------------------------------------------------
  // Physiological derived values
  // ---------------------------------------------------------------------------

  /// SpO2 inversely correlated with HR (elevated HR reduces peripheral saturation).
  int _spo2FromHr(int hr) {
    final base = (99 - ((hr - 70) * 0.030)).round();
    return _clampInt(base + _gaussInt(0, 1), 88, 100);
  }

  /// Systolic BP tracks HR with sympathetic nervous system lag.
  int _bpSysFromHr(int hr, int baseline) =>
      _clampInt(120 + ((hr - baseline) * 0.35).round() + _gaussInt(0, 4), 90, 190);

  /// Diastolic BP modest increase during exercise.
  int _bpDiaFromHr(int hr, int baseline) =>
      _clampInt(80 + ((hr - baseline) * 0.10).round() + _gaussInt(0, 3), 55, 115);

  // ---------------------------------------------------------------------------
  // Activity type for Edge AI / backend annotation
  // ---------------------------------------------------------------------------

  String _activityType(String phase) {
    switch (phase) {
      case 'warmup':     return 'walking';
      case 'steady':     return 'jogging';
      case 'peak':       return 'running';
      case 'cooldown':   return 'walking';
      case 'deep_sleep': return 'resting';
      case 'nrem1':
      case 'nrem2':
      case 'rem':        return 'resting';
      case 'critical':
      case 'recovery':
      case 'post_event': return 'resting';
      default:           return 'resting';
    }
  }

  // ---------------------------------------------------------------------------
  // Math helpers
  // ---------------------------------------------------------------------------

  /// Gaussian random using Box-Muller transform (Dart has no built-in).
  double _gaussDouble(double mean, double sigma) {
    final u1 = (_random.nextDouble()).clamp(1e-10, 1.0);
    final u2 = _random.nextDouble();
    final z = sqrt(-2.0 * log(u1)) * cos(2.0 * pi * u2);
    return mean + sigma * z;
  }

  int _gaussInt(num mean, double sigma) =>
      _gaussDouble(mean.toDouble(), sigma).round();

  int _clampInt(int value, int min, int max) => value.clamp(min, max);

  double _clampDouble(double value, double min, double max) =>
      value.clamp(min, max);

  int? _toInt(dynamic value) {
    if (value == null) return null;
    if (value is int) return value;
    if (value is double) return value.round();
    return int.tryParse(value.toString());
  }
}

// ---------------------------------------------------------------------------
// Extension to support withPhase() on _Vitals for the post_event transition
// ---------------------------------------------------------------------------

extension _VitalsPhase on _Vitals {
  _Vitals withPhase(String newPhase) =>
      _Vitals(hr, spo2, bpSys, bpDia, hrv, newPhase);
}
