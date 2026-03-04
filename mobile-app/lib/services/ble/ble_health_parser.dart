import 'dart:typed_data';
import 'dart:math' show pow;


/// Parsed Heart Rate Measurement from BLE characteristic 0x2A37.
class BleHeartRateReading {
  final int heartRate;
  final List<double> rrIntervalsMs;
  final bool usesUint16HeartRate;
  final bool sensorContactSupported;
  final bool sensorContactDetected;
  final int? energyExpended;
  final DateTime timestamp;
  final String? deviceId;
  final String? deviceName;

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


/// Parsed Pulse Oximeter measurement from BLE characteristic 0x2A5F.
class BlePulseOximeterReading {
  final int spo2;
  final int pulseRate;
  final DateTime timestamp;
  final String? deviceId;
  final String? deviceName;

  const BlePulseOximeterReading({
    required this.spo2,
    required this.pulseRate,
    required this.timestamp,
    this.deviceId,
    this.deviceName,
  });
}

/// Parsed Blood Pressure measurement from BLE characteristic 0x2A35.
class BleBloodPressureReading {
  final double systolic;
  final double diastolic;
  final double? meanArterialPressure;
  final DateTime timestamp;
  final String? deviceId;
  final String? deviceName;

  const BleBloodPressureReading({
    required this.systolic,
    required this.diastolic,
    this.meanArterialPressure,
    required this.timestamp,
    this.deviceId,
    this.deviceName,
  });
}

/// Parsed Body Temperature measurement from BLE characteristic 0x2A1C.
class BleTemperatureReading {
  final double temperatureCelsius;
  final DateTime timestamp;
  final String? deviceId;
  final String? deviceName;

  const BleTemperatureReading({
    required this.temperatureCelsius,
    required this.timestamp,
    this.deviceId,
    this.deviceName,
  });
}

/// BLE parser utilities for Heart Rate Service payloads.
class BleHealthParser {
  /// Parse bytes from Heart Rate Measurement characteristic (0x2A37).
  ///
  /// Returns null when payload is empty or malformed.
  /// 
  
