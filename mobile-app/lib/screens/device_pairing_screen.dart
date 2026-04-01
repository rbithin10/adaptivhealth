/*
Device Pairing Screen.

Lets the user connect a Bluetooth health device (like a heart rate monitor
or blood pressure cuff) to the app. Scans for nearby devices, shows them
in a list, and handles the pairing process. Also provides options to connect
via Apple Health, Google Health Connect, or Fitbit.
*/

import 'dart:async'; // Gives us StreamSubscription and Timer for async events

import 'package:flutter/foundation.dart' show kIsWeb; // Tells us if the app is running in a browser
import 'package:flutter/material.dart'; // Core Flutter UI toolkit
import 'package:flutter_blue_plus/flutter_blue_plus.dart'; // Bluetooth Low Energy library
import 'package:provider/provider.dart'; // State management

import '../config/platform_guard.dart'; // Detects iOS vs Android
import '../providers/vitals_provider.dart'; // Central hub for all vital sign data
import '../services/api_client.dart'; // Talks to our backend server
import '../services/ble/ble_permission_handler.dart'; // Asks for Bluetooth permissions at runtime
import '../services/ble/ble_service.dart'; // Our custom wrapper around the BLE library
import '../services/fitbit/fitbit_service.dart'; // Fitbit OAuth login + data sync
import '../theme/colors.dart'; // App colour palette
import '../widgets/ai_coach_overlay.dart'; // Floating AI coach button overlay

class DevicePairingScreen extends StatefulWidget {
  final ApiClient apiClient;

  const DevicePairingScreen({super.key, required this.apiClient});

  @override
  State<DevicePairingScreen> createState() => _DevicePairingScreenState();
}

class _DevicePairingScreenState extends State<DevicePairingScreen> {
  final BleService _bleService = BleService.instance;

  // Stream listeners for BLE scan results and connection state changes
  StreamSubscription<List<ScanResult>>? _scanSubscription;
  StreamSubscription<BluetoothConnectionState>? _connectionSubscription;

  // Devices discovered during scan
  List<ScanResult> _scanResults = [];
  // Current connection state (connected / disconnected)
  BluetoothConnectionState _connectionState =
      BluetoothConnectionState.disconnected;
  bool _isScanning = false;
  bool _isConnectingHealth = false;
  // When true, scan for ALL BLE devices instead of only heart rate monitors
  bool _discoverAll = false;
  String? _connectedDeviceId;

  // Tracks how long the current scan has been running
  DateTime? _scanStartTime;
  Timer? _scanElapsedTimer;
  int _scanElapsedSeconds = 0;

  // Remembers when each device was last seen so we can show "2s ago" etc.
  final Map<String, DateTime> _deviceLastSeen = {};

  // Set up BLE stream listeners when the screen loads
  @override
  void initState() {
    super.initState();

    // Listen for newly discovered devices during a scan
    _scanSubscription = _bleService.scanResultsStream.listen((results) {
      if (!mounted) return;
      final now = DateTime.now();
      setState(() {
        _scanResults = results;
        for (final r in results) {
          _deviceLastSeen[r.device.remoteId.str] = now;
        }
      });
    });

    // Listen for connection state changes (connected / disconnected)
    _connectionSubscription =
        _bleService.connectionStateStream.listen((state) {
      if (!mounted) return;
      setState(() {
        _connectionState = state;
      });
    });
  }

  // Clean up stream subscriptions and timers
  @override
  void dispose() {
    _scanSubscription?.cancel();
    _connectionSubscription?.cancel();
    _scanElapsedTimer?.cancel();
    super.dispose();
  }

