# BLE Reality Test Prompt — Definitive Simulator Detection

**Objective:** Run actual runtime tests with a real BLE device to prove whether the app is scanning real Bluetooth devices or running a simulator.

---

## PHASE 1: PHYSICAL DEVICE TEST (5 minutes)

### Test 1.1: Device Out-of-Range Test

**What to do:**
1. Open the app and start BLE scan
2. Note how many devices appear in the list
3. Walk your phone **50+ meters away** from your BLE device (outside Bluetooth range)
4. Observe the device list for **30 seconds**

**Real BLE behavior:**
- Device disappears from list within 5–10 seconds
- List may show 0 devices or old cached results fade out

**Simulator behavior:**
- Device remains in list regardless of distance
- List never changes
- Same MAC addresses appear indefinitely

**Verdict:** If device disappears, **it's REAL BLE**. If it stays, **it's a simulator**.

---

### Test 1.2: Device Movement & Signal Strength Test

**What to do:**
1. Start scan again
2. Place your BLE device on a table and watch the RSSI value (signal strength)
3. Walk toward the device, then away from it **repeatedly**
4. Observe if RSSI changes as you move

**Real BLE behavior:**
- RSSI gets stronger (-50 dBm) as you get closer
- RSSI gets weaker (-80 dBm) as you move away
- Values change **continuously** as you move

**Simulator behavior:**
- RSSI is constant (always same number)
- RSSI doesn't change with movement
- Same devices show same RSSI every time

**Verdict:** If RSSI changes with distance, **it's REAL BLE**. If static, **it's simulated**.

---

### Test 1.3: Multiple Device Test

**What to do:**
1. Have 2–3 BLE devices available
2. Power on just **Device A**, scan, note it appears
3. Turn **Device A off**, wait 5 seconds
4. Power on **Device B** (different MAC), scan
5. Watch if Device A reappears or Device B appears

**Real BLE behavior:**
- Device A disappears after 5–10 seconds when powered off
- Device B appears as a **new** unique MAC address
- Never the same MAC address for different devices

**Simulator behavior:**
- Device A may stay in list even after powered off
- Device B shows same MAC as Device A (recycled)
- Fixed list of devices always present

**Verdict:** If devices appear/disappear with power, **it's REAL BLE**. If list is static, **it's simulated**.

---

## PHASE 2: CONNECTION TEST (5 minutes)

### Test 2.1: Connection Timing Test

**What to do:**
1. Open the app, ready a stopwatch (phone timer app)
2. Press "Scan" button, start timer
3. When first device appears, note the time **T1**
4. Select that device and press "Connect"
5. When connection succeeds, stop timer — note time **T2**

**Real BLE behavior:**
- First device appears after **2–5 seconds** (T1)
- Connection completes after **1–3 seconds** from click (T2 - click time)
- Total scan + connect = **3–8 seconds**

**Simulator behavior:**
- First device appears **instantly** (< 500ms) (T1)
- Connection completes **instantly** (< 100ms) (T2 - click time)
- Total = **< 1 second**

**Verdict:** If it takes 2+seconds for first device to scan, **it's REAL BLE**. If instant, **it's simulated**.

---

### Test 2.2: Connection Failure Test

**What to do:**
1. Select a device to connect
2. **Immediately** (while connecting) turn off that BLE device's power
3. Watch what happens in the app

**Real BLE behavior:**
- Connection attempt continues for **10–12 seconds** (standard timeout)
- Shows error: "Connection failed" or "Timeout"
- App waits full timeout duration

**Simulator behavior:**
- Instantly shows "Connected" (ignores the disconnect)
- No error message
- No timeout

**Verdict:** If connection waits 10+ seconds and shows error, **it's REAL BLE**. If instant success, **it's simulated**.

---

### Test 2.3: Connected Device Disconnect Test

**What to do:**
1. Connect to a BLE device successfully
2. While connected, **turn off that device's power**
3. Watch the app for **30 seconds**

**Real BLE behavior:**
- App detects disconnect within **5–15 seconds**
- Shows "Disconnected" state
- May attempt auto-reconnect with backoff

**Simulator behavior:**
- App shows "Connected" indefinitely
- No disconnect detection
- Data continues to arrive as if still connected

**Verdict:** If app detects disconnect in <20s, **it's REAL BLE**. If it stays connected, **it's simulated**.

---

## PHASE 3: DATA AUTHENTICITY TEST (5 minutes)

### Test 3.1: Heart Rate Realism Test

**What to do:**
1. Connect to a real HR device
2. Record the heart rate values you see for **60 seconds**
3. Note the sequence of numbers

