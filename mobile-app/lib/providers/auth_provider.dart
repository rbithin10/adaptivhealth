/*
Authentication Provider.

Manages the user's login state for the whole app.
Handles signing in, signing out, and loading the user's profile.
All screens can check this to know if someone is logged in.
*/

// Lets us notify the UI whenever login state changes
import 'package:flutter/foundation.dart';

// Our helper that talks to the backend server
import '../services/api_client.dart';

// Represents the logged-in user's basic info
class User {
  final int? userId;       // The user's unique ID number from the server
  final String? email;     // The user's email address
  final String? name;      // The user's display name
  final int? age;          // The user's age (used for health calculations)
  final Map<String, dynamic> raw; // The full server response, in case we need extra fields

  const User({
    required this.raw,
    this.userId,
    this.email,
    this.name,
    this.age,
  });

  // Build a User object from the JSON data the server sends back
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      raw: json,
      // The server sometimes calls it 'user_id', sometimes 'id' — we handle both
      userId: json['user_id'] as int? ?? json['id'] as int?,
      email: json['email'] as String?,
      // Same thing for name — could be 'name' or 'full_name' depending on the endpoint
      name: json['name'] as String? ?? json['full_name'] as String?,
      age: json['age'] as int?,
    );
  }
}

// This class keeps track of whether the user is logged in, and who they are.
// Any screen can listen to it and automatically update when login state changes.
class AuthProvider extends ChangeNotifier {
  // The API helper we use to talk to the server
  final ApiClient _apiClient;

  AuthProvider({required ApiClient apiClient}) : _apiClient = apiClient;

  User? currentUser;              // The currently logged-in user (null if nobody is logged in)
  bool isAuthenticated = false;   // True when we have a valid login session
  String? token;                  // The login token the server gave us (proves we're logged in)
  bool isLoading = false;         // True while we're waiting for the server to respond
  String? errorMessage;           // Holds any error message to show the user

  // Try to log in with the given email and password
  Future<bool> login(String email, String password) async {
    // Show a loading spinner while we wait
    isLoading = true;
    errorMessage = null;
    notifyListeners(); // Tell all screens to refresh (they'll show a spinner)

    try {
      // Send the email and password to the server
      final response = await _apiClient.login(email, password);
      // Pull the login token out of the server's response
      token = response['access_token'] as String?;
      // If we got a token, we're logged in
      isAuthenticated = token != null;
      // Now fetch the full user profile (name, age, etc.)
      await refreshProfile();
      return isAuthenticated;
    } catch (e) {
      // Something went wrong — save the error so the login screen can display it
      errorMessage = e.toString();
      return false;
    } finally {
      // Whether it worked or not, stop showing the loading spinner
      isLoading = false;
      notifyListeners(); // Tell all screens to refresh
    }
  }

  // Log the user out and clear all their data from memory
  Future<void> logout() async {
    // Tell the server to end this session
    await _apiClient.logout();
    // Clear everything locally so the app goes back to the login screen
    currentUser = null;
    isAuthenticated = false;
    token = null;
    errorMessage = null;
    notifyListeners(); // Tell all screens to refresh (they'll show the login screen)
  }

  // Fetch the latest user profile from the server
  Future<void> refreshProfile() async {
    try {
      // Ask the server "who am I?" using our stored token
      final profile = await _apiClient.getCurrentUser();
      // Turn the server's response into a User object we can use
      currentUser = User.fromJson(profile);
      isAuthenticated = true;
      errorMessage = null;
    } catch (e) {
      // If it fails, save the error (maybe the token expired)
      errorMessage = e.toString();
    }
    notifyListeners(); // Tell all screens to refresh with the new profile data
  }
}