  // Start scanning for nearby BLE devices
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
      _scanStartTime = DateTime.now();
      _scanElapsedSeconds = 0;
    });
    _scanElapsedTimer?.cancel();
    _scanElapsedTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (mounted) setState(() => _scanElapsedSeconds++);
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
      _scanElapsedTimer?.cancel();
      if (mounted) {
        setState(() {
          _isScanning = false;
        });
      }
    }
  }

  // Connect to a selected BLE device
   Future<void> _connect(ScanResult result) async {
    setState(() {
      _connectedDeviceId = result.device.remoteId.str;
    });

    try {
      // Detect advertised services
      final advertisedServices = result.advertisementData.serviceUuids;
      final hasSpO2 = advertisedServices.contains(BleService.pulseOximeterServiceUuid);
      final hasBP = advertisedServices.contains(BleService.bloodPressureServiceUuid);
      final hasTemp = advertisedServices.contains(BleService.healthThermometerServiceUuid);

      // Connect via BLE service directly with multi-service support
      await _bleService.connectToDevice(
        result.device,
        subscribeSpO2: hasSpO2,
        subscribeBloodPressure: hasBP,
        subscribeTemperature: hasTemp,
      );

      // Also connect via VitalsProvider for unified pipeline
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


  // Disconnect from the currently connected device
  Future<void> _disconnect() async {
    await _bleService.disconnect();
    if (!mounted) return;
    setState(() {
      _connectedDeviceId = null;
    });
  }

  // ── Fitness platform definitions ─────────────────────────────────────────

  // List of supported fitness apps the user can sync through Health Connect
  static const List<_FitnessSource> _fitnessSources = [
    _FitnessSource(
      name: 'Samsung Health',
      icon: Icons.watch,
      color: Color(0xFF1428A0),
      syncNote: 'Open Samsung Health → Settings → Connected services → '
          'Health Connect and enable sync.',
    ),
    _FitnessSource(
      name: 'Garmin Connect',
      icon: Icons.directions_run,
      color: Color(0xFF007CC2),
      syncNote: 'Open Garmin Connect → More → Settings → Health Snapshot → '
          'allow Health Connect export.',
    ),
    _FitnessSource(
      name: 'Fitbit',
      icon: Icons.fitness_center,
      color: Color(0xFF00B0B9),
      syncNote: 'Open Fitbit → Today tab → Profile → App Settings → '
          'Health Connect → enable sync.',
    ),
    _FitnessSource(
      name: 'Polar Flow',
      icon: Icons.favorite,
      color: Color(0xFFD00000),
      syncNote: 'Open Polar Flow → Profile → General Settings → '
          'Health Connect → enable sync.',
    ),
    _FitnessSource(
      name: 'Withings Health Mate',
      icon: Icons.monitor_heart,
      color: Color(0xFF00C4B4),
      syncNote: 'Open Health Mate → Account → Connected Apps → '
          'Health Connect → allow write.',
    ),
    _FitnessSource(
      name: 'Zepp / Amazfit',
      icon: Icons.watch_outlined,
      color: Color(0xFF6B3FA0),
      syncNote: 'Open Zepp app → Profile → Health Connect → enable sync.',
    ),
    _FitnessSource(
      name: 'Google Fit',
      icon: Icons.sports_gymnastics,
      color: Color(0xFF4285F4),
      syncNote: 'Google Fit writes to Health Connect automatically once '
          'you grant AdaptivHealth read permissions.',
    ),
    _FitnessSource(
      name: 'Other / Generic',
      icon: Icons.devices_other,
      color: Colors.grey,
      syncNote: 'Any app that writes to Health Connect will be read once '
          'you grant AdaptivHealth permissions.',
    ),
  ];

  // Show the fitness platform picker, then connect via Health Connect
  Future<void> _connectViaHealth() async {
    if (isIOS) {
      // iOS always goes through HealthKit — no platform picker needed.
      await _doConnectViaHealth('Apple Health');
      return;
    }

    // Show platform picker
    final selected = await showModalBottomSheet<_FitnessSource>(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (ctx) {
        final brightness = Theme.of(ctx).brightness;
        return DraggableScrollableSheet(
          initialChildSize: 0.65,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder: (_, scrollController) => Column(
            children: [
              Container(
                margin: const EdgeInsets.symmetric(vertical: 12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Which fitness app are you using?',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w700,
                        color: AdaptivColors.getTextColor(brightness),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'AdaptivHealth reads data through Health Connect. '
                      'Select your platform to see how to enable the sync.',
                      style: TextStyle(
                        fontSize: 13,
                        color: AdaptivColors.getSecondaryTextColor(brightness),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 8),
              const Divider(),
              Expanded(
                child: ListView.separated(
                  controller: scrollController,
                  itemCount: _fitnessSources.length,
                  separatorBuilder: (_, __) =>
                      const Divider(height: 1, indent: 72),
                  itemBuilder: (_, i) {
                    final src = _fitnessSources[i];
                    return ListTile(
                      leading: Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: src.color.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Icon(src.icon, color: src.color, size: 22),
                      ),
                      title: Text(
                        src.name,
                        style: const TextStyle(fontWeight: FontWeight.w600),
                      ),
                      subtitle: Text(
                        'Syncs via Health Connect',
                        style: TextStyle(
                          fontSize: 12,
                          color:
                              AdaptivColors.getSecondaryTextColor(brightness),
                        ),
                      ),
                      trailing: const Icon(Icons.chevron_right, size: 20),
                      onTap: () => Navigator.pop(ctx, src),
                    );
                  },
                ),
              ),
            ],
          ),
        );
      },
    );

    if (selected == null || !mounted) return;

    // Fitbit is connected directly via the Web API (OAuth2 PKCE),
    // not through Health Connect.
    if (selected.name == 'Fitbit') {
      await _connectFitbitDirect();
      return;
    }

    // Show sync instructions for the chosen platform, then confirm
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            Icon(selected.icon, color: selected.color, size: 22),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                selected.name,
                style: const TextStyle(fontSize: 17),
              ),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Step 1 — Enable Health Connect sync:',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
            const SizedBox(height: 6),
            Text(
              selected.syncNote,
              style: const TextStyle(fontSize: 13),
            ),
            const SizedBox(height: 14),
            const Text(
              'Step 2 — Grant permissions:',
              style: TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
            const SizedBox(height: 6),
            const Text(
              'Tap "Grant Access" and allow AdaptivHealth to read '
              'Heart Rate, SpO₂, Blood Pressure, and Steps from '
              'Health Connect.',
              style: TextStyle(fontSize: 13),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Back'),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Grant Access'),
          ),
        ],
      ),
    );

    if (confirmed != true || !mounted) return;
    await _doConnectViaHealth(selected.name);
  }

  // ── Fitbit direct API connection ──────────────────────────────────────────────

  // Open Fitbit login in browser and pair via OAuth2 (no Health Connect needed)
  Future<void> _connectFitbitDirect() async {
    final brightness = Theme.of(context).brightness;

    final proceed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: const Color(0xFF00B0B9).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.fitness_center,
                  color: Color(0xFF00B0B9), size: 20),
            ),
            const SizedBox(width: 10),
            const Text('Connect Fitbit', style: TextStyle(fontSize: 17)),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'AdaptivHealth will connect directly to your Fitbit account '
              'via the Fitbit Web API.  No Health Connect is required.\n',
              style: TextStyle(
                fontSize: 13,
                color: AdaptivColors.getSecondaryTextColor(brightness),
              ),
            ),
            const Text(
              'What gets read (15-min refresh):',
              style: TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 6),
            const _BulletRow(icon: Icons.favorite, label: 'Heart Rate (intraday)'),
            const _BulletRow(icon: Icons.air, label: 'Blood Oxygen (SpO₂)'),
            const _BulletRow(
                icon: Icons.monitor_heart, label: 'Blood Pressure (if logged)'),
            const SizedBox(height: 14),
            Text(
              'Tapping “Connect” will open the Fitbit login page in your browser.',
              style: TextStyle(
                fontSize: 12,
                color: AdaptivColors.getSecondaryTextColor(brightness),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFF00B0B9),
              foregroundColor: Colors.white,
            ),
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Connect'),
          ),
        ],
      ),
    );

    if (proceed != true || !mounted) return;

    setState(() => _isConnectingHealth = true);
    try {
      await context.read<VitalsProvider>().connectFitbit();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Fitbit connected — data refreshes every 15 min'),
          backgroundColor: Color(0xFF00B0B9),
        ),
      );
    } on FitbitAuthException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fitbit auth failed: ${e.message}')),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Fitbit connection error: $e')),
      );
    } finally {
      if (mounted) setState(() => _isConnectingHealth = false);
    }
  }

  // ── Health Connect source ─────────────────────────────────────────────────

  // Actually connect to Health Connect / HealthKit and show the result
  Future<void> _doConnectViaHealth(String platformName) async {
    setState(() => _isConnectingHealth = true);
    try {
      await context.read<VitalsProvider>().enableHealthKit();
      if (!mounted) return;
      final provider = context.read<VitalsProvider>();
      final source = provider.activeSource;
      if (source == VitalsSource.health) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Connected via $platformName — syncing every 20 s'),
            backgroundColor: Colors.green,
          ),
        );
      } else {
        final healthError = provider.lastHealthError;
        final details = healthError != null ? '\nDetails: $healthError' : '';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Could not read from $platformName. '
              'Make sure $platformName has synced recently and '
              'Health Connect write-permission is enabled in that app. '
              'You can still use BLE pairing or Fitbit direct sync on this phone.'
              '$details',
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

  // Get the best available name for a scanned device
  String _resolveDeviceName(ScanResult result) {
    final platformName = result.device.platformName.trim();
    if (platformName.isNotEmpty) return platformName;
    final advertisedName = result.advertisementData.advName.trim();
    if (advertisedName.isNotEmpty) return advertisedName;
    // Return the short MAC/ID so the card always has a meaningful primary text.
    final id = result.device.remoteId.str;
    return id.length > 17 ? id.substring(0, 17) : id;
  }

  // Returns true if the device has no human-readable name
  bool _isNameUnknown(ScanResult result) {
    return result.device.platformName.trim().isEmpty &&
        result.advertisementData.advName.trim().isEmpty;
  }

  // Turn a BLE manufacturer ID into a name like "Apple" or "Polar"
  String? _resolveManufacturer(ScanResult result) {
    final mfData = result.advertisementData.manufacturerData;
    if (mfData.isEmpty) return null;
    final companyId = mfData.keys.first;
    const known = <int, String>{
      0x004C: 'Apple',
      0x0006: 'Microsoft',
      0x0059: 'Nordic Semi',
      0x0075: 'Samsung',
      0x0131: 'Polar',
      0x0157: 'Garmin',
      0x0294: 'Fitbit',
      0x0499: 'Ruuvi',
      0x000D: 'TI',
      0x001D: 'Qualcomm',
    };
    final name = known[companyId];
    if (name != null) return name;
    return '0x${companyId.toRadixString(16).toUpperCase().padLeft(4, '0')}';
  }

  // Format when a device was last detected (e.g. "2s ago")
  String _formatLastSeen(DateTime? lastSeen) {
    if (lastSeen == null) return '';
    final diff = DateTime.now().difference(lastSeen);
    if (diff.inSeconds < 60) return '${diff.inSeconds}s ago';
    return '${diff.inMinutes}m ago';
  }

  // Progress banner showing scan duration and number of devices found
  Widget _buildScanTimingBanner(Brightness brightness) {
    const totalSeconds = 10;
    final progress = (_scanElapsedSeconds / totalSeconds).clamp(0.0, 1.0);
    final subColor = AdaptivColors.getSecondaryTextColor(brightness);
    final deviceCount = _scanResults.length;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: Colors.blue.withValues(alpha: 0.07),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Colors.blue.withValues(alpha: 0.22)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                if (_isScanning)
                  const SizedBox(
                    width: 12,
                    height: 12,
                    child: CircularProgressIndicator(strokeWidth: 1.8),
                  )
                else
                  Icon(Icons.check_circle_outline,
                      color: Colors.green.shade600, size: 14),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    _isScanning
                        ? 'Scanning... ${_scanElapsedSeconds}s / ${totalSeconds}s'
                        : 'Scan complete — took ${_scanElapsedSeconds}s',
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                      color: _isScanning
                          ? Colors.blue.shade700
                          : Colors.green.shade700,
                    ),
                  ),
                ),
                Text(
                  '$deviceCount ${deviceCount == 1 ? 'device' : 'devices'} found',
                  style: TextStyle(fontSize: 11, color: subColor),
                ),
              ],
            ),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                value: _isScanning ? progress : 1.0,
                minHeight: 4,
                backgroundColor: Colors.blue.withValues(alpha: 0.15),
                valueColor: AlwaysStoppedAnimation<Color>(
                  _isScanning ? Colors.blue : Colors.green,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

    // Small coloured badge for a single service type (HR, SpO2, etc.)
    Widget _serviceBadge(String label, Color color) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10,
          fontWeight: FontWeight.w600,
          color: color,
        ),
      ),
    );
  }

    // Show which health services a device advertises (HR, SpO2, BP, Temp)
    Widget _buildServiceBadges(ScanResult result) {
    final advertisedServices = result.advertisementData.serviceUuids;
    final hasHR = advertisedServices.contains(BleService.heartRateServiceUuid);
    final hasSpO2 = advertisedServices.contains(BleService.pulseOximeterServiceUuid);
    final hasBP = advertisedServices.contains(BleService.bloodPressureServiceUuid);
    final hasTemp = advertisedServices.contains(BleService.healthThermometerServiceUuid);

    if (!hasHR && !hasSpO2 && !hasBP && !hasTemp) {
      return _serviceBadge('Unknown device', Colors.orange);
    }

    return Wrap(
      spacing: 4,
      runSpacing: 4,
      children: [
        if (hasHR) _serviceBadge('HR', Colors.red),
        if (hasSpO2) _serviceBadge('SpO2', Colors.blue),
        if (hasBP) _serviceBadge('BP', Colors.purple),
        if (hasTemp) _serviceBadge('Temp', Colors.teal),
      ],
    );
  }

  // Main screen layout
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
          if (_isScanning || _scanStartTime != null)
            _buildScanTimingBanner(brightness),

          // ── Health Connect / HealthKit section ─────────────────────
          if (kIsWeb)
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
          else
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
                Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: Text(
                      'Or connect a BLE device directly',
                      textAlign: TextAlign.center,
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
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, index) {
                      final result = _scanResults[index];
                      final deviceName = _resolveDeviceName(result);
                      final nameUnknown = _isNameUnknown(result);
                      final macAddress = result.device.remoteId.str;
                      final isConnected =
                          _connectedDeviceId == macAddress &&
                              _connectionState ==
                                  BluetoothConnectionState.connected;
                      final isHrDevice = result.advertisementData.serviceUuids
                          .contains(BleService.heartRateServiceUuid);
                      final isLastUsed =
                          _bleService.lastSavedDeviceId == macAddress;

                      return _ScanResultCard(
                        deviceName: deviceName,
                        nameUnknown: nameUnknown,
                        macAddress: macAddress,
                        rssi: result.rssi,
                        isHrDevice: isHrDevice,
                        isConnected: isConnected,
                        isLastUsed: isLastUsed,
                        serviceBadgesWidget: _buildServiceBadges(result),
                        brightness: brightness,
                        onConnect: () => _connect(result),
                        manufacturerName: _resolveManufacturer(result),
                        lastSeenLabel: _formatLastSeen(_deviceLastSeen[macAddress]),
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

  // Icon for the active data source (BLE, Health Connect, Fitbit, Demo)
  // Icon representing whichever data source is currently active
  Widget _sourceIcon(VitalsSource source) {
    switch (source) {
      case VitalsSource.ble:
        return const Icon(Icons.bluetooth, color: Colors.blue, size: 22);
      case VitalsSource.health:
        return const Icon(Icons.watch, color: Colors.green, size: 22);
      case VitalsSource.fitbit:
        return const Icon(Icons.fitness_center,
            color: Color(0xFF00B0B9), size: 22);
      case VitalsSource.mock:
        return const Icon(Icons.science, color: Colors.orange, size: 22);
    }
  }

  // Readable name for each data source
  // Human-readable name shown below the active source icon
  String _sourceName(VitalsSource source) {
    switch (source) {
      case VitalsSource.ble:
        return 'BLE Heart Rate Monitor';
      case VitalsSource.health:
        return isIOS ? 'Apple Health' : 'Health Connect';
      case VitalsSource.fitbit:
        return 'Fitbit';
      case VitalsSource.mock:
        return 'Simulated (Demo Mode)';
    }
  }

  // Coloured badge label (LIVE, SYNCED, FITBIT, DEMO)
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
      case VitalsSource.fitbit:
        color = const Color(0xFF00B0B9);
        label = 'FITBIT';
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
// ---------------------------------------------------------------------------
// Data class for fitness platform source picker
// ---------------------------------------------------------------------------

// Holds info about a fitness app (name, icon, sync instructions)
class _FitnessSource {
  final String name;
  final IconData icon;
  final Color color;

  /// Short instructions shown to the user explaining how to enable
  /// Health Connect sync in this specific app.
  final String syncNote;

  const _FitnessSource({
    required this.name,
    required this.icon,
    required this.color,
    required this.syncNote,
  });
}

// ---------------------------------------------------------------------------
// Small helper widget used inside the Fitbit auth dialog
// ---------------------------------------------------------------------------

// A single bullet point row with an icon and label
class _BulletRow extends StatelessWidget {
  final IconData icon;
  final String label;

  const _BulletRow({required this.icon, required this.label});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        children: [
          Icon(icon, size: 15, color: const Color(0xFF00B0B9)),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 13)),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// BLE scan result card
// ---------------------------------------------------------------------------

// Card showing one discovered device with name, signal, services, and connect button
class _ScanResultCard extends StatelessWidget {
  final String deviceName;
  final bool nameUnknown;
  final String macAddress;
  final int rssi;
  final bool isHrDevice;
  final bool isConnected;
  final bool isLastUsed;
  final Widget serviceBadgesWidget;
  final Brightness brightness;
  final VoidCallback onConnect;
  final String? manufacturerName;
  final String lastSeenLabel;

  const _ScanResultCard({
    required this.deviceName,
    required this.nameUnknown,
    required this.macAddress,
    required this.rssi,
    required this.isHrDevice,
    required this.isConnected,
    required this.isLastUsed,
    required this.serviceBadgesWidget,
    required this.brightness,
    required this.onConnect,
    this.manufacturerName,
    this.lastSeenLabel = '',
  });

  // Convert RSSI to 0-4 bars (like Wi-Fi strength indicator)
  int get _signalBars {
    if (rssi >= -60) return 4;
    if (rssi >= -70) return 3;
    if (rssi >= -80) return 2;
    if (rssi >= -90) return 1;
    return 0;
  }

  Color get _signalColor {
    if (rssi >= -60) return Colors.green;
    if (rssi >= -70) return Colors.lightGreen;
    if (rssi >= -80) return Colors.orange;
    return Colors.red;
  }

  String get _signalLabel {
    if (rssi >= -60) return 'Excellent';
    if (rssi >= -70) return 'Good';
    if (rssi >= -80) return 'Fair';
    return 'Weak';
  }

  @override
  Widget build(BuildContext context) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final subColor = AdaptivColors.getSecondaryTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);

    // Border is teal-green for HR monitors, subtle for generic devices.
    final borderColor = isConnected
        ? Colors.green
        : isHrDevice
            ? Colors.teal.withValues(alpha: 0.55)
            : AdaptivColors.neutral300;

    return Container(
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: borderColor, width: isConnected ? 2 : 1),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              // Device type icon
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: (isHrDevice ? Colors.red : Colors.blueGrey)
                      .withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(
                  isHrDevice ? Icons.monitor_heart_rounded : Icons.bluetooth,
                  color: isHrDevice ? Colors.red : Colors.blueGrey,
                  size: 22,
                ),
              ),
              const SizedBox(width: 12),

              // Name + MAC address
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Row: name + badges
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            deviceName,
                            style: TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                              color: nameUnknown ? subColor : textColor,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        if (isLastUsed) ...[
                          const SizedBox(width: 6),
                          _ChipLabel(
                              label: 'Last used',
                              color: Colors.blue.shade700),
                        ],
                        if (isConnected) ...[
                          const SizedBox(width: 6),
                          _ChipLabel(
                              label: 'Connected', color: Colors.green),
                        ],
                      ],
                    ),

                    const SizedBox(height: 2),

                    // MAC + manufacturer name
                    Row(
                      children: [
                        Text(
                          macAddress,
                          style: TextStyle(
                            fontSize: 11,
                            fontFamily: 'monospace',
                            color: subColor,
                            letterSpacing: 0.5,
                          ),
                        ),
                        if (manufacturerName != null) ...[
                          const SizedBox(width: 6),
                          Text(
                            '· $manufacturerName',
                            style: TextStyle(
                              fontSize: 11,
                              color: Colors.blue.shade400,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ],
                    ),
                    // Last-seen timestamp — updates on each scan advertisement
                    if (lastSeenLabel.isNotEmpty)
                      Text(
                        'Last seen: $lastSeenLabel',
                        style: TextStyle(
                          fontSize: 10,
                          color: subColor,
                          fontStyle: FontStyle.italic,
                        ),
                      ),
                  ],
                ),
              ),

              // Signal strength column
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  _SignalBars(bars: _signalBars, color: _signalColor),
                  const SizedBox(height: 2),
                  Text(
                    '$rssi dBm',
                    style: TextStyle(
                      fontSize: 10,
                      color: _signalColor,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    _signalLabel,
                    style: TextStyle(fontSize: 10, color: subColor),
                  ),
                ],
              ),
            ],
          ),

          // Device type + service badges row
          const SizedBox(height: 8),
          Row(
            children: [
              if (isHrDevice)
                Padding(
                  padding: const EdgeInsets.only(right: 6),
                  child: _ChipLabel(
                    label: 'Heart Rate Monitor',
                    color: Colors.red.shade700,
                    filled: false,
                  ),
                ),
              Expanded(child: serviceBadgesWidget),
              if (!isConnected)
                ElevatedButton(
                  onPressed: onConnect,
                  style: ElevatedButton.styleFrom(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                    minimumSize: Size.zero,
                    tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  ),
                  child: const Text('Connect',
                      style: TextStyle(
                          fontSize: 13, fontWeight: FontWeight.w600)),
                )
              else
                const Icon(Icons.check_circle_rounded,
                    color: Colors.green, size: 22),
            ],
          ),
        ],
      ),
    );
  }
}

// Tiny rounded label chip (e.g. "Last used", "Connected")
class _ChipLabel extends StatelessWidget {
  final String label;
  final Color color;
  final bool filled;

  const _ChipLabel({
    required this.label,
    required this.color,
    this.filled = true,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
      decoration: BoxDecoration(
        color: filled ? color.withValues(alpha: 0.12) : Colors.transparent,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.5)),
      ),
      child: Text(
        label,
        style: TextStyle(
            fontSize: 10, fontWeight: FontWeight.w700, color: color),
      ),
    );
  }
}

// Four-bar signal strength widget (like Wi-Fi bars)
class _SignalBars extends StatelessWidget {
  final int bars; // 0-4
  final Color color;

  const _SignalBars({required this.bars, required this.color});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.end,
      children: List.generate(4, (i) {
        final filled = i < bars;
        final height = 6.0 + i * 3.0; // 6, 9, 12, 15 px
        return Padding(
          padding: const EdgeInsets.only(left: 2),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: 5,
            height: height,
            decoration: BoxDecoration(
              color: filled ? color : color.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        );
      }),
    );
  }
}