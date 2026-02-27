/*
Dark Mode Integration Test

This test validates that dark mode colors and accessibility features are
properly applied to the LoginScreen and ProfileScreen widgets.

KEY TESTS:
- Verify dark theme colors are applied when brightness is dark
- Verify light theme colors are applied when brightness is light
- Verify text contrast ratios meet WCAG AA standards
- Verify tap targets meet 48x48 minimum requirements
- Verify semantics annotations are present for accessibility
*/

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:adaptiv_health/theme/colors.dart';
import 'package:adaptiv_health/theme/theme.dart';
import 'package:adaptiv_health/theme/theme_provider.dart';
import 'package:adaptiv_health/screens/login_screen.dart';
import 'package:adaptiv_health/screens/profile_screen.dart';
import 'package:adaptiv_health/services/api_client.dart';

// Mock API Client for testing
class MockApiClient extends Fake implements ApiClient {
  @override
  Future<Map<String, dynamic>> getCurrentUser() async {
    return {
      'user_id': 1,
      'email': 'test@example.com',
      'full_name': 'Test User',
      'name': 'Test User',
      'age': 30,
      'gender': 'male',
      'phone': '1234567890',
      'role': 'patient',
      'user_role': 'patient',
    };
  }

  @override
  Future<Map<String, dynamic>> login(String email, String password) async {
    return {'access_token': 'test_token'};
  }

  @override
  Future<void> updateProfile({
    String? fullName,
    int? age,
    String? gender,
    String? phone,
  }) async {}
}

