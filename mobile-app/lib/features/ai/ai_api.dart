import 'package:dio/dio.dart';

class AiApi {
  final Dio dio;
  AiApi(this.dio);

  // =========================================================================
  // Health Checks
  // =========================================================================

  Future<Map<String, dynamic>> getHealth() async {
    final res = await dio.get('/health');
    return Map<String, dynamic>.from(res.data);
  }

  // =========================================================================
  // Authentication
  // =========================================================================

  Future<Map<String, dynamic>> login(String email, String password) async {
    final formData = FormData.fromMap({
      'username': email,
      'password': password,
    });
    final res = await dio.post(
      '/login',
      data: formData,
      options: Options(
        contentType: 'application/x-www-form-urlencoded',
      ),
    );
    return Map<String, dynamic>.from(res.data);
  }

  // =========================================================================
  // User
  // =========================================================================

  Future<Map<String, dynamic>> getCurrentUser() async {
    final res = await dio.get('/users/me');
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> updateCurrentUserProfile({
    String? fullName,
    int? age,
    String? gender,
    String? phone,
  }) async {
    final Map<String, dynamic> data = {};
    if (fullName != null) data['full_name'] = fullName;
    if (age != null) data['age'] = age;
    if (gender != null) data['gender'] = gender;
    if (phone != null) data['phone'] = phone;

    final res = await dio.put('/users/me', data: data);
    return Map<String, dynamic>.from(res.data);
  }

  // =========================================================================
  // Vital Signs
  // =========================================================================

  Future<Map<String, dynamic>> getLatestVitals() async {
    final res = await dio.get('/vitals/latest');
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> getVitalsHistory({int page = 1, int perPage = 50}) async {
    final res = await dio.get('/vitals/history', queryParameters: {
      'page': page,
      'per_page': perPage,
    });
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> submitVitals({
    required int heartRate,
    double? spo2,
    int? bpSystolic,
    int? bpDiastolic,
    double? hrv,
    String? sourceDevice,
    String? deviceId,
    String? timestamp,
  }) async {
    final Map<String, dynamic> data = {
      'heart_rate': heartRate,
    };
    if (spo2 != null) data['spo2'] = spo2;
    if (bpSystolic != null) data['blood_pressure_systolic'] = bpSystolic;
    if (bpDiastolic != null) data['blood_pressure_diastolic'] = bpDiastolic;
    if (hrv != null) data['hrv'] = hrv;
    if (sourceDevice != null) data['source_device'] = sourceDevice;
    if (deviceId != null) data['device_id'] = deviceId;
    if (timestamp != null) data['timestamp'] = timestamp;

    final res = await dio.post('/vitals', data: data);
    return Map<String, dynamic>.from(res.data);
  }

  // =========================================================================
  // Risk Assessment (AI Core Feature)
  // =========================================================================

  /// Compute risk assessment using latest vitals in DB + store it + create recommendation
  Future<Map<String, dynamic>> computeMyRiskAssessment() async {
    final res = await dio.post('/risk-assessments/compute');
    return Map<String, dynamic>.from(res.data);
  }

  /// Get latest risk assessment for current user
  Future<Map<String, dynamic>> getMyLatestRisk() async {
    final res = await dio.get('/risk-assessments/latest');
    return Map<String, dynamic>.from(res.data);
  }

  /// Predict risk for a workout session with specific metrics
  Future<Map<String, dynamic>> predictRisk({
    required int age,
    required int baselineHr,
    required int maxSafeHr,
    required int avgHeartRate,
    required int peakHeartRate,
    required int minHeartRate,
    required int avgSpo2,
    required int durationMinutes,
    required int recoveryTimeMinutes,
    String activityType = 'walking',
  }) async {
    final res = await dio.post(
      '/predict/risk',
      data: {
        'age': age,
        'baseline_hr': baselineHr,
        'max_safe_hr': maxSafeHr,
        'avg_heart_rate': avgHeartRate,
        'peak_heart_rate': peakHeartRate,
        'min_heart_rate': minHeartRate,
        'avg_spo2': avgSpo2,
        'duration_minutes': durationMinutes,
        'recovery_time_minutes': recoveryTimeMinutes,
        'activity_type': activityType,
      },
    );
    return Map<String, dynamic>.from(res.data);
  }

  // =========================================================================
  // Recommendations
  // =========================================================================

  /// Get latest recommendation for current user
  Future<Map<String, dynamic>> getMyLatestRecommendation() async {
    final res = await dio.get('/recommendations/latest');
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> getRecommendations({int page = 1, int perPage = 50}) async {
    final res = await dio.get('/recommendations', queryParameters: {
      'page': page,
      'per_page': perPage,
    });
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> updateRecommendation(
    int recommendationId, {
    String? status,
    bool? isCompleted,
    String? userFeedback,
  }) async {
    final Map<String, dynamic> data = {};
    if (status != null) data['status'] = status;
    if (isCompleted != null) data['is_completed'] = isCompleted;
    if (userFeedback != null) data['user_feedback'] = userFeedback;

    final res = await dio.patch('/recommendations/$recommendationId', data: data);
    return Map<String, dynamic>.from(res.data);
  }

  // =========================================================================
  // Alerts
  // =========================================================================

  Future<Map<String, dynamic>> getAlerts({int page = 1, int perPage = 50}) async {
    final res = await dio.get('/alerts', queryParameters: {
      'page': page,
      'per_page': perPage,
    });
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> getAlertStats() async {
    final res = await dio.get('/alerts/stats');
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> acknowledgeAlert(int alertId) async {
    final res = await dio.patch('/alerts/$alertId/acknowledge');
    return Map<String, dynamic>.from(res.data);
  }

  // =========================================================================
  // Activities
  // =========================================================================

  Future<Map<String, dynamic>> getActivities({int page = 1, int perPage = 50}) async {
    final res = await dio.get('/activities', queryParameters: {
      'page': page,
      'per_page': perPage,
    });
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> startActivity(String activityType) async {
    final res = await dio.post(
      '/activities/start',
      data: {'activity_type': activityType},
    );
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> endActivity(int sessionId) async {
    final res = await dio.post('/activities/end/$sessionId');
    return Map<String, dynamic>.from(res.data);
  }

  Future<Map<String, dynamic>> updateActivity(
    int sessionId, {
    String? endTime,
    int? avgHeartRate,
    int? peakHeartRate,
    int? minHeartRate,
    int? durationMinutes,
    String? feelingAfter,
    String? userNotes,
    String? status,
  }) async {
    final Map<String, dynamic> data = {};
    if (endTime != null) data['end_time'] = endTime;
    if (avgHeartRate != null) data['avg_heart_rate'] = avgHeartRate;
    if (peakHeartRate != null) data['peak_heart_rate'] = peakHeartRate;
    if (minHeartRate != null) data['min_heart_rate'] = minHeartRate;
    if (durationMinutes != null) data['duration_minutes'] = durationMinutes;
    if (feelingAfter != null) data['feeling_after'] = feelingAfter;
    if (userNotes != null) data['user_notes'] = userNotes;
    if (status != null) data['status'] = status;

    final res = await dio.patch('/activities/$sessionId', data: data);
    return Map<String, dynamic>.from(res.data);
  }
}
