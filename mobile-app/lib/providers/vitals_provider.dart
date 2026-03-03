import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:health/health.dart';

import '../services/api_client.dart';
import '../services/ble/ble_health_parser.dart';
import '../services/ble/ble_service.dart';
import '../services/health/health_service.dart';
import '../services/mock_vitals_service.dart';
import '../services/edge_ai_store.dart';

/// Priority-ordered source selection for vitals.
enum VitalsSource {
  ble,
  health,
  mock,
}

/// Unified vitals model for all data sources.
class VitalsReading {
  final double heartRate;
  final double? spo2;
  final double? systolicBp;
  final double? diastolicBp;
  final DateTime timestamp;
  final VitalsSource source;

  const VitalsReading({
    required this.heartRate,
    required this.timestamp,
    required this.source,
    this.spo2,
    this.systolicBp,
    this.diastolicBp,
  });
}

/// ChangeNotifier that unifies BLE, Health, and Mock vitals streams.
class VitalsProvider extends ChangeNotifier {
  final ApiClient _apiClient;
  final EdgeAiStore _edgeAiStore;
  final BleService _bleService;
  final HealthService _healthService;

  MockVitalsService? _mockVitalsService;

  final StreamController<VitalsReading> _vitalsController =
      StreamController<VitalsReading>.broadcast();

  StreamSubscription<BleHeartRateReading>? _bleReadingSubscription;
  StreamSubscription<BluetoothConnectionState>? _bleConnectionSubscription;
  StreamSubscription<VitalReading>? _mockSubscription;

  Timer? _healthPollTimer;
  DateTime? _lastHealthReadingAt;

  VitalsSource _activeSource = VitalsSource.mock;

  int? _cachedAge;
  int? _cachedBaselineHr;
  int? _cachedMaxSafeHr;

  bool _isDisposed = false;

  VitalsProvider({
    required ApiClient apiClient,
    required EdgeAiStore edgeAiStore,
    BleService? bleService,
    HealthService? healthService,
  })  : _apiClient = apiClient,
        _edgeAiStore = edgeAiStore,
        _bleService = bleService ?? BleService.instance,
        _healthService = healthService ?? HealthService.instance {
    _listenToBleConnectionState();
    _loadPatientContext();
  }

  VitalsSource get activeSource => _activeSource;

  Stream<VitalsReading> get vitalsStream => _vitalsController.stream;

  bool get isConnected =>
      _activeSource == VitalsSource.ble || _activeSource == VitalsSource.health;

  Future<void> connectBle(BluetoothDevice device) async {
    await _stopMockSource();

    await _bleService.connectToDevice(device);

    _bleReadingSubscription?.cancel();
    _bleReadingSubscription = _bleService.heartRateStream.listen((reading) {
      final unified = VitalsReading(
        heartRate: reading.heartRate.toDouble(),
        spo2: null,
        systolicBp: null,
        diastolicBp: null,
        timestamp: reading.timestamp,
        source: VitalsSource.ble,
      );

      _emitReading(unified);
      _sendToEdgeAi(unified);
    });

    _setActiveSource(VitalsSource.ble);
  }

  Future<void> enableHealthKit() async {
    final authorized = await _healthService.requestAuthorization();
    if (!authorized) {
      fallbackToMock();
      return;
    }

    await _stopMockSource();
    _setActiveSource(VitalsSource.health);

    await _pollHealthAndEmit();

    _healthPollTimer?.cancel();
    _healthPollTimer = Timer.periodic(
      const Duration(seconds: 20),
      (_) => _pollHealthAndEmit(),
    );
  }

  void fallbackToMock() {
    _activateMockSource();
  }

  void _listenToBleConnectionState() {
    _bleConnectionSubscription?.cancel();
    _bleConnectionSubscription =
        _bleService.connectionStateStream.listen((state) async {
      if (_activeSource != VitalsSource.ble) {
        return;
      }

      if (state == BluetoothConnectionState.disconnected) {
        final healthActivated = await _tryEnableHealthSource();
        if (!healthActivated) {
          fallbackToMock();
        }
      }
    });
  }

  Future<bool> _tryEnableHealthSource() async {
    final authorized = await _healthService.requestAuthorization();
    if (!authorized) {
      return false;
    }

    _setActiveSource(VitalsSource.health);
    await _pollHealthAndEmit();

    _healthPollTimer?.cancel();
    _healthPollTimer = Timer.periodic(
      const Duration(seconds: 20),
      (_) => _pollHealthAndEmit(),
    );

    return true;
  }

