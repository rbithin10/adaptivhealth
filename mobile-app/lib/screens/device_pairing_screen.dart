import 'dart:async';

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter_blue_plus/flutter_blue_plus.dart';
import 'package:provider/provider.dart';

import '../config/platform_guard.dart';
import '../providers/vitals_provider.dart';
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
  bool _isConnectingHealth = false;
  bool _discoverAll = false;
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
    // Check that the Bluetooth adapter is powered on.
    final btOn = await BleService.isBluetoothOn();
    if (!btOn) {
      if (!mounted) return;
      final shouldEnable = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('Bluetooth is Off'),
          content: const Text(
            'Bluetooth must be enabled to scan for heart rate monitors.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('Enable Bluetooth'),
            ),
          ],
        ),
      );
      if (shouldEnable == true) {
        await BleService.requestBluetoothOn();
        // Give the adapter a moment to turn on.
        await Future.delayed(const Duration(seconds: 1));
        final nowOn = await BleService.isBluetoothOn();
        if (!nowOn) {
          if (!mounted) return;
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Bluetooth is still off. Please enable it in Settings.'),
            ),
          );
          return;
        }
      } else {
        return;
      }
    }

    // Request runtime BLE permissions.
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
      await _bleService.startScan(
        timeout: const Duration(seconds: 10),
        discoverAll: _discoverAll,
      );
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
      // Connect via VitalsProvider so the unified vitals pipeline receives
      // real BLE heart rate data (instead of staying on mock source).
      final vitalsProvider = context.read<VitalsProvider>();
      await vitalsProvider.connectBle(result.device);

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

  /// Show a rationale dialog then call enableHealthKit on the VitalsProvider.
  Future<void> _connectViaHealth() async {
    final healthAppName = isIOS ? 'Apple Health' : 'Health Connect';
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Connect via $healthAppName'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'AdaptivHealth will read the following data from $healthAppName:',
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            _bulletItem(Icons.favorite, 'Heart Rate'),
            _bulletItem(Icons.air, 'Blood Oxygen (SpO2)'),
            _bulletItem(Icons.monitor_heart, 'Blood Pressure'),
            _bulletItem(Icons.directions_walk, 'Steps'),
            const SizedBox(height: 12),
            Text(
              'This lets any smartwatch (Samsung, Fitbit, Garmin, Polar, '
              'Apple Watch, etc.) that syncs to $healthAppName feed live '
              'data into AdaptivHealth. Data is polled every 20 seconds.',
              style: const TextStyle(fontSize: 13),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Grant Access'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;

    setState(() => _isConnectingHealth = true);

    try {
      await context.read<VitalsProvider>().enableHealthKit();
      if (!mounted) return;
      final source = context.read<VitalsProvider>().activeSource;
      if (source == VitalsSource.health) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connected via $healthAppName — syncing every 20 s'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Could not read from $healthAppName. '
              'Make sure your watch app has synced recently and permissions are granted.',
            ),
          ),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Health connection failed: $e')),
      );
    } finally {
      if (mounted) setState(() => _isConnectingHealth = false);
    }
  }

  Widget _bulletItem(IconData icon, String label) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(icon, size: 16, color: AdaptivColors.primary),
          const SizedBox(width: 8),
          Text(label),
        ],
      ),
    );
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

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    final vitalsProvider = context.watch<VitalsProvider>();
    final activeSource = vitalsProvider.activeSource;

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
        body: Container(
          decoration: BoxDecoration(
            image: DecorationImage(
              image: const AssetImage('assets/images/health_bg4.png'),
              fit: BoxFit.cover,
              colorFilter: ColorFilter.mode(
                brightness == Brightness.dark
                    ? Colors.black.withOpacity(0.6)
                    : Colors.white.withOpacity(0.85),
                brightness == Brightness.dark
                    ? BlendMode.darken
                    : BlendMode.lighten,
              ),
            ),
          ),
          child: Column(
          children: [
          // ── Active source badge ──────────────────────────────────
          Container(
            width: double.infinity,
            margin: const EdgeInsets.fromLTRB(16, 16, 16, 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
              color: AdaptivColors.getSurfaceColor(brightness),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.neutral300),
            ),
            child: Row(
              children: [
                _sourceIcon(activeSource),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Active data source',
                        style: TextStyle(
                          fontSize: 11,
                          color: AdaptivColors.getSecondaryTextColor(brightness),
                        ),
                      ),
                      Text(
                        _sourceName(activeSource),
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          color: AdaptivColors.getTextColor(brightness),
                        ),
                      ),
                    ],
                  ),
                ),
                _sourceBadge(activeSource),
              ],
            ),
          ),

          // ── BLE scan controls ────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _isScanning ? null : _startScan,
                    icon: Icon(_isScanning ? Icons.sync : Icons.bluetooth_searching),
                    label: Text(_isScanning ? 'Scanning...' : 'Scan BLE Devices'),
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
          const SizedBox(height: 10),

          // ── Health Connect / HealthKit section ───────────────────          if (kIsWeb)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Container(
                decoration: BoxDecoration(
                  color: AdaptivColors.getSurfaceColor(brightness),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: AdaptivColors.neutral300),
                ),
                padding: const EdgeInsets.all(14),
                child: Row(
                  children: [
                    const Icon(Icons.info_outline, color: Colors.orange, size: 22),
                    const SizedBox(width: 12),
                    const Expanded(
                      child: Text(
                        'BLE pairing and HealthKit are only available on the mobile app. Use the Android or iOS app to connect a heart rate monitor.',
                        style: TextStyle(fontSize: 13),
                      ),
                    ),
                  ],
                ),
              ),
            )
          else          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              decoration: BoxDecoration(
                color: AdaptivColors.getSurfaceColor(brightness),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AdaptivColors.neutral300),
              ),
              padding: const EdgeInsets.all(14),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Colors.green.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.watch, color: Colors.green, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          isIOS ? 'Apple Health' : 'Health Connect',
                          style: TextStyle(
                            fontWeight: FontWeight.w600,
                            color: AdaptivColors.getTextColor(brightness),
                          ),
                        ),
                        Text(
                          'Samsung, Fitbit, Garmin, Polar, Apple Watch…',
                          style: TextStyle(
                            fontSize: 12,
                            color: AdaptivColors.getSecondaryTextColor(brightness),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(width: 8),
                  _isConnectingHealth
                      ? const SizedBox(
                          width: 20,
                          height: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : activeSource == VitalsSource.health
                          ? OutlinedButton(
                              onPressed: () {
                                vitalsProvider.fallbackToMock();
                              },
                              style: OutlinedButton.styleFrom(
                                foregroundColor: Colors.red,
                                side: const BorderSide(color: Colors.red),
                              ),
                              child: const Text('Disconnect'),
                            )
                          : ElevatedButton(
                              onPressed: _connectViaHealth,
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.green,
                                foregroundColor: Colors.white,
                              ),
                              child: const Text('Connect'),
                            ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),

          // ── Divider label ────────────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                const Expanded(child: Divider()),
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 8),
                  child: Flexible(
                    child: Text(
                      'Or connect a BLE device directly',
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 11,
                        color: AdaptivColors.getSecondaryTextColor(brightness),
                      ),
                    ),
                  ),
                ),
                const Expanded(child: Divider()),
              ],
            ),
          ),
          const SizedBox(height: 6),

          // ── Discover-all toggle ──────────────────────────────────
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(
              children: [
                Switch(
                  value: _discoverAll,
                  onChanged: (value) => setState(() => _discoverAll = value),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Show all BLE devices',
                        style: TextStyle(
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                          color: AdaptivColors.getTextColor(brightness),
                        ),
                      ),
                      Text(
                        _discoverAll
                            ? 'Scanning for all nearby BLE devices'
                            : 'Heart rate monitors only (default)',
                        style: TextStyle(
                          fontSize: 11,
                          color: AdaptivColors.getSecondaryTextColor(brightness),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 6),

          // ── BLE scan results ─────────────────────────────────────
          Expanded(
            child: _scanResults.isEmpty
                ? Center(
                    child: Text(
                      _isScanning
                          ? (_discoverAll
                              ? 'Scanning for all nearby BLE devices...'
                              : 'Searching for heart rate monitors...')
                          : 'No BLE devices found.\nTap "Scan BLE Devices" above.',
                      textAlign: TextAlign.center,
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
                      final isHrDevice = result.advertisementData.serviceUuids
                          .contains(BleService.heartRateServiceUuid);

                      return Container(
                        decoration: BoxDecoration(
                          color: AdaptivColors.getSurfaceColor(brightness),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: isHrDevice
                                ? AdaptivColors.neutral300
                                : Colors.orange.withValues(alpha: 0.5),
                          ),
                        ),
                        child: ListTile(
                          leading: Icon(
                            isHrDevice ? Icons.favorite : Icons.bluetooth,
                            color: isHrDevice ? Colors.red : Colors.grey,
                            size: 20,
                          ),
                          title: Text(deviceName),
                          subtitle: Text(
                            isHrDevice
                                ? 'RSSI: ${result.rssi} dBm'
                                : 'RSSI: ${result.rssi} dBm · not a heart rate monitor',
                            style: TextStyle(
                              fontSize: 12,
                              color: isHrDevice
                                  ? AdaptivColors.getSecondaryTextColor(brightness)
                                  : Colors.orange,
                            ),
                          ),
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
      ),
    );
  }

  Widget _sourceIcon(VitalsSource source) {
    switch (source) {
      case VitalsSource.ble:
        return const Icon(Icons.bluetooth, color: Colors.blue, size: 22);
      case VitalsSource.health:
        return const Icon(Icons.watch, color: Colors.green, size: 22);
      case VitalsSource.mock:
        return const Icon(Icons.science, color: Colors.orange, size: 22);
    }
  }

  String _sourceName(VitalsSource source) {
    switch (source) {
      case VitalsSource.ble:
        return 'BLE Heart Rate Monitor';
      case VitalsSource.health:
        return isIOS ? 'Apple Health' : 'Health Connect';
      case VitalsSource.mock:
        return 'Simulated (Demo Mode)';
    }
  }

  Widget _sourceBadge(VitalsSource source) {
    Color color;
    String label;
    switch (source) {
      case VitalsSource.ble:
        color = Colors.blue;
        label = 'LIVE';
        break;
      case VitalsSource.health:
        color = Colors.green;
        label = 'SYNCED';
        break;
      case VitalsSource.mock:
        color = Colors.orange;
        label = 'DEMO';
        break;
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }
}
