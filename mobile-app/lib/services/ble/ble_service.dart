import 'dart:async';

import 'package:flutter/foundation.dart';
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
class BleService {
  BleService._internal() {
    unawaited(_attemptReconnectFromSavedDevice());
  }

  static final BleService instance = BleService._internal();

  factory BleService() {
    return instance;
  }

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

  StreamSubscription<List<ScanResult>>? _scanSubscription;
  StreamSubscription<BluetoothConnectionState>? _connectionSubscription;
  StreamSubscription<List<int>>? _heartRateSubscription;

  BluetoothDevice? _connectedDevice;
  BluetoothCharacteristic? _heartRateCharacteristic;
  bool _manualDisconnectRequested = false;
  bool _isReconnecting = false;
  String? _lastSavedDeviceId;
  String? _lastSavedDeviceName;

  Stream<List<ScanResult>> get scanResultsStream => _scanResultsController.stream;
  Stream<BluetoothConnectionState> get connectionStateStream =>
      _connectionStateController.stream;
  Stream<BleHeartRateReading> get heartRateStream => _heartRateController.stream;

  BluetoothDevice? get connectedDevice => _connectedDevice;

  Future<void> startScan({Duration timeout = const Duration(seconds: 10)}) async {
    _updateConnectionStatus(BleConnectionStatus.scanning);

    _scanSubscription ??= FlutterBluePlus.scanResults.listen((results) {
      final filtered = results.where((result) {
        return result.advertisementData.serviceUuids
            .contains(heartRateServiceUuid);
      }).toList()
        ..sort((a, b) => b.rssi.compareTo(a.rssi));

      _scanResultsController.add(filtered);
    });

    await FlutterBluePlus.startScan(
      withServices: [heartRateServiceUuid],
      timeout: timeout,
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

  Future<void> connectToDevice(BluetoothDevice device) async {
    _manualDisconnectRequested = false;

    await stopScan();

    if (_connectedDevice != null && _connectedDevice!.remoteId != device.remoteId) {
      await disconnect();
    }

    _connectedDevice = device;
    _updateConnectionStatus(BleConnectionStatus.connecting);

    await _subscribeToConnectionState(device);

    await _connectAndSubscribe(device, allowAutoConnect: true);

    await _persistLastConnectedDevice(device);
    _updateConnectionStatus(BleConnectionStatus.connected);
  }

  Future<void> _connectAndSubscribe(
    BluetoothDevice device, {
    required bool allowAutoConnect,
  }) async {
    try {
      await device.connect(
        timeout: const Duration(seconds: 12),
        autoConnect: allowAutoConnect,
      );
    } catch (_) {
      // Ignore already-connected exceptions and continue service discovery.
    }

    await _discoverHeartRateCharacteristic(device);
    await _subscribeToHeartRate(device);
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

    if (_heartRateCharacteristic != null) {
      try {
        await _heartRateCharacteristic!.setNotifyValue(false);
      } catch (_) {
        // Best-effort cleanup.
      }
    }
    _heartRateCharacteristic = null;

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

    try {
      final device = BluetoothDevice.fromId(savedDeviceId);
      await connectToDevice(device);
    } catch (_) {
      _updateConnectionStatus(BleConnectionStatus.disconnected);
      _connectionStateController.add(BluetoothConnectionState.disconnected);
    }
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

  Future<void> dispose() async {
    await stopScan();
    await disconnect();
    await _scanSubscription?.cancel();
    _scanSubscription = null;
    connectionStatusNotifier.dispose();
  }
}
