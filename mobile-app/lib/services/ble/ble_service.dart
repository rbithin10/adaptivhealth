/*
Bluetooth (BLE) Service.

This is the main Bluetooth connection manager for the app. It handles:
- Scanning for nearby heart rate monitors, blood pressure cuffs, etc.
- Connecting to a chosen device
- Automatically reconnecting if the connection drops
- Receiving live health data (heart rate, SpO2, blood pressure, temperature)
- Remembering the last device so the app reconnects at next startup

Only one copy of this service exists in the whole app (shared everywhere).
*/

import 'dart:async';

import 'package:flutter/foundation.dart';
// Checks which platform we're on (Android, iOS, etc.)
import '../../config/platform_guard.dart';
// The Bluetooth library that talks to actual Bluetooth hardware
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
// Lets us save the last-connected device ID so we can reconnect on app restart
import 'package:shared_preferences/shared_preferences.dart';

// Our parser that turns raw Bluetooth bytes into readable health values
import 'ble_health_parser.dart';

// The possible states of our Bluetooth connection
enum BleConnectionStatus {
  disconnected,   // Not connected to any device
  scanning,       // Looking for nearby devices
  connecting,     // In the process of connecting
  connected,      // Successfully connected and receiving data
  reconnecting,   // Lost connection and trying to get it back
}

// Only one copy of this Bluetooth service exists in the whole app.
// It handles scanning, connecting, and receiving health data from BLE devices.
class BleService {
  // Private constructor — when the service starts, it watches the Bluetooth
  // adapter state and tries to reconnect to the last saved device
  BleService._internal() {
    _monitorAdapterState();
    unawaited(_attemptReconnectFromSavedDevice());
  }

  // The one shared instance of the Bluetooth service (used everywhere in the app)
  static final BleService instance = BleService._internal();

  // When someone requests a BleService, give them the existing shared instance
  factory BleService() {
    return instance;
  }

  // --- Official Bluetooth standard codes for health services and data ---
  // Each health device type has an assigned code. These are from the Bluetooth SIG.

  // Pulse oximeter (measures blood oxygen) — service code and data code
  static final Guid pulseOximeterServiceUuid = Guid('1822');
  static final Guid spo2ContinuousMeasurementUuid = Guid('2A5F');
  // Blood pressure cuff — service code and data code
  static final Guid bloodPressureServiceUuid = Guid('1810');
  static final Guid bloodPressureMeasurementUuid = Guid('2A35');
  // Thermometer — service code and data code
  static final Guid healthThermometerServiceUuid = Guid('1809');
  static final Guid temperatureMeasurementUuid = Guid('2A1C');
  // Heart rate monitor — service code and data code
  static final Guid heartRateServiceUuid = Guid('180D');
  static final Guid heartRateMeasurementUuid = Guid('2A37');

  // If the connection drops, wait 2 seconds then retry, then 4, then 8
  // This gradually increasing wait prevents flooding the device with connection attempts
  static const List<int> _reconnectBackoffSeconds = [2, 4, 8];
  // Storage keys for remembering the last device between app sessions
  static const String _lastDeviceIdKey = 'ble_last_device_remote_id';
  static const String _lastDeviceNameKey = 'ble_last_device_name';

  // Tells the UI what's happening with the Bluetooth connection right now
  final ValueNotifier<BleConnectionStatus> connectionStatusNotifier =
      ValueNotifier<BleConnectionStatus>(BleConnectionStatus.disconnected);

  // --- Data channels (streams) that send live updates to the rest of the app ---
  // "broadcast" means multiple screens can listen at the same time

