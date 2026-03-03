import 'package:adaptiv_health/screens/login_screen.dart';
import 'package:adaptiv_health/services/api_client.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

class _MockLoginApiClient extends ApiClient {
  _MockLoginApiClient();

  int loginCallCount = 0;

  @override
  Future<Map<String, dynamic>> login(String email, String password) async {
    loginCallCount += 1;
    return {'access_token': 'token'};
  }
}

void main() {
  testWidgets('renders email/password fields and validates empty submit', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockLoginApiClient();
    var loginSuccessCalled = false;

    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          apiClient: apiClient,
          onLoginSuccess: () => loginSuccessCalled = true,
        ),
      ),
    );

    expect(find.text('Email'), findsOneWidget);
    expect(find.text('Password'), findsOneWidget);

    await tester.tap(find.text('Sign In'));
    await tester.pump();

    expect(find.text('Email is required'), findsOneWidget);
    expect(find.text('Password is required'), findsOneWidget);
    expect(apiClient.loginCallCount, 0);
    expect(loginSuccessCalled, isFalse);
  });

  testWidgets('login button triggers API call and success callback', (
    WidgetTester tester,
  ) async {
    final apiClient = _MockLoginApiClient();
    var loginSuccessCalled = false;

    await tester.pumpWidget(
      MaterialApp(
        home: LoginScreen(
          apiClient: apiClient,
          onLoginSuccess: () => loginSuccessCalled = true,
        ),
      ),
    );

    await tester.enterText(find.byType(TextFormField).at(0), 'patient@test.com');
    await tester.enterText(find.byType(TextFormField).at(1), 'password123');

    await tester.tap(find.text('Sign In'));
    await tester.pumpAndSettle();

    expect(apiClient.loginCallCount, 1);
    expect(loginSuccessCalled, isTrue);
  });
}