  static BleHeartRateReading? parseHeartRateMeasurement(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    if (data.isEmpty) {
      return null;
    }

    final bytes = Uint8List.fromList(data);
    final flags = bytes[0];

    final usesUint16HeartRate = (flags & 0x01) != 0;
    final sensorContactSupported = (flags & 0x04) != 0;
    final sensorContactDetected = sensorContactSupported && (flags & 0x02) != 0;
    final hasEnergyExpended = (flags & 0x08) != 0;
    final hasRrIntervals = (flags & 0x10) != 0;

    var index = 1;

    int heartRate;
    if (usesUint16HeartRate) {
      if (bytes.length < index + 2) {
        return null;
      }
      heartRate = bytes[index] | (bytes[index + 1] << 8);
      index += 2;
    } else {
      if (bytes.length < index + 1) {
        return null;
      }
      heartRate = bytes[index];
      index += 1;
    }

    int? energyExpended;
    if (hasEnergyExpended) {
      if (bytes.length < index + 2) {
        return null;
      }
      energyExpended = bytes[index] | (bytes[index + 1] << 8);
      index += 2;
    }

    final rrIntervalsMs = <double>[];
    if (hasRrIntervals) {
      while (index + 1 < bytes.length) {
        final rrRaw = bytes[index] | (bytes[index + 1] << 8);
        final rrMs = (rrRaw / 1024.0) * 1000.0;
        rrIntervalsMs.add(rrMs);
        index += 2;
      }
    }

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

  /// Parse bytes from Pulse Oximeter Continuous Measurement characteristic (0x2A5F).
  ///
  /// Returns null when payload is empty or malformed.
  static BlePulseOximeterReading? parsePulseOximeter(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    if (data.isEmpty || data.length < 5) {
      return null;
    }

    final bytes = Uint8List.fromList(data);
    final flags = bytes[0];

    // SpO2 is always SFLOAT at bytes[1-2]
    final spo2Raw = bytes[1] | (bytes[2] << 8);
    final spo2 = _parseSFloat(spo2Raw);
    if (spo2 == null || spo2 < 0 || spo2 > 100) {
      return null;
    }

    // Pulse Rate is always SFLOAT at bytes[3-4]
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

  /// Parse bytes from Blood Pressure Measurement characteristic (0x2A35).
  ///
  /// Returns null when payload is empty or malformed.
  static BleBloodPressureReading? parseBloodPressure(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    if (data.isEmpty || data.length < 7) {
      return null;
    }

    final bytes = Uint8List.fromList(data);
    final flags = bytes[0];

    final usesKpa = (flags & 0x01) != 0; // 0 = mmHg, 1 = kPa
    final hasTimestamp = (flags & 0x02) != 0;
    final hasPulseRate = (flags & 0x04) != 0;
    final hasUserId = (flags & 0x08) != 0;
    final hasMeasurementStatus = (flags & 0x10) != 0;

    var index = 1;

    // Systolic (SFLOAT)
    if (bytes.length < index + 2) return null;
    final systolicRaw = bytes[index] | (bytes[index + 1] << 8);
    final systolic = _parseSFloat(systolicRaw);
    index += 2;

    // Diastolic (SFLOAT)
    if (bytes.length < index + 2) return null;
    final diastolicRaw = bytes[index] | (bytes[index + 1] << 8);
    final diastolic = _parseSFloat(diastolicRaw);
    index += 2;

    // Mean Arterial Pressure (SFLOAT)
    if (bytes.length < index + 2) return null;
    final mapRaw = bytes[index] | (bytes[index + 1] << 8);
    final map = _parseSFloat(mapRaw);
    index += 2;

    if (systolic == null || diastolic == null) {
      return null;
    }

    // Convert kPa to mmHg if needed (1 kPa = 7.50062 mmHg)
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

  /// Parse bytes from Temperature Measurement characteristic (0x2A1C).
  ///
  /// Returns null when payload is empty or malformed.
  static BleTemperatureReading? parseTemperature(
    List<int> data, {
    String? deviceId,
    String? deviceName,
  }) {
    if (data.isEmpty || data.length < 5) {
      return null;
    }

    final bytes = Uint8List.fromList(data);
    final flags = bytes[0];

    final usesFahrenheit = (flags & 0x01) != 0; // 0 = Celsius, 1 = Fahrenheit

    // Temperature is IEEE-11073 FLOAT at bytes[1-4]
    if (bytes.length < 5) return null;
    final tempRaw = bytes[1] | (bytes[2] << 8) | (bytes[3] << 16) | (bytes[4] << 24);
    final temp = _parseFloat(tempRaw);

    if (temp == null) {
      return null;
    }

    // Convert Fahrenheit to Celsius if needed
    final tempCelsius = usesFahrenheit ? (temp - 32) * 5 / 9 : temp;

    return BleTemperatureReading(
      temperatureCelsius: tempCelsius,
      timestamp: DateTime.now(),
      deviceId: deviceId,
      deviceName: deviceName,
    );
  }

  /// Parse IEEE-11073 16-bit SFLOAT (used in SpO2, BP).
  ///
  /// Format: 4-bit exponent (signed), 12-bit mantissa (signed).
  /// Returns null for special values (NaN, infinity, reserved).
  static double? _parseSFloat(int value) {
    if (value == 0x07FF || value == 0x0800 || value == 0x07FE) {
      return null; // NaN, NRes, +INFINITY reserved values
    }

    // Extract signed mantissa (12 bits)
    int mantissa = value & 0x0FFF;
    if (mantissa >= 0x0800) {
      mantissa = mantissa - 0x1000; // Two's complement for negative
    }

    // Extract signed exponent (4 bits)
    int exponent = (value >> 12) & 0x0F;
    if (exponent >= 0x08) {
      exponent = exponent - 0x10; // Two's complement for negative
    }

    return mantissa * pow(10, exponent).toDouble();
  }

  /// Parse IEEE-11073 32-bit FLOAT (used in Temperature).
  ///
  /// Format: 8-bit exponent (signed), 24-bit mantissa (signed).
  /// Returns null for special values.
  static double? _parseFloat(int value) {
    if (value == 0x007FFFFF || value == 0x00800000 || value == 0x007FFFFE) {
      return null; // NaN, NRes, +INFINITY reserved values
    }

    // Extract signed mantissa (24 bits)
    int mantissa = value & 0x00FFFFFF;
    if (mantissa >= 0x00800000) {
      mantissa = mantissa - 0x01000000; // Two's complement
    }

    // Extract signed exponent (8 bits)
    int exponent = (value >> 24) & 0xFF;
    if (exponent >= 0x80) {
      exponent = exponent - 0x100; // Two's complement
    }

    return mantissa * pow(10, exponent).toDouble();
  }
}