  // Sends the list of nearby devices found during scanning
  final StreamController<List<ScanResult>> _scanResultsController =
      StreamController<List<ScanResult>>.broadcast();
  // Sends connection state changes (connected, disconnected, etc.)
  final StreamController<BluetoothConnectionState> _connectionStateController =
      StreamController<BluetoothConnectionState>.broadcast();
  // Sends heart rate readings as they arrive from the device
  final StreamController<BleHeartRateReading> _heartRateController =
      StreamController<BleHeartRateReading>.broadcast();
  // Sends blood oxygen (SpO2) readings
  final StreamController<BlePulseOximeterReading> _spo2Controller =
      StreamController<BlePulseOximeterReading>.broadcast();
  // Sends blood pressure readings
  final StreamController<BleBloodPressureReading> _bpController =
      StreamController<BleBloodPressureReading>.broadcast();
  // Sends temperature readings
  final StreamController<BleTemperatureReading> _tempController =
      StreamController<BleTemperatureReading>.broadcast();

  // --- Active listeners that receive raw data from the Bluetooth device ---
  // We keep references so we can cancel them when disconnecting

  StreamSubscription<List<ScanResult>>? _scanSubscription;
  StreamSubscription<BluetoothConnectionState>? _connectionSubscription;
  StreamSubscription<List<int>>? _heartRateSubscription;      // Raw heart rate bytes
  StreamSubscription<List<int>>? _spo2Subscription;           // Raw SpO2 bytes
  StreamSubscription<List<int>>? _bpSubscription;             // Raw blood pressure bytes
  StreamSubscription<List<int>>? _tempSubscription;           // Raw temperature bytes
  StreamSubscription<BluetoothAdapterState>? _adapterStateSubscription; // Bluetooth on/off

  // The Bluetooth device we're currently connected to (null if not connected)
  BluetoothDevice? _connectedDevice;
  // The specific data channel on the device that sends heart rate values
  BluetoothCharacteristic? _heartRateCharacteristic;
  // True when the user deliberately tapped "Disconnect" (so we don't auto-reconnect)
  bool _manualDisconnectRequested = false;
  // True while we're in the middle of trying to reconnect
  bool _isReconnecting = false;
  // True when the phone's Bluetooth is turned on
  bool _isAdapterOn = true;
  // The Bluetooth ID and name of the last device we successfully connected to
  String? _lastSavedDeviceId;
  String? _lastSavedDeviceName;

  // Data channels for optional health measurements
  BluetoothCharacteristic? _spo2Characteristic;
  BluetoothCharacteristic? _bpCharacteristic;
  BluetoothCharacteristic? _tempCharacteristic;

  // --- Public data channels that screens can listen to ---

  // Listen to this to get the list of nearby devices found during a scan
  Stream<List<ScanResult>> get scanResultsStream => _scanResultsController.stream;
  // Listen to this to know when the connection state changes
  Stream<BluetoothConnectionState> get connectionStateStream =>
      _connectionStateController.stream;
  // Listen to this to get live heart rate readings
  Stream<BleHeartRateReading> get heartRateStream => _heartRateController.stream;
  // Listen to this to get live blood oxygen readings
  Stream<BlePulseOximeterReading> get spo2Stream => _spo2Controller.stream;
  // Listen to this to get live blood pressure readings
  Stream<BleBloodPressureReading> get bpStream => _bpController.stream;
  // Listen to this to get live temperature readings
  Stream<BleTemperatureReading> get tempStream => _tempController.stream;

  // The device we're currently connected to (null if none)
  BluetoothDevice? get connectedDevice => _connectedDevice;

  // The Bluetooth ID of the last device we connected to (used by the pairing screen
  // to highlight the "last used" device in the list)
  String? get lastSavedDeviceId => _lastSavedDeviceId;

  // Whether the phone's Bluetooth is currently turned on
  bool get isAdapterOn => _isAdapterOn;

  // Check if the phone's Bluetooth is on right now
  // Returns true on platforms where we can't check (like web) so we try anyway
  static Future<bool> isBluetoothOn() async {
    try {
      final state = await FlutterBluePlus.adapterState.first;
      return state == BluetoothAdapterState.on;
    } catch (_) {
      // If we can't check, assume it's on — the scan will fail naturally if it's not
      return true;
    }
  }

