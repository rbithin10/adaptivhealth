# BLE Implementation Legitimacy Audit Prompt

**Objective:** Determine whether the AdaptivHealth Flutter app has a real BLE (Bluetooth Low Energy) implementation or a hardcoded/mocked demo.

**Task Type:** Code audit + runtime behavior analysis  
**Scope:** Mobile app (`mobile-app/lib/`)  
**Expected Output:** Detailed findings document with Pass/Fail per criterion

---

## PHASE 1: CODE INSPECTION (Static Analysis)

### 1.1 BLE Library & Initialization
- [ ] Check `pubspec.yaml` for `flutter_blue_plus` dependency version
  - **Legitimate indicator:** Real package version (e.g., `flutter_blue_plus: ^1.40.0`)
  - **Red flag:** No dependency, or commented out
- [ ] Locate `ble_service.dart` or equivalent BLE service file
  - Search workspace for files containing: `flutter_blue_plus`, `FlutterBluePlus`, `BluetoothDevice`
  - Report file path and line count
- [ ] Check BLE service initialization code
  - **Legitimate:** Calls `FlutterBluePlus.instance`, `FlutterBluePlus.startScan()`, `flutterBluePlus.state` property
  - **Red flag:** Hard-coded device list like `List<BluetoothDevice> mockDevices = [...]` at service init
  - **Red flag:** Constructor returns pre-filled scanned devices without calling scan

### 1.2 Device Scanning Logic
- [ ] Locate device scan implementation
  - Search for: `startScan()`, `startScan({`, `stopScan()`, `scanResults`, `FlutterBluePlus.instance.scan`
- [ ] Inspect scan parameters / filters
  - **Real implementation:** Specifies service UUIDs (e.g., `0x180D` for Heart Rate), timeout, allowDuplicates
  - **Demo flag:** Scans with zero filtering or hardcoded results returned immediately
- [ ] Check for scan result stream usage
  - **Legitimate:** Listens to `FlutterBluePlus.instance.onScanResults`, processes dynamic results
  - **Demo flag:** Scan completes but device list is static/cached from app startup
- [ ] Verify scan stops on timeout or user action
  - **Legitimate:** `FlutterBluePlus.instance.stopScan()` called after X seconds or on user tap
  - **Red flag:** Scan never stops, or stopScan is not called in catches/timeouts

### 1.3 Device Connection Logic
- [ ] Locate connection code (search: `connect()`, `connectToDevice()`, `BluetoothDevice.connect`)
- [ ] Check connection state listeners
  - **Legitimate:** Subscribes to `device.connectionState`, handles `disconnected` → `connecting` → `connected`
  - **Demo flag:** Immediately jumps to `connected` state without awaiting connection future
- [ ] Verify timeout handling
  - **Legitimate:** Has `.timeout(Duration(seconds: X))` or connection abort logic
  - **Red flag:** No timeout, or catch blocks silently ignore connection errors
- [ ] Check for disconnect/reconnection logic
  - **Legitimate:** `device.disconnect()` actually called on cleanup; app handles surprise disconnects
  - **Demo flag:** No disconnect method called, or connection never actually closes

### 1.4 GATT Service Discovery
- [ ] Search for: `discoverServices()`, `services`, `characteristics`, `0x180D`, `0x2A37`
- [ ] Verify Heart Rate Service (0x180D) is discovered
  - **Legitimate:** Code iterates `device.discoveredServices`, filters for `0x180D`, extracts characteristic `0x2A37`
  - **Demo flag:** Services list is hard-coded or assumed to exist without discovery
- [ ] Check if services list is dynamic
  - **Legitimate:** `await device.discoverServices()` called on connect, services populated at runtime
  - **Demo flag:** `List<BluetoothService> services = const [...]` or services never re-fetched after reconnect
- [ ] Verify characteristic UUID validation
  - **Legitimate:** Code checks characteristic UUID matches `0x2A37` before reading
  - **Red flag:** Reads any characteristic without UUID validation, or reads characteristics that don't exist on device

### 1.5 Data Reading/Writing Logic
- [ ] Locate read characteristic code (search: `read()`, `readValue()`, `onValueReceived`)
- [ ] Check notification subscription
  - **Legitimate:** `characteristic.onValueReceived.listen()` OR `characteristic.read()` used with timeout
  - **Demo flag:** Mock data returned without actual BLE read (e.g., `return Future.value([72, 0])`)
- [ ] Verify data parsing matches BLE spec
  - **Legitimate:** Heart rate value extracted from byte array `data[0] & 0xFF` (Heart Rate Measurement spec)
  - **Demo flag:** Hardcoded `heartRate = 72` or random `Random().nextInt(180)`
