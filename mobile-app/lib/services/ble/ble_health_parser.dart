/*
BLE Health Data Parser.

Bluetooth health devices (heart rate monitors, blood pressure cuffs,
pulse oximeters, thermometers) send raw number data in a specific format.
This file reads that raw data and turns it into simple, usable health
readings like "heart rate: 72 bpm" or "blood pressure: 120/80 mmHg".

Each health device type has an official Bluetooth standard format.
This parser knows how to read those formats.
*/

// Gives us tools to work with raw bytes (the numbers devices send)
import 'dart:typed_data';
// We need the pow() function for number format conversion
import 'dart:math' show pow;


// Holds a heart rate reading received from a Bluetooth chest strap or wrist band.
// Bluetooth standard code for this: 0x2A37
class BleHeartRateReading {
  final int heartRate;                  // The heart rate in beats per minute (BPM)
  final List<double> rrIntervalsMs;     // Time gaps between heartbeats in milliseconds (used for heart rhythm analysis)
  final bool usesUint16HeartRate;       // Whether the device sends the heart rate as a larger number (some devices do)
  final bool sensorContactSupported;    // Whether the device can detect if it's touching your skin
  final bool sensorContactDetected;     // Whether the device IS touching your skin right now
  final int? energyExpended;            // Calories burned (if the device tracks this)
  final DateTime timestamp;             // When this reading was taken
  final String? deviceId;               // The Bluetooth ID of the device that sent this
  final String? deviceName;             // The name of the device (e.g., "Polar H10")

  const BleHeartRateReading({
    required this.heartRate,
    required this.rrIntervalsMs,
    required this.usesUint16HeartRate,
    required this.sensorContactSupported,
    required this.sensorContactDetected,
    required this.timestamp,
    this.energyExpended,
    this.deviceId,
    this.deviceName,
  });
}


// Holds a blood oxygen (SpO2) reading from a Bluetooth pulse oximeter.
// Bluetooth standard code for this: 0x2A5F
class BlePulseOximeterReading {
  final int spo2;            // Blood oxygen saturation percentage (normal is 95-100%)
  final int pulseRate;       // Pulse rate in beats per minute
  final DateTime timestamp;  // When this reading was taken
  final String? deviceId;    // The Bluetooth ID of the device
  final String? deviceName;  // The name of the device

  const BlePulseOximeterReading({
    required this.spo2,
    required this.pulseRate,
    required this.timestamp,
    this.deviceId,
    this.deviceName,
  });
}

// Holds a blood pressure reading from a Bluetooth BP cuff.
// Bluetooth standard code for this: 0x2A35
class BleBloodPressureReading {
  final double systolic;               // Top number (pressure when heart pumps)
  final double diastolic;              // Bottom number (pressure when heart rests)
  final double? meanArterialPressure;  // Average pressure during one heartbeat cycle
  final DateTime timestamp;            // When this reading was taken
  final String? deviceId;              // The Bluetooth ID of the device
  final String? deviceName;            // The name of the device

  const BleBloodPressureReading({
    required this.systolic,
    required this.diastolic,
    this.meanArterialPressure,
    required this.timestamp,
    this.deviceId,
    this.deviceName,
  });
}

// Holds a body temperature reading from a Bluetooth thermometer.
// Bluetooth standard code for this: 0x2A1C
class BleTemperatureReading {
  final double temperatureCelsius;  // Body temperature in Celsius
  final DateTime timestamp;         // When this reading was taken
  final String? deviceId;           // The Bluetooth ID of the device
  final String? deviceName;         // The name of the device

  const BleTemperatureReading({
    required this.temperatureCelsius,
    required this.timestamp,
    this.deviceId,
    this.deviceName,
  });
}

// This class contains all the logic to read raw Bluetooth data
// and convert it into the readable health objects above.
class BleHealthParser {

