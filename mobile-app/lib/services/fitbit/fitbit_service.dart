/*
 * FitbitService
 *
 * Manages Fitbit OAuth 2.0 PKCE authentication and intraday vitals polling
 * directly against the Fitbit Web API — no Health Connect intermediary.
 *
 * Setup (one-time):
 *   1. Register your app at https://dev.fitbit.com/apps/new
 *   2. Choose "Client" application type (PKCE, no client secret required).
 *   3. Set OAuth 2.0 Application Type to "Personal".
 *   4. Add Redirect URI:  adaptivhealth://fitbit/callback
 *   5. Copy your Client ID into [_kClientId] below.
 *
 * Data polled every 15 minutes:
 *   - Heart Rate  (intraday 15-min buckets)
 *   - SpO₂        (daily average when watch sync is complete)
 *   - Blood Pressure (manual log or compatible Fitbit Sense/Versa)
 *
 * Tokens are stored in flutter_secure_storage and refreshed automatically.
 */

import 'dart:async';
import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart';
import 'package:dio/dio.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

// =============================================================================
// FITBIT APPLICATION CONFIGURATION
// =============================================================================
// Replace with your Client ID from https://dev.fitbit.com/apps
const String _kClientId = 'YOUR_FITBIT_CLIENT_ID';

const String _kCallbackScheme = 'adaptivhealth';
const String _kCallbackUrl = 'adaptivhealth://fitbit/callback';
const String _kAuthUrl = 'https://www.fitbit.com/oauth2/authorize';
const String _kTokenUrl = 'https://api.fitbit.com/oauth2/token';
const String _kApiBase = 'https://api.fitbit.com';

// Scopes: heartrate is intraday, oxygen_saturation and cardio_fitness
// are wellness metrics, activity covers steps.
const String _kScopes =
    'heartrate oxygen_saturation cardio_fitness activity';

// Secure storage keys
const String _kKeyAccess = 'fitbit_access_token';
const String _kKeyRefresh = 'fitbit_refresh_token';
const String _kKeyExpiry = 'fitbit_token_expiry';

// =============================================================================
// DATA MODELS
// =============================================================================

/// Latest vitals snapshot fetched from the Fitbit Web API.
class FitbitVitals {
  final double? heartRate;
  final double? spo2;
  final double? systolicBp;
  final double? diastolicBp;
  final DateTime timestamp;

  const FitbitVitals({
    this.heartRate,
    this.spo2,
    this.systolicBp,
    this.diastolicBp,
    required this.timestamp,
  });
}

// =============================================================================
// SERVICE
// =============================================================================

/// Singleton that handles Fitbit OAuth2 PKCE auth and vitals fetch.
class FitbitService {
  // Singleton
  static final FitbitService instance = FitbitService._();
  FitbitService._();

