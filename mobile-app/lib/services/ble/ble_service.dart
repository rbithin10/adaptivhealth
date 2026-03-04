import 'dart:async';

import 'package:flutter/foundation.dart';
import '../../config/platform_guard.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'ble_health_parser.dart';

enum BleConnectionStatus {
  disconnected,
  scanning,
  connecting,
  connected,
  reconnecting,
}

/// BLE service singleton for Heart Rate Service (0x180D) devices.
///
/// Handles scanning, connection, auto-reconnect, and heart rate notification
/// subscription for standard BLE heart rate monitors.
class BleService {
  BleService._internal() {
    _monitorAdapterState();
    unawaited(_attemptReconnectFromSavedDevice());
  }

  static final BleService instance = BleService._internal();

  factory BleService() {
    return instance;
  }
    // Additional health service UUIDs
  static final Guid pulseOximeterServiceUuid = Guid('1822');
  static final Guid spo2ContinuousMeasurementUuid = Guid('2A5F');
  static final Guid bloodPressureServiceUuid = Guid('1810');
  static final Guid bloodPressureMeasurementUuid = Guid('2A35');
  static final Guid healthThermometerServiceUuid = Guid('1809');
  static final Guid temperatureMeasurementUuid = Guid('2A1C');


  static final Guid heartRateServiceUuid = Guid('180D');
  static final Guid heartRateMeasurementUuid = Guid('2A37');
  static const List<int> _reconnectBackoffSeconds = [2, 4, 8];
  static const String _lastDeviceIdKey = 'ble_last_device_remote_id';
  static const String _lastDeviceNameKey = 'ble_last_device_name';

  final ValueNotifier<BleConnectionStatus> connectionStatusNotifier =
      ValueNotifier<BleConnectionStatus>(BleConnectionStatus.disconnected);

  final StreamController<List<ScanResult>> _scanResultsController =
      StreamController<List<ScanResult>>.broadcast();
  final StreamController<BluetoothConnectionState> _connectionStateController =
      StreamController<BluetoothConnectionState>.broadcast();
  final StreamController<BleHeartRateReading> _heartRateController =
      StreamController<BleHeartRateReading>.broadcast();
    final StreamController<BlePulseOximeterReading> _spo2Controller =
      StreamController<BlePulseOximeterReading>.broadcast();
  final StreamController<BleBloodPressureReading> _bpController =
      StreamController<BleBloodPressureReading>.broadcast();
  final StreamController<BleTemperatureReading> _tempController =
      StreamController<BleTemperatureReading>.broadcast();

  StreamSubscription<List<ScanResult>>? _scanSubscription;
  StreamSubscription<BluetoothConnectionState>? _connectionSubscription;
  StreamSubscription<List<int>>? _heartRateSubscription;
  StreamSubscription<List<int>>? _spo2Subscription;
  StreamSubscription<List<int>>? _bpSubscription;
  StreamSubscription<List<int>>? _tempSubscription;
  StreamSubscription<BluetoothAdapterState>? _adapterStateSubscription;

  BluetoothDevice? _connectedDevice;
  BluetoothCharacteristic? _heartRateCharacteristic;
  bool _manualDisconnectRequested = false;
  bool _isReconnecting = false;
  bool _isAdapterOn = true;
  String? _lastSavedDeviceId;
  String? _lastSavedDeviceName;

  BluetoothCharacteristic? _spo2Characteristic;
  BluetoothCharacteristic? _bpCharacteristic;
  BluetoothCharacteristic? _tempCharacteristic;


  Stream<List<ScanResult>> get scanResultsStream => _scanResultsController.stream;
  Stream<BluetoothConnectionState> get connectionStateStream =>
      _connectionStateController.stream;
  Stream<BleHeartRateReading> get heartRateStream => _heartRateController.stream;

  Stream<BlePulseOximeterReading> get spo2Stream => _spo2Controller.stream;
  Stream<BleBloodPressureReading> get bpStream => _bpController.stream;
  Stream<BleTemperatureReading> get tempStream => _tempController.stream;


  BluetoothDevice? get connectedDevice => _connectedDevice;

