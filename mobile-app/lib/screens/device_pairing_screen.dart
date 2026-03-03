import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';

import '../services/api_client.dart';
import '../services/ble/ble_permission_handler.dart';
import '../services/ble/ble_service.dart';
import '../theme/colors.dart';
import '../widgets/ai_coach_overlay.dart';

class DevicePairingScreen extends StatefulWidget {
  final ApiClient apiClient;

  const DevicePairingScreen({super.key, required this.apiClient});

  @override
  State<DevicePairingScreen> createState() => _DevicePairingScreenState();
}

class _DevicePairingScreenState extends State<DevicePairingScreen> {
  final BleService _bleService = BleService.instance;

  StreamSubscription<List<ScanResult>>? _scanSubscription;
  StreamSubscription<BluetoothConnectionState>? _connectionSubscription;

  List<ScanResult> _scanResults = [];
  BluetoothConnectionState _connectionState =
      BluetoothConnectionState.disconnected;
  bool _isScanning = false;
  String? _connectedDeviceId;

  @override
  void initState() {
    super.initState();

    _scanSubscription = _bleService.scanResultsStream.listen((results) {
      if (!mounted) return;
      setState(() {
        _scanResults = results;
      });
    });

    _connectionSubscription =
        _bleService.connectionStateStream.listen((state) {
      if (!mounted) return;
      setState(() {
        _connectionState = state;
      });
    });
  }

  @override
  void dispose() {
    _scanSubscription?.cancel();
    _connectionSubscription?.cancel();
    super.dispose();
  }

  Future<void> _startScan() async {
    final hasPermission = await BlePermissionHandler.requestBlePermissions();
    if (!hasPermission) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Bluetooth permission is required to scan devices.'),
        ),
      );
      return;
    }

    setState(() {
      _isScanning = true;
      _scanResults = [];
    });

    try {
      await _bleService.startScan(timeout: const Duration(seconds: 10));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Scan failed: $e')),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isScanning = false;
        });
      }
    }
  }

  Future<void> _connect(ScanResult result) async {
    setState(() {
      _connectedDeviceId = result.device.remoteId.str;
    });

    try {
      await _bleService.connectToDevice(result.device);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Connected to ${_resolveDeviceName(result)}'),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Connection failed: $e')),
      );
      setState(() {
        _connectedDeviceId = null;
      });
    }
  }

  Future<void> _disconnect() async {
    await _bleService.disconnect();
    if (!mounted) return;
    setState(() {
      _connectedDeviceId = null;
    });
  }

  String _resolveDeviceName(ScanResult result) {
    final platformName = result.device.platformName.trim();
    if (platformName.isNotEmpty) {
      return platformName;
    }
    final advertisedName = result.advertisementData.advName.trim();
    if (advertisedName.isNotEmpty) {
      return advertisedName;
    }
    return 'Unknown Device';
  }

  String _connectionLabel(BluetoothConnectionState state) {
    if (state == BluetoothConnectionState.connected) return 'Connected';
    return 'Disconnected';
  }

  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;

    return AiCoachOverlay(
      apiClient: widget.apiClient,
      child: Scaffold(
        backgroundColor: AdaptivColors.getBackgroundColor(brightness),
        appBar: AppBar(
          title: const Text('Pair Heart Rate Monitor'),
          backgroundColor: AdaptivColors.getSurfaceColor(brightness),
          foregroundColor: AdaptivColors.getTextColor(brightness),
          elevation: 0,
        ),
        body: Column(
          children: [
          Container(
            width: double.infinity,
            margin: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AdaptivColors.getSurfaceColor(brightness),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.neutral300),
            ),
            child: Text(
              'Connection state: ${_connectionLabel(_connectionState)}',
              style: TextStyle(
                color: AdaptivColors.getTextColor(brightness),
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isScanning ? null : _startScan,
                    icon: Icon(_isScanning ? Icons.sync : Icons.bluetooth_searching),
                    label: Text(_isScanning ? 'Scanning...' : 'Scan Devices'),
                  ),
                ),
                const SizedBox(width: 12),
                OutlinedButton(
                  onPressed: _connectedDeviceId == null ? null : _disconnect,
                  child: const Text('Disconnect'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Expanded(
            child: _scanResults.isEmpty
                ? Center(
                    child: Text(
                      _isScanning
                          ? 'Searching for heart rate monitors...'
                          : 'No devices found yet. Tap Scan Devices.',
                      style: TextStyle(
                        color: AdaptivColors.getSecondaryTextColor(brightness),
                      ),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                    itemCount: _scanResults.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, index) {
                      final result = _scanResults[index];
                      final deviceName = _resolveDeviceName(result);
                      final isConnected =
                          _connectedDeviceId == result.device.remoteId.str &&
                              _connectionState == BluetoothConnectionState.connected;

                      return Container(
                        decoration: BoxDecoration(
                          color: AdaptivColors.getSurfaceColor(brightness),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: AdaptivColors.neutral300),
                        ),
                        child: ListTile(
                          title: Text(deviceName),
                          subtitle: Text('RSSI: ${result.rssi} dBm'),
                          trailing: isConnected
                              ? const Icon(Icons.check_circle, color: Colors.green)
                              : ElevatedButton(
                                  onPressed: () => _connect(result),
                                  child: const Text('Connect'),
                                ),
                        ),
                      );
                    },
                  ),
          ),
          ],
        ),
      ),
    );
  }
}
