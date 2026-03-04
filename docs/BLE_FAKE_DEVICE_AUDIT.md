# BLE Fake Device Detection & Fix Prompt

**Objective:** Determine if the BLE scan is returning real devices or hardcoded/generated fake devices, and fix the issue.

**Red Flags Observed:**
- Devices appear instantly (no 2–5 second BLE discovery latency)
- All devices show only MAC addresses, no names
- App connects to "every device" instantly (suspicious instant success)
- Devices remain in list regardless of physical device proximity

---

## PHASE 1: DEVICE NAME RESOLUTION AUDIT

### 1.1 Check Device Name Source

Search for how device names are resolved in the pairing screen:

**Files to inspect:**
- [mobile-app/lib/screens/device_pairing_screen.dart](mobile-app/lib/screens/device_pairing_screen.dart)
- Check `_resolveDeviceName()` method and how `ScanResult` names are displayed

**What to look for:**

```dart
// RED FLAG: Device name from nowhere (not from ScanResult)
String _resolveDeviceName(ScanResult result) {
  return result.device.platformName ?? result.device.remoteId.str;
  // ^ If this always returns remoteId.str, names are not being discovered
}

// LEGITIMATE: Device name from advertisement payload
String _resolveDeviceName(ScanResult result) {
  final advName = result.advertisementData.localName;
  if (advName != null && advName.isNotEmpty) return advName;
  return result.device.platformName ?? result.device.remoteId.str;
  // ^ This checks advertisement local name first
}
```

**Action:** Search for device name display in [device_pairing_screen.dart](mobile-app/lib/screens/device_pairing_screen.dart):
- Find the widget that renders each `ScanResult` in the list
- Check if it displays `advertiser.localName` or only MAC address
- Look for `remoteId.str` being the fallback

### 1.2 Check Advertisement Data Parsing

Verify `ScanResult.advertisementData` is being populated by `flutter_blue_plus`:

```dart
// In _startScan() or scan results listener:
_bleService.scanResultsStream.listen((results) {
  for (final result in results) {
    final localName = result.advertisementData.localName;
    final serviceUuids = result.advertisementData.serviceUuids;
    
    if (localName != null && localName.isNotEmpty) {
      debugPrint('Found device: $localName (${result.device.remoteId})');
      // ^ This should print actual BLE device names
    } else {
      debugPrint('Device with no name: ${result.device.remoteId}');
      // ^ Legitimate if device doesn't advertise a name
    }
  }
});
```

**Red flag:** If **all devices** have `localName == null` or empty, the advertisement data is not being parsed, OR devices are hardcoded without names.

---

## PHASE 2: SCAN RESULT SOURCE VERIFICATION

### 2.1 Check if Scan Results Are Hardcoded

Search [ble_service.dart](mobile-app/lib/services/ble/ble_service.dart) for any hardcoded device generation:

```dart
// RED FLAG: Hardcoded scan results
List<ScanResult> _generateFakeDevices() {
  return [
    // Mock device objects created in code
  ];
}

// RED FLAG: Device list initialized at startup
final List<ScanResult> _mockDevices = [
  // Pre-populated devices
];

// RED FLAG: Scan results returned without listening to flutter_blue_plus
Future<void> startScan() {
  return Future.delayed(Duration(milliseconds: 100)).then((_) {
    _scanResultsController.add(_mockDevices); // <- FAKE
  });
}
```

**Legitimate pattern:**
```dart
Future<void> startScan() {
  _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
    // results come from native BLE stack, not hardcoded
    _scanResultsController.add(results);
  });
  
  await FlutterBluePlus.startScan(...);
}
```

**Action:** Grep for:
- `const.*ScanResult`
- `List<ScanResult>.*=.*\[`
- `_generateFakeScanResults`
- `_mockDevices`
- `Future.value.*ScanResult`

### 2.2 Check Scan Start Call

Verify `FlutterBluePlus.startScan()` is actually called:

```dart
// LEGITIMATE: Real flutter_blue_plus.startScan() called
await FlutterBluePlus.startScan(
  withServices: [heartRateServiceUuid],
  timeout: Duration(seconds: 10),
  androidScanMode: AndroidScanMode.lowLatency,
);

// RED FLAG: Hardcoded return instead of awaiting native scan
Future<void> startScan() {
  return Future.value(); // Nothing happens; results added artificially
}
```

