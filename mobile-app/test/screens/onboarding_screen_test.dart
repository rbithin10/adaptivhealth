import 'package:adaptiv_health/screens/onboarding_screen.dart';
import 'package:adaptiv_health/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _MockOnboardingApiClient extends ApiClient {
  _MockOnboardingApiClient();

  @override
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
  }) async {
    return {};
  }

  @override
  Future<Map<String, dynamic>> updateMedicalHistory({
    List<String>? conditions,
    List<String>? medications,
    List<String>? allergies,
    List<String>? surgeries,
    String? notes,
  }) async {
    return {};
  }

  @override
  Future<Map<String, dynamic>> getCurrentUser() async {
    return {'email': 'onboarding@test.com'};
  }
}

void main() {
  testWidgets('renders step 1 and can navigate to step 2', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockOnboardingApiClient();

    await tester.pumpWidget(
      MaterialApp(
        home: OnboardingScreen(
          apiClient: apiClient,
          onComplete: () {},
        ),
      ),
    );

    expect(find.textContaining('Welcome to'), findsOneWidget);

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();

    expect(find.text('Health Profile'), findsOneWidget);
    expect(find.text('Age'), findsOneWidget);
  });

  testWidgets('health profile fields accept input and next step works', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockOnboardingApiClient();

    await tester.pumpWidget(
      MaterialApp(
        home: OnboardingScreen(
          apiClient: apiClient,
          onComplete: () {},
        ),
      ),
    );

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).at(0), '30');
    await tester.enterText(find.byType(TextField).at(1), '70');
    await tester.enterText(find.byType(TextField).at(2), '175');

    await tester.tap(find.text('Next'));
    await tester.pumpAndSettle();

    expect(find.text('Fitness & Rehab'), findsOneWidget);
  });
}
