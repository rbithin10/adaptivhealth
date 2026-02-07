/*
This class talks to the backend server.

It also keeps the login token and sends it with each request.
All screens reuse this one client so everything stays consistent.
*/

import 'package:dio/dio.dart';

class ApiClient {
  // Server address. Change this for your own backend.
  static const String baseUrl = 'http://localhost:8000/api/v1';

  // One HTTP client shared by the whole app.
  final Dio _dio;
  
  // Login token saved in memory.
  // Note: This will reset if the app restarts.
  static String? _authToken;

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
          if (error.response?.statusCode == 401) {
            _authToken = null;
            // In a real app, you would redirect to Login here.
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
      
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Register a new user account.
  /// This does not log the user in automatically.
  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    required String name,
    required int age,
    required String gender,
    required String phone,
  }) async {
    try {
      final response = await _dio.post(
        '/register',
        data: {
          'email': email,
          'password': password,
          'name': name,
          'age': age,
          'gender': gender,
          'phone': phone,
        },
      );
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Logout by clearing the local token.
  Future<void> logout() async {
    _authToken = null;
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
