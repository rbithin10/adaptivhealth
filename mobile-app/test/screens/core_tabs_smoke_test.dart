import 'package:adaptiv_health/providers/chat_provider.dart';
import 'package:adaptiv_health/screens/doctor_messaging_screen.dart';
import 'package:adaptiv_health/screens/nutrition_screen.dart';
import 'package:adaptiv_health/screens/workout_screen.dart';
import 'package:adaptiv_health/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

class _MockCoreTabsApiClient extends ApiClient {
  _MockCoreTabsApiClient();

  @override
  Future<Map<String, dynamic>> getCurrentUser() async {
    return {
      'user_id': 1,
      'age': 34,
      'weight_kg': 70,
      'height_cm': 172,
      'gender': 'male',
      'activity_level': 'active',
    };
  }

  @override
  Future<Map<String, dynamic>> getRecentNutrition({int limit = 5}) async {
    return {
      'entries': <Map<String, dynamic>>[],
      'total_count': 0,
    };
  }

  @override
  Future<Map<String, dynamic>?> getAssignedClinician() async {
    return {
      'user_id': 2,
      'full_name': 'Dr. Test Clinician',
    };
  }

  @override
  Future<List<Map<String, dynamic>>> getMessageThread(
    int clinicianId, {
    int limit = 50,
  }) async {
    return <Map<String, dynamic>>[];
  }

  @override
  Future<Map<String, dynamic>> markMessageRead(int messageId) async {
    return {'ok': true};
  }
}

void main() {
  testWidgets('Workout screen smoke test renders key content', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockCoreTabsApiClient();

    await tester.pumpWidget(
      MaterialApp(
        home: WorkoutScreen(apiClient: apiClient),
      ),
    );

    await tester.pump(const Duration(milliseconds: 200));

    expect(find.text('Workout'), findsOneWidget);
    expect(find.text('How are you feeling?'), findsOneWidget);
  });

  testWidgets('Nutrition screen smoke test renders key content', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockCoreTabsApiClient();

    await tester.pumpWidget(
      MaterialApp(
        home: NutritionScreen(apiClient: apiClient),
      ),
    );

    await tester.pump(const Duration(milliseconds: 250));

    expect(find.text('Nutrition'), findsOneWidget);
    expect(find.text('Daily Nutrition Goals'), findsOneWidget);
  });

  testWidgets('Messaging screen smoke test renders key content', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockCoreTabsApiClient();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          ChangeNotifierProvider<ChatProvider>(
            create: (_) => ChatProvider(apiClient: apiClient),
          ),
        ],
        child: MaterialApp(
          home: DoctorMessagingScreen(apiClient: apiClient),
        ),
      ),
    );

    await tester.pump(const Duration(milliseconds: 350));

    expect(find.text('Messages'), findsOneWidget);
    expect(find.text('No messages yet'), findsOneWidget);
  });
}
