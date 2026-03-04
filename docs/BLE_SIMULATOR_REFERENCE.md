# BLE Simulator Reference Guide
## How to Test the AdaptivHealth App Using Your Phone as a BLE Device

---

## Option A: nRF Connect App (Recommended — Android & iOS)

**nRF Connect** lets your phone advertise as a custom BLE peripheral with real GATT services including the Heart Rate Service that AdaptivHealth looks for.

### Setup Steps

1. **Install nRF Connect for Mobile**
   - Android: [Google Play — nRF Connect](https://play.google.com/store/apps/details?id=no.nordicsemi.android.mcp)
   - iOS: [App Store — nRF Connect](https://apps.apple.com/app/nrf-connect-for-mobile/id1054362403)

2. **Create a Heart Rate Server**
   - Open nRF Connect
   - Tap the **THREE-LINE menu** (hamburger) → **Configure GATT Server**
   - Tap **Add service**
   - Select **Heart Rate** (UUID: `0x180D`) from the list
   - It will automatically add:
     - Heart Rate Measurement characteristic (`0x2A37`) — **Notify** property
     - Body Sensor Location (`0x2A38`) — optional
   - Tap **OK** to save

3. **Advertise the Service**
   - Tap **Advertiser** tab
   - Tap the **+** button to create a new advertiser
   - Set **Device Name** — e.g., `TestHRM`
   - Under **Payload**, tap **Add Record → Complete Local Name** → enter `TestHRM`
   - Under **Payload**, tap **Add Record → Complete List of 16-bit UUIDs** → add `0x180D`
   - Tap **OK** → toggle advertiser **ON**

4. **Now scan from AdaptivHealth**
   - Open AdaptivHealth on your test phone
   - Navigate to **Pair Heart Rate Monitor**
   - Tap **Scan BLE Devices**
   - `TestHRM` should appear within 2–5 seconds with the **HR** badge

---

## Option B: BLE Peripheral Simulator App (Android)

**BLE Peripheral Simulator** is simpler — one tap to start a Heart Rate peripheral.

1. Install: [BLE Peripheral Simulator (GitHub/APK)](https://github.com/neXenio/BLE-Peripheral-Simulator)
   - Or search "BLE Peripheral" on Google Play
2. Open app → Select **Heart Rate Monitor**
3. Tap **Start Advertising**
4. The app will advertise with service UUID `0x180D` and simulate HR values (60–100 BPM)
5. Scan from AdaptivHealth — it will show as a real BLE HR device

---

## Option C: LightBlue App (iOS & Android)

**LightBlue** can act as both a scanner and a peripheral.

1. Install LightBlue (App Store / Play Store)
2. Open LightBlue → Tap **Create Virtual Device**
3. Select **Heart Rate Monitor** template
4. Tap **Advertise**
5. From AdaptivHealth on another phone, scan — LightBlue device appears in 2–5 seconds

---

## What to Look for When Testing

Once you have a BLE simulator running, verify these indicators in AdaptivHealth:

### Scan Timing Banner (New Feature)
```
📡 Scanning... 3s / 10s          [1 device found]
████████░░░░░░░░░░░░
```
- First device should appear **2–5 seconds** into the scan
- If it appears in < 500ms, something is wrong (likely returning cached results)

### Device Card (New Features)
```
⬜ TestHRM                               [Last used]
   DE:AD:BE:EF:12:34  · Nordic Semi      ← MAC + Manufacturer
   Last seen: 2s ago                      ← Updates every scan cycle
   ████ -65 dBm / Excellent
   [HR] [Heart Rate Monitor]   [Connect]
```
- **RSSI** should change as you move the simulator phone closer/farther
- **Last seen** should update every 1–3 seconds while advertising
- **Manufacturer** shows the company ID decoded from advertisement data

---

## Reality Check Tests with Simulator

Run these to confirm scanning is real:

| Test | Action | Expected | Fake Sign |
|------|--------|----------|-----------|
| **Latency test** | Press Scan, start stopwatch | `TestHRM` appears at 2–5s | Appears at < 500ms |
| **RSSI test** | Move simulator phone 2m vs 10m away | RSSI changes (e.g., −55 vs −80) | RSSI stays same |
| **Disappear test** | Stop advertising in LightBlue/nRF | Device gone from list in 5–10s | Device stays forever |
| **Reappear test** | Restart advertising | Device reappears within 3s | Nothing changes |
| **Name test** | Check device name shown | "TestHRM" (the name you set) | Just MAC address |
| **Connect test** | Tap Connect | Takes 1–3 seconds | Instant (<200ms) |
| **Disconnect test** | Stop advertising while connected | App shows "Disconnected" in 10s | App stays "Connected" |

---

## Interpreting RSSI Values

| RSSI Range | Signal | Typical Distance |
|------------|--------|-----------------|
| −50 to −60 dBm | Excellent | < 1 metre |
| −60 to −70 dBm | Good | 1–3 metres |
| −70 to −80 dBm | Fair | 3–8 metres |
| −80 to −90 dBm | Weak | 8–15 metres |
| < −90 dBm | Very weak | > 15 metres |

**Real-world tip:** Hold both phones 30 cm apart → RSSI should be −50 to −60. Walk 5 metres apart → should drop to −70 to −80. This changing RSSI proves real BLE is working.

---

## Manufacturer Company IDs (Decoded in App)

The app now decodes the manufacturer company ID from the advertisement payload:

| Company ID | Decoded Name | Common Devices |
|-----------|-------------|----------------|
| `0x004C` | Apple | iPhone, Apple Watch |
| `0x0075` | Samsung | Galaxy Watch |
| `0x0059` | Nordic Semi | Most dev boards, fitness trackers |
| `0x0131` | Polar | Polar H10, OH1 |
| `0x0157` | Garmin | Garmin watches, HRM straps |
| `0x0294` | Fitbit | Fitbit Inspire, Charge |
| `0x0499` | Ruuvi | Ruuvi Tag sensors |
| `0x????` | Unknown | Shows raw hex ID |

If you see `0x????` (raw hex), the device manufacturer is not in the known list but the device is **still real** — it just uses an uncommon company ID.

---

## Troubleshooting

**Device not appearing in scan:**
- Ensure BLE advertising is active in the simulator app (not just GATT server)
- Check AdaptivHealth's "Show all BLE devices" toggle is ON
- Ensure both phones are within 10 metres
- Toggle Bluetooth off/on on both phones

**Device appears but shows only MAC (no name):**
- In nRF Connect, ensure "Complete Local Name" was added to the advertiser payload
- The device name is in the advertisement packet, not the GATT connection — you don't need to connect to see it

**RSSI not changing:**
- RSSI only updates when a new advertisement packet is received
- Move the phones while scanning is active (not after scan stopped)

**"Scan complete — took 0s":**
- This means the scan returned immediately (possible cached results)
- Clear Bluetooth cache: Settings → Apps → Bluetooth → Storage → Clear cache