  Future<void> _pollHealthAndEmit() async {
    if (_activeSource != VitalsSource.health) {
      return;
    }

    final heartRatePoints = await _healthService.getHeartRate(
      lookback: const Duration(minutes: 15),
    );

    if (heartRatePoints.isEmpty) {
      return;
    }

    final latestHeartRatePoint = _latestPoint(heartRatePoints);
    final heartRate = _valueToDouble(latestHeartRatePoint.value);
    if (heartRate == null || heartRate <= 0) {
      return;
    }

    final spo2Points = await _healthService.getBloodOxygen(
      lookback: const Duration(minutes: 30),
    );
    final systolicPoints = await _healthService.getBloodPressureSystolic(
      lookback: const Duration(minutes: 30),
    );
    final diastolicPoints = await _healthService.getBloodPressureDiastolic(
      lookback: const Duration(minutes: 30),
    );

    final timestamp = latestHeartRatePoint.dateTo;
    if (_lastHealthReadingAt != null &&
        !timestamp.isAfter(_lastHealthReadingAt!)) {
      return;
    }

    _lastHealthReadingAt = timestamp;

    var spo2 = _latestValue(spo2Points);
    if (spo2 != null && spo2 <= 1.0) {
      spo2 = spo2 * 100.0;
    }

    final unified = VitalsReading(
      heartRate: heartRate,
      spo2: spo2,
      systolicBp: _latestValue(systolicPoints),
      diastolicBp: _latestValue(diastolicPoints),
      timestamp: timestamp,
      source: VitalsSource.health,
    );

    _emitReading(unified);
    _sendToEdgeAi(unified);
  }

  Future<void> _activateMockSource() async {
    await _stopBleReadingSubscription();
    _stopHealthPolling();

    _mockVitalsService ??= MockVitalsService(
      apiClient: _apiClient,
      edgeAiStore: _edgeAiStore,
    );

    _mockSubscription?.cancel();
    _mockSubscription = _mockVitalsService!.stream.listen((reading) {
      final unified = VitalsReading(
        heartRate: reading.heartRate.toDouble(),
        spo2: reading.spo2.toDouble(),
        systolicBp: reading.bloodPressureSystolic.toDouble(),
        diastolicBp: reading.bloodPressureDiastolic.toDouble(),
        timestamp: reading.timestamp,
        source: VitalsSource.mock,
      );
      _emitReading(unified);
    });

    if (!(_mockVitalsService!.isRunning)) {
      await _mockVitalsService!.start();
    }

    _setActiveSource(VitalsSource.mock);
  }

  Future<void> _stopMockSource() async {
    await _mockSubscription?.cancel();
    _mockSubscription = null;

    if (_mockVitalsService != null && _mockVitalsService!.isRunning) {
      _mockVitalsService!.stop();
    }
  }

  Future<void> _stopBleReadingSubscription() async {
    await _bleReadingSubscription?.cancel();
    _bleReadingSubscription = null;
  }

  void _stopHealthPolling() {
    _healthPollTimer?.cancel();
    _healthPollTimer = null;
  }

  void _setActiveSource(VitalsSource source) {
    _activeSource = source;
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  void _emitReading(VitalsReading reading) {
    if (!_vitalsController.isClosed) {
      _vitalsController.add(reading);
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

  void _sendToEdgeAi(VitalsReading reading) {
    _edgeAiStore.processVitals(
      heartRate: reading.heartRate.round(),
      spo2: reading.spo2?.round(),
      bpSystolic: reading.systolicBp?.round(),
      bpDiastolic: reading.diastolicBp?.round(),
      age: _cachedAge,
      baselineHr: _cachedBaselineHr,
      maxSafeHr: _cachedMaxSafeHr,
      activityType: _mapSourceToActivity(reading.source),
    );
  }

  String _mapSourceToActivity(VitalsSource source) {
    switch (source) {
      case VitalsSource.ble:
        return 'wearable';
      case VitalsSource.health:
        return 'healthkit';
      case VitalsSource.mock:
        return 'walking';
    }
  }

  HealthDataPoint _latestPoint(List<HealthDataPoint> points) {
    points.sort((a, b) => a.dateTo.compareTo(b.dateTo));
    return points.last;
  }

  double? _latestValue(List<HealthDataPoint> points) {
    if (points.isEmpty) {
      return null;
    }
    final latest = _latestPoint(points);
    return _valueToDouble(latest.value);
  }

  double? _valueToDouble(dynamic value) {
    if (value == null) {
      return null;
    }

    if (value is num) {
      return value.toDouble();
    }

    try {
      final numeric = value.numericValue;
      if (numeric is num) {
        return numeric.toDouble();
      }
    } catch (_) {
      // ignore dynamic access failure
    }

    final raw = value.toString();
    final match = RegExp(r'-?\d+(\.\d+)?').firstMatch(raw);
    if (match == null) {
      return null;
    }

    return double.tryParse(match.group(0)!);
  }

  int? _toInt(dynamic value) {
    if (value is int) return value;
    if (value is double) return value.round();
    if (value is String) return int.tryParse(value);
    return null;
  }

  @override
  void dispose() {
    _isDisposed = true;

    _bleReadingSubscription?.cancel();
    _bleConnectionSubscription?.cancel();
    _mockSubscription?.cancel();
    _healthPollTimer?.cancel();

    _mockVitalsService?.dispose();
    _vitalsController.close();

    super.dispose();
  }
}