- [ ] Check for write operations (if any)
  - **Legitimate:** `characteristic.write()` called with proper byte array, awaits response
  - **Demo flag:** Write calls are mocked or don't actually send data over BLE
- [ ] Verify error handling on read failure
  - **Legitimate:** Catches `blue_plus.FlutterBluePlusException`, handles timeout, wraps in try-catch
  - **Red flag:** Returns dummy data on error instead of propagating failure

### 1.6 Hardcoded Data Red Flags
Search entire BLE service file for:
- [ ] `const mockData = [...]` or `mockDevices = [...]`
- [ ] `return Future.value([...])` returning data without actual BLE call
- [ ] `Random().nextInt()` to generate "sensor" data
- [ ] Hardcoded heart rates like `heartRate = 72`, `heartRate = Random().nextInt(180)`
- [ ] Static device UUIDs/MAC addresses that never change
- [ ] `// TODO: Replace with real BLE` or `// MOCK:` comments

---

## PHASE 2: RUNTIME BEHAVIOR ANALYSIS

### 2.1 Test Setup
- [ ] Have a real BLE device available (smartwatch, fitness tracker, BLE simulator)
- [ ] Connect device to test phone, verify it appears in system Bluetooth settings
- [ ] Note device MAC address and advertised name
- [ ] Keep the device powered on and in range (< 10 meters)

### 2.2 Scanning Test
- [ ] Open app, navigate to BLE pairing/scanning screen
- [ ] Start scan and observe logs (use `flutter run --verbose`)
  - **Legitimate signature:**
    - Logs show `FlutterBluePlus.instance.scan` called
    - Scan results arrive over time (not instantly)
    - Device appears in list once per advertisement packet (may take 2–5 seconds per device)
  - **Demo signature:**
    - Device list populated immediately with no delay
    - Same devices always appear regardless of physical device state
    - No delay between button press and data display
- [ ] Move device out of range, wait 10 seconds
  - **Legitimate:** Device disappears from scan results (or shows periodically)
  - **Demo:** Device remains in list permanently
- [ ] Move device back in range
  - **Legitimate:** Device reappears in scan results
  - **Demo:** Device was never removed

### 2.3 Connection Test
- [ ] Tap device to connect
- [ ] Observe logs for connection sequence
  - **Legitimate:**
    - Logs: `connectionState changed to connecting`
    - Brief delay (1–3 seconds typically)
    - Logs: `connectionState changed to connected`
    - Logs: `Discovering services...` then service UUIDs printed
  - **Demo:**
    - Immediate `connected` state with no delay
    - No service discovery logs
    - First data appears instantly without GATT operations
- [ ] Check if GATT service discovery completes
  - **Legitimate:** Logs show discovered service `0x180D`, characteristic `0x2A37`
  - **Demo:** No service discovery output, or services assumed
- [ ] Turn off device or move out of range while connected
  - **Legitimate:** App shows disconnection message, UI reflects disconnect state
  - **Demo:** Data continues to arrive or connection state doesn't change

### 2.4 Data Reading Test
- [ ] Once connected, observe heart rate data
  - **Legitimate signature:**
    - Data updates every 1–2 seconds (BLE notification rate)
    - Values change naturally (e.g., 72, 73, 75, 72, 71 BPM)
    - Matches actual device readings checked in system Bluetooth settings
  - **Demo signature:**
    - Data updates at fixed interval (e.g., every exactly 1 second)
    - Values cycle predictably (e.g., 70–80, then 80–90, pseudo-random)
    - Does NOT match actual device when checked elsewhere
- [ ] Perform physical action (walk, exercise, or rest)
  - **Legitimate:** Heart rate responds naturally to activity within 5–10 seconds
  - **Demo:** Heart rate unchanged or follows sequence unrelated to activity
- [ ] Verify data format
  - **Legitimate:** Byte-level parsing of 0x2A37 spec (HR flags + HR value in BPM)
  - **Demo:** Always integer 0–255, or unrealistic values (e.g., 500 BPM)

### 2.5 Device Switching Test
- [ ] If app supports multiple devices, connect to Device A
- [ ] Disconnect from Device A, connect to Device B
  - **Legitimate:** App properly closes Device A connection, clears old services, discovers new ones
  - **Demo:** May not properly disconnect, services from A remain in memory, confusing behavior
- [ ] Check logs for old service references after switching
  - **Red flag:** Old device's characteristic still being read after switching

### 2.6 Error Handling Test
- [ ] Disable Bluetooth on phone while connected
  - **Legitimate:** App shows error message, gracefully handles disconnection
  - **Demo:** Crash or continue displaying stale data
