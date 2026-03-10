/*
BLE Permission Handler.

Asks the user for permission to use Bluetooth on their phone.
Different phones need different permissions:
  - iPhones: just need Bluetooth permission
  - Android 12+: need Bluetooth Scan + Bluetooth Connect
  - Older Android: need Location permission (required for BLE scanning)

This runs before the app tries to connect to any Bluetooth device.
*/

// Gives us debugging tools and kDebugMode flag
import 'package:flutter/foundation.dart';
// Plugin that handles asking the user for system permissions
import 'package:permission_handler/permission_handler.dart';
// Checks which platform we're running on (iOS, Android, desktop)
import '../../config/platform_guard.dart';

// Handles requesting Bluetooth permissions on different phone types
class BlePermissionHandler {

  // Ask the user for all the Bluetooth permissions we need
  static Future<bool> requestBlePermissions() async {
    // On iPhones: just request the basic Bluetooth permission
    if (isIOS) {
      final status = await Permission.bluetooth.request();
      // Granted or limited both mean we can use Bluetooth
      return status.isGranted || status.isLimited;
    }

    // On desktop or web: no Bluetooth permissions needed
    if (!isAndroid) {
      return true;
    }

    // On Android: figure out which version we're on
    final sdkInt = _getAndroidSdkInt();

    // Android 12+ needs scan + connect permissions
    final permissions = <Permission>[
      Permission.bluetoothScan,
      Permission.bluetoothConnect,
    ];

    // Older Android also needs location permission for BLE scanning
    if (sdkInt == null || sdkInt < 31) {
      permissions.add(Permission.locationWhenInUse);
    }

    // Show the permission dialogs to the user
    final statusMap = await permissions.request();

    // Check if the user granted everything we asked for
    final allGranted = statusMap.values.every(
      (status) => status.isGranted || status.isLimited,
    );

    // Log which permissions were denied (only during development)
    if (!allGranted && kDebugMode) {
      debugPrint('BLE permissions denied: $statusMap');
    }

    return allGranted;
  }

  // Check if we already have Bluetooth permissions (without showing a dialog)
  static Future<bool> hasPermissions() async {
    if (isIOS) {
      // On iPhone: check the Bluetooth permission status
      return (await Permission.bluetooth.status).isGranted;
    }
    if (isAndroid) {
      // On Android: check both scan and connect permissions
      final scan = await Permission.bluetoothScan.status;
      final connect = await Permission.bluetoothConnect.status;
      return scan.isGranted && connect.isGranted;
    }
    // Desktop/web: permissions not needed, always "granted"
    return true;
  }

  // Try to read the Android SDK version number from the OS version string
  static int? _getAndroidSdkInt() {
    final version = safeOsVersion;
    // Look for "SDK 31" or similar pattern in the version string
    final match = RegExp(r'SDK\s*(\d+)').firstMatch(version);
    if (match == null) {
      return null;
    }
    return int.tryParse(match.group(1) ?? '');
  }
}
