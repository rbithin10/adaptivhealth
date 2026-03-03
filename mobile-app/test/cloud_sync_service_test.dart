import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:adaptiv_health/models/edge_prediction.dart';
import 'package:adaptiv_health/services/cloud_sync_service.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

typedef _RequestHandler = Future<ResponseBody> Function(RequestOptions options);

class _QueueHttpClientAdapter implements HttpClientAdapter {
  final List<_RequestHandler> handlers;
  int _index = 0;

  _QueueHttpClientAdapter(this.handlers);

  @override
  void close({bool force = false}) {}

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<dynamic>? cancelFuture,
  ) async {
    if (_index >= handlers.length) {
      return ResponseBody.fromString(
        json.encode({}),
        200,
        headers: {
          Headers.contentTypeHeader: [Headers.jsonContentType],
        },
      );
    }

    final handler = handlers[_index++];
    return handler(options);
  }
}

EdgeRiskPrediction _prediction() {
  return EdgeRiskPrediction(
    riskScore: 0.81,
    riskLevel: 'high',
    confidence: 0.9,
    inferenceTimeMs: 12,
    modelVersion: '1.0.0',
  );
}

Map<String, dynamic> _vitals() {
  return {
    'heart_rate': 164,
    'spo2': 95,
    'bp_systolic': 132,
    'bp_diastolic': 82,
    'timestamp': DateTime.now().toIso8601String(),
  };
}

ResponseBody _ok() {
  return ResponseBody.fromString(
    json.encode({}),
    200,
    headers: {
      Headers.contentTypeHeader: [Headers.jsonContentType],
    },
  );
}

DioException _connectionError(RequestOptions options) {
  return DioException(
    requestOptions: options,
    type: DioExceptionType.connectionError,
    error: 'offline',
  );
}

DioException _httpError(RequestOptions options, int statusCode) {
  return DioException(
    requestOptions: options,
    response: Response(
      requestOptions: options,
      statusCode: statusCode,
      data: {'detail': 'error'},
    ),
    type: DioExceptionType.badResponse,
  );
}

void main() {
  group('CloudSyncService state transitions', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('network down/up transition does not stick in false offline', () async {
      final dio = Dio();
      dio.httpClientAdapter = _QueueHttpClientAdapter([
        (options) async => throw _connectionError(options), // init probe
        (options) async => throw _connectionError(options), // trySync probe (down)
        (options) async => _ok(), // trySync probe (up)
        (options) async => _ok(), // batch sync
      ]);

      final service = CloudSyncService(dio);
      await service.initialize();

      await service.queuePrediction(prediction: _prediction(), vitals: _vitals());

      final firstTry = await service.trySync();
      expect(firstTry, isFalse);
      expect(service.syncState, CloudSyncState.offline);
      expect(service.pendingCount, 1);

      final secondTry = await service.trySync();
      expect(secondTry, isTrue);
      expect(service.pendingCount, 0);
      expect(
        service.syncState == CloudSyncState.idle ||
            service.syncState == CloudSyncState.online,
        isTrue,
      );

      service.dispose();
    });

    test('401 maps to authExpired instead of offline', () async {
      final dio = Dio();
      dio.httpClientAdapter = _QueueHttpClientAdapter([
        (options) async => throw _httpError(options, 401), // init probe
        (options) async => throw _httpError(options, 401), // trySync probe
      ]);

      final service = CloudSyncService(dio);
      await service.initialize();

      await service.queuePrediction(prediction: _prediction(), vitals: _vitals());
      final success = await service.trySync();

      expect(success, isFalse);
      expect(service.syncState, CloudSyncState.authExpired);
      expect(service.lastSyncErrorType, 'auth_expired');
      expect(service.pendingCount, 1);

      service.dispose();
    });

    test('429 maps to rateLimited instead of offline', () async {
      final dio = Dio();
      dio.httpClientAdapter = _QueueHttpClientAdapter([
        (options) async => _ok(), // init probe
        (options) async => _ok(), // trySync probe
        (options) async => throw _httpError(options, 429), // batch sync
      ]);

      final service = CloudSyncService(dio);
      await service.initialize();

      await service.queuePrediction(prediction: _prediction(), vitals: _vitals());
      final success = await service.trySync();

      expect(success, isFalse);
      expect(service.syncState, CloudSyncState.rateLimited);
      expect(service.lastSyncErrorType, 'rate_limited');
      expect(service.pendingCount, 1);

      service.dispose();
    });

    test('5xx maps to serverError instead of offline', () async {
      final dio = Dio();
      dio.httpClientAdapter = _QueueHttpClientAdapter([
        (options) async => _ok(), // init probe
        (options) async => _ok(), // trySync probe
        (options) async => throw _httpError(options, 503), // batch sync
      ]);

      final service = CloudSyncService(dio);
      await service.initialize();

      await service.queuePrediction(prediction: _prediction(), vitals: _vitals());
      final success = await service.trySync();

      expect(success, isFalse);
      expect(service.syncState, CloudSyncState.serverError);
      expect(service.lastSyncErrorType, 'server_error');
      expect(service.pendingCount, 1);

      service.dispose();
    });

    test('non-retryable validation error drops batch with surfaced reason', () async {
      final dio = Dio();
      dio.httpClientAdapter = _QueueHttpClientAdapter([
        (options) async => _ok(), // init probe
        (options) async => _ok(), // trySync probe
        (options) async => throw _httpError(options, 422), // batch sync
      ]);

      final service = CloudSyncService(dio);
      await service.initialize();

      await service.queuePrediction(prediction: _prediction(), vitals: _vitals());
      final success = await service.trySync();

      expect(success, isFalse);
      expect(service.pendingCount, 0);
      expect(service.lastSyncErrorType, 'validation_error');
      expect(service.lastQueueEventType, 'validation_error');
      expect(service.lastQueueEventMessage, isNotNull);
      expect(service.lastQueueEventAt, isNotNull);

      service.dispose();
    });
  });
}
