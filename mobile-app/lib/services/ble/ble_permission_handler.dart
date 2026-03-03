import 'dart:io';

import 'package:permission_handler/permission_handler.dart';

/// Handles runtime BLE permission requests for Android.
class BlePermissionHandler {
  /// Request BLE permissions required for scanning and connecting.
  ///
  /// Android 12+ (SDK 31+):
  /// - BLUETOOTH_SCAN
  /// - BLUETOOTH_CONNECT
  ///
  /// Android < 12:
  /// - ACCESS_FINE_LOCATION
  static Future<bool> requestBlePermissions() async {
    if (!Platform.isAndroid) {
      return true;
    }

    final sdkInt = _getAndroidSdkInt();

    final permissions = <Permission>[
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
    ];

    if (sdkInt != null && sdkInt < 31) {
      permissions.add(Permission.locationWhenInUse);
    }

    final statusMap = await permissions.request();

    for (final status in statusMap.values) {
      if (!(status.isGranted || status.isLimited)) {
        return false;
      }
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