**Action:** Check [ble_service.dart L148-162](mobile-app/lib/services/ble/ble_service.dart#L148-L162) — verify `FlutterBluePlus.startScan()` is called and awaited.

---

## PHASE 3: INSTANT CONNECTION RED FLAG

### 3.1 Check Connection Behavior

The fact that **every device connects instantly** is a major red flag. Real BLE connections take 1–5 seconds:

**Red flag pattern:**
```dart
Future<void> connectToDevice(BluetoothDevice device) async {
  // If this completes in < 100ms, it's fake
  _updateConnectionStatus(BleConnectionStatus.connected);
  return; // Instant return without calling device.connect()
}

// RED FLAG: Mocking connection state
_connectionActiveDevice = device;
_connectionState = BluetoothConnectionState.connected;
// ^ Sets state without awaiting device.connect()
```

**Legitimate pattern:**
```dart
Future<void> connectToDevice(BluetoothDevice device) async {
  _updateConnectionStatus(BleConnectionStatus.connecting);
  
  try {
    await device.connect(
      timeout: const Duration(seconds: 12),
      autoConnect: true,
    );
    // ^ This takes 1–5 seconds on real devices
    
    _updateConnectionStatus(BleConnectionStatus.connected);
  } catch (e) {
    _updateConnectionStatus(BleConnectionStatus.disconnected);
    rethrow;
  }
}
```

**Action:** Check [ble_service.dart L172-201](mobile-app/lib/services/ble/ble_service.dart#L172-L201) — verify `await device.connect(timeout: ...)` is called.

---

## PHASE 4: DEVICE NAME DISPLAY IN UI

### 4.1 Check Pairing Screen Device Tile

Find how each device is rendered in the list:

**File:** [device_pairing_screen.dart](mobile-app/lib/screens/device_pairing_screen.dart)

Search for where device name is displayed:

```dart
// RED FLAG: Only showing MAC address
Text(result.device.remoteId.str) // Just MAC, no name resolution

// LEGITIMATE: Show advertised name first, fall back to MAC
Text(
  result.advertisementData.localName ?? 
  result.device.platformName ?? 
  result.device.remoteId.str
)

// LEGITIMATE: Show both name and MAC for clarity
Text(
  '${result.advertisementData.localName ?? "Unknown"} (${result.device.remoteId.str})'
)
```

**Action:** Find the device list widget (should be a `ListView` or `Column` iterating `_scanResults`), check what text is displayed for each device.

---

## PHASE 5: SCANNING LATENCY TEST

### 5.1 Check Scan Timeline

Add debug logging to measure real scan latency:

```dart
Future<void> startScan() {
  _updateConnectionStatus(BleConnectionStatus.scanning);
  
  final scanStartTime = DateTime.now();
  print('[BLE] Scan started at $scanStartTime');
  
  _scanSubscription = FlutterBluePlus.scanResults.listen((results) {
    final elapsed = DateTime.now().difference(scanStartTime).inMilliseconds;
    print('[BLE] Received ${results.length} results after ${elapsed}ms');
    
    for (final result in results) {
      print('[BLE] Device: ${result.advertisementData.localName ?? result.device.remoteId.str} (RSSI: ${result.rssi})');
    }
    
    _scanResultsController.add(results);
  });
  
  await FlutterBluePlus.startScan(
    withServices: [heartRateServiceUuid],
    timeout: Duration(seconds: 10),
  );
  
  print('[BLE] startScan() returned');
}
```

**Expected behavior:**
- `Received 0 results` → wait 1–2 seconds → `Received 1 result` → wait → `Received 2 results`, etc.
- Each device appears over time, not all at once

**Fake behavior:**
- `Received 5 results` immediately on first call
- All results show at once with no delay

---

## PHASE 6: FIX IF FAKE DEVICES DETECTED

If devices are hardcoded/fake, apply these fixes:

### 6.1 Remove Hardcoded Device Lists

**Find & delete:**
```dart
const List<ScanResult> _mockDevices = [
  // Remove this entire section
];
```

### 6.2 Verify BluetoothDevice UUID Matching

Ensure devices are filtered by actual service UUID, not by name/MAC:

**File:** [ble_service.dart L137-150](mobile-app/lib/services/ble/ble_service.dart#L137-L150)

```dart
// CORRECT: Filter by advertised service UUID
_scanSubscription = FlutterBluePlus.scanResults.listen((results) {
  final filtered = discoverAll
      ? results.toList()
      : results.where((result) {
          return result.advertisementData.serviceUuids
              .contains(heartRateServiceUuid);
        }).toList();
  _scanResultsController.add(filtered);
});
```

If this filter is not working, verify:
- Real BLE device advertises Heart Rate Service UUID (0x180D)
- `result.advertisementData.serviceUuids` is being populated by `flutter_blue_plus`

### 6.3 Fix Device Name Display

**File:** [device_pairing_screen.dart](mobile-app/lib/screens/device_pairing_screen.dart)

Find the device tile widget and update it:

```dart
// BEFORE (only MAC):
ListTile(
  title: Text(result.device.remoteId.str),
)

// AFTER (name or MAC):
ListTile(
  title: Text(
    result.advertisementData.localName ?? 
    result.device.platformName ??
    'Unknown Device'
  ),
  subtitle: Text(result.device.remoteId.str), // Show MAC as subtitle for clarity
)
```

### 6.4 Add Connection Timeout Logging

**File:** [ble_service.dart _connectAndSubscribe](mobile-app/lib/services/ble/ble_service.dart#L200-L230)

Add debug output to verify real connection attempt:

```dart
Future<void> _connectAndSubscribe(...) async {
  try {
    final startTime = DateTime.now();
    debugPrint('[BLE] Attempting to connect to ${device.platformName}...');
    
    await device.connect(
      timeout: const Duration(seconds: 12),
      autoConnect: allowAutoConnect,
    );
    
    final elapsed = DateTime.now().difference(startTime).inMilliseconds;
    debugPrint('[BLE] Connected in ${elapsed}ms');
    
  } catch (e) {
    debugPrint('[BLE] Connection failed after 12s: $e');
    rethrow;
  }
}
```

**Expected:**
- First connection: 1000–5000ms
- Reconnection: 100–500ms (cached bond)
- Failure: 12000ms (timeout reached)

**Fake sign:**
- Completes in < 100ms every time

---

## EXECUTION CHECKLIST

Run these checks in order:

- [ ] **Search [ble_service.dart](mobile-app/lib/services/ble/ble_service.dart) for hardcoded device lists**
  - Grep: `const.*ScanResult|_mockDevices|_generateFake`

- [ ] **Verify `FlutterBluePlus.startScan()` is called** at [L148-162](mobile-app/lib/services/ble/ble_service.dart#L148-L162)

- [ ] **Check device name resolution** in [device_pairing_screen.dart](mobile-app/lib/screens/device_pairing_screen.dart)
  - Search for how `ScanResult` is rendered in the list

- [ ] **Add temporal logging** to `startScan()` and `_connectAndSubscribe()` to measure real latency

- [ ] **Test with real device:**
  - Activate a real BLE Heart Rate monitor (or use a simulator)
  - Press "Scan" button in app
  - Observe logs: devices should appear **over 2–5 seconds**, not instantly
  - Press "Connect" on one device
  - Observe logs: connection should take **1–5 seconds**, not instant

- [ ] **If latency is realistic**, BLE is real
- [ ] **If latency is instant**, remove hardcoded devices and fix the scan pipeline

---

## EXPECTED REAL-DEVICE BEHAVIOR

When `ShowAllDevices` is toggled and scanning with a real device in range:

```
[BLE] Scan started at ...
[BLE] startScan() returned
... (wait 1–2 seconds) ...
[BLE] Received 1 results after 1234ms
[BLE] Device: PixelWatch (1A:2B:3C:4D:5E:6F) (RSSI: -65)
... (wait 1–2 seconds) ...
[BLE] Received 2 results after 3456ms
[BLE] Device: PixelWatch (1A:2B:3C:4D:5E:6F) (RSSI: -62)
[BLE] Device: CoospoH808S (7H:8I:9J:0K:1L:2M) (RSSI: -75)
```

**Key signatures:**
- Names appear (not just MAC addresses)
- Latency between first and second device result: 1–3 seconds
- RSSI values vary (signal strength)
- Same device repeats with different RSSI (natural BLE behavior)

---

## REPORTING TEMPLATE

After investigation, provide:

```markdown
# BLE Fake Device Investigation Report

## Device List Behavior
- Devices appear: [ ] Instantly (FAKE) / [ ] Over 2–5 seconds (REAL)
- Device names shown: [ ] None, only MAC / [ ] Advertised names or MAC fallback
- All devices named identically: [ ] Yes (FAKE) / [ ] No (REAL)

## Connection Behavior
- Connection completes in: [ ] <100ms (FAKE) / [ ] 1–5000ms (REAL)
- Timeout errors occur: [ ] Never / [ ] On bad/distant devices (REAL)

## Code Inspection
- Hardcoded device list found: [ ] Yes (DELETE IT) / [ ] No
- FlutterBluePlus.startScan() called: [ ] Yes (PASS) / [ ] No (FIX)
- Real advertementData.localName used: [ ] Yes / [ ] No (FIX)

## Verdict
[ ] Real BLE Implementation  
[ ] Hardcoded Demo (requires fix)  
[ ] Partial (mix of real + fake)

## Fixes Applied
1. [list any code changes made]
2. [delete any hardcoded data]
3. [update UI to show real names]
```