  // Read raw bytes from a heart rate monitor and return a heart rate reading.
  // Returns null if the data is too short or corrupted.
  static BleHeartRateReading? parseHeartRateMeasurement(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    // No data? Nothing to parse
    if (data.isEmpty) {
      return null;
    }

    // Convert the raw numbers into a byte array we can read piece by piece
    final bytes = Uint8List.fromList(data);
    // The first byte is a set of flags that tell us what's in the rest of the data
    final flags = bytes[0];

    // Read each flag bit to understand what info the device included
    final usesUint16HeartRate = (flags & 0x01) != 0;       // Bit 0: heart rate is stored as 2 bytes instead of 1
    final sensorContactSupported = (flags & 0x04) != 0;     // Bit 2: device can detect skin contact
    final sensorContactDetected = sensorContactSupported && (flags & 0x02) != 0; // Bit 1: sensor IS touching skin
    final hasEnergyExpended = (flags & 0x08) != 0;          // Bit 3: calories burned is included
    final hasRrIntervals = (flags & 0x10) != 0;             // Bit 4: heartbeat timing data is included

    // Start reading after the flags byte
    var index = 1;

    // Read the heart rate value
    int heartRate;
    if (usesUint16HeartRate) {
      // Heart rate is stored as 2 bytes (for rates over 255, used by some devices)
      if (bytes.length < index + 2) {
        return null; // Data too short — something went wrong
      }
      // Combine 2 bytes into one number (low byte first, then high byte)
      heartRate = bytes[index] | (bytes[index + 1] << 8);
      index += 2;
    } else {
      // Heart rate is stored as 1 byte (most common)
      if (bytes.length < index + 1) {
        return null; // Data too short
      }
      heartRate = bytes[index];
      index += 1;
    }

    // Read calories burned (if the device included it)
    int? energyExpended;
    if (hasEnergyExpended) {
      if (bytes.length < index + 2) {
        return null; // Data too short
      }
      // Combine 2 bytes into the calorie count
      energyExpended = bytes[index] | (bytes[index + 1] << 8);
      index += 2;
    }

    // Read the time gaps between heartbeats (used for heart rhythm analysis)
    final rrIntervalsMs = <double>[];
    if (hasRrIntervals) {
      // There can be multiple intervals — read them all until we run out of data
      while (index + 1 < bytes.length) {
        // Combine 2 bytes into the raw interval value
        final rrRaw = bytes[index] | (bytes[index + 1] << 8);
        // Convert from the device's format (1/1024 seconds) to milliseconds
        final rrMs = (rrRaw / 1024.0) * 1000.0;
        rrIntervalsMs.add(rrMs);
        index += 2;
      }
    }

    // Put it all together into a readable heart rate reading
    return BleHeartRateReading(
      heartRate: heartRate,
      rrIntervalsMs: rrIntervalsMs,
      usesUint16HeartRate: usesUint16HeartRate,
      sensorContactSupported: sensorContactSupported,
      sensorContactDetected: sensorContactDetected,
      energyExpended: energyExpended,
      timestamp: DateTime.now(),
      deviceId: deviceId,
      deviceName: deviceName,
    );
  }

  // Read raw bytes from a pulse oximeter and return a blood oxygen reading.
  // Returns null if the data is too short or the values don't make sense.
  static BlePulseOximeterReading? parsePulseOximeter(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    // Need at least 5 bytes: 1 flag + 2 SpO2 + 2 pulse rate
    if (data.isEmpty || data.length < 5) {
      return null;
    }

    final bytes = Uint8List.fromList(data);
    final flags = bytes[0];

    // SpO2 (blood oxygen %) is stored in a special medical number format at bytes 1-2
    final spo2Raw = bytes[1] | (bytes[2] << 8);
    final spo2 = _parseSFloat(spo2Raw);
    // SpO2 must be between 0% and 100% to be valid
    if (spo2 == null || spo2 < 0 || spo2 > 100) {
      return null;
    }

    // Pulse rate is stored in the same format at bytes 3-4
    final pulseRateRaw = bytes[3] | (bytes[4] << 8);
    final pulseRate = _parseSFloat(pulseRateRaw);
    if (pulseRate == null || pulseRate < 0) {
      return null;
    }

    return BlePulseOximeterReading(
      spo2: spo2.round(),
      pulseRate: pulseRate.round(),
      timestamp: DateTime.now(),
      deviceId: deviceId,
      deviceName: deviceName,
    );
  }