- [ ] Turn device off while connected
  - **Legitimate:** App detects disconnection within 5–10 seconds
  - **Demo:** Takes > 30 seconds or never detects it
- [ ] Go out of range (> 50 meters)
  - **Legitimate:** Connection fails or drops after 10–30 seconds
  - **Demo:** No timeout or connection persists incorrectly

### 2.7 Logcat / Console Output Analysis
Run in verbose mode and inspect for:
- [ ] `flutter_blue_plus` framework logs (legitimate implementation uses official package logs)
- [ ] Actual BLE stack logs (Linux/Android: `BluetoothAdapter`, `BluetoothLeScanner`)
- [ ] Service UUIDs and characteristic UUIDs being discovered
- [ ] Byte data being received from GATT reads/notifications
- **Red flag:** No native BLE logs, only app-level print statements with mocked values

---

## PHASE 3: SOURCE CODE TRAPS

### 3.1 Search for Hardcoded Escape Hatches
```
Files to grep:
- lib/services/ble_service.dart
- lib/services/vitals_provider.dart
- lib/widgets/device_scan_screen.dart
- lib/models/ble_device_model.dart
```

Search patterns:
- [ ] `"isDemo"`, `"isMocked"`, `"isDevelopment"` boolean flags (if true, BLE is bypassed)
- [ ] `const DEVICE_LIST = [...]` or `const MOCK_DEVICES = [...]`
- [ ] `if (Platform.isAndroid && kDebugMode) { /* use mock */ }`
- [ ] Service UUIDs hardcoded as strings: `const serviceUUID = "0000180d-0000-1000-8000-00805f9b34fb"`
- [ ] Test/demo functions like `simulateHeartRateReading()`, `generateMockData()`

### 3.2 Payload Inspection
- [ ] Check if characteristic `onValueReceived` listener always receives same byte length
  - **Legitimate:** Varies (depends on notifications, GATT MTU size, device behavior)
  - **Demo:** Always same format, e.g., always `[0x14, heartRate, 0x00]`
- [ ] Check if BLE reads have proper error handling for timeout
  - **Demo flag:** No `.timeout()` on read futures
- [ ] Verify connection futures are properly awaited
  - **Demo flag:** `device.connect()` called but future not awaited; code assumes contract

---

## PHASE 4: FINAL VERDICT

### Legitimacy Scoring

| Criterion | Points | Status |
|-----------|--------|--------|
| Uses `flutter_blue_plus` package | 10 | [ ] |
| Implements real scan with listen stream | 15 | [ ] |
| GATT service discovery at runtime | 15 | [ ] |
| Real characteristic UUID validation | 10 | [ ] |
| No hardcoded device/service lists | 10 | [ ] |
| Proper connection state management | 10 | [ ] |
| Timeout handling on all async BLE calls | 10 | [ ] |
| Natural data values (not cycling patterns) | 10 | [ ] |
| Handles disconnection gracefully | 10 | [ ] |
| Byte-level GATT parsing (not pseudo-random) | 15 | [ ] |
| **TOTAL** | **125** | [ ] |

### Pass Criteria
- **Legitimate:** ≥ 100 points + no red flags in Phase 1 code inspection
- **Hybrid (Partial):** 70–99 points (some real BLE, some fallback/demo mode)
- **Demo/Hardcoded:** < 70 points or critical red flags (no real library usage, pure mocking)

---

## REPORTING TEMPLATE

When done, provide a summary report:

```markdown
# BLE Legitimacy Audit Report – AdaptivHealth Mobile

**Date:** [date]  
**Auditor:** Mobile Agent  
**Verdict:** [ ] LEGITIMATE | [ ] HYBRID | [ ] DEMO

## Key Findings

### Code Audit
- Real library usage: YES / NO
- Hardcoded devices: NONE / [list them]
- Service discovery: DYNAMIC / STATIC

### Runtime Behavior
- Scan latency: [observed time]
- Connection handshake: [observed sequence]
- Data patterns: [natural / synthetic]
- Disconnection handling: GRACEFUL / BROKEN

### Red Flags
1. [if any]
2. [if any]

## Recommendation
[Fix required areas or certify implementation]
```

---

## EXECUTION INSTRUCTIONS

1. **Clone/unzip** the AdaptivHealth mobile app workspace
2. **Run Phase 1** code inspection (automated grep + AST analysis)
3. **Run Phase 2** runtime tests (requires device + `flutter run`)
4. **Score** using provided rubric
5. **Generate** final report with file paths and line numbers as evidence
6. **Provide** specific fixes if demo mode detected

**Time estimate:** 45–90 minutes (depending on code clarity and device availability)

