/*
Patient onboarding flow.

Shown to new patients after their first login. Collects health profile,
medical background, and emergency contact in a step-by-step wizard.

Steps:
  1. Welcome — 3 swipeable intro cards (what the app does)
  2. Health Profile — age, weight, height
  3. Fitness & Rehab — activity level, exercise limitations, rehab phase
  4. Goals & Wellbeing — primary goal, stress level, sleep quality
  5. Lifestyle Screening — smoking, alcohol, sedentary time, PHQ-2
  6. Medical Background — conditions, medications, allergies
  7. Emergency Contact — name, phone
  8. All Set — summary, navigate to Home

Data is sent to:
  - PUT /api/v1/users/me              (health profile + emergency contact + lifestyle)
  - PUT /api/v1/users/me/medical-history  (conditions, medications, allergies)
*/

// Tools for encoding/decoding JSON data
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
// Custom fonts for a polished look
import 'package:google_fonts/google_fonts.dart';
// Saves small pieces of data on the device (like whether onboarding is done)
import 'package:shared_preferences/shared_preferences.dart';
import '../theme/colors.dart';
import '../services/api_client.dart';

// Storage key prefix — we add the user's email to make it unique per person
const String _kOnboardingCompletePrefix = 'onboarding_complete_';

// Build the full storage key for a specific user's onboarding status
String _getOnboardingKey(String userEmail) {
  return '$_kOnboardingCompletePrefix${userEmail.toLowerCase()}';
}

// Check if this patient has already finished the onboarding wizard
Future<bool> hasCompletedOnboarding(String userEmail) async {
  try {
    final prefs = await SharedPreferences.getInstance();
    final key = _getOnboardingKey(userEmail);
    final completed = prefs.getBool(key) ?? false;
    if (kDebugMode) {
      debugPrint('DEBUG hasCompletedOnboarding: User $userEmail, status = $completed');
    }
    return completed;
  } catch (e) {
    if (kDebugMode) debugPrint('ERROR hasCompletedOnboarding: $e');
    return false;  // Default to showing onboarding if error
  }
}

// Save that this patient has finished onboarding so it won't show again
Future<void> markOnboardingComplete(String userEmail) async {
  if (kDebugMode) {
    debugPrint('DEBUG markOnboardingComplete: Marking onboarding as complete for $userEmail');
  }
  final prefs = await SharedPreferences.getInstance();
  final key = _getOnboardingKey(userEmail);
  await prefs.setBool(key, true);
}

