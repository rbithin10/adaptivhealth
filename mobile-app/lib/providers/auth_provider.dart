import 'package:flutter/foundation.dart';

import '../services/api_client.dart';

class User {
  final int? userId;
  final String? email;
  final String? name;
  final int? age;
  final Map<String, dynamic> raw;

  const User({
    required this.raw,
    this.userId,
    this.email,
    this.name,
    this.age,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      raw: json,
      userId: json['user_id'] as int? ?? json['id'] as int?,
      email: json['email'] as String?,
      name: json['name'] as String? ?? json['full_name'] as String?,
      age: json['age'] as int?,
    );
  }
}

class AuthProvider extends ChangeNotifier {
  final ApiClient _apiClient;

  AuthProvider({required ApiClient apiClient}) : _apiClient = apiClient;

  User? currentUser;
  bool isAuthenticated = false;
  String? token;
  bool isLoading = false;
  String? errorMessage;

  Future<bool> login(String email, String password) async {
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.login(email, password);
      token = response['access_token'] as String?;
      isAuthenticated = token != null;
      await refreshProfile();
      return isAuthenticated;
    } catch (e) {
      errorMessage = e.toString();
      return false;
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await _apiClient.logout();
    currentUser = null;
    isAuthenticated = false;
    token = null;
    errorMessage = null;
    notifyListeners();
  }

  Future<void> refreshProfile() async {
    try {
      final profile = await _apiClient.getCurrentUser();
      currentUser = User.fromJson(profile);
      isAuthenticated = true;
      errorMessage = null;
    } catch (e) {
      errorMessage = e.toString();
    }
    notifyListeners();
  }
}
