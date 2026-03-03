import 'package:adaptiv_health/screens/home_screen.dart';
import 'package:adaptiv_health/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _MockHomeApiClient extends ApiClient {
  _MockHomeApiClient();

  @override
  Future<Map<String, dynamic>> getCurrentUser() async {
    return {
      'name': 'Test User',
      'age': 42,
      'resting_hr': 72,
    };
  }

  @override
  Future<Map<String, dynamic>> getLatestVitals() async {
    return {
      'heart_rate': 78,
      'spo2': 98,
      'systolic_bp': 120,
      'diastolic_bp': 80,
      'timestamp': DateTime.now().toIso8601String(),
    };
  }

  @override
  Future<Map<String, dynamic>> getLatestRiskAssessment() async {
    return {
      'risk_level': 'low',
      'risk_score': 0.2,
    };
  }

  @override
  Future<Map<String, dynamic>> getLatestRecommendation() async {
    return {
      'title': 'Stay hydrated',
      'description': 'Drink water regularly today.',
      'confidence_score': 0.9,
    };
  }

  @override
  Future<List<dynamic>> getActivities({
    int limit = 20,
    int offset = 0,
  }) async {
    return [];
  }

  @override
  Future<List<dynamic>> getVitalHistory({
    int days = 7,
    int limit = 100,
  }) async {
    return [];
  }
}

class _EmptyHomeApiClient extends _MockHomeApiClient {
  @override
  Future<Map<String, dynamic>> getLatestVitals() async {
    return {
      'heart_rate': 0,
      'spo2': 0,
      'systolic_bp': 0,
      'diastolic_bp': 0,
      'timestamp': DateTime.now().toIso8601String(),
    };
  }
}

void main() {
  testWidgets('renders HomeScreen without crash and shows core sections', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockHomeApiClient();

    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          apiClient: apiClient,
          onLogout: () {},
        ),
      ),
    );

    await tester.pump();

    expect(find.text('Adaptiv Health'), findsOneWidget);
    expect(find.text('Recommended For You'), findsOneWidget);
  });

  testWidgets('handles empty vitals data state', (WidgetTester tester) async {
    final apiClient = _EmptyHomeApiClient();

    await tester.pumpWidget(
      MaterialApp(
        home: HomeScreen(
          apiClient: apiClient,
          onLogout: () {},
        ),
      ),
    );

    await tester.pump();

    expect(find.text('Adaptiv Health'), findsOneWidget);
    expect(find.byType(Scaffold), findsOneWidget);
  });
}
