import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:permission_handler/permission_handler.dart';

/// Handles runtime BLE permission requests for Android and iOS.
///
/// iOS: Core Bluetooth prompts automatically on first BLE access; this
/// handler requests the `bluetoothConnect` permission so the user sees
/// the system dialog proactively.
///
/// Android 12+ (SDK 31+): BLUETOOTH_SCAN + BLUETOOTH_CONNECT.
/// Android < 12: ACCESS_FINE_LOCATION (required for BLE scanning).
class BlePermissionHandler {
  /// Request BLE permissions required for scanning and connecting.
  ///
  /// Returns `true` if all necessary permissions are granted.
  static Future<bool> requestBlePermissions() async {
    if (Platform.isIOS) {
      // On iOS the system shows the Bluetooth permission dialog when we
      // first attempt to use Core Bluetooth. Requesting the permission here
      // triggers the dialog proactively so the user is not surprised.
      final status = await Permission.bluetooth.request();
      return status.isGranted || status.isLimited;
    }

    if (!Platform.isAndroid) {
      // Desktop / web — no runtime BLE permissions required.
      return true;
    }

    final sdkInt = _getAndroidSdkInt();

    final permissions = <Permission>[
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
    ];

    // Android < 12 requires location to perform BLE scanning.
    if (sdkInt == null || sdkInt < 31) {
      permissions.add(Permission.locationWhenInUse);
    }

    final statusMap = await permissions.request();

    final allGranted = statusMap.values.every(
      (status) => status.isGranted || status.isLimited,
    );

    if (!allGranted && kDebugMode) {
      debugPrint('BLE permissions denied: $statusMap');
    }

    return allGranted;
  }

  /// Returns `true` if BLE permissions have already been granted without
  /// showing a dialog. Useful for checking before auto-reconnect.
  static Future<bool> hasPermissions() async {
    if (Platform.isIOS) {
      return (await Permission.bluetooth.status).isGranted;
    }
    if (Platform.isAndroid) {
      final scan = await Permission.bluetoothScan.status;
      final connect = await Permission.bluetoothConnect.status;
      return scan.isGranted && connect.isGranted;
    }
    return true;
  }

  static int? _getAndroidSdkInt() {
    final version = Platform.operatingSystemVersion;
    final match = RegExp(r'SDK\s*(\d+)').firstMatch(version);
    if (match == null) {
      return null;
    }
    return int.tryParse(match.group(1) ?? '');
  }
}
