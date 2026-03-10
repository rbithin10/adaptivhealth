/*
Fitbit Service.

Connects to the user's Fitbit account to read health data like
heart rate, blood oxygen (SpO2), and blood pressure.

Uses the Fitbit Web API with OAuth 2.0 PKCE authentication —
this means the user logs into their Fitbit account through a
secure browser window, and we get permission to read their data.

Tokens (login credentials) are stored securely on the phone and
refreshed automatically when they expire.

Data polled every 15 minutes:
  - Heart Rate (intraday 15-minute buckets from the Fitbit watch)
  - SpO2 (daily average blood oxygen from the watch sensor)
  - Blood Pressure (from manual entries or BP-capable Fitbit devices)

Setup: Register your app at https://dev.fitbit.com/apps/new and
put your Client ID in the _kClientId constant below.
*/

// Timers and async helpers
import 'dart:async';
// Converts JSON text to/from Dart objects
import 'dart:convert';
// Generates secure random numbers for PKCE codes
import 'dart:math';

// Creates SHA-256 hashes needed for the PKCE security flow
import 'package:crypto/crypto.dart';
// HTTP client for making API calls to Fitbit servers
import 'package:dio/dio.dart';
// Securely stores login tokens on the phone's encrypted keychain
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
// Opens the system browser for the Fitbit login page
import 'package:flutter_web_auth_2/flutter_web_auth_2.dart';

// =============================================================================
// FITBIT APP SETTINGS — replace the Client ID with yours from dev.fitbit.com
// =============================================================================

// Your Fitbit app's Client ID from https://dev.fitbit.com/apps
const String _kClientId = 'YOUR_FITBIT_CLIENT_ID';

// The URL scheme the app listens for when Fitbit redirects back after login
const String _kCallbackScheme = 'adaptivhealth';
// The full callback URL Fitbit will redirect to after the user logs in
const String _kCallbackUrl = 'adaptivhealth://fitbit/callback';
// Fitbit's login page URL
const String _kAuthUrl = 'https://www.fitbit.com/oauth2/authorize';
// Fitbit's token exchange URL
const String _kTokenUrl = 'https://api.fitbit.com/oauth2/token';
// Fitbit's API base URL for data requests
const String _kApiBase = 'https://api.fitbit.com';

// What types of data we want to read (heartrate, oxygen, fitness, steps)
const String _kScopes =
    'heartrate oxygen_saturation cardio_fitness activity';

// Keys for storing tokens securely on the phone
const String _kKeyAccess = 'fitbit_access_token';
const String _kKeyRefresh = 'fitbit_refresh_token';
const String _kKeyExpiry = 'fitbit_token_expiry';

// =============================================================================
// DATA MODELS — holds the health readings from Fitbit
// =============================================================================

// A snapshot of the latest vitals fetched from Fitbit
class FitbitVitals {
  // Heart rate in beats per minute (if available)
  final double? heartRate;
  // Blood oxygen percentage (if available)
  final double? spo2;
  // Top blood pressure number (if available)
  final double? systolicBp;
  // Bottom blood pressure number (if available)
  final double? diastolicBp;
  // When these readings were fetched
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
// FITBIT SERVICE — handles login and data fetching
// =============================================================================

// Only one instance of this service exists in the whole app
class FitbitService {
  // The single shared instance
  static final FitbitService instance = FitbitService._();
  // Private constructor — prevents creating extra instances
  FitbitService._();

  // Encrypted storage for keeping login tokens safe on the phone
  final _storage = const FlutterSecureStorage();
  // HTTP client for talking to Fitbit's servers
  final _dio = Dio(BaseOptions(
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 15),
  ));

  // Login token kept in memory for faster access (also saved to storage)
  String? _accessToken;
  // When the current login token expires
  DateTime? _tokenExpiry;

  // ── PKCE Helpers — security codes for the login flow ────────────────────────

  // Generate a random 128-character code used to prove our identity to Fitbit
  static String _codeVerifier() {
    const chars =
        'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~';
    final rng = Random.secure();
    return List.generate(128, (_) => chars[rng.nextInt(chars.length)]).join();
  }

