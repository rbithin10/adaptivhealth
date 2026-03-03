import 'dart:typed_data';

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

/// BLE parser utilities for Heart Rate Service payloads.
class BleHealthParser {
  /// Parse bytes from Heart Rate Measurement characteristic (0x2A37).
  ///
  /// Returns null when payload is empty or malformed.
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
}
