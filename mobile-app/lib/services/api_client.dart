/*
This class talks to the backend server.

It also keeps the login token and sends it with each request.
All screens reuse this one client so everything stays consistent.
*/

import 'dart:io'; // Needed for file uploads and HTTP client tweaks
import 'dart:convert'; // For converting data to/from JSON

import 'package:dio/dio.dart'; // Our HTTP client library (like Axios for Flutter)
import 'package:dio/io.dart'; // Low-level HTTP adapter for certificate handling
import 'package:flutter/foundation.dart'; // Gives us kIsWeb and kDebugMode checks
import 'package:flutter_secure_storage/flutter_secure_storage.dart'; // Encrypted storage for login tokens

class ApiClient {
  // Server address. Change this for your own backend.
  // Why this logic:
  // - Android emulator cannot reach host machine via localhost.
  // - Web/desktop can use localhost directly.
  // - API_BASE_URL can override all defaults via --dart-define.
  static const String _configuredBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: '',
  );

  // Production endpoint.
  // Use: flutter run --dart-define=USE_PRODUCTION=true
  static const String _productionBaseUrl =
      'https://api.back-adaptivhealthuowd.xyz/api/v1';

  static const String _useProduction = String.fromEnvironment(
    'USE_PRODUCTION',
    defaultValue: 'false',
  );

  // EC2 development server — used by emulator, physical device, and web.
  static const String _ec2BaseUrl = 'https://api.back-adaptivhealthuowd.xyz/api/v1';

  // Local development server running on this machine.
  // Flutter Web / Desktop reach it via localhost.
  // Android emulator reaches the host machine via 10.0.2.2.
  // Use: flutter run --dart-define=USE_LOCAL=true
  static const String _useLocal = String.fromEnvironment(
    'USE_LOCAL',
    defaultValue: 'false',
  );
  static const String _localWebUrl      = 'http://localhost:8080/api/v1';
  static const String _localAndroidUrl  = 'http://10.0.2.2:8080/api/v1';

  // Picks the right server address based on build settings
  static String get baseUrl {
    if (_configuredBaseUrl.isNotEmpty) {
      return _configuredBaseUrl; // Developer manually set a custom URL
    }
    if (_useProduction == 'true') {
      return _productionBaseUrl; // Use the live production server
    }
    if (_useLocal == 'true') {
      // Web and desktop can reach localhost directly.
      // Android emulator must use the special 10.0.2.2 alias.
      return kIsWeb ? _localWebUrl : _localAndroidUrl;
    }
    return _ec2BaseUrl; // Default: the cloud development server
  }

  final Dio _dio; // One HTTP client shared by the whole app

  static const _storage = FlutterSecureStorage(); // Encrypted vault for login tokens on the device

  static String? _authToken; // The current login token kept in memory for speed
  static String? _refreshToken; // A backup token used to get a new login token when the current one expires

  static bool _isRefreshing = false; // Prevents multiple token refresh attempts from running at the same time

  static String? _readStringField(Map<String, dynamic> data, String key) {
    final value = data[key];
    if (value is String && value.isNotEmpty) {
      return value;
    }
    return null;
  }

  /// Load previously saved tokens from secure device storage.
  /// Must be called once from main() before runApp() so the app starts
  /// in an authenticated state when a valid session already exists.
  static Future<void> initialize() async {
    _authToken = await _storage.read(key: 'auth_token'); // Grab the saved login token
    _refreshToken = await _storage.read(key: 'refresh_token'); // Grab the saved refresh token
    debugPrint('[DIAG][FLUTTER_API_TARGET][INIT] '
        'baseUrl=$baseUrl '
        'configured=${_configuredBaseUrl.isNotEmpty} '
        'useProduction=$_useProduction '
        'useLocal=$_useLocal '
        'tokenPresent=${_authToken != null} '
        'refreshPresent=${_refreshToken != null}');
  }

  /// Persist new tokens both in memory and in secure storage.
  static Future<void> _saveTokens({
    required String accessToken,
    String? refreshToken,
  }) async {
    _authToken = accessToken; // Keep in memory for fast access
    await _storage.write(key: 'auth_token', value: accessToken); // Also save to encrypted storage
    if (refreshToken != null) {
      _refreshToken = refreshToken;
      await _storage.write(key: 'refresh_token', value: refreshToken); // Save the backup token too
    }
  }

  /// Wipe tokens from memory and from secure storage.
  static Future<void> _clearStoredTokens() async {
    _authToken = null; // Forget the login token
    _refreshToken = null; // Forget the refresh token
    await _storage.delete(key: 'auth_token'); // Remove from encrypted storage
    await _storage.delete(key: 'refresh_token'); // Remove refresh token from storage too
  }

  // When creating this client, either use a provided Dio instance (for testing) or make a new one
  ApiClient({
    Dio? dio,
  })  : _dio = dio ?? _createDio() {
    _setupInterceptors(); // Attach the auto-login and auto-refresh helpers
  }

  // Create the Dio client with default settings.
  // Flutter web requires the backend to have CORS enabled:
  // from fastapi.middleware.cors import CORSMiddleware
  // app.add_middleware(
  //     CORSMiddleware,
  //     allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
  //     allow_credentials=True,
  //     allow_methods=["*"],
  //     allow_headers=["*"],
  // )
  static Dio _createDio() {
    final dio = Dio(
      BaseOptions(
        baseUrl: baseUrl, // Every request starts from this server address
        // Stop requests from hanging too long.
        connectTimeout: const Duration(seconds: 10), // Give up connecting after 10 seconds
        receiveTimeout: const Duration(seconds: 10), // Give up waiting for a response after 10 seconds
      ),
    );
    debugPrint('[DIAG][FLUTTER_API_TARGET][DIO_CREATE] baseUrl=${dio.options.baseUrl}');

    // In debug builds, trust self-signed certificates on the EC2 dev server.
    // This block is compiled out in release builds.
      // In debug builds, trust self-signed certificates on the EC2 dev server.
      // For convenience during testing it's also possible to enable this in
      // non-debug builds by passing a compile-time define:
      //   --dart-define=ALLOW_INVALID_CERTS=true
      // NOTE: Enabling this for release builds is insecure and should only be
      // used for local testing against self-signed dev servers.
      // Accept self-signed certificates in debug mode so we can test against dev servers
      const allowInvalidCerts = bool.fromEnvironment('ALLOW_INVALID_CERTS', defaultValue: false);
      if (!kIsWeb && (kDebugMode || allowInvalidCerts)) {
        (dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
          final client = HttpClient();
          client.badCertificateCallback = (cert, host, port) => true; // Trust any certificate during dev
          return client;
        };
      }

    return dio;
  }

  // Attach automatic behaviour to every request and error
  void _setupInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        // Automatically attach the login token to every outgoing request
        onRequest: (options, handler) async {
          final token = _authToken;
          if (token != null) {
            options.headers['Authorization'] = 'Bearer $token'; // Standard "Bearer" auth format
          }
          return handler.next(options);
        },
        
        // Handle errors returned by the server
        onError: (error, handler) async {
          // 401 means our login token expired — try to get a new one automatically
          // The _isRefreshing guard prevents multiple 401s from all trying to refresh at once
          if (error.response?.statusCode == 401 &&
              _refreshToken != null &&
              !_isRefreshing &&
              !(error.requestOptions.extra['_retried'] ?? false)) {
            _isRefreshing = true; // Lock so no other request tries to refresh simultaneously
            try {
              // Ask the server for a fresh token using our backup refresh token
              final refreshResp = await _dio.post(
                '/auth/token/refresh',
                data: {'refresh_token': _refreshToken},
                options: Options(extra: {'_retried': true}),
              );
              final refreshData = Map<String, dynamic>.from(
                (refreshResp.data as Map?) ?? <String, dynamic>{},
              );
              final newToken = _readStringField(refreshData, 'access_token');
              final newRefresh = _readStringField(refreshData, 'refresh_token');
              if (newToken == null) {
                throw Exception('Refresh response missing access_token');
              }
              await _saveTokens(accessToken: newToken, refreshToken: newRefresh);
              // Now retry the original request that failed, using the fresh token
              error.requestOptions.headers['Authorization'] = 'Bearer $newToken';
              error.requestOptions.extra['_retried'] = true; // Mark it so we don't loop
              final retryResponse = await _dio.fetch(error.requestOptions);
              return handler.resolve(retryResponse); // Return the successful retry result
            } catch (_) {
              await _clearStoredTokens(); // Refresh failed too — user must log in again
            } finally {
              _isRefreshing = false; // Unlock so future requests can refresh if needed
            }
          } else if (error.response?.statusCode == 401) {
            await _clearStoredTokens(); // Can't refresh — clear everything
          }
          return handler.next(error); // Pass the error along to the calling code
        },
      ),
    );
  }

  // ===================================
  // AUTHENTICATION ENDPOINTS
  // ===================================

  /// Login with email and password.
  /// If it works, we save the token for future requests.
  Future<Map<String, dynamic>> login(String email, String password) async {
    try {
      final response = await _dio.post(
        '/auth/signin',
        data: {
          'username': email,  // The backend expects "username" even though it's really an email
          'password': password,
        },
        options: Options(
          contentType: Headers.formUrlEncodedContentType, // Send as form data, not JSON
          headers: {'Content-Type': Headers.formUrlEncodedContentType},
        ),
      );
      final data = Map<String, dynamic>.from(
        (response.data as Map?) ?? <String, dynamic>{},
      );
      
      // Save the login tokens so the user stays logged in even after closing the app
      final accessToken = _readStringField(data, 'access_token');
      final refreshToken = _readStringField(data, 'refresh_token');
      if (accessToken == null) {
        final detail = data['detail']?.toString() ?? 'No access token in login response';
        throw Exception('Login failed: $detail');
      }
      await _saveTokens(accessToken: accessToken, refreshToken: refreshToken);
      
      return data; // Return the full server response to the caller
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Request password reset email.
  Future<Map<String, dynamic>> requestPasswordReset(String email) async {
    try {
      final response = await _dio.post(
        '/reset-password',
        data: {'email': email},
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Confirm password reset with token.
  Future<Map<String, dynamic>> confirmPasswordReset(String token, String newPassword) async {
    try {
      final response = await _dio.post(
        '/reset-password/confirm',
        data: {'token': token, 'new_password': newPassword},
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Register a new user account.
  /// This does not log the user in automatically.
  /// Age, gender, and phone are optional.
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String name,
    int? age,
    String? gender,
    String? phone,
  }) async {
    try {
      // Build the registration payload — only include fields that were provided
      final data = <String, dynamic>{
        'email': email,
        'password': password,
        'name': name,
      };
      if (age != null) data['age'] = age;
      if (gender != null) data['gender'] = gender;
      if (phone != null && phone.isNotEmpty) data['phone'] = phone;

      final response = await _dio.post(
        '/auth/create',
        data: data,
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Logout: revoke the access token on the server and clear local storage.
  /// Safe to call even when already logged out.
  Future<void> logout() async {
    try {
      // Tell the server to block this token so nobody can reuse it
      if (_authToken != null) {
        await _dio.post('/logout');
      }
    } catch (_) {
      // Even if the server can't be reached, always wipe local tokens
    } finally {
      await _clearStoredTokens(); // Remove tokens from memory and encrypted storage
    }
  }

  // ===================================
  // USER ENDPOINTS
  // ===================================

  /// Get the current user's profile.
  Future<Map<String, dynamic>> getCurrentUser() async {
    try {
      final response = await _dio.get('/users/me');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get list of clinicians (for patient-clinician assignment).
  /// Returns list of users with role=clinician.
  Future<List<Map<String, dynamic>>> getClinicians({int limit = 10}) async {
    try {
      final response = await _dio.get(
        '/users',
        queryParameters: {
          'role': 'clinician', // Only fetch users who are clinicians
          'per_page': limit,
          'page': 1,
        },
      );
      final List<dynamic> users = response.data['users'] ?? []; // Extract the clinician list
      return users.cast<Map<String, dynamic>>();
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get the clinician assigned to the current patient.
  /// Returns clinician details or null if nobody is assigned yet.
  Future<Map<String, dynamic>?> getAssignedClinician() async {
    try {
      final response = await _dio.get('/users/me/clinician');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) {
        return null; // No clinician assigned yet — that's okay, return nothing
      }
      throw _handleDioError(e);
    }
  }

  /// Update current user profile.
  /// Sends only non-null fields (only updates what the user actually changed).
  Future<Map<String, dynamic>> updateProfile({
    String? fullName,
    int? age,
    String? gender,
    String? phone,
    double? weightKg,
    double? heightCm,
    String? emergencyContactName,
    String? emergencyContactPhone,
    String? activityLevel,
    String? exerciseLimitations,
    String? primaryGoal,
    String? rehabPhase,
    int? stressLevel,
    String? sleepQuality,
    String? smokingStatus,
    String? alcoholFrequency,
    double? sedentaryHours,
    int? phq2Score,
  }) async {
    try {
      // Build a map with only the fields the user actually provided
      final data = <String, dynamic>{};
      if (fullName != null) data['name'] = fullName;
      if (age != null) data['age'] = age;
      if (gender != null) data['gender'] = gender;
      if (phone != null) data['phone'] = phone;
      if (weightKg != null) data['weight_kg'] = weightKg;
      if (heightCm != null) data['height_cm'] = heightCm;
      if (emergencyContactName != null) {
        data['emergency_contact_name'] = emergencyContactName;
      }
      if (emergencyContactPhone != null) {
        data['emergency_contact_phone'] = emergencyContactPhone;
      }
      if (activityLevel != null) data['activity_level'] = activityLevel;
      if (exerciseLimitations != null) {
        data['exercise_limitations'] = exerciseLimitations;
      }
      if (primaryGoal != null) data['primary_goal'] = primaryGoal;
      if (rehabPhase != null) data['rehab_phase'] = rehabPhase;
      if (stressLevel != null) data['stress_level'] = stressLevel;
      if (sleepQuality != null) data['sleep_quality'] = sleepQuality;
      if (smokingStatus != null) data['smoking_status'] = smokingStatus;
      if (alcoholFrequency != null) data['alcohol_frequency'] = alcoholFrequency;
      if (sedentaryHours != null) data['sedentary_hours'] = sedentaryHours;
      if (phq2Score != null) data['phq2_score'] = phq2Score;

      final response = await _dio.put('/users/me', data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Update medical history (encrypted on server for privacy).
  /// Used during onboarding and profile settings.
  Future<Map<String, dynamic>> updateMedicalHistory({
    List<String>? conditions,
    List<String>? medications,
    List<String>? allergies,
    List<String>? surgeries,
    String? notes,
  }) async {
    try {
      // Only include sections the user actually filled in
      final data = <String, dynamic>{};
      if (conditions != null) data['conditions'] = conditions;
      if (medications != null) data['medications'] = medications;
      if (allergies != null) data['allergies'] = allergies;
      if (surgeries != null) data['surgeries'] = surgeries;
      if (notes != null) data['notes'] = notes;

      final response = await _dio.put('/users/me/medical-history', data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ===================================
  // VITAL SIGNS ENDPOINTS
  // ===================================

  /// Get the latest vital signs for the user.
  Future<Map<String, dynamic>> getLatestVitals() async {
    try {
      final response = await _dio.get('/vitals/latest');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get vital sign history for the last N days.
  /// 4. User can spot patterns (improving or declining?)
  ///
  /// PARAMETERS:
  /// - days: Number of days to retrieve (default 7, typical range 1-90)
  ///
  /// RESPONSE:
  /// Array of vitals records:
  /// [
  ///   {vital_signs record},
  ///   {vital_signs record},
  ///   ...
  /// ]
  ///
  /// WHY days parameter:
  /// - User controls how far back to look
  /// - Reduces server load (don't fetch entire history)
  /// - Mobile can cache recent history locally
  Future<List<dynamic>> getVitalHistory({int days = 7}) async {
    try {
      final response = await _dio.get(
        '/vitals/history',
        queryParameters: {'days': days},
      );
      // Backend wraps results in {vitals: [...]} — extract the list
      if (response.data is Map && response.data['vitals'] is List) {
        return response.data['vitals'];
      }
      // Some server versions return a plain list instead
      return response.data is List ? response.data : [];
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Submit a vital reading to the server.
  /// Used when the app receives data from a wearable device or mock stream.
  Future<Map<String, dynamic>> submitVitalSigns({
    required int heartRate,
    int? spo2,
    int? systolicBp,
    int? diastolicBp,
    double? hrv,
    DateTime? timestamp,
  }) async {
    try {
      // Build the vitals payload — heart rate is required, everything else is optional
      final payload = <String, dynamic>{
        'heart_rate': heartRate,
        'timestamp': (timestamp ?? DateTime.now()).toIso8601String(), // Default to right now
      };

      if (spo2 != null) payload['spo2'] = spo2;
      if (systolicBp != null) payload['blood_pressure_systolic'] = systolicBp;
      if (diastolicBp != null) payload['blood_pressure_diastolic'] = diastolicBp;
      if (hrv != null) payload['hrv'] = hrv;

      final fullUrl = '${_dio.options.baseUrl}/vitals';
      debugPrint('[DIAG][FLUTTER_VITALS_POST][REQUEST] url=$fullUrl payload=$payload');
      final response = await _dio.post('/vitals', data: payload);
      debugPrint('[DIAG][FLUTTER_VITALS_POST][RESPONSE] '
          'url=$fullUrl status=${response.statusCode} data=${response.data}');
      return Map<String, dynamic>.from(response.data as Map);
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============================================================================
  // REMOVED METHODS (cleaned up 2026-02-21)
  // ============================================================================
  // submitVitalSigns() - POST /vitals
  //   Reason: No screens use manual vitals entry. Vitals are captured 
  //   automatically during workouts via endSession(). If manual entry is 
  //   needed in future, backend endpoint exists at POST /api/v1/vitals.
  //
  // predictRisk() - POST /predict/risk  
  //   Reason: Risk prediction is handled server-side automatically. App fetches
  //   pre-calculated risk via getLatestRiskAssessment(). No need for client to
  //   trigger risk calculations. ML model runs on backend only.
  // ============================================================================

  // ============ Activity Endpoints ============

  /// Start an exercise session on the server
  Future<Map<String, dynamic>> startSession({
    required String sessionType,
    required int targetDuration,
  }) async {
    try {
      final response = await _dio.post(
        '/activities/start',
        data: {
          'activity_type': sessionType, // e.g. "walking", "cycling"
          'duration_minutes': targetDuration, // How long the user plans to exercise
          'start_time': DateTime.now().toIso8601String(), // Record when they started
        },
      );
      final responseData = response.data;
      if (responseData is Map<String, dynamic>) {
        if (responseData['session_id'] == null) {
          throw 'Invalid response from server: missing session_id'; // Server must return an ID
        }
        return responseData;
      }
      throw 'Invalid response from server: expected JSON object';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// End an exercise session and record the heart rate stats
  Future<Map<String, dynamic>> endSession({
    required int sessionId,
    required int avgHeartRate,
    required int maxHeartRate,
    String? activityType,
    int? durationMinutes,
    int? caloriesBurned,
  }) async {
    try {
      final response = await _dio.post(
        '/activities/end/$sessionId', // Tell the server which session we're finishing
        data: {
          'end_time': DateTime.now().toIso8601String(), // When the exercise ended
          'avg_heart_rate': avgHeartRate, // Average HR during the workout
          'peak_heart_rate': maxHeartRate, // Highest HR recorded during the workout
          if (activityType != null) 'activity_type': activityType,
          if (durationMinutes != null && durationMinutes > 0) 'duration_minutes': durationMinutes,
          if (caloriesBurned != null && caloriesBurned > 0) 'calories_burned': caloriesBurned,
        },
      );
      final responseData = response.data;
      if (responseData is Map<String, dynamic>) {
        return responseData;
      }
      throw 'Invalid response from server: expected JSON object';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get my activity history
  Future<List<dynamic>> getActivities({
    int limit = 50,
    int offset = 0,
  }) async {
    try {
      final response = await _dio.get(
        '/activities',
        queryParameters: {
          'limit': limit,
          'offset': offset,
        },
      );
      return response.data as List<dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get activity by ID
  Future<Map<String, dynamic>> getActivityById(int sessionId) async {
    try {
      final response = await _dio.get('/activities/$sessionId');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Recommendation Endpoints ============

  /// Get the latest personalized recommendation for the current user.
  Future<Map<String, dynamic>> getLatestRecommendation() async {
    try {
      final response = await _dio.get('/recommendations/latest');
      final responseData = response.data;
      if (responseData is Map<String, dynamic>) {
        return responseData;
      }
      throw 'Invalid response from server: expected JSON object';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Backward-compatible wrapper.
  Future<Map<String, dynamic>> getRecommendation() async {
    return getLatestRecommendation();
  }

  /// Mark a recommendation as completed or partially completed.
  Future<Map<String, dynamic>> completeRecommendation(
    int recommendationId, {
    int? actualMinutes,
  }) async {
    try {
      final response = await _dio.post(
        '/recommendations/$recommendationId/complete',
        data: actualMinutes != null ? {'actual_minutes': actualMinutes} : {},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get today's recovery score breakdown.
  Future<Map<String, dynamic>> getDailyRecoveryScore({String? date}) async {
    try {
      final response = await _dio.get(
        '/recovery/daily-score',
        queryParameters: date != null ? {'date': date} : null,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get last 7 days of recovery scores.
  Future<List<Map<String, dynamic>>> getWeeklyRecoveryScores() async {
    try {
      final response = await _dio.get('/recovery/weekly-scores');
      final data = response.data;
      if (data is Map && data['scores'] is List) {
        return List<Map<String, dynamic>>.from(data['scores']);
      }
      if (data is List) {
        return List<Map<String, dynamic>>.from(data);
      }
      return [];
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Sleep Endpoints ============

  /// Log a sleep entry.
  Future<Map<String, dynamic>> logSleep({
    required DateTime bedtime,
    required DateTime wakeTime,
    required int qualityRating,
    String? notes,
  }) async {
    try {
      final data = {
        'bedtime': bedtime.toIso8601String(),
        'wake_time': wakeTime.toIso8601String(),
        'quality_rating': qualityRating,
        if (notes != null && notes.trim().isNotEmpty) 'notes': notes.trim(),
      };
      final response = await _dio.post('/sleep', data: data);
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get the most recent sleep entry.
  Future<Map<String, dynamic>> getLatestSleep() async {
    try {
      final response = await _dio.get('/sleep/latest');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get sleep history for the last N days.
  Future<Map<String, dynamic>> getSleepHistory({int days = 7}) async {
    try {
      final response = await _dio.get(
        '/sleep',
        queryParameters: {'days': days},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Alert Endpoints ============

  /// Create a new alert (used by the SOS button and automated warnings).
  ///
  /// The backend needs: user_id, alert_type, severity, message.
  Future<Map<String, dynamic>> createAlert({
    required String alertType,
    required String severity,
    String? notes,
    String? title,
    String? actionRequired,
    String? triggerValue,
    String? thresholdValue,
  }) async {
    try {
      // First, look up our own user ID so the server knows who triggered this alert
      final profile = await getCurrentUser();
      final userIdRaw = profile['user_id'] ?? profile['id'];
      if (userIdRaw == null) {
        throw 'Unable to determine current user ID';
      }

      final userId = userIdRaw is int
          ? userIdRaw
          : int.tryParse(userIdRaw.toString()); // Convert to number if it came as text
      if (userId == null) {
        throw 'Invalid current user ID format';
      }

      final response = await _dio.post(
        '/alerts',
        data: {
          'user_id': userId,
          'alert_type': alertType, // e.g. "sos", "vital_abnormal"
          'severity': severity.toLowerCase(), // "critical", "warning", or "info"
          'message': (notes != null && notes.trim().isNotEmpty)
              ? notes.trim()
              : 'Manual alert triggered by patient', // Default message if none provided
          if (title != null && title.trim().isNotEmpty) 'title': title.trim(),
          if (actionRequired != null && actionRequired.trim().isNotEmpty)
            'action_required': actionRequired.trim(),
          if (triggerValue != null && triggerValue.trim().isNotEmpty)
            'trigger_value': triggerValue.trim(),
          if (thresholdValue != null && thresholdValue.trim().isNotEmpty)
            'threshold_value': thresholdValue.trim(),
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get my alerts with pagination and optional filters.
  Future<Map<String, dynamic>> getAlerts({
    int page = 1,
    int perPage = 50,
    bool? acknowledged,
    String? severity,
  }) async {
    try {
      // Build query filters — only include the ones that were specified
      final queryParams = <String, dynamic>{
        'page': page,
        'per_page': perPage,
      };
      if (acknowledged != null) queryParams['acknowledged'] = acknowledged;
      if (severity != null) queryParams['severity'] = severity;

      final response = await _dio.get(
        '/alerts',
        queryParameters: queryParams,
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Acknowledge an alert (patient has seen it).
  Future<Map<String, dynamic>> acknowledgeAlert(int alertId) async {
    try {
      final response = await _dio.patch('/alerts/$alertId/acknowledge');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Resolve an alert — mark it as handled, with optional notes about what was done.
  Future<Map<String, dynamic>> resolveAlert(
    int alertId, {
    String? resolutionNotes,
  }) async {
    try {
      final response = await _dio.patch(
        '/alerts/$alertId/resolve',
        data: {
          if (resolutionNotes != null) 'resolution_notes': resolutionNotes,
        },
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Risk Assessment Endpoints ============

  /// Get the patient's most recent stored risk assessment.
  ///
  /// Used by the Home screen to show the latest cardiovascular
  /// risk level and score without recomputing the ML model.
  Future<Map<String, dynamic>> getLatestRiskAssessment() async {
    try {
      final response = await _dio.get('/risk-assessments/latest');
      return response.data;
    } on DioException catch (e) {
      // Let caller decide how to handle specific status codes
      throw _handleDioError(e);
    }
  }

  // ============ Consent Endpoints ============

  /// Get current consent/sharing status
  Future<Map<String, dynamic>> getConsentStatus() async {
    try {
      final response = await _dio.get('/consent/status');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Request to stop sharing health data with clinicians.
  Future<Map<String, dynamic>> requestDisableSharing({String? reason}) async {
    try {
      final response = await _dio.post(
        '/consent/disable',
        data: {'reason': reason},
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Turn data sharing with clinicians back on.
  Future<Map<String, dynamic>> enableSharing() async {
    try {
      final response = await _dio.post('/consent/enable');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Natural Language / AI ============

  /// Get a simple, patient-friendly summary of their health risk.
  Future<String> getNLRiskSummary() async {
    try {
      final response = await _dio.get('/nl/risk-summary');
      if (response.data is Map && response.data['nl_summary'] != null) {
        return response.data['nl_summary'] as String; // The AI-generated summary text
      }
      return 'Your health status is stable. Keep up your current routine.'; // Fallback if server returns nothing
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get today's personalized workout recommendation.
  Future<String> getNLTodaysWorkout() async {
    try {
      final response = await _dio.get('/nl/todays-workout');
      if (response.data is Map && response.data['nl_summary'] != null) {
        return response.data['nl_summary'] as String;
      }
      return 'Check the Fitness tab for today\'s recommended activity.';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get explanation for a specific health alert.
  Future<String> getNLAlertExplanation({String? alertId}) async {
    try {
      final params = <String, dynamic>{};
      if (alertId != null) params['alert_id'] = alertId;

      final response = await _dio.get(
        '/nl/alert-explanation',
        queryParameters: params,
      );
      if (response.data is Map && response.data['nl_summary'] != null) {
        return response.data['nl_summary'] as String;
      }
      return 'No recent alerts to explain.';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get motivational progress summary comparing periods.
  Future<String> getNLProgressSummary({String range = '7d'}) async {
    try {
      final response = await _dio.get(
        '/nl/progress-summary',
        queryParameters: {'range': range},
      );
      if (response.data is Map && response.data['nl_summary'] != null) {
        return response.data['nl_summary'] as String;
      }
      return 'Great work! You\'re making positive progress.';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get a patient-friendly nutrition plan summary.
  ///
  /// Calls GET /nutrition/recommendations and formats the response
  /// into a readable string listing daily calorie goal and 4 suggested meals.
  Future<String> getNLNutritionPlan() async {
    try {
      final response = await _dio.get('/nutrition/recommendations');
      final data = response.data;
      if (data is Map<String, dynamic>) {
        final goals = data['daily_nutrition_goals'] as Map<String, dynamic>?;
        final meals = data['meals'] as List<dynamic>?;

        final buffer = StringBuffer();

        // Daily calorie goal
        if (goals != null && goals['calories_target'] != null) {
          buffer.writeln(
            'Your daily calorie goal is ${goals['calories_target']} kcal.',
          );
        }

        // Suggested meals
        if (meals != null && meals.isNotEmpty) {
          buffer.writeln('');
          buffer.writeln('Today\'s suggested meals:');
          for (final meal in meals) {
            if (meal is Map<String, dynamic>) {
              final type = (meal['meal_type'] as String?)?.toUpperCase() ?? 'MEAL';
              final items = meal['suggested_items'] as List<dynamic>?;
              final itemsStr = items != null ? items.join(', ') : 'See nutrition tab';
              buffer.writeln('• $type — $itemsStr');
            }
          }
        }

        final result = buffer.toString().trim();
        if (result.isNotEmpty) return result;
      }
      return 'Visit the Nutrition tab for personalised meal recommendations.';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  @Deprecated('Use getNLRiskSummary() instead.')
  Future<String> getRiskSummaryNL() async {
    return getNLRiskSummary();
  }

  /// Send a chat message to the AI health coach.
  ///
  /// The server uses quick templates for common questions
  /// or sends it to a Gemini AI for open-ended conversations.
  Future<String> postNLChat(
    String message,
    List<Map<String, String>> conversationHistory, // Previous messages for context
  ) async {
    try {
      final response = await _dio.post(
        '/nl/chat',
        data: {
          'message': message,
          'conversation_history': conversationHistory,
        },
      );
      if (response.data is Map && response.data['response'] != null) {
        return response.data['response'] as String;
      }
      return 'I can help with your health, workouts, and alerts. What would you like to know?';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Send a photo along with a chat message for the AI to analyze.
  ///
  /// Useful for food photo analysis, medication identification, etc.
  Future<String> postNLChatWithImage(
    File imageFile,
    String message,
    String analysisType, // e.g. "food", "medication", "wound"
    List<Map<String, String>> history,
  ) async {
    try {
      final filename = imageFile.path.split(RegExp(r'[\\/]')).last; // Extract just the file name
      final formData = FormData.fromMap({
        'image': await MultipartFile.fromFile( // Attach the photo as a file upload
          imageFile.path,
          filename: filename,
        ),
        'message': message, // The user's question about the image
        'analysis_type': analysisType, // What kind of analysis to run
        'conversation_history': jsonEncode(history), // Previous chat messages as JSON text
      });

      final response = await _dio.post(
        '/nl/chat-with-image',
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );

      if (response.data is Map && response.data['response'] != null) {
        return response.data['response'] as String;
      }
      return 'I analyzed the image, but could not format a full response. Please try again.';
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Nutrition Endpoints ============

  /// Analyze a food photo and return detected nutrition data.
  ///
  /// The AI identifies the food and estimates calories and nutrients.
  Future<Map<String, dynamic>> analyzeFoodImage(File imageFile) async {
    try {
      final filename = imageFile.path.split(RegExp(r'[\\/]')).last; // Get the file name
      final formData = FormData.fromMap({
        'image': await MultipartFile.fromFile( // Upload the food photo
          imageFile.path,
          filename: filename,
        ),
      });

      final response = await _dio.post(
        '/food/analyze-image',
        data: formData,
        options: Options(contentType: 'multipart/form-data'),
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Look up nutrition info for a product by scanning its barcode.
  Future<Map<String, dynamic>> lookupBarcode(String barcode) async {
    try {
      final response = await _dio.get('/food/barcode/$barcode');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get recent nutrition entries for the current user
  /// 
  /// Returns a list of nutrition entries ordered by timestamp descending.
  /// Each entry contains: entry_id, meal_type, description, calories,
  /// protein_grams, carbs_grams, fat_grams, timestamp.
  /// 
  /// PARAMETERS:
  /// - limit: Maximum number of entries to retrieve (default 5, max 100)
  /// 
  /// RESPONSE:
  /// {
  ///   "entries": [
  ///     {
  ///       "entry_id": 123,
  ///       "user_id": 1,
  ///       "meal_type": "breakfast",
  ///       "description": "Oatmeal with berries",
  ///       "calories": 350,
  ///       "protein_grams": 12,
  ///       "carbs_grams": 45,
  ///       "fat_grams": 14,
  ///       "timestamp": "2026-02-21T08:30:00Z"
  ///     },
  ///     ...
  ///   ],
  ///   "total_count": 47,
  ///   "limit": 5
  /// }
  Future<Map<String, dynamic>> getRecentNutrition({
    int limit = 5,
    String? date,
  }) async {
    try {
      final queryParams = <String, dynamic>{'limit': limit};
      if (date != null && date.trim().isNotEmpty) {
        queryParams['date'] = date.trim();
      }
      final response = await _dio.get(
        '/nutrition/recent',
        queryParameters: queryParams,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Create a new nutrition entry
  /// 
  /// Logs a meal or snack with calories and optional macronutrients.
  /// 
  /// PARAMETERS (all via payload map):
  /// - meal_type: Required. One of: "breakfast", "lunch", "dinner", "snack", "other"
  /// - calories: Required. Total calories (0-10,000)
  /// - description: Optional. Meal description (max 500 chars)
  /// - protein_grams: Optional. Protein in grams (0-500)
  /// - carbs_grams: Optional. Carbohydrates in grams (0-1,000)
  /// - fat_grams: Optional. Fat in grams (0-500)
  /// 
  /// RESPONSE:
  /// Full nutrition entry with entry_id and timestamp
  Future<Map<String, dynamic>> createNutritionEntry({
    required String mealType,
    required int calories,
    String? description,
    int? proteinGrams,
    int? carbsGrams,
    int? fatGrams,
    DateTime? loggedAt,
  }) async {
    try {
      final data = <String, dynamic>{
        'meal_type': mealType,
        'calories': calories,
      };
      if (description != null && description.isNotEmpty) {
        data['description'] = description;
      }
      if (proteinGrams != null) data['protein_grams'] = proteinGrams;
      if (carbsGrams != null) data['carbs_grams'] = carbsGrams;
      if (fatGrams != null) data['fat_grams'] = fatGrams;
      if (loggedAt != null) data['logged_at'] = loggedAt.toIso8601String();

      final response = await _dio.post('/nutrition', data: data);
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Delete a nutrition entry
  /// 
  /// Users can only delete their own entries.
  /// Returns nothing on success (204 No Content).
  /// 
  /// PARAMETERS:
  /// - entryId: ID of the nutrition entry to delete
  /// 
  /// ERRORS:
  /// - 404: Entry not found or does not belong to current user
  Future<void> deleteNutritionEntry(int entryId) async {
    try {
      await _dio.delete('/nutrition/$entryId');
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Messaging Endpoints ============

  /// Get message thread between current user and another user
  ///
  /// Returns list of messages ordered by sent_at ascending.
  Future<List<Map<String, dynamic>>> getMessageThread(
    int otherUserId, {
    int limit = 50,
  }) async {
    try {
      final response = await _dio.get(
        '/messages/thread/$otherUserId',
        queryParameters: {'limit': limit},
      );
      final data = response.data;
      if (data is List) {
        return List<Map<String, dynamic>>.from(data);
      }
      return [];
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Send a text message to another user (patient or clinician).
  Future<void> sendMessage({
    required int receiverId,
    required String content,
  }) async {
    try {
      await _dio.post(
        '/messages',
        data: {
          'receiver_id': receiverId,
          'content': content,
        },
      );
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Mark a specific message as read so the sender knows it was seen.
  Future<Map<String, dynamic>> markMessageRead(int messageId) async {
    try {
      final response = await _dio.post('/messages/$messageId/read');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Medication Reminder Endpoints ============

  /// Get all medication reminders set up for this user.
  Future<List<Map<String, dynamic>>> getMedicationReminders() async {
    try {
      final response = await _dio.get('/medications/reminders');
      final data = response.data;
      if (data is List) {
        return List<Map<String, dynamic>>.from(data);
      }
      return [];
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Update reminder settings for a specific medication.
  /// 
  /// PARAMETERS:
  /// - medId: ID of the medication
  /// - time: Optional reminder time in HH:MM format (e.g., '08:00')
  /// - enabled: Optional flag to enable/disable reminders
  Future<Map<String, dynamic>> updateMedicationReminder(
    int medId, {
    String? time,
    bool? enabled,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (time != null) data['reminder_time'] = time;
      if (enabled != null) data['reminder_enabled'] = enabled;

      final response = await _dio.put(
        '/medications/$medId/reminder',
        data: data,
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Record whether the user took or skipped a medication on a given day.
  Future<Map<String, dynamic>> logAdherence(
    int medId,
    String date,
    bool taken,
  ) async {
    try {
      final response = await _dio.post(
        '/medications/adherence',
        data: {
          'medication_id': medId,
          'date': date,
          'taken': taken,
        },
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get medication adherence history for the current user.
  /// 
  /// PARAMETERS:
  /// - days: Number of days to look back (default 7, max 90)
  /// 
  /// RETURNS:
  /// Map with entries, total_scheduled, total_taken, adherence_percent
  Future<Map<String, dynamic>> getAdherenceHistory({int days = 7}) async {
    try {
      final response = await _dio.get(
        '/medications/adherence/history',
        queryParameters: {'days': days},
      );
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Rehab Program Endpoints ============

  /// Get the user's active rehab program with session plan and progress.
  /// Returns the full program object or throws on 404 (not in rehab).
  Future<Map<String, dynamic>> getRehabProgram() async {
    try {
      final response = await _dio.get('/rehab/current-program');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Record a completed rehab session. Returns updated progress.
  Future<Map<String, dynamic>> completeRehabSession({
    required int actualDurationMinutes,
    int? avgHeartRate,
    int? peakHeartRate,
    required String activityType,
  }) async {
    try {
      final data = <String, dynamic>{
        'actual_duration_minutes': actualDurationMinutes,
        'activity_type': activityType,
      };
      if (avgHeartRate != null) data['avg_heart_rate'] = avgHeartRate;
      if (peakHeartRate != null) data['peak_heart_rate'] = peakHeartRate;

      final response = await _dio.post('/rehab/complete-session', data: data);
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get rehab progress summary without modifying state.
  Future<Map<String, dynamic>> getRehabProgress() async {
    try {
      final response = await _dio.get('/rehab/progress');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Error Handling ============

  String _handleDioError(DioException e) {
    if (e.response != null) {
      final statusCode = e.response!.statusCode;
      final data = e.response!.data;
      String detail = 'Unknown error';
      if (data is Map && data['detail'] != null) {
        detail = data['detail'].toString();
      } else if (data != null) {
        detail = data.toString();
      }
      
      if (statusCode == 401) {
        return 'Unauthorized: Please log in again';
      } else if (statusCode == 422) {
        return 'Validation error: $detail';
      } else if (statusCode == 500) {
        return 'Server error: Please try again later';
      } else {
        return 'Error ($statusCode): $detail';
      }
    } else if (e.type == DioExceptionType.connectionTimeout) {
      return 'Connection timeout: Could not reach backend at $baseUrl';
    } else if (e.type == DioExceptionType.connectionError) {
      return 'Connection error: Could not reach backend at $baseUrl';
    } else if (e.type == DioExceptionType.receiveTimeout) {
      return 'Request timeout: Server not responding';
    } else {
      final msg = e.message ?? 'no details available';
      return 'Unexpected network error: $msg';
    }
  }

  // Getter for Dio instance (for testing)
  Dio get dio => _dio;
}