  // Create a hashed version of the verifier code that Fitbit checks against
  static String _codeChallenge(String verifier) {
    final bytes = utf8.encode(verifier);
    final digest = sha256.convert(bytes);
    return base64UrlEncode(digest.bytes).replaceAll('=', '');
  }

  // ── Auth State — check if we're logged into Fitbit ──────────────────────────

  // Check if we have a valid (non-expired) Fitbit login token
  Future<bool> get isConnected async {
    // Read the stored access token
    final token = await _storage.read(key: _kKeyAccess);
    if (token == null) return false;
    // Read when the token expires
    final expiryStr = await _storage.read(key: _kKeyExpiry);
    final expiry = expiryStr != null ? DateTime.tryParse(expiryStr) : null;
    if (expiry == null) return false;
    // Consider it expired if within 60 seconds of the deadline
    return DateTime.now()
        .isBefore(expiry.subtract(const Duration(seconds: 60)));
  }

  // ── OAuth2 PKCE Login Flow — opens browser for Fitbit login ─────────────────

  // Open the Fitbit login page, wait for the user to log in, then save tokens
  Future<void> authorize() async {
    // Generate the PKCE security codes
    final verifier = _codeVerifier();
    final challenge = _codeChallenge(verifier);

    // Build the Fitbit login page URL with all required parameters
    final authUri = Uri.parse(_kAuthUrl).replace(queryParameters: {
      'client_id': _kClientId,
      'redirect_uri': _kCallbackUrl,
      'response_type': 'code',
      'scope': _kScopes,
      'code_challenge': challenge,
      'code_challenge_method': 'S256',
    });

    // Open the system browser and wait for the user to login
    final callbackResult = await FlutterWebAuth2.authenticate(
      url: authUri.toString(),
      callbackUrlScheme: _kCallbackScheme,
    );

    // Extract the authorization code from the callback URL
    final code = Uri.parse(callbackResult).queryParameters['code'];
    if (code == null || code.isEmpty) {
      throw const FitbitAuthException(
          'Authorization was cancelled or the code was missing.');
    }

    // Exchange the temporary code for permanent login tokens
    await _exchangeCode(code, verifier);
  }

