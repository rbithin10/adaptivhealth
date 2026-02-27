/*
This class talks to the backend server.

It also keeps the login token and sends it with each request.
All screens reuse this one client so everything stays consistent.
*/

import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

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

  static String get baseUrl {
    if (_configuredBaseUrl.isNotEmpty) {
      return _configuredBaseUrl;
    }
    if (kIsWeb) {
      return 'http://localhost:8080/api/v1';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8080/api/v1';
    }
    return 'http://localhost:8080/api/v1';
  }

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

  /// Get list of clinicians (for patient-clinician assignment).
  /// Returns list of users with role=clinician.
  Future<List<Map<String, dynamic>>> getClinicians({int limit = 10}) async {
    try {
      final response = await _dio.get(
        '/users',
        queryParameters: {
          'role': 'clinician',
          'per_page': limit,
          'page': 1,
        },
      );
      // Backend returns {users: [...], total: n, page: 1, per_page: n}
      final List<dynamic> users = response.data['users'] ?? [];
      return users.cast<Map<String, dynamic>>();
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Get the clinician assigned to the current patient.
  /// Returns clinician details (user_id, full_name, email, phone).
  /// Throws 404 if no clinician assigned.
  Future<Map<String, dynamic>?> getAssignedClinician() async {
    try {
      final response = await _dio.get('/users/me/clinician');
      return response.data as Map<String, dynamic>;
    } on DioException catch (e) {
      // 404 means no clinician assigned - return null instead of throwing
      if (e.response?.statusCode == 404) {
        return null;
      }
      throw _handleDioError(e);
    }
  }

  /// Update current user profile.
  /// Sends only non-null fields (partial update).
  Future<Map<String, dynamic>> updateProfile({
    String? fullName,
    int? age,
    String? gender,
    String? phone,
    double? weightKg,
    double? heightCm,
    String? emergencyContactName,
    String? emergencyContactPhone,
  }) async {
    try {
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

      final response = await _dio.put('/users/me', data: data);
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Update medical history (encrypted on server).
  /// Used during onboarding and profile settings.
  Future<Map<String, dynamic>> updateMedicalHistory({
    List<String>? conditions,
    List<String>? medications,
    List<String>? allergies,
    List<String>? surgeries,
    String? notes,
  }) async {
    try {
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
      return response.data is List ? response.data : [];
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Submit a vital reading to backend.
  /// This is used by wearable ingestion paths (real BLE and dev mock stream).
  Future<Map<String, dynamic>> submitVitalSigns({
    required int heartRate,
    int? spo2,
    int? systolicBp,
    int? diastolicBp,
    double? hrv,
    DateTime? timestamp,
  }) async {
    try {
      final payload = <String, dynamic>{
        'heart_rate': heartRate,
        'timestamp': (timestamp ?? DateTime.now()).toIso8601String(),
      };

      if (spo2 != null) payload['spo2'] = spo2;
      if (systolicBp != null) payload['blood_pressure_systolic'] = systolicBp;
      if (diastolicBp != null) payload['blood_pressure_diastolic'] = diastolicBp;
      if (hrv != null) payload['hrv'] = hrv;

      final response = await _dio.post('/vitals', data: payload);
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

  /// Start an exercise session
  Future<Map<String, dynamic>> startSession({
    required String sessionType,
    required int targetDuration,
  }) async {
    try {
      final response = await _dio.post(
        '/activities/start',
        data: {
          'activity_type': sessionType,
          'duration_minutes': targetDuration,
          'start_time': DateTime.now().toIso8601String(),
        },
      );
      final responseData = response.data;
      if (responseData is Map<String, dynamic>) {
        if (responseData['session_id'] == null) {
          throw 'Invalid response from server: missing session_id';
        }
        return responseData;
      }
      throw 'Invalid response from server: expected JSON object';
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
        '/activities/end/$sessionId',
        data: {
          'end_time': DateTime.now().toIso8601String(),
          'avg_heart_rate': avgHeartRate,
          'peak_heart_rate': maxHeartRate,
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

  // ============ Alert Endpoints ============

  /// Get my alerts with pagination and filtering.
  Future<Map<String, dynamic>> getAlerts({
    int page = 1,
    int perPage = 50,
    bool? acknowledged,
    String? severity,
  }) async {
    try {
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

  /// Acknowledge an alert (mark as read).
  Future<Map<String, dynamic>> acknowledgeAlert(int alertId) async {
    try {
      final response = await _dio.patch('/alerts/$alertId/acknowledge');
      return response.data;
    } on DioException catch (e) {
      throw _handleDioError(e);
    }
  }

  /// Resolve an alert with optional notes.
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

  // ============ Natural Language / AI ============

  /// Get patient-friendly risk summary for AI chatbot.
  Future<String> getNLRiskSummary() async {
    try {
      final response = await _dio.get('/nl/risk-summary');
      if (response.data is Map && response.data['nl_summary'] != null) {
        return response.data['nl_summary'] as String;
      }
      return 'Your health status is stable. Keep up your current routine.';
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

  // ============ Nutrition Endpoints ============

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
  Future<Map<String, dynamic>> getRecentNutrition({int limit = 5}) async {
    try {
      final response = await _dio.get(
        '/nutrition/recent',
        queryParameters: {'limit': limit},
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

  /// Send a message to another user
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

  /// Mark a message as read
  Future<Map<String, dynamic>> markMessageRead(int messageId) async {
    try {
      final response = await _dio.post('/messages/$messageId/read');
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
      return 'Error: ${e.message}';
    }
  }

  // Getter for Dio instance (for testing)
  Dio get dio => _dio;
}
