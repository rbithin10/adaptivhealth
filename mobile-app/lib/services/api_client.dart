/*
This class talks to the backend server.

It also keeps the login token and sends it with each request.
All screens reuse this one client so everything stays consistent.
*/

import 'package:dio/dio.dart';

class ApiClient {
  // Server address. Change this for your own backend.
  static const String baseUrl = 'http://localhost:8080/api/v1';

  // One HTTP client shared by the whole app.
  final Dio _dio;
  
  // Login token saved in memory.
  // Note: This will reset if the app restarts.
  static String? _authToken;
  static String? _refreshToken;

  ApiClient({
    Dio? dio,
  })  : _dio = dio ?? _createDio() {
    _setupInterceptors();
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
    return Dio(
      BaseOptions(
        baseUrl: baseUrl,
        // Stop requests from hanging too long.
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 10),
      ),
    );
  }

  // Add helpers that run on every request and error.
  void _setupInterceptors() {
    _dio.interceptors.add(
      InterceptorsWrapper(
        // Add the login token to each request.
        onRequest: (options, handler) async {
          final token = _authToken;
          if (token != null) {
            // Standard Authorization header format.
            options.headers['Authorization'] = 'Bearer $token';
          }
          return handler.next(options);
        },
        
        // Handle errors returned by the server.
        onError: (error, handler) async {
          // 401 means the token is not valid anymore.
          if (error.response?.statusCode == 401 &&
              _refreshToken != null &&
              !(error.requestOptions.extra['_retried'] ?? false)) {
            // Try refreshing the token once
            try {
              final refreshResp = await _dio.post(
                '/refresh',
                data: {'refresh_token': _refreshToken},
                options: Options(extra: {'_retried': true}),
              );
              final newToken = refreshResp.data['access_token'];
              _authToken = newToken;
              if (refreshResp.data['refresh_token'] != null) {
                _refreshToken = refreshResp.data['refresh_token'];
              }
              // Retry the original request with new token
              error.requestOptions.headers['Authorization'] = 'Bearer $newToken';
              error.requestOptions.extra['_retried'] = true;
              final retryResponse = await _dio.fetch(error.requestOptions);
              return handler.resolve(retryResponse);
            } catch (_) {
              // Refresh failed — clear tokens
              _authToken = null;
              _refreshToken = null;
            }
          } else if (error.response?.statusCode == 401) {
            _authToken = null;
            _refreshToken = null;
          }
          return handler.next(error);
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
        '/login',
        data: {
          'username': email,  // FastAPI OAuth2 uses 'username'
          'password': password,
        },
        options: Options(
          contentType: Headers.formUrlEncodedContentType,
          headers: {'Content-Type': Headers.formUrlEncodedContentType},
        ),
      );
      
      // Save the token so future requests are authenticated.
      final accessToken = response.data['access_token'];
      _authToken = accessToken;
      
      // Store refresh token if provided
      if (response.data['refresh_token'] != null) {
        _refreshToken = response.data['refresh_token'];
      }
      
      return response.data;
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
      final data = <String, dynamic>{
        'email': email,
        'password': password,
        'name': name,
      };
      if (age != null) data['age'] = age;
      if (gender != null) data['gender'] = gender;
      if (phone != null && phone.isNotEmpty) data['phone'] = phone;

      final response = await _dio.post(
        '/register',
        data: data,
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Logout by clearing the local tokens.
  Future<void> logout() async {
    _authToken = null;
    _refreshToken = null;
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
  /// Update current user profile
  Future<Map<String, dynamic>> updateProfile({
    String? fullName,
    int? age,
    String? gender,
    String? phone,
  }) async {
    try {
      final data = <String, dynamic>{};
      if (fullName != null) data['name'] = fullName;
      if (age != null) data['age'] = age;
      if (gender != null) data['gender'] = gender;
      if (phone != null) data['phone'] = phone;

      final response = await _dio.put('/users/me', data: data);
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
      return response.data is List ? response.data : [];
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Submit vital signs reading
  Future<Map<String, dynamic>> submitVitalSigns({
    required int heartRate,
    required int spo2,
    required int systolicBp,
    required int diastolicBp,
  }) async {
    try {
      final response = await _dio.post(
        '/vitals',
        data: {
          'heart_rate': heartRate,
          'spo2': spo2,
          'blood_pressure_systolic': systolicBp,
          'blood_pressure_diastolic': diastolicBp,
          'timestamp': DateTime.now().toIso8601String(),
        },
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Risk Prediction Endpoints ============

  /// Get AI risk prediction
  Future<Map<String, dynamic>> predictRisk({
    required int heartRate,
    required int spo2,
    required int systolicBp,
    required int diastolicBp,
  }) async {
    try {
      final response = await _dio.post(
        '/predict/risk',
        data: {
          'heart_rate': heartRate,
          'spo2': spo2,
          'systolic_bp': systolicBp,
          'diastolic_bp': diastolicBp,
        },
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Activity Endpoints ============

  /// Start an exercise session
  Future<Map<String, dynamic>> startSession({
    required String sessionType,
    required int targetDuration,
  }) async {
    try {
      final response = await _dio.post(
        '/activity/start',
        data: {
          'session_type': sessionType,
          'target_duration': targetDuration,
          'start_time': DateTime.now().toIso8601String(),
        },
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// End exercise session
  Future<Map<String, dynamic>> endSession({
    required int sessionId,
    required int avgHeartRate,
    required int maxHeartRate,
  }) async {
    try {
      final response = await _dio.post(
        '/activity/end/$sessionId',
        data: {
          'end_time': DateTime.now().toIso8601String(),
          'avg_heart_rate': avgHeartRate,
          'max_heart_rate': maxHeartRate,
        },
      );
      return response.data;
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

  /// Get personalized exercise recommendation
  Future<Map<String, dynamic>> getRecommendation() async {
    try {
      final response = await _dio.get('/recommendations/latest');
      return response.data;
    } on DioException catch (e) {
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

  /// Request to disable data sharing with clinicians
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

  /// Re-enable data sharing
  Future<Map<String, dynamic>> enableSharing() async {
    try {
      final response = await _dio.post('/consent/enable');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  // ============ Error Handling ============

  String _handleDioError(DioException e) {
    if (e.response != null) {
      final statusCode = e.response!.statusCode;
      final data = e.response!.data;
      
      if (statusCode == 401) {
        return 'Unauthorized: Please log in again';
      } else if (statusCode == 422) {
        return 'Validation error: ${data['detail']}';
      } else if (statusCode == 500) {
        return 'Server error: Please try again later';
      } else {
        return 'Error: ${data['detail'] ?? 'Unknown error'}';
      }
    } else if (e.type == DioExceptionType.connectionTimeout) {
      return 'Connection timeout: Check your internet connection';
    } else if (e.type == DioExceptionType.receiveTimeout) {
      return 'Request timeout: Server not responding';
    } else {
      return 'Error: ${e.message}';
    }
  }

  // Getter for Dio instance (for testing)
  Dio get dio => _dio;
}