// Reset onboarding so it shows again (useful for testing or account switches)
Future<void> clearOnboardingFlag([String? userEmail]) async {
  if (kDebugMode) {
    debugPrint('DEBUG clearOnboardingFlag: Clearing onboarding flag for ${userEmail ?? "all users"}');
  }
  final prefs = await SharedPreferences.getInstance();
  
  if (userEmail != null) {
    // Clear for specific user
    final key = _getOnboardingKey(userEmail);
    await prefs.remove(key);
  } else {
    // Clear for all users (remove all onboarding keys)
    final keys = prefs.getKeys();
    for (final key in keys) {
      if (key.startsWith(_kOnboardingCompletePrefix)) {
        await prefs.remove(key);
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Onboarding Screen
// ---------------------------------------------------------------------------

// The step-by-step new patient setup wizard
class OnboardingScreen extends StatefulWidget {
  // Connection to the server for saving the patient's profile
  final ApiClient apiClient;
  // Called when the wizard is done so the app moves to the home screen
  final VoidCallback onComplete;

  const OnboardingScreen({
    super.key,
    required this.apiClient,
    required this.onComplete,
  });

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  // Controls which wizard page is shown
  final PageController _pageController = PageController();
  // Which step the patient is currently on (0–7)
  int _currentPage = 0;
  // Total number of steps in the onboarding wizard
  static const int _totalPages = 8;

  // Step 2 — Basic health measurements
  final _ageController = TextEditingController();
  final _weightController = TextEditingController();
  final _heightController = TextEditingController();

  // Step 3 — How active the patient is and any exercise limitations
  String? _activityLevel;
  final List<String> _selectedLimitations = [];
  // Whether the patient is in cardiac rehabilitation
  String _rehabPhase = 'not_in_rehab';

  // Step 4 — What the patient wants to achieve
  String? _primaryGoal;
  // Self-reported stress level (1–10)
  int _stressLevel = 5;
  String? _sleepQuality;

  // Step 5 — Lifestyle habits that affect heart health
  String _smokingStatus = 'never';
  String _alcoholFrequency = 'never';
  // Hours spent sitting each day
  double _sedentaryHours = 4.0;
  // PHQ-2 depression screening scores (0–3 each)
  int _phq2Score1 = 0;
  int _phq2Score2 = 0;

  // Step 6 — Medical conditions, medications, and allergies
  final List<String> _selectedConditions = [];
  final _medicationsController = TextEditingController();
  final _allergiesController = TextEditingController();

  // Step 7 — Emergency contact person
  final _emergencyNameController = TextEditingController();
  final _emergencyPhoneController = TextEditingController();

  // Whether we're currently saving the patient's data to the server
  bool _isSaving = false;

  // List of common heart conditions patients can select from
  static const List<String> _commonConditions = [
    'Hypertension',
    'Heart Failure',
    'Coronary Artery Disease',
    'Atrial Fibrillation',
    'Diabetes',
    'High Cholesterol',
    'Asthma / COPD',
    'Previous Heart Attack',
    'Previous Stroke',
  ];

  @override
  void dispose() {
    _pageController.dispose();
    _ageController.dispose();
    _weightController.dispose();
    _heightController.dispose();
    _medicationsController.dispose();
    _allergiesController.dispose();
    _emergencyNameController.dispose();
    _emergencyPhoneController.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  // Move to the next wizard page with a smooth slide animation
  void _nextPage() {
    if (_currentPage < _totalPages - 1) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeInOut,
      );
    }
  }

  // Go back to the previous wizard page
  void _previousPage() {
    if (_currentPage > 0) {
      _pageController.previousPage(
        duration: const Duration(milliseconds: 350),
        curve: Curves.easeInOut,
      );
    }
  }

  // ---------------------------------------------------------------------------
  // Submit data & finish
  // ---------------------------------------------------------------------------

  // Save all the patient's answers to the server and finish the wizard
  Future<void> _finishOnboarding() async {
    setState(() => _isSaving = true);

    try {
      // 1. Update health profile (age, weight, height)
      final double? weight = double.tryParse(_weightController.text.trim());
      final double? height = double.tryParse(_heightController.text.trim());
      final int? age = int.tryParse(_ageController.text.trim());

      if (weight != null || height != null || age != null) {
        await widget.apiClient.updateProfile(
          weightKg: weight,
          heightCm: height,
          age: age,
        );
      }

      // 2. Update emergency contact
      final emergencyName = _emergencyNameController.text.trim();
      final emergencyPhone = _emergencyPhoneController.text.trim();

      if (emergencyName.isNotEmpty || emergencyPhone.isNotEmpty) {
        await widget.apiClient.updateProfile(
          emergencyContactName: emergencyName.isNotEmpty ? emergencyName : null,
          emergencyContactPhone: emergencyPhone.isNotEmpty ? emergencyPhone : null,
        );
      }

      // 3. Update lifestyle & fitness data
      await widget.apiClient.updateProfile(
        activityLevel: _activityLevel,
        exerciseLimitations: _selectedLimitations.isNotEmpty
            ? jsonEncode(_selectedLimitations)
            : null,
        primaryGoal: _primaryGoal,
        rehabPhase: _rehabPhase,
        stressLevel: _stressLevel,
        sleepQuality: _sleepQuality,
        smokingStatus: _smokingStatus,
        alcoholFrequency: _alcoholFrequency,
        sedentaryHours: _sedentaryHours,
        phq2Score: _phq2Score1 + _phq2Score2,
      );

      // 4. Update medical history (conditions, medications, allergies)
      if (_selectedConditions.isNotEmpty ||
          _medicationsController.text.trim().isNotEmpty ||
          _allergiesController.text.trim().isNotEmpty) {
        final medications = _medicationsController.text
            .trim()
            .split(',')
            .map((s) => s.trim())
            .where((s) => s.isNotEmpty)
            .toList();

        final allergies = _allergiesController.text
            .trim()
            .split(',')
            .map((s) => s.trim())
            .where((s) => s.isNotEmpty)
            .toList();

        await widget.apiClient.updateMedicalHistory(
          conditions: _selectedConditions.isNotEmpty ? _selectedConditions : null,
          medications: medications.isNotEmpty ? medications : null,
          allergies: allergies.isNotEmpty ? allergies : null,
        );
      }

      // 5. Mark complete locally so we don't show again
      // Get user email to save completion status
      try {
        final userProfile = await widget.apiClient.getCurrentUser();
        final userEmail = userProfile['email'] as String?;
        if (userEmail != null) {
          await markOnboardingComplete(userEmail);
        }
      } catch (e) {
        if (kDebugMode) {
          debugPrint('ERROR: Could not save onboarding completion: $e');
        }
      }

      // Done — navigate to Home
      widget.onComplete();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Could not save some data: $e'),
            backgroundColor: AdaptivColors.critical,
            action: SnackBarAction(
              label: 'Skip',
              textColor: AdaptivColors.white,
              onPressed: () async {
                try {
                  final userProfile = await widget.apiClient.getCurrentUser();
                  final userEmail = userProfile['email'] as String?;
                  if (userEmail != null) {
                    await markOnboardingComplete(userEmail);
                  }
                } catch (e) {
                  if (kDebugMode) {
                    debugPrint('ERROR: Could not save onboarding skip: $e');
                  }
                }
                widget.onComplete();
              },
            ),
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    final bgColor = AdaptivColors.getBackgroundColor(brightness);
    final textColor = AdaptivColors.getTextColor(brightness);

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Container(
        decoration: BoxDecoration(
          image: DecorationImage(
            image: const AssetImage('assets/images/splash_bg.png'),
            fit: BoxFit.cover,
            colorFilter: ColorFilter.mode(
              brightness == Brightness.dark
                  ? Colors.black.withOpacity(0.6)
                  : Colors.white.withOpacity(0.85),
              brightness == Brightness.dark
                  ? BlendMode.darken
                  : BlendMode.lighten,
            ),
          ),
        ),
        child: SafeArea(
        child: Column(
          children: [
            // Progress indicator
            _buildProgressBar(brightness),

            // Pages
            Expanded(
              child: PageView(
                controller: _pageController,
                physics: const NeverScrollableScrollPhysics(),
                onPageChanged: (i) => setState(() => _currentPage = i),
                children: [
                  _buildWelcomePage(brightness),
                  _buildHealthProfilePage(brightness),
                  _buildFitnessRehabPage(brightness),
                  _buildGoalsWellbeingPage(brightness),
                  _buildLifestyleScreeningPage(brightness),
                  _buildMedicalBackgroundPage(brightness),
                  _buildEmergencyContactPage(brightness),
                  _buildAllSetPage(brightness),
                ],
              ),
            ),

            // Bottom navigation buttons
            _buildBottomBar(brightness),
          ],
        ),
        ),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Progress bar
  // ---------------------------------------------------------------------------

  // Build the step progress bar at the top showing how far the patient is
  Widget _buildProgressBar(Brightness brightness) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      child: Row(
        children: List.generate(_totalPages, (i) {
          final isActive = i <= _currentPage;
          return Expanded(
            child: Container(
              height: 4,
              margin: EdgeInsets.only(right: i < _totalPages - 1 ? 6 : 0),
              decoration: BoxDecoration(
                color: isActive
                    ? AdaptivColors.getPrimaryColor(brightness)
                    : AdaptivColors.getBorderColor(brightness),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          );
        }),
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 1: Welcome
  // ---------------------------------------------------------------------------

  // Step 1: Welcome page introducing what the app does
  Widget _buildWelcomePage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        children: [
          const SizedBox(height: 32),

          // Logo
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: AdaptivColors.primaryUltralight,
              border: Border.all(
                color: AdaptivColors.getPrimaryColor(brightness),
                width: 3,
              ),
            ),
            child: const Icon(
              Icons.favorite,
              color: AdaptivColors.critical,
              size: 48,
            ),
          ),
          const SizedBox(height: 32),

          Text(
            'Welcome to\nAdaptiv Health',
            textAlign: TextAlign.center,
            style: GoogleFonts.dmSans(
              fontSize: 28,
              fontWeight: FontWeight.w700,
              color: textColor,
              height: 1.2,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'Your personal cardiovascular health companion',
            textAlign: TextAlign.center,
            style: GoogleFonts.dmSans(
              fontSize: 16,
              color: secondaryText,
            ),
          ),
          const SizedBox(height: 48),

          // Feature highlights
          _featureCard(
            icon: Icons.monitor_heart_outlined,
            title: 'Real-time Monitoring',
            description:
                'Track heart rate, blood oxygen, and blood pressure with clinical-grade accuracy.',
            brightness: brightness,
          ),
          const SizedBox(height: 16),
          _featureCard(
            icon: Icons.fitness_center_outlined,
            title: 'Personalised Fitness',
            description:
                'AI-powered workout plans adapted to your cardiac profile and recovery.',
            brightness: brightness,
          ),
          const SizedBox(height: 16),
          _featureCard(
            icon: Icons.shield_outlined,
            title: 'Safety Alerts',
            description:
                'Instant notifications when vital signs exceed safe thresholds.',
            brightness: brightness,
          ),
        ],
      ),
    );
  }

  // A card highlighting one feature of the app (monitoring, fitness, alerts)
  Widget _featureCard({
    required IconData icon,
    required String title,
    required String description,
    required Brightness brightness,
  }) {
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final borderColor = AdaptivColors.getBorderColor(brightness);
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: borderColor),
      ),
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              color: AdaptivColors.primaryUltralight,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Icon(icon, color: AdaptivColors.primary, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: GoogleFonts.dmSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    color: textColor,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  description,
                  style: GoogleFonts.dmSans(
                    fontSize: 13,
                    color: secondaryText,
                    height: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 2: Health Profile
  // ---------------------------------------------------------------------------

  // Step 2: Collect the patient's age, weight, and height
  Widget _buildHealthProfilePage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final borderColor = AdaptivColors.getBorderColor(brightness);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Center(
            child: Icon(Icons.accessibility_new_rounded,
                size: 56, color: AdaptivColors.getPrimaryColor(brightness)),
          ),
          const SizedBox(height: 24),
          Center(
            child: Text(
              'Health Profile',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'Help us personalise your experience.\nAll fields are optional.',
              textAlign: TextAlign.center,
              style: GoogleFonts.dmSans(fontSize: 14, color: secondaryText),
            ),
          ),
          const SizedBox(height: 32),

          // Age
          _fieldLabel('Age', brightness),
          const SizedBox(height: 8),
          _styledTextField(
            controller: _ageController,
            hint: 'e.g. 55',
            icon: Icons.cake_outlined,
            keyboardType: TextInputType.number,
            brightness: brightness,
          ),
          const SizedBox(height: 24),

          // Weight
          _fieldLabel('Weight (kg)', brightness),
          const SizedBox(height: 8),
          _styledTextField(
            controller: _weightController,
            hint: 'e.g. 75',
            icon: Icons.monitor_weight_outlined,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            brightness: brightness,
          ),
          const SizedBox(height: 24),

          // Height
          _fieldLabel('Height (cm)', brightness),
          const SizedBox(height: 8),
          _styledTextField(
            controller: _heightController,
            hint: 'e.g. 170',
            icon: Icons.height_outlined,
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            brightness: brightness,
          ),
          const SizedBox(height: 32),

          // Info card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AdaptivColors.primaryUltralight,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.primaryLight),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline,
                    color: AdaptivColors.primary, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'These measurements help calculate safe heart rate zones during exercise.',
                    style: GoogleFonts.dmSans(
                      fontSize: 13,
                      color: AdaptivColors.primary,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 3: Fitness & Rehab
  // ---------------------------------------------------------------------------

  // Step 3: Ask about fitness level, exercise limitations, and rehab status
  Widget _buildFitnessRehabPage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final borderColor = AdaptivColors.getBorderColor(brightness);

    const activityOptions = <String, _ActivityOption>{
      'none': _ActivityOption(Icons.weekend, 'None', "I'm mostly sedentary"),
      'light': _ActivityOption(
          Icons.directions_walk, 'Light', 'Short walks, light chores'),
      'moderate': _ActivityOption(Icons.directions_run, 'Moderate',
          'Regular walking, some exercise'),
      'active': _ActivityOption(Icons.fitness_center, 'Active',
          'Frequent exercise, physically active'),
    };

    const limitations = [
      'Joint pain',
      'Shortness of breath',
      'Balance issues',
      'Chest pain with exertion',
      'None',
    ];

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Center(
            child: Icon(Icons.directions_run,
                size: 56, color: AdaptivColors.getPrimaryColor(brightness)),
          ),
          const SizedBox(height: 24),
          Center(
            child: Text(
              'Fitness & Rehab',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'Help us understand your current activity level',
              textAlign: TextAlign.center,
              style: GoogleFonts.dmSans(fontSize: 14, color: secondaryText),
            ),
          ),
          const SizedBox(height: 24),

          // Activity Level
          _fieldLabel('Activity Level', brightness),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.35,
            children: activityOptions.entries.map((entry) {
              final selected = _activityLevel == entry.key;
              final opt = entry.value;
              return GestureDetector(
                onTap: () => setState(() => _activityLevel = entry.key),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: selected
                        ? AdaptivColors.primaryUltralight
                        : surfaceColor,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: selected
                          ? AdaptivColors.primary
                          : borderColor,
                      width: selected ? 2 : 1,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(opt.icon,
                          size: 28,
                          color: selected
                              ? AdaptivColors.primary
                              : secondaryText),
                      const SizedBox(height: 6),
                      Text(
                        opt.label,
                        style: GoogleFonts.dmSans(
                          fontSize: 14,
                          fontWeight:
                              selected ? FontWeight.w700 : FontWeight.w500,
                          color: selected ? AdaptivColors.primary : textColor,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        opt.subtitle,
                        textAlign: TextAlign.center,
                        style: GoogleFonts.dmSans(
                          fontSize: 11,
                          color: secondaryText,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 24),

          // Exercise Limitations
          _fieldLabel('Exercise Limitations', brightness),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: limitations.map((lim) {
              final key = lim.toLowerCase().replaceAll(' ', '_');
              final isNone = lim == 'None';
              final selected = isNone
                  ? _selectedLimitations.isEmpty
                  : _selectedLimitations.contains(key);
              return FilterChip(
                label: Text(lim),
                selected: selected,
                selectedColor: AdaptivColors.primaryLight,
                checkmarkColor: AdaptivColors.primary,
                labelStyle: GoogleFonts.dmSans(
                  fontSize: 13,
                  color: selected ? AdaptivColors.primary : textColor,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                  side: BorderSide(
                    color: selected
                        ? AdaptivColors.primary
                        : AdaptivColors.getBorderColor(brightness),
                  ),
                ),
                onSelected: (val) {
                  setState(() {
                    if (isNone) {
                      _selectedLimitations.clear();
                    } else if (val) {
                      _selectedLimitations.add(key);
                    } else {
                      _selectedLimitations.remove(key);
                    }
                  });
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 24),

          // Cardiac Rehab Phase
          _fieldLabel('Cardiac Rehab Phase', brightness),
          const SizedBox(height: 8),
          ...[
            ('phase_2', 'Phase II — supervised outpatient'),
            ('phase_3', 'Phase III — independent maintenance'),
            ('not_in_rehab', 'Not in cardiac rehab'),
          ].map((entry) {
            return RadioListTile<String>(
              value: entry.$1,
              groupValue: _rehabPhase,
              title: Text(
                entry.$2,
                style: GoogleFonts.dmSans(fontSize: 14, color: textColor),
              ),
              activeColor: AdaptivColors.primary,
              contentPadding: EdgeInsets.zero,
              dense: true,
              onChanged: (val) {
                if (val != null) setState(() => _rehabPhase = val);
              },
            );
          }),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 4: Goals & Wellbeing
  // ---------------------------------------------------------------------------

  // Step 4: Ask about health goals, stress, and sleep quality
  Widget _buildGoalsWellbeingPage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final borderColor = AdaptivColors.getBorderColor(brightness);

    const goalOptions = <String, _ActivityOption>{
      'reduce_bp': _ActivityOption(
          Icons.favorite, 'Reduce blood pressure', ''),
      'lose_weight': _ActivityOption(
          Icons.monitor_weight, 'Lose weight', ''),
      'post_surgery_recovery': _ActivityOption(
          Icons.local_hospital, 'Post-surgery recovery', ''),
      'general_heart_health': _ActivityOption(
          Icons.favorite_border, 'General heart health', ''),
    };

    const sleepOptions = ['Good', 'Fair', 'Poor'];

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Center(
            child: Icon(Icons.emoji_events_outlined,
                size: 56, color: AdaptivColors.getPrimaryColor(brightness)),
          ),
          const SizedBox(height: 24),
          Center(
            child: Text(
              'Goals & Wellbeing',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'What matters most to you?',
              textAlign: TextAlign.center,
              style: GoogleFonts.dmSans(fontSize: 14, color: secondaryText),
            ),
          ),
          const SizedBox(height: 24),

          // Primary Goal
          _fieldLabel('Primary Goal', brightness),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.6,
            children: goalOptions.entries.map((entry) {
              final selected = _primaryGoal == entry.key;
              final opt = entry.value;
              return GestureDetector(
                onTap: () => setState(() => _primaryGoal = entry.key),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: selected
                        ? AdaptivColors.primaryUltralight
                        : surfaceColor,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: selected
                          ? AdaptivColors.primary
                          : borderColor,
                      width: selected ? 2 : 1,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(opt.icon,
                          size: 28,
                          color: selected
                              ? AdaptivColors.primary
                              : secondaryText),
                      const SizedBox(height: 6),
                      Text(
                        opt.label,
                        textAlign: TextAlign.center,
                        style: GoogleFonts.dmSans(
                          fontSize: 13,
                          fontWeight:
                              selected ? FontWeight.w700 : FontWeight.w500,
                          color: selected ? AdaptivColors.primary : textColor,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 28),

          // Stress Level
          _fieldLabel('Stress Level', brightness),
          const SizedBox(height: 8),
          Center(
            child: Text(
              '$_stressLevel',
              style: GoogleFonts.dmSans(
                fontSize: 36,
                fontWeight: FontWeight.w700,
                color: AdaptivColors.getPrimaryColor(brightness),
              ),
            ),
          ),
          Row(
            children: [
              Text('Relaxed',
                  style: GoogleFonts.dmSans(
                      fontSize: 12, color: secondaryText)),
              Expanded(
                child: Slider(
                  value: _stressLevel.toDouble(),
                  min: 1,
                  max: 10,
                  divisions: 9,
                  activeColor: AdaptivColors.primary,
                  inactiveColor: AdaptivColors.getBorderColor(brightness),
                  onChanged: (val) =>
                      setState(() => _stressLevel = val.round()),
                ),
              ),
              Text('Very stressed',
                  style: GoogleFonts.dmSans(
                      fontSize: 12, color: secondaryText)),
            ],
          ),
          const SizedBox(height: 24),

          // Sleep Quality
          _fieldLabel('Sleep Quality', brightness),
          const SizedBox(height: 12),
          Row(
            children: sleepOptions.map((opt) {
              final key = opt.toLowerCase();
              final selected = _sleepQuality == key;
              return Expanded(
                child: Padding(
                  padding: EdgeInsets.only(
                      right: opt != sleepOptions.last ? 8 : 0),
                  child: GestureDetector(
                    onTap: () => setState(() => _sleepQuality = key),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 14),
                      decoration: BoxDecoration(
                        color: selected
                            ? AdaptivColors.primaryUltralight
                            : surfaceColor,
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: selected
                              ? AdaptivColors.primary
                              : borderColor,
                          width: selected ? 2 : 1,
                        ),
                      ),
                      child: Center(
                        child: Text(
                          opt,
                          style: GoogleFonts.dmSans(
                            fontSize: 14,
                            fontWeight: selected
                                ? FontWeight.w700
                                : FontWeight.w500,
                            color: selected
                                ? AdaptivColors.primary
                                : textColor,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 5: Lifestyle Screening
  // ---------------------------------------------------------------------------

  // Step 5: Ask about smoking, alcohol, sitting time, and mood check
  Widget _buildLifestyleScreeningPage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final borderColor = AdaptivColors.getBorderColor(brightness);

    const smokingOptions = <String, _ActivityOption>{
      'never': _ActivityOption(Icons.block, 'Never', ''),
      'former': _ActivityOption(Icons.history, 'Former', ''),
      'current': _ActivityOption(Icons.smoking_rooms, 'Current', ''),
    };

    const alcoholOptions = <String, _ActivityOption>{
      'never': _ActivityOption(Icons.no_drinks, 'Never', ''),
      'occasional': _ActivityOption(Icons.local_bar, 'Occasional', ''),
      'moderate': _ActivityOption(Icons.wine_bar, 'Moderate', ''),
      'heavy': _ActivityOption(Icons.warning_amber_outlined, 'Heavy', ''),
    };

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Center(
            child: Icon(Icons.health_and_safety_outlined,
                size: 56, color: AdaptivColors.getPrimaryColor(brightness)),
          ),
          const SizedBox(height: 24),
          Center(
            child: Text(
              'Lifestyle Screening',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'This helps personalize your care recommendations.',
              textAlign: TextAlign.center,
              style: GoogleFonts.dmSans(fontSize: 14, color: secondaryText),
            ),
          ),
          const SizedBox(height: 24),

          _fieldLabel('Smoking Status', brightness),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.1,
            children: smokingOptions.entries.map((entry) {
              final selected = _smokingStatus == entry.key;
              final opt = entry.value;
              return GestureDetector(
                onTap: () => setState(() => _smokingStatus = entry.key),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: selected ? AdaptivColors.primaryUltralight : surfaceColor,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: selected ? AdaptivColors.primary : borderColor,
                      width: selected ? 2 : 1,
                    ),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(opt.icon,
                          size: 26,
                          color: selected ? AdaptivColors.primary : secondaryText),
                      const SizedBox(height: 6),
                      Text(
                        opt.label,
                        style: GoogleFonts.dmSans(
                          fontSize: 13,
                          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                          color: selected ? AdaptivColors.primary : textColor,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 24),

          _fieldLabel('Alcohol Frequency', brightness),
          const SizedBox(height: 12),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.45,
            children: alcoholOptions.entries.map((entry) {
              final selected = _alcoholFrequency == entry.key;
              final opt = entry.value;
              return GestureDetector(
                onTap: () => setState(() => _alcoholFrequency = entry.key),
                child: Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: selected ? AdaptivColors.primaryUltralight : surfaceColor,
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: selected ? AdaptivColors.primary : borderColor,
                      width: selected ? 2 : 1,
                    ),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(opt.icon,
                          size: 20,
                          color: selected ? AdaptivColors.primary : secondaryText),
                      const SizedBox(width: 8),
                      Text(
                        opt.label,
                        style: GoogleFonts.dmSans(
                          fontSize: 13,
                          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                          color: selected ? AdaptivColors.primary : textColor,
                        ),
                      ),
                    ],
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 24),

          _fieldLabel('Sedentary Hours (per day)', brightness),
          const SizedBox(height: 8),
          Center(
            child: Text(
              _sedentaryHours.toStringAsFixed(1),
              style: GoogleFonts.dmSans(
                fontSize: 36,
                fontWeight: FontWeight.w700,
                color: AdaptivColors.getPrimaryColor(brightness),
              ),
            ),
          ),
          Row(
            children: [
              Text('0h', style: GoogleFonts.dmSans(fontSize: 12, color: secondaryText)),
              Expanded(
                child: Slider(
                  value: _sedentaryHours,
                  min: 0,
                  max: 16,
                  divisions: 32,
                  activeColor: AdaptivColors.primary,
                  inactiveColor: AdaptivColors.getBorderColor(brightness),
                  onChanged: (val) => setState(() => _sedentaryHours = val),
                ),
              ),
              Text('16h', style: GoogleFonts.dmSans(fontSize: 12, color: secondaryText)),
            ],
          ),
          const SizedBox(height: 20),

          _fieldLabel('PHQ-2 Mood Check', brightness),
          const SizedBox(height: 10),
          _buildPhq2Question(
            brightness: brightness,
            question:
                'Over the last 2 weeks, how often have you had little interest or pleasure in doing things?',
            value: _phq2Score1,
            onChanged: (value) => setState(() => _phq2Score1 = value),
          ),
          const SizedBox(height: 16),
          _buildPhq2Question(
            brightness: brightness,
            question:
                'Over the last 2 weeks, how often have you been feeling down, depressed, or hopeless?',
            value: _phq2Score2,
            onChanged: (value) => setState(() => _phq2Score2 = value),
          ),
          const SizedBox(height: 8),
        ],
      ),
    );
  }

  // Build a single PHQ-2 question with 4 answer options (mood screening)
  Widget _buildPhq2Question({
    required Brightness brightness,
    required String question,
    required int value,
    required ValueChanged<int> onChanged,
  }) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final borderColor = AdaptivColors.getBorderColor(brightness);

    const options = <(String, int)>[
      ('Not at all', 0),
      ('Several days', 1),
      ('More than half the days', 2),
      ('Nearly every day', 3),
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          question,
          style: GoogleFonts.dmSans(
            fontSize: 13,
            color: textColor,
            fontWeight: FontWeight.w500,
            height: 1.35,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: options.asMap().entries.map((entry) {
            final index = entry.key;
            final (label, score) = entry.value;
            final selected = value == score;

            return Expanded(
              child: GestureDetector(
                onTap: () => onChanged(score),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 10),
                  decoration: BoxDecoration(
                    color: selected ? AdaptivColors.primaryUltralight : surfaceColor,
                    border: Border(
                      top: BorderSide(color: selected ? AdaptivColors.primary : borderColor, width: selected ? 2 : 1),
                      bottom: BorderSide(color: selected ? AdaptivColors.primary : borderColor, width: selected ? 2 : 1),
                      left: BorderSide(color: selected ? AdaptivColors.primary : borderColor, width: selected ? 2 : 1),
                      right: BorderSide(
                        color: selected ? AdaptivColors.primary : borderColor,
                        width: selected ? 2 : (index == options.length - 1 ? 1 : 0),
                      ),
                    ),
                    borderRadius: BorderRadius.only(
                      topLeft: Radius.circular(index == 0 ? 10 : 0),
                      bottomLeft: Radius.circular(index == 0 ? 10 : 0),
                      topRight: Radius.circular(index == options.length - 1 ? 10 : 0),
                      bottomRight: Radius.circular(index == options.length - 1 ? 10 : 0),
                    ),
                  ),
                  child: Column(
                    children: [
                      Text(
                        label,
                        textAlign: TextAlign.center,
                        style: GoogleFonts.dmSans(
                          fontSize: 10,
                          height: 1.2,
                          color: selected ? AdaptivColors.primary : textColor,
                          fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '$score',
                        style: GoogleFonts.dmSans(
                          fontSize: 12,
                          color: selected ? AdaptivColors.primary : textColor,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ],
    );
  }

  // ---------------------------------------------------------------------------
  // Step 6: Medical Background
  // ---------------------------------------------------------------------------

  // Step 6: Collect medical conditions, medications, and allergies
  Widget _buildMedicalBackgroundPage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Center(
            child: Icon(Icons.medical_information_outlined,
                size: 56, color: AdaptivColors.getPrimaryColor(brightness)),
          ),
          const SizedBox(height: 24),
          Center(
            child: Text(
              'Medical Background',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'Select any conditions that apply to you.\nThis helps tailor safety thresholds.',
              textAlign: TextAlign.center,
              style: GoogleFonts.dmSans(fontSize: 14, color: secondaryText),
            ),
          ),
          const SizedBox(height: 24),

          // Condition chips
          _fieldLabel('Conditions', brightness),
          const SizedBox(height: 8),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: _commonConditions.map((c) {
              final selected = _selectedConditions.contains(c);
              return FilterChip(
                label: Text(c),
                selected: selected,
                selectedColor: AdaptivColors.primaryLight,
                checkmarkColor: AdaptivColors.primary,
                labelStyle: GoogleFonts.dmSans(
                  fontSize: 13,
                  color: selected ? AdaptivColors.primary : textColor,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                  side: BorderSide(
                    color: selected
                        ? AdaptivColors.primary
                        : AdaptivColors.getBorderColor(brightness),
                  ),
                ),
                onSelected: (val) {
                  setState(() {
                    if (val) {
                      _selectedConditions.add(c);
                    } else {
                      _selectedConditions.remove(c);
                    }
                  });
                },
              );
            }).toList(),
          ),
          const SizedBox(height: 24),

          // Medications
          _fieldLabel('Current Medications (comma-separated)', brightness),
          const SizedBox(height: 8),
          _styledTextField(
            controller: _medicationsController,
            hint: 'e.g. Lisinopril, Metoprolol',
            icon: Icons.medication_outlined,
            brightness: brightness,
            maxLines: 2,
          ),
          const SizedBox(height: 24),

          // Allergies
          _fieldLabel('Allergies (comma-separated)', brightness),
          const SizedBox(height: 8),
          _styledTextField(
            controller: _allergiesController,
            hint: 'e.g. Penicillin, Aspirin',
            icon: Icons.warning_amber_outlined,
            brightness: brightness,
            maxLines: 2,
          ),
          const SizedBox(height: 24),

          // Privacy note
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AdaptivColors.stableBg,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.stableBorder),
            ),
            child: Row(
              children: [
                const Icon(Icons.lock_outline,
                    color: AdaptivColors.stable, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Your medical data is encrypted and stored in compliance with HIPAA regulations.',
                    style: GoogleFonts.dmSans(
                      fontSize: 13,
                      color: AdaptivColors.stableText,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 6: Emergency Contact
  // ---------------------------------------------------------------------------

  // Step 7: Collect emergency contact name and phone number
  Widget _buildEmergencyContactPage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Center(
            child: Icon(Icons.contact_phone_outlined,
                size: 56, color: AdaptivColors.getPrimaryColor(brightness)),
          ),
          const SizedBox(height: 24),
          Center(
            child: Text(
              'Emergency Contact',
              style: GoogleFonts.dmSans(
                fontSize: 24,
                fontWeight: FontWeight.w700,
                color: textColor,
              ),
            ),
          ),
          const SizedBox(height: 8),
          Center(
            child: Text(
              'Someone we can reach if a critical\nevent is detected.',
              textAlign: TextAlign.center,
              style: GoogleFonts.dmSans(fontSize: 14, color: secondaryText),
            ),
          ),
          const SizedBox(height: 32),

          _fieldLabel('Contact Name', brightness),
          const SizedBox(height: 8),
          _styledTextField(
            controller: _emergencyNameController,
            hint: 'e.g. Jane Doe',
            icon: Icons.person_outline,
            brightness: brightness,
          ),
          const SizedBox(height: 24),

          _fieldLabel('Contact Phone', brightness),
          const SizedBox(height: 8),
          _styledTextField(
            controller: _emergencyPhoneController,
            hint: 'e.g. +61 400 000 000',
            icon: Icons.phone_outlined,
            keyboardType: TextInputType.phone,
            brightness: brightness,
          ),
          const SizedBox(height: 32),

          // Info card
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AdaptivColors.warningBg,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.warningBorder),
            ),
            child: Row(
              children: [
                const Icon(Icons.info_outline,
                    color: AdaptivColors.warning, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'This person may be contacted by your care team in case of a cardiac emergency.',
                    style: GoogleFonts.dmSans(
                      fontSize: 13,
                      color: AdaptivColors.warningText,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Step 7: All Set
  // ---------------------------------------------------------------------------

  // Step 8: Show a summary of everything the patient entered
  Widget _buildAllSetPage(Brightness brightness) {
    final textColor = AdaptivColors.getTextColor(brightness);
    final secondaryText = AdaptivColors.getSecondaryTextColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final borderColor = AdaptivColors.getBorderColor(brightness);

    // Build summary items from what the user entered
    final summary = <_SummaryItem>[];

    if (_ageController.text.trim().isNotEmpty) {
      summary.add(_SummaryItem(Icons.cake_outlined,
          'Age', '${_ageController.text.trim()} years'));
    }
    if (_weightController.text.trim().isNotEmpty) {
      summary.add(_SummaryItem(Icons.monitor_weight_outlined,
          'Weight', '${_weightController.text.trim()} kg'));
    }
    if (_heightController.text.trim().isNotEmpty) {
      summary.add(_SummaryItem(Icons.height_outlined,
          'Height', '${_heightController.text.trim()} cm'));
    }
    if (_activityLevel != null) {
      final label = _activityLevel![0].toUpperCase() +
          _activityLevel!.substring(1);
      summary.add(_SummaryItem(
          Icons.directions_run, 'Activity Level', label));
    }
    if (_rehabPhase != 'not_in_rehab') {
      final label = _rehabPhase == 'phase_2' ? 'Phase II' : 'Phase III';
      summary.add(_SummaryItem(
          Icons.medical_services_outlined, 'Rehab Phase', label));
    }
    if (_primaryGoal != null) {
      final goalLabels = {
        'reduce_bp': 'Reduce BP',
        'lose_weight': 'Lose weight',
        'post_surgery_recovery': 'Post-surgery recovery',
        'general_heart_health': 'General heart health',
      };
      summary.add(_SummaryItem(Icons.emoji_events_outlined,
          'Primary Goal', goalLabels[_primaryGoal] ?? _primaryGoal!));
    }
    if (_selectedConditions.isNotEmpty) {
      summary.add(_SummaryItem(Icons.medical_information_outlined,
          'Conditions', '${_selectedConditions.length} selected'));
    }
    if (_medicationsController.text.trim().isNotEmpty) {
      final count = _medicationsController.text
          .split(',')
          .where((s) => s.trim().isNotEmpty)
          .length;
      summary
          .add(_SummaryItem(Icons.medication_outlined, 'Medications', '$count'));
    }
    if (_emergencyNameController.text.trim().isNotEmpty) {
      summary.add(_SummaryItem(Icons.contact_phone_outlined,
          'Emergency Contact', _emergencyNameController.text.trim()));
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
      child: Column(
        children: [
          const SizedBox(height: 32),

          // Checkmark icon
          Container(
            width: 80,
            height: 80,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              color: AdaptivColors.stableBg,
            ),
            child: const Icon(Icons.check_rounded,
                color: AdaptivColors.stable, size: 48),
          ),
          const SizedBox(height: 24),

          Text(
            "You're All Set!",
            style: GoogleFonts.dmSans(
              fontSize: 24,
              fontWeight: FontWeight.w700,
              color: textColor,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            summary.isEmpty
                ? 'You can update your profile any time\nfrom the Profile tab.'
                : "Here's a summary of what you've shared.",
            textAlign: TextAlign.center,
            style: GoogleFonts.dmSans(fontSize: 14, color: secondaryText),
          ),
          const SizedBox(height: 32),

          // Summary list
          if (summary.isNotEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: surfaceColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: borderColor),
              ),
              child: Column(
                children: summary
                    .map((item) => Padding(
                          padding:
                              const EdgeInsets.symmetric(vertical: 8),
                          child: Row(
                            children: [
                              Icon(item.icon,
                                  size: 20,
                                  color: AdaptivColors.getPrimaryColor(
                                      brightness)),
                              const SizedBox(width: 12),
                              Text(
                                item.label,
                                style: GoogleFonts.dmSans(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w500,
                                  color: secondaryText,
                                ),
                              ),
                              const Spacer(),
                              Text(
                                item.value,
                                style: GoogleFonts.dmSans(
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                  color: textColor,
                                ),
                              ),
                            ],
                          ),
                        ))
                    .toList(),
              ),
            ),

          const SizedBox(height: 24),

          // Tip
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AdaptivColors.primaryUltralight,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AdaptivColors.primaryLight),
            ),
            child: Row(
              children: [
                const Icon(Icons.lightbulb_outline,
                    color: AdaptivColors.primary, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Tip: Connect a wearable device from the Home tab to start live heart rate monitoring.',
                    style: GoogleFonts.dmSans(
                      fontSize: 13,
                      color: AdaptivColors.primary,
                      height: 1.4,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Bottom bar (Back / Next / Finish buttons)
  // ---------------------------------------------------------------------------

  // The Back / Next / Finish buttons at the bottom of each step
  Widget _buildBottomBar(Brightness brightness) {
    final isLastPage = _currentPage == _totalPages - 1;
    final isFirstPage = _currentPage == 0;

    return Container(
      padding: const EdgeInsets.fromLTRB(24, 12, 24, 16),
      child: Row(
        children: [
          // Back button
          if (!isFirstPage)
            TextButton(
              onPressed: _previousPage,
              child: Text(
                'Back',
                style: GoogleFonts.dmSans(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: AdaptivColors.getSecondaryTextColor(brightness),
                ),
              ),
            )
          else
            // Skip — does NOT persist, so onboarding shows again next login
            TextButton(
              onPressed: () {
                widget.onComplete();
              },
              child: Text(
                'Skip',
                style: GoogleFonts.dmSans(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: AdaptivColors.getSecondaryTextColor(brightness),
                ),
              ),
            ),

          const Spacer(),

          // Next / Finish button
          ElevatedButton(
            onPressed: _isSaving
                ? null
                : (isLastPage ? _finishOnboarding : _nextPage),
            style: ElevatedButton.styleFrom(
              backgroundColor: AdaptivColors.getPrimaryColor(brightness),
              foregroundColor: AdaptivColors.white,
              disabledBackgroundColor: AdaptivColors.neutral300,
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isSaving
                ? const SizedBox(
                    width: 20,
                    height: 20,
                    child: CircularProgressIndicator(
                      valueColor:
                          AlwaysStoppedAnimation<Color>(AdaptivColors.white),
                      strokeWidth: 2,
                    ),
                  )
                : Text(
                    isLastPage ? 'Get Started' : 'Next',
                    style: GoogleFonts.dmSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
          ),
        ],
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Shared UI helpers
  // ---------------------------------------------------------------------------

  // A styled label shown above each form field
  Widget _fieldLabel(String text, Brightness brightness) {
    return Text(
      text,
      style: GoogleFonts.dmSans(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: AdaptivColors.getSecondaryTextColor(brightness),
      ),
    );
  }

  // A consistently styled text input box used throughout the wizard
  Widget _styledTextField({
    required TextEditingController controller,
    required String hint,
    required IconData icon,
    required Brightness brightness,
    TextInputType keyboardType = TextInputType.text,
    int maxLines = 1,
  }) {
    final borderColor = AdaptivColors.getBorderColor(brightness);
    final surfaceColor = AdaptivColors.getSurfaceColor(brightness);
    final textColor = AdaptivColors.getTextColor(brightness);

    return TextField(
      controller: controller,
      keyboardType: keyboardType,
      maxLines: maxLines,
      style: GoogleFonts.dmSans(fontSize: 15, color: textColor),
      decoration: InputDecoration(
        hintText: hint,
        prefixIcon: Icon(icon, size: 20),
        filled: true,
        fillColor: surfaceColor,
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: borderColor),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: borderColor),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AdaptivColors.primary, width: 2),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Summary item model (used on final page)
// ---------------------------------------------------------------------------

// Holds one row of the summary shown on the final "All Set" page
class _SummaryItem {
  final IconData icon;
  final String label;
  final String value;
  const _SummaryItem(this.icon, this.label, this.value);
}

// Holds the icon, label, and description for activity level / goal options
class _ActivityOption {
  final IconData icon;
  final String label;
  final String subtitle;
  const _ActivityOption(this.icon, this.label, this.subtitle);
}