  final _storage = const FlutterSecureStorage();
  final _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 15),
  ));

  // In-memory token cache
  String? _accessToken;
  DateTime? _tokenExpiry;

  // ── PKCE helpers ────────────────────────────────────────────────────────────

  static String _codeVerifier() {
    const chars =
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    final rng = Random.secure();
    return List.generate(128, (_) => chars[rng.nextInt(chars.length)]).join();
  }

  static String _codeChallenge(String verifier) {
    final bytes = utf8.encode(verifier);
    final digest = sha256.convert(bytes);
    return base64UrlEncode(digest.bytes).replaceAll('=', '');
  }

  // ── Auth state ──────────────────────────────────────────────────────────────

  /// Returns true if valid (non-expired) tokens are stored.
  Future<bool> get isConnected async {
    final token = await _storage.read(key: _kKeyAccess);
    if (token == null) return false;
    final expiryStr = await _storage.read(key: _kKeyExpiry);
    final expiry = expiryStr != null ? DateTime.tryParse(expiryStr) : null;
    if (expiry == null) return false;
    // Treat as expired if within 60 s of deadline to avoid edge cases.
    return DateTime.now()
        .isBefore(expiry.subtract(const Duration(seconds: 60)));
  }

  // ── OAuth2 PKCE authorization flow ─────────────────────────────────────────

  /// Opens Fitbit's authorization page in the system browser, waits for the
  /// callback redirect, and exchanges the code for access/refresh tokens.
  ///
  /// Throws [FitbitAuthException] if the user cancels or the exchange fails.
  Future<void> authorize() async {
    final verifier = _codeVerifier();
    final challenge = _codeChallenge(verifier);

    final authUri = Uri.parse(_kAuthUrl).replace(queryParameters: {
      'client_id': _kClientId,
      'redirect_uri': _kCallbackUrl,
      'response_type': 'code',
      'scope': _kScopes,
      'code_challenge': challenge,
      'code_challenge_method': 'S256',
    });

    final callbackResult = await FlutterWebAuth2.authenticate(
      url: authUri.toString(),
      callbackUrlScheme: _kCallbackScheme,
    );

    final code = Uri.parse(callbackResult).queryParameters['code'];
    if (code == null || code.isEmpty) {
      throw const FitbitAuthException(
          'Authorization was cancelled or the code was missing.');
    }

    await _exchangeCode(code, verifier);
  }

  Future<void> _exchangeCode(String code, String verifier) async {
    try {
      final response = await _dio.post(
        _kTokenUrl,
        data: {
          'client_id': _kClientId,
          'code': code,
          'code_verifier': verifier,
          'grant_type': 'authorization_code',
          'redirect_uri': _kCallbackUrl,
        },
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
        ),
      );
      await _storeTokens(response.data);
    } on DioException catch (e) {
      throw FitbitAuthException(
          'Token exchange failed: ${e.response?.data ?? e.message}');
    }
  }

  Future<void> _refreshToken() async {
    final refresh = await _storage.read(key: _kKeyRefresh);
    if (refresh == null) {
      throw const FitbitAuthException(
          'No refresh token found. Please reconnect to Fitbit.');
    }

    try {
      final response = await _dio.post(
        _kTokenUrl,
        data: {
          'client_id': _kClientId,
          'refresh_token': refresh,
          'grant_type': 'refresh_token',
        },
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
        ),
      );
      await _storeTokens(response.data);
    } on DioException catch (e) {
      // Refresh failed — clear tokens so the UI can prompt re-auth.
      await disconnect();
      throw FitbitAuthException(
          'Token refresh failed: ${e.response?.data ?? e.message}');
    }
  }

  Future<void> _storeTokens(Map<String, dynamic> data) async {
    final access = data['access_token'] as String;
    final refresh = data['refresh_token'] as String;
    final expiresIn = (data['expires_in'] as num).toInt();
    final expiry = DateTime.now().add(Duration(seconds: expiresIn));

    _accessToken = access;
    _tokenExpiry = expiry;

    await Future.wait([
      _storage.write(key: _kKeyAccess, value: access),
      _storage.write(key: _kKeyRefresh, value: refresh),
      _storage.write(key: _kKeyExpiry, value: expiry.toIso8601String()),
    ]);
  }

  /// Revokes the locally-stored tokens. Does not call Fitbit's revoke endpoint.
  Future<void> disconnect() async {
    _accessToken = null;
    _tokenExpiry = null;
    await Future.wait([
      _storage.delete(key: _kKeyAccess),
      _storage.delete(key: _kKeyRefresh),
      _storage.delete(key: _kKeyExpiry),
    ]);
  }

  // ── Authenticated API calls ─────────────────────────────────────────────────

  Future<Response> _get(String path) async {
    // Hydrate in-memory token from storage if needed.
    _accessToken ??= await _storage.read(key: _kKeyAccess);

    if (_tokenExpiry == null) {
      final str = await _storage.read(key: _kKeyExpiry);
      _tokenExpiry = str != null ? DateTime.tryParse(str) : null;
    }

    final needsRefresh = _tokenExpiry == null ||
        DateTime.now()
            .isAfter(_tokenExpiry!.subtract(const Duration(minutes: 2)));

    if (needsRefresh) await _refreshToken();

    try {
      return await _dio.get(
        '$_kApiBase$path',
        options: Options(
          headers: {'Authorization': 'Bearer $_accessToken'},
        ),
      );
    } on DioException catch (e) {
      // One automatic retry after refreshing on 401.
      if (e.response?.statusCode == 401) {
        await _refreshToken();
        return _dio.get(
          '$_kApiBase$path',
          options: Options(
            headers: {'Authorization': 'Bearer $_accessToken'},
          ),
        );
      }
      rethrow;
    }
  }

  // ── Vitals fetching ─────────────────────────────────────────────────────────

  /// Fetches the latest available vitals for today from the Fitbit API.
  ///
  /// All three metric calls are issued in parallel; any individual failure
  /// returns null for that metric rather than throwing.
  Future<FitbitVitals> fetchLatestVitals() async {
    final results = await Future.wait([
      _fetchHeartRate(),
      _fetchSpo2(),
      _fetchBloodPressure(),
    ]);

    final hr = results[0] as double?;
    final spo2 = results[1] as double?;
    final bp = results[2] as _BpReading?;

    return FitbitVitals(
      heartRate: hr,
      spo2: spo2,
      systolicBp: bp?.systolic,
      diastolicBp: bp?.diastolic,
      timestamp: DateTime.now(),
    );
  }

  Future<double?> _fetchHeartRate() async {
    try {
      // Intraday 15-minute resolution for today.
      final resp = await _get(
          '/1/user/-/activities/heart/date/today/1d/15min.json');

      final intraday =
          resp.data['activities-heart-intraday']?['dataset'] as List?;

      if (intraday != null && intraday.isNotEmpty) {
        final value = intraday.last['value'];
        if (value != null) return (value as num).toDouble();
      }

      // Fallback: daily resting heart rate.
      final daily = resp.data['activities-heart'] as List?;
      if (daily != null && daily.isNotEmpty) {
        final resting = daily.first['value']?['restingHeartRate'];
        if (resting != null) return (resting as num).toDouble();
      }

      return null;
    } catch (_) {
      return null;
    }
  }

  Future<double?> _fetchSpo2() async {
    try {
      final resp = await _get('/1/user/-/spo2/date/today.json');
      // Response: { "dateTime": "...", "value": { "avg": 97.2, "min": 95.0, "max": 99.0 } }
      final avg = resp.data['value']?['avg'];
      return avg != null ? (avg as num).toDouble() : null;
    } catch (_) {
      return null;
    }
  }

  Future<_BpReading?> _fetchBloodPressure() async {
    try {
      // Blood pressure is only available from Fitbit devices with a BP sensor
      // (Fitbit Sense / Versa 3 ECG app) or from manual log entries.
      final resp = await _get('/1/user/-/bp/date/today.json');
      final list = resp.data['bp'] as List?;
      if (list == null || list.isEmpty) return null;
      final latest = list.last;
      final sys = latest['systolic'];
      final dia = latest['diastolic'];
      if (sys == null || dia == null) return null;
      return _BpReading(
        systolic: (sys as num).toDouble(),
        diastolic: (dia as num).toDouble(),
      );
    } catch (_) {
      return null;
    }
  }
}

// =============================================================================
// INTERNAL HELPERS
// =============================================================================

class _BpReading {
  final double systolic;
  final double diastolic;
  const _BpReading({required this.systolic, required this.diastolic});
}

// =============================================================================
// EXCEPTION
// =============================================================================

class FitbitAuthException implements Exception {
  final String message;
  const FitbitAuthException(this.message);

  @override
  String toString() => 'FitbitAuthException: $message';
}