  // Read raw bytes from a blood pressure cuff and return a BP reading.
  // Returns null if the data is too short or corrupted.
  static BleBloodPressureReading? parseBloodPressure(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    // Need at least 7 bytes: 1 flag + 2 systolic + 2 diastolic + 2 mean arterial
    if (data.isEmpty || data.length < 7) {
      return null;
    }

    final bytes = Uint8List.fromList(data);
    final flags = bytes[0];

    // Read what extra info the device included
    final usesKpa = (flags & 0x01) != 0;             // 0 = mmHg (most common), 1 = kilopascals
    final hasTimestamp = (flags & 0x02) != 0;         // Device included a time stamp
    final hasPulseRate = (flags & 0x04) != 0;         // Device included pulse rate
    final hasUserId = (flags & 0x08) != 0;            // Device included a user ID
    final hasMeasurementStatus = (flags & 0x10) != 0; // Device included measurement status flags

    var index = 1;

    // Read systolic (top number) — stored in medical number format
    if (bytes.length < index + 2) return null;
    final systolicRaw = bytes[index] | (bytes[index + 1] << 8);
    final systolic = _parseSFloat(systolicRaw);
    index += 2;

    // Read diastolic (bottom number) — same format
    if (bytes.length < index + 2) return null;
    final diastolicRaw = bytes[index] | (bytes[index + 1] << 8);
    final diastolic = _parseSFloat(diastolicRaw);
    index += 2;

    // Read mean arterial pressure (average pressure) — same format
    if (bytes.length < index + 2) return null;
    final mapRaw = bytes[index] | (bytes[index + 1] << 8);
    final map = _parseSFloat(mapRaw);
    index += 2;

    // If we couldn't read systolic or diastolic, the data is bad
    if (systolic == null || diastolic == null) {
      return null;
    }

    // If the device sends kilopascals, convert to mmHg (the standard unit doctors use)
    // 1 kPa = 7.50062 mmHg
    final systolicMmHg = usesKpa ? systolic * 7.50062 : systolic;
    final diastolicMmHg = usesKpa ? diastolic * 7.50062 : diastolic;
    final mapMmHg = (map != null && usesKpa) ? map * 7.50062 : map;

    return BleBloodPressureReading(
      systolic: systolicMmHg,
      diastolic: diastolicMmHg,
      meanArterialPressure: mapMmHg,
      timestamp: DateTime.now(),
      deviceId: deviceId,
      deviceName: deviceName,
    );
  }

  // Read raw bytes from a thermometer and return a temperature reading.
  // Returns null if the data is too short or corrupted.
  static BleTemperatureReading? parseTemperature(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    // Need at least 5 bytes: 1 flag + 4 temperature
    if (data.isEmpty || data.length < 5) {
      return null;
    }

    final bytes = Uint8List.fromList(data);
    final flags = bytes[0];

    // Check if the thermometer sends Fahrenheit instead of Celsius
    final usesFahrenheit = (flags & 0x01) != 0;

    // Temperature is stored as a 4-byte medical number at bytes 1-4
    if (bytes.length < 5) return null;
    final tempRaw = bytes[1] | (bytes[2] << 8) | (bytes[3] << 16) | (bytes[4] << 24);
    final temp = _parseFloat(tempRaw);

    if (temp == null) {
      return null;
    }

    // Convert Fahrenheit to Celsius if needed (we always store in Celsius)
    final tempCelsius = usesFahrenheit ? (temp - 32) * 5 / 9 : temp;

    return BleTemperatureReading(
      temperatureCelsius: tempCelsius,
      timestamp: DateTime.now(),
      deviceId: deviceId,
      deviceName: deviceName,
    );
  }

  // Convert a 16-bit medical number (SFLOAT) into a regular decimal number.
  // Medical devices use this special format — it has a tiny exponent and mantissa.
  // Returns null for special values that mean "not a number" or "infinity".
  static double? _parseSFloat(int value) {
    // These special codes mean the reading is invalid or out of range
    if (value == 0x07FF || value == 0x0800 || value == 0x07FE) {
      return null;
    }

    // The bottom 12 bits are the main number (mantissa)
    int mantissa = value & 0x0FFF;
    // If the top bit of mantissa is set, it's a negative number (two's complement math)
    if (mantissa >= 0x0800) {
      mantissa = mantissa - 0x1000;
    }

    // The top 4 bits are the power of 10 to multiply by (exponent)
    int exponent = (value >> 12) & 0x0F;
    // Same negative number handling for the exponent
    if (exponent >= 0x08) {
      exponent = exponent - 0x10;
    }

    // Final value = mantissa × 10^exponent (e.g., 975 × 10^-1 = 97.5)
    return mantissa * pow(10, exponent).toDouble();
  }

  // Convert a 32-bit medical number (FLOAT) into a regular decimal number.
  // Same idea as SFLOAT above but with more precision (used for temperature).
  // Returns null for special values.
  static double? _parseFloat(int value) {
    // These special codes mean the reading is invalid
    if (value == 0x007FFFFF || value == 0x00800000 || value == 0x007FFFFE) {
      return null;
    }

    // The bottom 24 bits are the main number (mantissa)
    int mantissa = value & 0x00FFFFFF;
    if (mantissa >= 0x00800000) {
      mantissa = mantissa - 0x01000000; // Negative number handling
    }

    // The top 8 bits are the power of 10 (exponent)
    int exponent = (value >> 24) & 0xFF;
    if (exponent >= 0x80) {
      exponent = exponent - 0x100; // Negative number handling
    }

    // Final value = mantissa × 10^exponent
    return mantissa * pow(10, exponent).toDouble();
  }
}