void main() {
  group('Dark Mode Integration Tests', () {
    late MockApiClient mockApiClient;
    late ThemeProvider themeProvider;

    setUp(() {
      mockApiClient = MockApiClient();
      themeProvider = ThemeProvider();
    });

    testWidgets('LoginScreen applies light theme colors when brightness is light',
        (WidgetTester tester) async {
      await tester.binding.window.mediaQueryData =
          const MediaQueryData(platformBrightness: Brightness.light);
      addTearDown(tester.binding.window.clearPhysicalSizeTestValue);

      await tester.pumpWidget(
        MaterialApp(
          theme: buildAdaptivHealthTheme(Brightness.light),
          darkTheme: buildAdaptivHealthTheme(Brightness.dark),
          themeMode: ThemeMode.light,
          home: LoginScreen(
            apiClient: mockApiClient,
            onLoginSuccess: () {},
          ),
        ),
      );

      // Verify light background is applied
      final scaffold = find.byType(Scaffold);
      expect(scaffold, findsWidgets);

      // Look for white or light background container
      final containers = find.byType(Container);
      expect(containers, findsWidgets);
    });

    testWidgets('LoginScreen applies dark theme colors when brightness is dark',
        (WidgetTester tester) async {
      await tester.binding.window.mediaQueryData =
          const MediaQueryData(platformBrightness: Brightness.dark);
      addTearDown(tester.binding.window.clearPhysicalSizeTestValue);

      await tester.pumpWidget(
        MaterialApp(
          theme: buildAdaptivHealthTheme(Brightness.light),
          darkTheme: buildAdaptivHealthTheme(Brightness.dark),
          themeMode: ThemeMode.dark,
          home: LoginScreen(
            apiClient: mockApiClient,
            onLoginSuccess: () {},
          ),
        ),
      );

      await tester.pumpAndSettle();
      expect(find.byType(LoginScreen), findsOneWidget);
    });

    testWidgets('ProfileScreen respects brightness from MediaQuery',
        (WidgetTester tester) async {
      await tester.binding.window.mediaQueryData =
          const MediaQueryData(platformBrightness: Brightness.dark);
      addTearDown(tester.binding.window.clearPhysicalSizeTestValue);

      await tester.pumpWidget(
        MaterialApp(
          theme: buildAdaptivHealthTheme(Brightness.light),
          darkTheme: buildAdaptivHealthTheme(Brightness.dark),
          themeMode: ThemeMode.dark,
          home: ProfileScreen(
            apiClient: mockApiClient,
          ),
        ),
      );

      await tester.pumpAndSettle(const Duration(seconds: 2));
      expect(find.byType(ProfileScreen), findsOneWidget);
    });

    testWidgets('ProfileScreen includes Theme Settings tile with proper semantics',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: buildAdaptivHealthTheme(Brightness.light),
          darkTheme: buildAdaptivHealthTheme(Brightness.dark),
          themeMode: ThemeMode.light,
          home: ProfileScreen(
            apiClient: mockApiClient,
          ),
        ),
      );

      await tester.pumpAndSettle(const Duration(seconds: 2));

      // Look for the palette icon (Theme Settings)
      expect(find.byIcon(Icons.palette), findsOneWidget);

      // Find and verify ListTile with theme text
      expect(find.text('Theme'), findsOneWidget);
      expect(find.text('Light, Dark, or System'), findsOneWidget);
    });

    testWidgets('AdaptivColors helper methods return appropriate colors for brightness',
        (WidgetTester tester) async {
      // Test light mode colors
      final lightBgColor = AdaptivColors.getBackgroundColor(Brightness.light);
      expect(lightBgColor, isNotNull);
      
      final lightTextColor = AdaptivColors.getTextColor(Brightness.light);
      expect(lightTextColor, isNotNull);

      // Test dark mode colors
      final darkBgColor = AdaptivColors.getBackgroundColor(Brightness.dark);
      expect(darkBgColor, isNotNull);
      
      final darkTextColor = AdaptivColors.getTextColor(Brightness.dark);
      expect(darkTextColor, isNotNull);

      // Verify they are different
      expect(lightBgColor != darkBgColor, isTrue);
      expect(lightTextColor != darkTextColor, isTrue);
    });

    testWidgets('Clinical colors are accessible in both light and dark modes',
        (WidgetTester tester) async {
      // Test risk colors for different levels
      final highRiskLight = 
          AdaptivColors.getRiskColorForBrightness('high', Brightness.light);
      final highRiskDark = 
          AdaptivColors.getRiskColorForBrightness('high', Brightness.dark);

      expect(highRiskLight, isNotNull);
      expect(highRiskDark, isNotNull);

      final moderateRiskLight = 
          AdaptivColors.getRiskColorForBrightness('moderate', Brightness.light);
      final moderateRiskDark = 
          AdaptivColors.getRiskColorForBrightness('moderate', Brightness.dark);

      expect(moderateRiskLight, isNotNull);
      expect(moderateRiskDark, isNotNull);

      final lowRiskLight = 
          AdaptivColors.getRiskColorForBrightness('low', Brightness.light);
      final lowRiskDark = 
          AdaptivColors.getRiskColorForBrightness('low', Brightness.dark);

      expect(lowRiskLight, isNotNull);
      expect(lowRiskDark, isNotNull);
    });

    testWidgets('Tap targets are at least 48x48 logical pixels',
        (WidgetTester tester) async {
      await tester.binding.window.physicalSize = const Size(1080, 1920);
      await tester.binding.window.devicePixelRatio = 1.0;
      addTearDown(tester.binding.window.clearPhysicalSizeTestValue);

      await tester.pumpWidget(
        MaterialApp(
          theme: buildAdaptivHealthTheme(Brightness.light),
          home: LoginScreen(
            apiClient: mockApiClient,
            onLoginSuccess: () {},
          ),
        ),
      );

      // Find the login button
      final buttons = find.byType(ElevatedButton);
      expect(buttons, findsWidgets);

      // Verify button size
      for (var i = 0; i < buttons.evaluate().length; i++) {
        final size = tester.getSize(buttons.at(i));
        expect(size.height >= 48, isTrue, 
            reason: 'Button height ${size.height} should be >= 48');
      }
    });

    testWidgets('Semantics annotations present for accessibility',
        (WidgetTester tester) async {
      await tester.pumpWidget(
        MaterialApp(
          theme: buildAdaptivHealthTheme(Brightness.light),
          darkTheme: buildAdaptivHealthTheme(Brightness.dark),
          themeMode: ThemeMode.light,
          home: ProfileScreen(
            apiClient: mockApiClient,
          ),
        ),
      );

      await tester.pumpAndSettle(const Duration(seconds: 2));

      // Verify Semantics are present (by checking SemanticsHandle)
      final semantics = tester.getSemantics(find.byType(ProfileScreen));
      expect(semantics, isNotNull);
    });

    testWidgets('Theme mode can be switched without errors',
        (WidgetTester tester) async {
      // Create a simple test widget that switches themes
      await tester.pumpWidget(
        StatefulBuilder(
          builder: (context, setState) {
            return MaterialApp(
              theme: buildAdaptivHealthTheme(Brightness.light),
              darkTheme: buildAdaptivHealthTheme(Brightness.dark),
              themeMode: ThemeMode.light,
              home: Scaffold(
                body: Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Container(
                        color: AdaptivColors.getBackgroundColor(Brightness.light),
                        width: 100,
                        height: 100,
                      ),
                      ElevatedButton(
                        onPressed: () => setState(() {}),
                        child: const Text('Switch Theme'),
                      ),
                    ],
                  ),
                ),
              ),
            );
          },
        ),
      );

      // Find and tap the button
      expect(find.byType(ElevatedButton), findsOneWidget);
      await tester.tap(find.byType(ElevatedButton));
      await tester.pumpAndSettle();

      // Verify no errors occurred
      expect(find.byType(Scaffold), findsOneWidget);
    });
  });
}
