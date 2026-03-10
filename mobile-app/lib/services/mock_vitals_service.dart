/*
Mock Vitals Service — DEVELOPMENT ONLY.

Simulates a wearable device sending health data for testing purposes.
Generates realistic heart rate, blood oxygen, blood pressure, and HRV
readings that follow real physiological patterns.

Do NOT use in production — this is only for demos and testing.
*/

// Timers for periodic vital sign generation
import 'dart:async';
// Random numbers and math functions for realistic vital sign simulation
import 'dart:math';

// Talks to the server to submit simulated readings
import 'api_client.dart';
// Sends simulated vitals through the AI for testing
import 'edge_ai_store.dart';

// ---------------------------------------------------------------------------
// Scenario enum — 4 realistic physiological scenarios
// ---------------------------------------------------------------------------

// The 4 different health scenarios we can simulate
enum MockScenario {
  rest,       // Calm resting: HR ~68, SpO2 97-99%, normal blood pressure
  workout,    // Full exercise: warmup → steady → peak → cooldown (90 ticks)
  sleep,      // Sleep cycles: NREM and REM with low heart rate, BP dip
  emergency,  // Life-threatening: HR>180, SpO2<90, BP>160 — triggers all alerts
}

// ---------------------------------------------------------------------------
// VitalReading — extended with BP, HRV, scenario, phase
// ---------------------------------------------------------------------------

// One simulated health reading with all vital signs and context
class VitalReading {
  // When this reading was generated
  final DateTime timestamp;
  // Simulated heart rate in beats per minute
  final int heartRate;
  // Simulated blood oxygen percentage
  final int spo2;
  // Simulated top blood pressure number
  final int bloodPressureSystolic;
  // Simulated bottom blood pressure number
  final int bloodPressureDiastolic;
  // Heart rate variability — how much time between heartbeats varies
  final double? hrv;
  // Which scenario generated this reading (rest, workout, sleep, emergency)
  final MockScenario scenario;
  // Current phase within the scenario (e.g. 'warmup', 'peak', 'deep_sleep')
  final String phase;

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

// Internal data bundle that holds all the numbers for one tick
class _Vitals {
  final int hr;       // Heart rate
  final int spo2;     // Blood oxygen
  final int bpSys;    // Systolic blood pressure (top number)
  final int bpDia;    // Diastolic blood pressure (bottom number)
  final double hrv;   // Heart rate variability
  final String phase; // Current phase label

  const _Vitals(this.hr, this.spo2, this.bpSys, this.bpDia, this.hrv, this.phase);
}

// ---------------------------------------------------------------------------
// MockVitalsService
// ---------------------------------------------------------------------------

// The main mock simulator — generates fake vital signs on a timer
class MockVitalsService {
  // Sends simulated vitals to the server
  final ApiClient _apiClient;
  // Processes simulated vitals through the AI system
  final EdgeAiStore _edgeAiStore;
  // Random number generator for realistic variation
  final Random _random = Random();

  // Broadcasts readings to anyone listening (like a real device stream)
  final StreamController<VitalReading> _controller =
      StreamController<VitalReading>.broadcast();

  // Timer that fires every 5 seconds to generate a new reading
  Timer? _timer;
  // Which scenario we're currently running
  MockScenario _scenario = MockScenario.rest;
  // How many ticks have passed since the scenario started
  int _scenarioTick = 0;
  // What phase of the scenario we're in (e.g. 'warmup', 'peak')
  String _currentPhase = 'rest';
  // Heart rate at the start of cooldown (used for realistic decay)
  double _cooldownStartHr = 160;

  // Workout session tracking for activity API lifecycle
  int? _workoutSessionId;
  final List<int> _workoutHrValues = [];
  int _workoutPeakHr = 0;

  // Cached patient info from the server (used for realistic ranges)
  int? _cachedAge;
  int? _cachedBaselineHr;
  int? _cachedMaxSafeHr;

  MockVitalsService({
    required ApiClient apiClient,
    required EdgeAiStore edgeAiStore,
  })  : _apiClient = apiClient,
        _edgeAiStore = edgeAiStore;