**Real BLE behavior:**
- Values change naturally: 72, 73, 74, 73, 72, 71, 70, 72, 75...
- Range is realistic (60–120 BPM at rest, can spike during motion)
- Patterns match your physiology (stays ~70 if you're sitting still)

**Simulator behavior:**
- Repeating patterns: 70, 71, 72, 73, 74, 75, 74, 73, 72, 71, 70, 71, 72... (cycles)
- OR constant value: always 72 BPM
- OR random: 150, 45, 189, 52 (unrealistic jumps)

**Verdict:** If HR changes naturally with physiology, **it's REAL BLE**. If cycling/constant, **it's simulated**.

---

### Test 3.2: Heart Rate Variability (RR Intervals) Test

**What to do:**
1. If the app displays RR intervals (beat-to-beat intervals):
   - Note a few values: e.g., 812ms, 820ms, 815ms
2. If NO RR intervals shown:
   - Connect to the device and check logcat: `flutter logs | grep -i "rr\|interval"`
3. Award points if RR intervals are **diverse** and **frequent**

**Real BLE behavior:**
- RR intervals vary: 800ms, 850ms, 820ms, 805ms (natural human heart variability)
- Intervals arrive frequently (every heartbeat, so 60–100 per minute)
- Changes with breathing and activity

**Simulator behavior:**
- RR intervals absent (app doesn't parse them)
- OR RR intervals are fake/constant
- OR no interval data in logs

**Verdict:** If RR intervals are diverse and change dynamically, **it's REAL BLE**. If missing/fake, **it's simulated**.

---

## PHASE 4: CODE EVIDENCE TEST (Evidence Gathering)

### Test 4.1: Check Logs for Real BLE Operations

**What to do:**
1. Open Terminal/PowerShell in VS Code
2. Run: `flutter logs` (or `adb logcat | grep flutter` on Android)
3. Perform a scan and connection in the app
4. Look for these log messages:

**Real BLE evidence (should see these):**
```
[BLE] Bluetooth adapter is on
[BLE] Attempting to connect to...
[BLE] Discovering services...
[BLE] Found service: 0x180D (Heart Rate)
[BLE] Found characteristic: 0x2A37 (HR Measurement)
[BLE] Subscribed to notifications
[BLE] Received HR data: [...bytes...]
```

**Simulator evidence (if you see these):**
```
[Mock] Simulating device...
[Mock] Generated fake HR: 72
[Demo] Returning hardcoded ScanResult
```

**Action:**
- Run scan + connect while watching logs
- Screenshot or copy the log output
- If you see device UUIDs (0x180D, 0x2A37) and byte data, **it's REAL**
- If you see "[Mock]" or "[Demo]" or hardcoded values, **it's simulated**

---

## PHASE 5: FINAL VERDICT CHECKLIST

Mark each test as PASS or FAIL:

| Test | Result | Real BLE Indicator |
|------|--------|-------------------|
| 1.1 Device disappears when out of range | PASS / FAIL | ✅ PASS = Real |
| 1.2 RSSI changes with movement | PASS / FAIL | ✅ PASS = Real |
| 1.3 Different devices show unique MACs | PASS / FAIL | ✅ PASS = Real |
| 2.1 Scan takes 2–5 seconds first device | PASS / FAIL | ✅ PASS = Real |
| 2.2 Connection shows timeout error | PASS / FAIL | ✅ PASS = Real |
| 2.3 App detects device disconnect < 20s | PASS / FAIL | ✅ PASS = Real |
| 3.1 Heart rate values realistic & natural | PASS / FAIL | ✅ PASS = Real |
| 3.2 RR intervals diverse & change | PASS / FAIL | ✅ PASS = Real |
| 4.1 Logs show real BLE operations | PASS / FAIL | ✅ PASS = Real |

**Scoring:**
- **8–9 PASS:** ✅ **100% REAL BLE** (not a simulator)
- **5–7 PASS:** ⚠️ **HYBRID** (real BLE + some fallback/mock)
- **0–4 PASS:** ❌ **SIMULATED** (hardcoded demo mode)

---

## EXECUTION ROADMAP

```
1. Grab a real BLE Heart Rate monitor (or use phone as test device)
2. Run Tests 1.1 → 1.2 → 1.3 (5 min)
3. Run Tests 2.1 → 2.2 → 2.3 (5 min)
4. Run Tests 3.1 → 3.2 (5 min)
5. Run Test 4.1 (check logs) (2 min)
6. Count PASS marks
7. Declare verdict above
```

**Total time:** ~20 minutes (assumes you have devices available)

---

## WHAT TO REPORT BACK

After running all tests, provide:

```markdown
## BLE Simulator Reality Test Results

**Date:** [today]
**Device tested:** [e.g., Coospo H808S, Polar H10, etc.]

### Test Results Summary
- Out-of-range test: [PASS/FAIL]
- Signal strength test: [PASS/FAIL]
- Multiple device test: [PASS/FAIL]
- Connection timing: [PASS/FAIL]
- Disconnect detection: [PASS/FAIL]
- Heart rate realism: [PASS/FAIL]
- RR intervals: [PASS/FAIL]
- Log evidence: [PASS/FAIL]

**Total PASS:** 7/8

**Verdict:** ✅ **REAL BLE** — Not a simulator

**Key evidence:**
1. [e.g., Device disappeared after moving 100m away]
2. [e.g., RSSI changed from -55 dBm to -75 dBm as I moved away]
3. [e.g., Connection took 4.2 seconds, showed error when device powered off]
4. [e.g., Heart rate changed naturally: 72 → 74 → 76 → 75 → 73 (physiological response)]
5. [e.g., Logs show: "Found characteristic: 0x2A37"]
```

**Then share this report so we can confirm the BLE implementation is legitimate!**