  // Send the authorization code to Fitbit and get access/refresh tokens back
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
      // Save the tokens securely on the phone
      await _storeTokens(response.data);
    } on DioException catch (e) {
      throw FitbitAuthException(
          'Token exchange failed: ${e.response?.data ?? e.message}');
    }
  }

  // Use the refresh token to get a new access token when the old one expires
  Future<void> _refreshToken() async {
    // Read the saved refresh token
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
      // Save the fresh tokens
      await _storeTokens(response.data);
    } on DioException catch (e) {
      // Refresh failed — clear everything so the user can re-login
      await disconnect();
      throw FitbitAuthException(
          'Token refresh failed: ${e.response?.data ?? e.message}');
    }
  }

  // Save the login tokens securely on the phone
  Future<void> _storeTokens(Map<String, dynamic> data) async {
    // Extract the access token, refresh token, and expiry time
    final access = data['access_token'] as String;
    final refresh = data['refresh_token'] as String;
    final expiresIn = (data['expires_in'] as num).toInt();
    // Calculate when the token will expire
    final expiry = DateTime.now().add(Duration(seconds: expiresIn));

    // Keep in memory for fast access
    _accessToken = access;
    _tokenExpiry = expiry;

    // Save all three values to encrypted phone storage (in parallel)
    await Future.wait([
      _storage.write(key: _kKeyAccess, value: access),
      _storage.write(key: _kKeyRefresh, value: refresh),
      _storage.write(key: _kKeyExpiry, value: expiry.toIso8601String()),
    ]);
  }

  // Log out from Fitbit by deleting all stored tokens
  Future<void> disconnect() async {
    // Clear memory cache
    _accessToken = null;
    _tokenExpiry = null;
    // Delete all three tokens from secure storage (in parallel)
    await Future.wait([
      _storage.delete(key: _kKeyAccess),
      _storage.delete(key: _kKeyRefresh),
      _storage.delete(key: _kKeyExpiry),
    ]);
  }

  // ── Authenticated API Calls — talk to Fitbit's servers ──────────────────────

  // Make a GET request to Fitbit's API with automatic token refresh
  Future<Response> _get(String path) async {
    // Load the token from storage if we don't have it in memory yet
    _accessToken ??= await _storage.read(key: _kKeyAccess);

    // Load the expiry time from storage if we don't have it in memory
    if (_tokenExpiry == null) {
      final str = await _storage.read(key: _kKeyExpiry);
      _tokenExpiry = str != null ? DateTime.tryParse(str) : null;
    }

    // Check if the token is expired or about to expire
    final needsRefresh = _tokenExpiry == null ||
        DateTime.now()
            .isAfter(_tokenExpiry!.subtract(const Duration(minutes: 2)));

    // Refresh the token if it's expired
    if (needsRefresh) await _refreshToken();

    try {
      // Make the API request with our login token
      return await _dio.get(
        '$_kApiBase$path',
        options: Options(
          headers: {'Authorization': 'Bearer $_accessToken'},
        ),
      );
    } on DioException catch (e) {
      // If we get a 401 (unauthorized), refresh the token and try once more
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

  // ── Vitals Fetching — get the latest health data from Fitbit ────────────────

  // Fetch heart rate, SpO2, and blood pressure from Fitbit all at once
  Future<FitbitVitals> fetchLatestVitals() async {
    // Request all three types of data in parallel for speed
    final results = await Future.wait([
      _fetchHeartRate(),
      _fetchSpo2(),
      _fetchBloodPressure(),
    ]);

    // Unpack the results (any could be null if that data isn't available)
    final hr = results[0] as double?;
    final spo2 = results[1] as double?;
    final bp = results[2] as _BpReading?;

    // Bundle everything into a single vitals snapshot
    return FitbitVitals(
      heartRate: hr,
      spo2: spo2,
      systolicBp: bp?.systolic,
      diastolicBp: bp?.diastolic,
      timestamp: DateTime.now(),
    );
  }

  // Fetch the latest heart rate reading from Fitbit
  Future<double?> _fetchHeartRate() async {
    try {
      // Get today's heart rate data in 15-minute intervals
      final resp = await _get(
          '/1/user/-/activities/heart/date/today/1d/15min.json');

      // Try to get the most recent 15-minute reading
      final intraday =
          resp.data['activities-heart-intraday']?['dataset'] as List?;

      if (intraday != null && intraday.isNotEmpty) {
        // Use the last (most recent) reading from the intraday data
        final value = intraday.last['value'];
        if (value != null) return (value as num).toDouble();
      }

      // If no intraday data, fall back to the daily resting heart rate
      final daily = resp.data['activities-heart'] as List?;
      if (daily != null && daily.isNotEmpty) {
        final resting = daily.first['value']?['restingHeartRate'];
        if (resting != null) return (resting as num).toDouble();
      }

      return null;
    } catch (_) {
      // If the request fails, just return nothing
      return null;
    }
  }

  // Fetch the daily blood oxygen (SpO2) average from Fitbit
  Future<double?> _fetchSpo2() async {
    try {
      final resp = await _get('/1/user/-/spo2/date/today.json');
      // The response contains an average SpO2 value for the day
      final avg = resp.data['value']?['avg'];
      return avg != null ? (avg as num).toDouble() : null;
    } catch (_) {
      return null;
    }
  }

  // Fetch the latest blood pressure reading from Fitbit (manual or device)
  Future<_BpReading?> _fetchBloodPressure() async {
    try {
      // Blood pressure is only available from BP-capable Fitbit devices
      // or from manual entries the user logged in the Fitbit app
      final resp = await _get('/1/user/-/bp/date/today.json');
      final list = resp.data['bp'] as List?;
      if (list == null || list.isEmpty) return null;
      // Get the most recent blood pressure entry from today
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

// Holds a blood pressure reading (systolic/diastolic pair)
class _BpReading {
  final double systolic;
  final double diastolic;
  const _BpReading({required this.systolic, required this.diastolic});
}

// =============================================================================
// EXCEPTION — thrown when Fitbit login or token refresh fails
// =============================================================================

// Custom error type for Fitbit authentication problems
class FitbitAuthException implements Exception {
  // A human-readable explanation of what went wrong
  final String message;
  const FitbitAuthException(this.message);

  @override
  String toString() => 'FitbitAuthException: $message';
}