  // Listen to the stream of simulated readings
  Stream<VitalReading> get stream => _controller.stream;
  // Check if the simulator is currently running
  bool get isRunning => _timer != null;
  // Which scenario is currently active
  MockScenario get currentScenario => _scenario;
  // What phase of the scenario we're in right now
  String get currentPhase => _currentPhase;

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  // Start the simulator — generates a new reading every 5 seconds
  Future<void> start({
    Duration interval = const Duration(seconds: 5),
    MockScenario scenario = MockScenario.rest,
  }) async {
    // Don't start twice
    if (isRunning) return;

    // Set up the scenario
    _scenario = scenario;
    _scenarioTick = 0;
    _currentPhase = _initialPhase(scenario);
    // Load the patient's age and baseline HR for realistic ranges
    await _loadPatientContext();

    // Start the periodic timer
    _timer = Timer.periodic(interval, (_) {
      _emitReading();
    });

    // Generate the first reading immediately
    await _emitReading();
  }

  // Stop the simulator
  void stop() {
    _timer?.cancel();
    _timer = null;
    _resetWorkoutSession();
  }

  // Switch to a different scenario mid-stream
  void setScenario(MockScenario scenario) {
    _resetWorkoutSession();
    _scenario = scenario;
    _scenarioTick = 0;
    _currentPhase = _initialPhase(scenario);
  }

  // Clean up everything when the service is no longer needed
  Future<void> dispose() async {
    stop();
    await _controller.close();
  }

  // End any in-progress workout session (fire-and-forget)
  void _resetWorkoutSession() {
    if (_workoutSessionId == null) return;
    final avgHr = _workoutHrValues.isEmpty
        ? 0
        : (_workoutHrValues.reduce((a, b) => a + b) / _workoutHrValues.length).round();
    _apiClient.endSession(
      sessionId: _workoutSessionId!,
      avgHeartRate: avgHr,
      maxHeartRate: _workoutPeakHr,
    ).catchError((_) => <String, dynamic>{});
    _workoutSessionId = null;
    _workoutHrValues.clear();
    _workoutPeakHr = 0;
  }

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  // What's the starting phase for each scenario?
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

  // Load the patient's real age and resting heart rate from the server
  Future<void> _loadPatientContext() async {
    try {
      // Get the user's profile from the server
      final user = await _apiClient.getCurrentUser();
      final age = _toInt(user['age']);
      final baseline = _toInt(user['baseline_hr'] ?? user['resting_hr']);

      // Use real values if available, otherwise use healthy defaults
      _cachedAge = age != null && age > 0 ? age : 35;
      _cachedBaselineHr = baseline != null && baseline > 0 ? baseline : 72;
      // Maximum safe heart rate is roughly 220 minus age
      _cachedMaxSafeHr = 220 - (_cachedAge ?? 35);
    } catch (_) {
      // Can't reach server — use safe defaults for a 35-year-old
      _cachedAge = 35;
      _cachedBaselineHr = 72;
      _cachedMaxSafeHr = 185;
    }
  }

  // Generate one reading and send it to listeners, AI, and server
  Future<void> _emitReading() async {
    final baseline = _cachedBaselineHr ?? 72;
    final maxHr = _cachedMaxSafeHr ?? 185;

    // Generate vital signs based on the current scenario and tick
    final v = _generateVitals(baseline, maxHr);
    _currentPhase = v.phase;

    // Package the numbers into a VitalReading object
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

    // Broadcast the reading to anyone listening
    _controller.add(reading);

    // --- Activity session lifecycle for workout scenario ---
    if (_scenario == MockScenario.workout) {
      final tick = _scenarioTick % 90;
      if (tick == 0 && _workoutSessionId == null) {
        try {
          final result = await _apiClient.startSession(
            sessionType: 'walking',
            targetDuration: 8,
          );
          _workoutSessionId = result['session_id'] as int?;
          _workoutHrValues.clear();
          _workoutPeakHr = 0;
        } catch (_) {}
      }
      _workoutHrValues.add(reading.heartRate);
      if (reading.heartRate > _workoutPeakHr) {
        _workoutPeakHr = reading.heartRate;
      }
      if (tick == 89 && _workoutSessionId != null) {
        final avgHr = _workoutHrValues.isEmpty
            ? 0
            : (_workoutHrValues.reduce((a, b) => a + b) / _workoutHrValues.length).round();
        try {
          await _apiClient.endSession(
            sessionId: _workoutSessionId!,
            avgHeartRate: avgHr,
            maxHeartRate: _workoutPeakHr,
          );
        } catch (_) {}
        _workoutSessionId = null;
        _workoutHrValues.clear();
        _workoutPeakHr = 0;
      }
    }

    // Move to the next tick in the scenario
    _scenarioTick++;

    // Send vitals through the AI system (threshold checks + TFLite prediction)
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
      // Also submit to the server for the doctor's dashboard
      await _apiClient.submitVitalSigns(
        heartRate: reading.heartRate,
        spo2: reading.spo2,
        systolicBp: reading.bloodPressureSystolic,
        diastolicBp: reading.bloodPressureDiastolic,
        hrv: reading.hrv,
        timestamp: reading.timestamp,
      );
    } catch (_) {
      // Server submit failed — that's OK, keep generating readings
    }
  }