  /// The remote ID of the last device that successfully connected.
  /// Used by the pairing screen to highlight the "last used" device.
  String? get lastSavedDeviceId => _lastSavedDeviceId;

  /// Whether the Bluetooth adapter is currently powered on.
  bool get isAdapterOn => _isAdapterOn;

  /// Check whether the Bluetooth adapter is turned on.
  ///
  /// Returns `true` on platforms where the check is not applicable (e.g. web).
  static Future<bool> isBluetoothOn() async {
    try {
      final state = await FlutterBluePlus.adapterState.first;
      return state == BluetoothAdapterState.on;
    } catch (_) {
      // If we cannot determine adapter state, assume on and let scan fail
      // naturally — the user will see a scan-failed error.
      return true;
    }
  }

  /// Request the OS to enable Bluetooth (Android only; no-op on iOS).
  static Future<void> requestBluetoothOn() async {
    if (isAndroid) {
      try {
        await FlutterBluePlus.turnOn();
      } catch (_) {
        // User declined or platform does not support.
      }
    }
  }

  Future<void> startScan({
    Duration timeout = const Duration(seconds: 10),
    bool discoverAll = false,
  }) async {
    _updateConnectionStatus(BleConnectionStatus.scanning);

    // Cancel any existing subscription so the new filter mode takes effect.
    await _scanSubscription?.cancel();
    _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
      final filtered = discoverAll
          ? results.toList()
          : results.where((result) {
              return result.advertisementData.serviceUuids
                  .contains(heartRateServiceUuid);
            }).toList();
      filtered.sort((a, b) => b.rssi.compareTo(a.rssi));
      _scanResultsController.add(filtered);
    });

    await FlutterBluePlus.startScan(
      withServices: discoverAll ? [] : [heartRateServiceUuid],
      timeout: timeout,
      // lowLatency delivers more advertisement packets per second, which
      // means device names appear faster (names are buried in the advert
      // local-name field that may only arrive on the first packet seen).
      androidScanMode: AndroidScanMode.lowLatency,
    );

    if (_connectedDevice == null && !_isReconnecting) {
      _updateConnectionStatus(BleConnectionStatus.disconnected);
    }
  }

  Future<void> stopScan() async {
    await FlutterBluePlus.stopScan();

    if (_connectedDevice == null && !_isReconnecting) {
      _updateConnectionStatus(BleConnectionStatus.disconnected);
    }
  }

  Future<void> connectToDevice(
    BluetoothDevice device, {
    bool subscribeSpO2 = false,
    bool subscribeBloodPressure = false,
    bool subscribeTemperature = false,
  }) async {
    _manualDisconnectRequested = false;

    await stopScan();

    if (_connectedDevice != null && _connectedDevice!.remoteId != device.remoteId) {
      await disconnect();
    }

    _connectedDevice = device;
    _updateConnectionStatus(BleConnectionStatus.connecting);

    await _subscribeToConnectionState(device);

    await _connectAndSubscribe(
      device,
      allowAutoConnect: true,
      subscribeSpO2: subscribeSpO2,
      subscribeBloodPressure: subscribeBloodPressure,
      subscribeTemperature: subscribeTemperature,
    );

    await _persistLastConnectedDevice(device);
    _updateConnectionStatus(BleConnectionStatus.connected);
  }

    Future<void> _connectAndSubscribe(
    BluetoothDevice device, {
    required bool allowAutoConnect,
    bool subscribeSpO2 = false,
    bool subscribeBloodPressure = false,
    bool subscribeTemperature = false,
  }) async {
    try {
      await device.connect(
        timeout: const Duration(seconds: 12),
        autoConnect: allowAutoConnect,
      );
    } catch (_) {
      // Ignore already-connected exceptions and continue service discovery.
    }

    // Always attempt HR (backward compatibility)
    try {
      await _discoverHeartRateCharacteristic(device);
      await _subscribeToHeartRate(device);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('BLE: Heart Rate service not found or failed to subscribe: $e');
      }
      // Continue to try other services even if HR fails
    }

    // Optional SpO2 subscription
    if (subscribeSpO2) {
      try {
        await _discoverAndSubscribeSpo2(device);
      } catch (e) {
        if (kDebugMode) {
          debugPrint('BLE: SpO2 service not found: $e');
        }
      }
    }

    // Optional Blood Pressure subscription
    if (subscribeBloodPressure) {
      try {
        await _discoverAndSubscribeBp(device);
      } catch (e) {
        if (kDebugMode) {
          debugPrint('BLE: Blood Pressure service not found: $e');
        }
      }
    }

    // Optional Temperature subscription
    if (subscribeTemperature) {
      try {
        await _discoverAndSubscribeTemp(device);
      } catch (e) {
        if (kDebugMode) {
          debugPrint('BLE: Temperature service not found: $e');
        }
      }
    }
  }


  Future<void> _discoverHeartRateCharacteristic(BluetoothDevice device) async {
    final services = await device.discoverServices();
    BluetoothCharacteristic? hrChar;

    for (final service in services) {
      if (service.uuid != heartRateServiceUuid) {
        continue;
      }
      for (final characteristic in service.characteristics) {
        if (characteristic.uuid == heartRateMeasurementUuid) {
          hrChar = characteristic;
          break;
        }
      }
      if (hrChar != null) {
        break;
      }
    }

    if (hrChar == null) {
      throw Exception('Heart Rate Measurement characteristic 0x2A37 not found');
    }

    _heartRateCharacteristic = hrChar;
  }

  Future<void> _subscribeToHeartRate(BluetoothDevice device) async {
    await _heartRateCharacteristic!.setNotifyValue(true);

    _heartRateSubscription?.cancel();
    _heartRateSubscription = _heartRateCharacteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) {
        return;
      }

      final reading = BleHealthParser.parseHeartRateMeasurement(
        data,
        deviceId: device.remoteId.str,
        deviceName: _resolveDeviceName(device),
      );

      if (reading != null) {
        _heartRateController.add(reading);
      }
    });
  }
    Future<void> _discoverAndSubscribeSpo2(BluetoothDevice device) async {
    final services = await device.discoverServices();
    BluetoothCharacteristic? spo2Char;

    for (final service in services) {
      if (service.uuid != pulseOximeterServiceUuid) {
        continue;
      }
      for (final characteristic in service.characteristics) {
        if (characteristic.uuid == spo2ContinuousMeasurementUuid) {
          spo2Char = characteristic;
          break;
        }
      }
      if (spo2Char != null) {
        break;
      }
    }

    if (spo2Char == null) {
      throw Exception('SpO2 Continuous Measurement characteristic 0x2A5F not found');
    }

    _spo2Characteristic = spo2Char;

    await _spo2Characteristic!.setNotifyValue(true);

    _spo2Subscription?.cancel();
    _spo2Subscription = _spo2Characteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) return;

      final reading = BleHealthParser.parsePulseOximeter(
        data,
        deviceId: device.remoteId.str,
        deviceName: _resolveDeviceName(device),
      );

      if (reading != null) {
        _spo2Controller.add(reading);
      }
    });
  }

  Future<void> _discoverAndSubscribeBp(BluetoothDevice device) async {
    final services = await device.discoverServices();
    BluetoothCharacteristic? bpChar;

    for (final service in services) {
      if (service.uuid != bloodPressureServiceUuid) {
        continue;
      }
      for (final characteristic in service.characteristics) {
        if (characteristic.uuid == bloodPressureMeasurementUuid) {
          bpChar = characteristic;
          break;
        }
      }
      if (bpChar != null) {
        break;
      }
    }

    if (bpChar == null) {
      throw Exception('Blood Pressure Measurement characteristic 0x2A35 not found');
    }

    _bpCharacteristic = bpChar;

    await _bpCharacteristic!.setNotifyValue(true);

    _bpSubscription?.cancel();
    _bpSubscription = _bpCharacteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) return;

      final reading = BleHealthParser.parseBloodPressure(
        data,
        deviceId: device.remoteId.str,
        deviceName: _resolveDeviceName(device),
      );

      if (reading != null) {
        _bpController.add(reading);
      }
    });
  }

  Future<void> _discoverAndSubscribeTemp(BluetoothDevice device) async {
    final services = await device.discoverServices();
    BluetoothCharacteristic? tempChar;

    for (final service in services) {
      if (service.uuid != healthThermometerServiceUuid) {
        continue;
      }
      for (final characteristic in service.characteristics) {
        if (characteristic.uuid == temperatureMeasurementUuid) {
          tempChar = characteristic;
          break;
        }
      }
      if (tempChar != null) {
        break;
      }
    }

    if (tempChar == null) {
      throw Exception('Temperature Measurement characteristic 0x2A1C not found');
    }

    _tempCharacteristic = tempChar;

    await _tempCharacteristic!.setNotifyValue(true);

    _tempSubscription?.cancel();
    _tempSubscription = _tempCharacteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) return;

      final reading = BleHealthParser.parseTemperature(
        data,
        deviceId: device.remoteId.str,
        deviceName: _resolveDeviceName(device),
      );

      if (reading != null) {
        _tempController.add(reading);
      }
    });
  }

  Future<void> _subscribeToConnectionState(BluetoothDevice device) async {
    await _connectionSubscription?.cancel();
    _connectionSubscription = device.connectionState.listen((state) async {
      _connectionStateController.add(state);

      if (state == BluetoothConnectionState.connected) {
        _updateConnectionStatus(BleConnectionStatus.connected);
        return;
      }

      if (state == BluetoothConnectionState.connecting && !_isReconnecting) {
        _updateConnectionStatus(BleConnectionStatus.connecting);
        return;
      }

      if (state == BluetoothConnectionState.disconnected ||
          state == BluetoothConnectionState.disconnecting) {
        if (_manualDisconnectRequested || _isReconnecting) {
          if (_manualDisconnectRequested) {
            _updateConnectionStatus(BleConnectionStatus.disconnected);
          }
          return;
        }

        await _attemptAutoReconnect();
      }
    });
  }

  Future<void> _attemptAutoReconnect() async {
    final device = _connectedDevice;
    if (device == null || _isReconnecting) {
      return;
    }

    _isReconnecting = true;
    _updateConnectionStatus(BleConnectionStatus.reconnecting);

    for (final seconds in _reconnectBackoffSeconds) {
      if (_manualDisconnectRequested) {
        break;
      }

      await Future.delayed(Duration(seconds: seconds));

      try {
        await _connectAndSubscribe(device, allowAutoConnect: true);
        _isReconnecting = false;
        _updateConnectionStatus(BleConnectionStatus.connected);
        return;
      } catch (_) {
        // Continue exponential retry attempts.
      }
    }

    _isReconnecting = false;
    _heartRateCharacteristic = null;
    _connectedDevice = null;
    _updateConnectionStatus(BleConnectionStatus.disconnected);
    _connectionStateController.add(BluetoothConnectionState.disconnected);
  }

  Future<void> disconnect() async {
    _manualDisconnectRequested = true;
    _isReconnecting = false;

    await _heartRateSubscription?.cancel();
    _heartRateSubscription = null;

    await _spo2Subscription?.cancel();
    _spo2Subscription = null;

    await _bpSubscription?.cancel();
    _bpSubscription = null;

    await _tempSubscription?.cancel();
    _tempSubscription = null;

    // Cleanup Heart Rate
    if (_heartRateCharacteristic != null) {
      try {
        await _heartRateCharacteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _heartRateCharacteristic = null;

    // Cleanup SpO2
    if (_spo2Characteristic != null) {
      try {
        await _spo2Characteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _spo2Characteristic = null;

    // Cleanup Blood Pressure
    if (_bpCharacteristic != null) {
      try {
        await _bpCharacteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _bpCharacteristic = null;

    // Cleanup Temperature
    if (_tempCharacteristic != null) {
      try {
        await _tempCharacteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _tempCharacteristic = null;


    await _connectionSubscription?.cancel();
    _connectionSubscription = null;

    if (_connectedDevice != null) {
      try {
        await _connectedDevice!.disconnect();
      } catch (_) {
        // Best-effort cleanup.
      }
    }

    _connectedDevice = null;
    _updateConnectionStatus(BleConnectionStatus.disconnected);
    _connectionStateController.add(BluetoothConnectionState.disconnected);
  }

  Future<void> _persistLastConnectedDevice(BluetoothDevice device) async {
    _lastSavedDeviceId = device.remoteId.str;
    _lastSavedDeviceName = _resolveDeviceName(device);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastDeviceIdKey, _lastSavedDeviceId!);
    await prefs.setString(_lastDeviceNameKey, _lastSavedDeviceName!);
  }

  Future<void> _attemptReconnectFromSavedDevice() async {
    final prefs = await SharedPreferences.getInstance();
    final savedDeviceId = prefs.getString(_lastDeviceIdKey);
    final savedDeviceName = prefs.getString(_lastDeviceNameKey);

    if (savedDeviceId == null || savedDeviceId.isEmpty) {
      return;
    }

    _lastSavedDeviceId = savedDeviceId;
    _lastSavedDeviceName = savedDeviceName;

    // Verify BT adapter is on before attempting reconnect.
    final adapterOn = await isBluetoothOn();
    if (!adapterOn) {
      if (kDebugMode) {
        debugPrint('BLE: Skipping reconnect — Bluetooth adapter is off');
      }
      return;
    }

    try {
      final device = BluetoothDevice.fromId(savedDeviceId);
      await connectToDevice(device);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('BLE: Auto-reconnect to $savedDeviceId failed: $e');
      }
      _updateConnectionStatus(BleConnectionStatus.disconnected);
      _connectionStateController.add(BluetoothConnectionState.disconnected);
    }
  }

  /// Monitors the Bluetooth adapter state (on/off) and reacts to changes.
  void _monitorAdapterState() {
    _adapterStateSubscription = FlutterBluePlus.adapterState.listen((state) {
      final wasOn = _isAdapterOn;
      _isAdapterOn = (state == BluetoothAdapterState.on);

      if (wasOn && !_isAdapterOn) {
        // Bluetooth was just turned off — clean up gracefully.
        if (kDebugMode) {
          debugPrint('BLE: Bluetooth adapter turned off — disconnecting');
        }
        _manualDisconnectRequested = true;
        _isReconnecting = false;
        _heartRateCharacteristic = null;
        _connectedDevice = null;
        _updateConnectionStatus(BleConnectionStatus.disconnected);
        _connectionStateController.add(BluetoothConnectionState.disconnected);
      } else if (!wasOn && _isAdapterOn) {
        // Bluetooth was just turned on — attempt reconnect to last device.
        if (kDebugMode) {
          debugPrint('BLE: Bluetooth adapter turned on — attempting reconnect');
        }
        _manualDisconnectRequested = false;
        unawaited(_attemptReconnectFromSavedDevice());
      }
    });
  }

  void _updateConnectionStatus(BleConnectionStatus status) {
    if (connectionStatusNotifier.value != status) {
      connectionStatusNotifier.value = status;
    }
  }

  String _resolveDeviceName(BluetoothDevice device) {
    final name = device.platformName.trim();
    if (name.isNotEmpty) {
      return name;
    }
    return 'Unknown Device';
  }

  /// Clear persistent device data (e.g. on user logout).
  Future<void> forgetSavedDevice() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_lastDeviceIdKey);
    await prefs.remove(_lastDeviceNameKey);
    _lastSavedDeviceId = null;
    _lastSavedDeviceName = null;
  }

  Future<void> dispose() async {
    await stopScan();
    await disconnect();

    await _scanSubscription?.cancel();
    _scanSubscription = null;

    await _adapterStateSubscription?.cancel();
    _adapterStateSubscription = null;

    // Close broadcast stream controllers to release listeners.
    await _spo2Subscription?.cancel();
    _spo2Subscription = null;
    await _bpSubscription?.cancel();
    _bpSubscription = null;
    await _tempSubscription?.cancel();
    _tempSubscription = null;

    await _scanResultsController.close();
    await _connectionStateController.close();
    await _heartRateController.close();
    await _spo2Controller.close();
    await _bpController.close();
    await _tempController.close();


    connectionStatusNotifier.dispose();
  }
}