  // Ask the phone to turn on Bluetooth (only works on Android — iOS doesn't allow this)
  static Future<void> requestBluetoothOn() async {
    if (isAndroid) {
      try {
        await FlutterBluePlus.turnOn();
      } catch (_) {
        // User said no, or this feature isn't available on their phone
      }
    }
  }

  // Start searching for nearby Bluetooth health devices
  Future<void> startScan({
    Duration timeout = const Duration(seconds: 10),
    bool discoverAll = false, // If true, show ALL Bluetooth devices (not just heart rate monitors)
  }) async {
    // Update the UI to show we're scanning
    _updateConnectionStatus(BleConnectionStatus.scanning);

    // Stop any previous scan listener before starting a new one
    await _scanSubscription?.cancel();
    // Listen for devices found during the scan
    _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
      // Either show all devices, or only those that offer heart rate monitoring
      final filtered = discoverAll
          ? results.toList()
          : results.where((result) {
              return result.advertisementData.serviceUuids
                  .contains(heartRateServiceUuid);
            }).toList();
      // Sort by signal strength — closest devices appear first
      filtered.sort((a, b) => b.rssi.compareTo(a.rssi));
      // Send the filtered list to anyone listening (e.g., the pairing screen)
      _scanResultsController.add(filtered);
    });

    // Actually start the Bluetooth scan
    await FlutterBluePlus.startScan(
      // Only look for heart rate devices unless discoverAll is true
      withServices: discoverAll ? [] : [heartRateServiceUuid],
      timeout: timeout,
      // Low latency mode finds device names faster (names don't always show up immediately)
      androidScanMode: AndroidScanMode.lowLatency,
    );

    // If we're not connected to anything and not reconnecting, mark as disconnected
    if (_connectedDevice == null && !_isReconnecting) {
      _updateConnectionStatus(BleConnectionStatus.disconnected);
    }
  }

  // Stop searching for nearby devices
  Future<void> stopScan() async {
    await FlutterBluePlus.stopScan();

    if (_connectedDevice == null && !_isReconnecting) {
      _updateConnectionStatus(BleConnectionStatus.disconnected);
    }
  }

  // Connect to a specific Bluetooth device and start receiving health data
  Future<void> connectToDevice(
    BluetoothDevice device, {
    bool subscribeSpO2 = false,            // Also receive blood oxygen data
    bool subscribeBloodPressure = false,    // Also receive blood pressure data
    bool subscribeTemperature = false,      // Also receive temperature data
  }) async {
    // Reset the manual disconnect flag since the user is choosing to connect
    _manualDisconnectRequested = false;

    // Stop scanning — we found what we want
    await stopScan();

    // If we're already connected to a different device, disconnect first
    if (_connectedDevice != null && _connectedDevice!.remoteId != device.remoteId) {
      await disconnect();
    }

    _connectedDevice = device;
    // Tell the UI we're connecting
    _updateConnectionStatus(BleConnectionStatus.connecting);

    // Listen for connection state changes (so we know if the device disconnects)
    await _subscribeToConnectionState(device);

    // Connect to the device and set up data subscriptions
    await _connectAndSubscribe(
      device,
      allowAutoConnect: true,
      subscribeSpO2: subscribeSpO2,
      subscribeBloodPressure: subscribeBloodPressure,
      subscribeTemperature: subscribeTemperature,
    );

    // Save this device's ID so we can reconnect automatically next time
    await _persistLastConnectedDevice(device);
    _updateConnectionStatus(BleConnectionStatus.connected);
  }

  // Internal: Connect to the device and subscribe to all requested health data
  Future<void> _connectAndSubscribe(
    BluetoothDevice device, {
    required bool allowAutoConnect,
    bool subscribeSpO2 = false,
    bool subscribeBloodPressure = false,
    bool subscribeTemperature = false,
  }) async {
    try {
      // Establish the Bluetooth connection (12 second timeout)
      await device.connect(
        timeout: const Duration(seconds: 12),
        autoConnect: allowAutoConnect,
      );
    } catch (_) {
      // If the device is already connected, that's fine — continue setting things up
    }

    // Always try to set up heart rate monitoring (it's the primary use case)
    try {
      // Find the heart rate data channel on the device
      await _discoverHeartRateCharacteristic(device);
      // Tell the device to start sending heart rate data
      await _subscribeToHeartRate(device);
    } catch (e) {
      if (kDebugMode) {
        debugPrint('BLE: Heart Rate service not found or failed to subscribe: $e');
      }
      // If heart rate isn't available, still try other services below
    }

    // Set up blood oxygen monitoring if requested
    if (subscribeSpO2) {
      try {
        await _discoverAndSubscribeSpo2(device);
      } catch (e) {
        if (kDebugMode) {
          debugPrint('BLE: SpO2 service not found: $e');
        }
      }
    }

    // Set up blood pressure monitoring if requested
    if (subscribeBloodPressure) {
      try {
        await _discoverAndSubscribeBp(device);
      } catch (e) {
        if (kDebugMode) {
          debugPrint('BLE: Blood Pressure service not found: $e');
        }
      }
    }

    // Set up temperature monitoring if requested
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

  // Find the heart rate data channel on the connected Bluetooth device
  Future<void> _discoverHeartRateCharacteristic(BluetoothDevice device) async {
    // Ask the device to list all its available services (features)
    final services = await device.discoverServices();
    BluetoothCharacteristic? hrChar;

    // Look through the services to find the heart rate one
    for (final service in services) {
      if (service.uuid != heartRateServiceUuid) {
        continue; // Skip services that aren't heart rate
      }
      // Inside the heart rate service, find the specific data channel
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

    // If the device doesn't have heart rate monitoring, throw an error
    if (hrChar == null) {
      throw Exception('Heart Rate Measurement characteristic 0x2A37 not found');
    }

    _heartRateCharacteristic = hrChar;
  }

  // Tell the heart rate monitor to start sending us data, and listen for it
  Future<void> _subscribeToHeartRate(BluetoothDevice device) async {
    // Turn on notifications — the device will now push data to us automatically
    await _heartRateCharacteristic!.setNotifyValue(true);

    // Stop any previous listener before starting a new one
    _heartRateSubscription?.cancel();
    // Listen for raw data bytes as they arrive
    _heartRateSubscription = _heartRateCharacteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) {
        return; // No data to process
      }

      // Parse the raw bytes into a human-readable heart rate reading
      final reading = BleHealthParser.parseHeartRateMeasurement(
        data,
        deviceId: device.remoteId.str,
        deviceName: _resolveDeviceName(device),
      );

      // Send the reading to all screens that are listening
      if (reading != null) {
        _heartRateController.add(reading);
      }
    });
  }

  // Find and subscribe to the blood oxygen (SpO2) channel on the device
  Future<void> _discoverAndSubscribeSpo2(BluetoothDevice device) async {
    final services = await device.discoverServices();
    BluetoothCharacteristic? spo2Char;

    // Search for the pulse oximeter service
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

    // Turn on notifications so the device pushes SpO2 readings to us
    await _spo2Characteristic!.setNotifyValue(true);

    _spo2Subscription?.cancel();
    _spo2Subscription = _spo2Characteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) return;

      // Parse Bluetooth bytes into a readable SpO2 reading
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

  // Find and subscribe to the blood pressure channel on the device
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

    // Turn on notifications so the device pushes blood pressure readings
    await _bpCharacteristic!.setNotifyValue(true);

    _bpSubscription?.cancel();
    _bpSubscription = _bpCharacteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) return;

      // Parse Bluetooth bytes into a readable blood pressure reading
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

  // Find and subscribe to the temperature channel on the device
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

    // Turn on notifications so the device pushes temperature readings
    await _tempCharacteristic!.setNotifyValue(true);

    _tempSubscription?.cancel();
    _tempSubscription = _tempCharacteristic!.lastValueStream.listen((data) {
      if (data.isEmpty) return;

      // Parse Bluetooth bytes into a readable temperature reading
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

  // Watch for connection state changes (connected → disconnected, etc.)
  // and auto-reconnect if the connection drops unexpectedly
  Future<void> _subscribeToConnectionState(BluetoothDevice device) async {
    await _connectionSubscription?.cancel();
    _connectionSubscription = device.connectionState.listen((state) async {
      // Forward the state to anyone listening
      _connectionStateController.add(state);

      if (state == BluetoothConnectionState.connected) {
        _updateConnectionStatus(BleConnectionStatus.connected);
        return;
      }

      if (state == BluetoothConnectionState.connecting && !_isReconnecting) {
        _updateConnectionStatus(BleConnectionStatus.connecting);
        return;
      }

      // If we lost the connection unexpectedly, try to reconnect
      if (state == BluetoothConnectionState.disconnected ||
          state == BluetoothConnectionState.disconnecting) {
        // Don't auto-reconnect if the user chose to disconnect, or we're already reconnecting
        if (_manualDisconnectRequested || _isReconnecting) {
          if (_manualDisconnectRequested) {
            _updateConnectionStatus(BleConnectionStatus.disconnected);
          }
          return;
        }

        // Connection dropped unexpectedly — try to get it back
        await _attemptAutoReconnect();
      }
    });
  }

  // Try to reconnect to the last device with increasing wait times (2s, 4s, 8s)
  Future<void> _attemptAutoReconnect() async {
    final device = _connectedDevice;
    // Nothing to reconnect to, or already trying
    if (device == null || _isReconnecting) {
      return;
    }

    _isReconnecting = true;
    _updateConnectionStatus(BleConnectionStatus.reconnecting);

    // Try up to 3 times with increasing delays (2s, 4s, 8s)
    for (final seconds in _reconnectBackoffSeconds) {
      // If user manually disconnected while we're trying, stop
      if (_manualDisconnectRequested) {
        break;
      }

      // Wait before trying again
      await Future.delayed(Duration(seconds: seconds));

      try {
        await _connectAndSubscribe(device, allowAutoConnect: true);
        // Reconnection succeeded!
        _isReconnecting = false;
        _updateConnectionStatus(BleConnectionStatus.connected);
        return;
      } catch (_) {
        // This attempt failed — try again with a longer wait
      }
    }

    // All reconnection attempts failed — give up and mark as disconnected
    _isReconnecting = false;
    _heartRateCharacteristic = null;
    _connectedDevice = null;
    _updateConnectionStatus(BleConnectionStatus.disconnected);
    _connectionStateController.add(BluetoothConnectionState.disconnected);
  }

  // Disconnect from the current device and clean up everything
  Future<void> disconnect() async {
    // Mark this as intentional so we don't try to auto-reconnect
    _manualDisconnectRequested = true;
    _isReconnecting = false;

    // Stop listening for data from all health channels
    await _heartRateSubscription?.cancel();
    _heartRateSubscription = null;

    await _spo2Subscription?.cancel();
    _spo2Subscription = null;

    await _bpSubscription?.cancel();
    _bpSubscription = null;

    await _tempSubscription?.cancel();
    _tempSubscription = null;

    // Tell each health channel to stop sending data
    if (_heartRateCharacteristic != null) {
      try {
        await _heartRateCharacteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _heartRateCharacteristic = null;

    if (_spo2Characteristic != null) {
      try {
        await _spo2Characteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _spo2Characteristic = null;

    if (_bpCharacteristic != null) {
      try {
        await _bpCharacteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _bpCharacteristic = null;

    if (_tempCharacteristic != null) {
      try {
        await _tempCharacteristic!.setNotifyValue(false);
      } catch (_) {}
    }
    _tempCharacteristic = null;

    // Stop watching for connection changes
    await _connectionSubscription?.cancel();
    _connectionSubscription = null;

    // Actually disconnect the Bluetooth device
    if (_connectedDevice != null) {
      try {
        await _connectedDevice!.disconnect();
      } catch (_) {
        // Best-effort — the device might already be gone
      }
    }

    _connectedDevice = null;
    _updateConnectionStatus(BleConnectionStatus.disconnected);
    _connectionStateController.add(BluetoothConnectionState.disconnected);
  }

  // Save the device ID and name to the phone's storage so we can reconnect later
  Future<void> _persistLastConnectedDevice(BluetoothDevice device) async {
    _lastSavedDeviceId = device.remoteId.str;
    _lastSavedDeviceName = _resolveDeviceName(device);

    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_lastDeviceIdKey, _lastSavedDeviceId!);
    await prefs.setString(_lastDeviceNameKey, _lastSavedDeviceName!);
  }

  // On app startup, try to reconnect to the last Bluetooth device we used
  Future<void> _attemptReconnectFromSavedDevice() async {
    // Read the saved device info from phone storage
    final prefs = await SharedPreferences.getInstance();
    final savedDeviceId = prefs.getString(_lastDeviceIdKey);
    final savedDeviceName = prefs.getString(_lastDeviceNameKey);

    // If no device was saved, nothing to reconnect to
    if (savedDeviceId == null || savedDeviceId.isEmpty) {
      return;
    }

    _lastSavedDeviceId = savedDeviceId;
    _lastSavedDeviceName = savedDeviceName;

    // Make sure Bluetooth is actually on before trying to connect
    final adapterOn = await isBluetoothOn();
    if (!adapterOn) {
      if (kDebugMode) {
        debugPrint('BLE: Skipping reconnect — Bluetooth adapter is off');
      }
      return;
    }

    // Try to connect to the saved device
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

  // Watch whether the phone's Bluetooth is turned on or off, and react accordingly
  void _monitorAdapterState() {
    _adapterStateSubscription = FlutterBluePlus.adapterState.listen((state) {
      final wasOn = _isAdapterOn;
      _isAdapterOn = (state == BluetoothAdapterState.on);

      if (wasOn && !_isAdapterOn) {
        // Bluetooth was just turned OFF — clean up the connection
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
        // Bluetooth was just turned ON — try to reconnect to the last device
        if (kDebugMode) {
          debugPrint('BLE: Bluetooth adapter turned on — attempting reconnect');
        }
        _manualDisconnectRequested = false;
        unawaited(_attemptReconnectFromSavedDevice());
      }
    });
  }

  // Update the connection status if it actually changed (avoids unnecessary UI refreshes)
  void _updateConnectionStatus(BleConnectionStatus status) {
    if (connectionStatusNotifier.value != status) {
      connectionStatusNotifier.value = status;
    }
  }

  // Get the device's name, or "Unknown Device" if it doesn't have one
  String _resolveDeviceName(BluetoothDevice device) {
    final name = device.platformName.trim();
    if (name.isNotEmpty) {
      return name;
    }
    return 'Unknown Device';
  }

  // Erase the saved device info (called when the user logs out)
  Future<void> forgetSavedDevice() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_lastDeviceIdKey);
    await prefs.remove(_lastDeviceNameKey);
    _lastSavedDeviceId = null;
    _lastSavedDeviceName = null;
  }

  // Shut down everything when the app closes — stop scanning, disconnect, and clean up
  Future<void> dispose() async {
    await stopScan();
    await disconnect();

    await _scanSubscription?.cancel();
    _scanSubscription = null;

    await _adapterStateSubscription?.cancel();
    _adapterStateSubscription = null;

    // Cancel any remaining data subscriptions
    await _spo2Subscription?.cancel();
    _spo2Subscription = null;
    await _bpSubscription?.cancel();
    _bpSubscription = null;
    await _tempSubscription?.cancel();
    _tempSubscription = null;

    // Close all the data channels so listeners know we're done
    await _scanResultsController.close();
    await _connectionStateController.close();
    await _heartRateController.close();
    await _spo2Controller.close();
    await _bpController.close();
    await _tempController.close();

    connectionStatusNotifier.dispose();
  }
}