  // Route to the right scenario generator based on current scenario
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

  // REST scenario: calm resting state with normal vital signs
  _Vitals _restVitals(int baseline) {
    // Heart rate stays near the patient's resting baseline with small variation
    final hr = _clampInt(_gaussInt(baseline, 5), 50, 100);
    // Blood oxygen stays high: 95-100%
    final spo2 = _clampInt(_gaussInt(98, 1), 95, 100);
    // Normal resting blood pressure
    final bpSys = _clampInt(_gaussInt(112, 5), 100, 130);
    final bpDia = _clampInt(_gaussInt(72, 3), 60, 85);
    // High HRV during rest (sign of good heart health)
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

  // WORKOUT scenario: realistic exercise with warmup, steady, peak, cooldown
  _Vitals _workoutVitals(int baseline, int maxHr) {
    // 90-tick cycle: 10 warmup + 20 steady + 10 peak + 50 cooldown
    final tick = _scenarioTick % 90;

    int hr;
    double hrv;
    String phase;

    if (tick < 10) {
      // Warmup: heart rate gradually rises from resting to ~100 BPM
      final progress = tick / 10.0;
      final target = baseline + (100 - baseline) * progress;
      hr = _clampInt(_gaussInt(target, 4), baseline, 115);
      hrv = _clampDouble(_gaussDouble(35, 3), 20, 50);
      phase = 'warmup';
    } else if (tick < 30) {
      // Steady exercise: heart rate at about 82% of maximum
      final steadyTarget = maxHr * 0.82;
      hr = _clampInt(_gaussInt(steadyTarget, 6), 100, 160);
      hrv = _clampDouble(_gaussDouble(22, 3), 10, 35);
      phase = 'steady';
    } else if (tick < 40) {
      // Peak effort: heart rate at 90% of max — crosses the 150 BPM warning zone
      final peakTarget = maxHr * 0.90;
      hr = _clampInt(_gaussInt(peakTarget, 4), 148, maxHr - 3);
      hrv = _clampDouble(_gaussDouble(12, 2), 5, 20);
      phase = 'peak';
      // Record peak HR for exponential decay in cooldown
      if (tick == 30) _cooldownStartHr = hr.toDouble();
    } else {
      // Cooldown: heart rate decays back to resting (realistic exponential curve)
      final t = (tick - 40).toDouble();
      final decayHr = baseline + (_cooldownStartHr - baseline) * exp(-t / 10.0);
      hr = _clampInt(_gaussInt(decayHr, 3), baseline - 5, maxHr);
      final recoveryFraction = (t / 50.0).clamp(0.0, 1.0);
      hrv = _clampDouble(_gaussDouble(12 + 28 * recoveryFraction, 3), 5, 50);
      phase = 'cooldown';
    }

    // Calculate SpO2 and BP based on the current heart rate
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

  // SLEEP scenario: realistic NREM/REM sleep cycles with low heart rate
  _Vitals _sleepVitals(int baseline) {
    // 18-tick cycle representing a compressed 90-minute sleep cycle
    final cyclePos = _scenarioTick % 18;

    int hrMean;
    double spo2Mean;
    double hrvMean;
    int bpSysMean;
    int bpDiaMean;
    String phase;

    if (cyclePos < 4) {
      // NREM Stage 1: light sleep, heart rate about 84% of baseline
      hrMean = (baseline * 0.84).round();
      spo2Mean = 96.5;
      hrvMean = 42;
      bpSysMean = 108;
      bpDiaMean = 66;
      phase = 'nrem1';
    } else if (cyclePos < 9) {
      // NREM Stage 2: true sleep, heart rate drops to about 77% of baseline
      hrMean = (baseline * 0.77).round();
      spo2Mean = 96.0;
      hrvMean = 52;
      bpSysMean = 104;
      bpDiaMean = 63;
      phase = 'nrem2';
    } else if (cyclePos < 13) {
      // Deep sleep: lowest heart rate (~50 BPM), highest HRV, BP dips
      hrMean = (baseline * 0.70).round();
      spo2Mean = 95.0;
      hrvMean = 60;
      bpSysMean = 100;
      bpDiaMean = 60;
      phase = 'deep_sleep';
    } else {
      // REM sleep: dreaming phase, heart rate slightly elevated and more variable
      hrMean = (baseline * 0.87).round();
      spo2Mean = 95.8;
      hrvMean = 33;
      bpSysMean = 106;
      bpDiaMean = 65;
      phase = 'rem';
    }

    // Add realistic random variation to all values
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

  // EMERGENCY scenario: dangerously abnormal vitals that trigger all alerts
  _Vitals _emergencyVitals(int baseline) {
    if (_scenarioTick < 24) {
      // Critical phase: all vitals cross danger thresholds simultaneously
      // HR > 180, SpO2 < 90, BP > 160 — triggers critical alerts
      final hr = _clampInt(_gaussInt(188, 4), 181, 200);
      final spo2 = _clampInt(_gaussInt(87, 1), 84, 89);
      final bpSys = _clampInt(_gaussInt(172, 5), 162, 185);
      final bpDia = _clampInt(_gaussInt(102, 4), 90, 115);
      final hrv = _clampDouble(_gaussDouble(6, 1.5), 3, 12);
      return _Vitals(hr, spo2, bpSys, bpDia, hrv, 'critical');
    } else if (_scenarioTick < 48) {
      // Recovery: vitals gradually return to normal (exponential decay)
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
      // After the emergency: settled back to calm resting
      return _restVitals(baseline).withPhase('post_event');
    }
  }

  // ---------------------------------------------------------------------------
  // Realistic relationships between vital signs
  // ---------------------------------------------------------------------------

  // Higher heart rate slightly reduces blood oxygen (realistic relationship)
  int _spo2FromHr(int hr) {
    final base = (99 - ((hr - 70) * 0.030)).round();
    return _clampInt(base + _gaussInt(0, 1), 88, 100);
  }

  // Blood pressure rises when heart rate increases (sympathetic response)
  int _bpSysFromHr(int hr, int baseline) =>
      _clampInt(120 + ((hr - baseline) * 0.35).round() + _gaussInt(0, 4), 90, 190);

  // Bottom BP number rises modestly during exercise
  int _bpDiaFromHr(int hr, int baseline) =>
      _clampInt(80 + ((hr - baseline) * 0.10).round() + _gaussInt(0, 3), 55, 115);

  // ---------------------------------------------------------------------------
  // Convert scenario phase to activity type for the AI model
  // ---------------------------------------------------------------------------

  // Tell the AI what kind of activity the simulated patient is doing
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
  // Math helpers — generates realistic random variation
  // ---------------------------------------------------------------------------

  // Generate a random number following a bell curve (most values near the mean)
  double _gaussDouble(double mean, double sigma) {
    final u1 = (_random.nextDouble()).clamp(1e-10, 1.0);
    final u2 = _random.nextDouble();
    final z = sqrt(-2.0 * log(u1)) * cos(2.0 * pi * u2);
    return mean + sigma * z;
  }

  // Round a random double to the nearest integer
  int _gaussInt(num mean, double sigma) =>
      _gaussDouble(mean.toDouble(), sigma).round();

  // Keep an integer within a safe range
  int _clampInt(int value, int min, int max) => value.clamp(min, max);

  // Keep a decimal number within a safe range
  double _clampDouble(double value, double min, double max) =>
      value.clamp(min, max);

  // Safely convert any value to an integer (or null if it can't be converted)
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

// Helper that lets us change the phase label on a _Vitals object
extension _VitalsPhase on _Vitals {
  // Create a copy with a different phase name
  _Vitals withPhase(String newPhase) =>
      _Vitals(hr, spo2, bpSys, bpDia, hrv, newPhase);
}
