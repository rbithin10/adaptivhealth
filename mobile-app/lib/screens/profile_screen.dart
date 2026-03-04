/*
Profile screen.

Shows user profile information like name, age, gender, email.
Users can update their profile details and view their account settings.
*/

import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:provider/provider.dart';
import 'package:intl/intl.dart';
import 'dart:async';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../services/edge_ai_store.dart';
import '../services/mock_vitals_service.dart';
import '../services/notification_service.dart';
import '../services/medication_reminder_service.dart';
import '../providers/auth_provider.dart';
import '../screens/onboarding_screen.dart';
import '../screens/device_pairing_screen.dart';

class ProfileScreen extends StatefulWidget {
  final ApiClient apiClient;
  final MockVitalsService? mockVitalsService;
  final VoidCallback? onLogout;  // Called when user logs out

  const ProfileScreen({
    super.key,
    required this.apiClient,
    this.mockVitalsService,
    this.onLogout,
  });

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  Map<String, dynamic>? _userProfile;
  bool _loading = true;
  bool _editing = false;
  String? _error;

  final _formKey = GlobalKey<FormState>();
  late TextEditingController _nameController;
  late TextEditingController _ageController;
  late TextEditingController _phoneController;
  String? _selectedGender;

  // Consent state
  String _shareState = 'SHARING_ON';
  bool _consentLoading = false;

  // DEV demo stream state
  MockVitalsService? _mockVitalsService;
  StreamSubscription<VitalReading>? _mockVitalsSub;
  bool _mockRunning = false;
  bool _mockBusy = false;
  MockScenario _mockMode = MockScenario.rest;
  VitalReading? _lastMockReading;

  // Medication reminders state
  List<Map<String, dynamic>> _medications = [];
  Map<String, dynamic>? _adherenceHistory;
  bool _medicationsLoading = true;
  Map<int, bool> _todayAdherence = {}; // medication_id -> taken status

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _ageController = TextEditingController();
    _phoneController = TextEditingController();
    _loadProfile();
    _loadConsentStatus();
    _loadMedicationReminders();

    if (widget.mockVitalsService != null) {
      _mockVitalsService = widget.mockVitalsService;
      _mockRunning = _mockVitalsService!.isRunning;
      _mockMode = _mockVitalsService!.currentScenario;
      _mockVitalsSub = _mockVitalsService!.stream.listen((reading) {
        if (!mounted) return;
        setState(() {
          _lastMockReading = reading;
          _mockRunning = _mockVitalsService?.isRunning ?? false;
        });
      });
    }
  }

  @override
  void dispose() {
    _mockVitalsSub?.cancel();
    if (widget.mockVitalsService == null) {
      _mockVitalsService?.dispose();
    }
    _nameController.dispose();
    _ageController.dispose();
    _phoneController.dispose();
    super.dispose();
  }

  Future<void> _startMockVitalsStream() async {
    if (_mockBusy || _mockRunning) return;

    setState(() => _mockBusy = true);
    try {
      if (_mockVitalsService == null) {
        final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
        _mockVitalsService = MockVitalsService(
          apiClient: widget.apiClient,
          edgeAiStore: edgeStore,
        );
      }

      await _mockVitalsSub?.cancel();
      _mockVitalsSub = _mockVitalsService!.stream.listen((reading) {
        if (!mounted) return;
        setState(() {
          _lastMockReading = reading;
        });
      });

      await _mockVitalsService!.start(
        interval: const Duration(seconds: 5),
        scenario: _mockMode,
      );

      if (!mounted) return;
      setState(() {
        _mockRunning = true;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Mock vitals stream started (DEV ONLY)'),
          duration: Duration(seconds: 2),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Could not start mock stream: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _mockBusy = false);
      }
    }
  }

  Future<void> _stopMockVitalsStream() async {
    if (_mockBusy || !_mockRunning) return;

    setState(() => _mockBusy = true);
    try {
      _mockVitalsService?.stop();
      await _mockVitalsSub?.cancel();
      _mockVitalsSub = null;

      if (!mounted) return;
      setState(() {
        _mockRunning = false;
      });

      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Mock vitals stream stopped'),
          duration: Duration(seconds: 2),
        ),
      );
    } finally {
      if (mounted) {
        setState(() => _mockBusy = false);
      }
    }
  }

  Future<void> _loadProfile() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final profile = await widget.apiClient.getCurrentUser();
      setState(() {
        _userProfile = profile;
        _nameController.text = profile['full_name'] ?? profile['name'] ?? '';
        _ageController.text = profile['age']?.toString() ?? '';
        _phoneController.text = profile['phone'] ?? '';
        _selectedGender = profile['gender'];
        _loading = false;
      });
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  Future<void> _loadConsentStatus() async {
    try {
      final status = await widget.apiClient.getConsentStatus();
      if (mounted) {
        setState(() {
          _shareState = status['share_state'] ?? 'SHARING_ON';
        });
      }
    } catch (e) {
      if (kDebugMode) debugPrint('Could not load consent status: $e');
    }
  }

  Future<void> _loadMedicationReminders() async {
    try {
      final medications = await widget.apiClient.getMedicationReminders();
      final adherence = await widget.apiClient.getAdherenceHistory(days: 7);
      
      // Build today's adherence map from history
      final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
      final todayMap = <int, bool>{};
      final entries = adherence['entries'] as List? ?? [];
      for (final entry in entries) {
        final dateStr = entry['scheduled_date']?.toString().split('T').first;
        if (dateStr == today && entry['taken'] != null) {
          todayMap[entry['medication_id'] as int] = entry['taken'] as bool;
        }
      }
      
      if (mounted) {
        setState(() {
          _medications = medications;
          _adherenceHistory = adherence;
          _todayAdherence = todayMap;
          _medicationsLoading = false;
        });
      }
    } catch (e) {
      if (kDebugMode) debugPrint('Could not load medication reminders: $e');
      if (mounted) {
        setState(() {
          _medicationsLoading = false;
        });
      }
    }
  }

  Future<void> _updateMedicationReminder(int medId, {String? time, bool? enabled}) async {
    try {
      await widget.apiClient.updateMedicationReminder(medId, time: time, enabled: enabled);
      // Refresh local notifications
      await MedicationReminderService().refreshReminders(widget.apiClient);
      // Reload medications list
      await _loadMedicationReminders();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error updating reminder: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _logMedicationAdherence(int medId, bool taken) async {
    final today = DateFormat('yyyy-MM-dd').format(DateTime.now());
    try {
      await widget.apiClient.logAdherence(medId, today, taken);
      setState(() {
        _todayAdherence[medId] = taken;
      });
      // Refresh adherence history
      final adherence = await widget.apiClient.getAdherenceHistory(days: 7);
      if (mounted) {
        setState(() {
          _adherenceHistory = adherence;
        });
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error logging adherence: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  Future<void> _showTimePicker(Map<String, dynamic> med) async {
    final currentTime = med['reminder_time'] as String? ?? '08:00';
    final parts = currentTime.split(':');
    final initialTime = TimeOfDay(
      hour: int.tryParse(parts[0]) ?? 8,
      minute: int.tryParse(parts.length > 1 ? parts[1] : '0') ?? 0,
    );
    
    final picked = await showTimePicker(
      context: context,
      initialTime: initialTime,
    );
    
    if (picked != null) {
      final timeStr = '${picked.hour.toString().padLeft(2, '0')}:${picked.minute.toString().padLeft(2, '0')}';
      await _updateMedicationReminder(med['medication_id'] as int, time: timeStr);
    }
  }

  Future<void> _toggleSharing() async {
    setState(() => _consentLoading = true);
    try {
      if (_shareState == 'SHARING_ON') {
        await widget.apiClient.requestDisableSharing(reason: 'User toggled off');
        setState(() => _shareState = 'SHARING_DISABLE_REQUESTED');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Disable request submitted. A clinician will review it.'),
              backgroundColor: Colors.orange,
            ),
          );
        }
      } else if (_shareState == 'SHARING_OFF') {
        await widget.apiClient.enableSharing();
        setState(() => _shareState = 'SHARING_ON');
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Data sharing re-enabled.'),
              backgroundColor: Colors.green,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e'), backgroundColor: Colors.red),
        );
      }
    } finally {
      setState(() => _consentLoading = false);
    }
  }

  Future<void> _saveProfile() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _loading = true);

    try {
      await widget.apiClient.updateProfile(
        fullName: _nameController.text.trim(),
        age: _ageController.text.trim().isNotEmpty ? int.parse(_ageController.text.trim()) : null,
        gender: _selectedGender,
        phone: _phoneController.text.trim().isNotEmpty ? _phoneController.text.trim() : null,
      );

      final authProvider = context.read<AuthProvider>();
      await authProvider.refreshProfile();

      if (authProvider.currentUser != null && mounted) {
        setState(() {
          _userProfile = authProvider.currentUser!.raw;
        });
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Profile updated successfully'),
            backgroundColor: Colors.green,
          ),
        );
      }

      await _loadProfile();
      setState(() => _editing = false);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update profile: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      setState(() => _loading = false);
    }
  }

  void _toggleEdit() {
    if (_editing) {
      // Cancel edit
      _nameController.text = _userProfile?['full_name'] ?? _userProfile?['name'] ?? '';
      _ageController.text = _userProfile?['age']?.toString() ?? '';
      _phoneController.text = _userProfile?['phone'] ?? '';
      _selectedGender = _userProfile?['gender'];
    }
    setState(() => _editing = !_editing);
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return Container(
      color: AdaptivColors.getBackgroundColor(brightness),
      child: Column(
        children: [
          // Inline header (replaces AppBar for tab embedding)
          Container(
            color: AdaptivColors.getSurfaceColor(brightness),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Text('Profile', style: AdaptivTypography.screenTitle),
                const Spacer(),
                if (!_loading && _userProfile != null)
                  IconButton(
                    icon: Icon(_editing ? Icons.close : Icons.edit),
                    onPressed: _toggleEdit,
                  ),
              ],
            ),
          ),
          Expanded(
            child: Container(
              decoration: BoxDecoration(
                image: DecorationImage(
                  image: const AssetImage('assets/images/profile_bg.png'),
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
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(24),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(Icons.error_outline, size: 64, color: Colors.red),
                        const SizedBox(height: 16),
                        Text(
                          'Failed to load profile',
                          style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.bold),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _error!,
                          style: AdaptivTypography.caption,
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton(
                          onPressed: _loadProfile,
                          child: const Text('Retry'),
                        ),
                      ],
                    ),
                  ),
                )
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Form(
                    key: _formKey,
                    child: Column(
                      children: [
                        // Avatar
                        Container(
                          width: 100,
                          height: 100,
                          decoration: BoxDecoration(
                            color: AdaptivColors.primary.withOpacity(0.1),
                            shape: BoxShape.circle,
                          ),
                          child: const Icon(
                            Icons.person,
                            size: 50,
                            color: AdaptivColors.primary,
                          ),
                        ),
                        const SizedBox(height: 24),

                        // Email (Read-only)
                        Card(
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: ListTile(
                            leading: const Icon(Icons.email, color: AdaptivColors.primary),
                            title: Text('Email', style: AdaptivTypography.caption),
                            subtitle: Text(
                              _userProfile?['email'] ?? 'Not set',
                              style: AdaptivTypography.body,
                            ),
                          ),
                        ),
                        const SizedBox(height: 12),

                        // Full Name
                        Card(
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: _editing
                              ? Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: TextFormField(
                                    controller: _nameController,
                                    decoration: const InputDecoration(
                                      labelText: 'Full Name',
                                      prefixIcon: Icon(Icons.person_outline),
                                      border: OutlineInputBorder(),
                                    ),
                                    validator: (value) {
                                      if (value == null || value.trim().isEmpty) {
                                        return 'Please enter your full name';
                                      }
                                      return null;
                                    },
                                  ),
                                )
                              : ListTile(
                                  leading: const Icon(Icons.person_outline, color: AdaptivColors.primary),
                                  title: Text('Full Name', style: AdaptivTypography.caption),
                                  subtitle: Text(
                                    _userProfile?['full_name'] ?? _userProfile?['name'] ?? 'Not set',
                                    style: AdaptivTypography.body,
                                  ),
                                ),
                        ),
                        const SizedBox(height: 12),

                        // Age
                        Card(
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: _editing
                              ? Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: TextFormField(
                                    controller: _ageController,
                                    decoration: const InputDecoration(
                                      labelText: 'Age',
                                      prefixIcon: Icon(Icons.cake_outlined),
                                      border: OutlineInputBorder(),
                                    ),
                                    keyboardType: TextInputType.number,
                                    validator: (value) {
                                      if (value != null && value.isNotEmpty) {
                                        final age = int.tryParse(value);
                                        if (age == null || age < 0 || age > 150) {
                                          return 'Please enter a valid age';
                                        }
                                      }
                                      return null;
                                    },
                                  ),
                                )
                              : ListTile(
                                  leading: const Icon(Icons.cake_outlined, color: AdaptivColors.primary),
                                  title: Text('Age', style: AdaptivTypography.caption),
                                  subtitle: Text(
                                    _userProfile?['age']?.toString() ?? 'Not set',
                                    style: AdaptivTypography.body,
                                  ),
                                ),
                        ),
                        const SizedBox(height: 12),

                        // Gender
                        Card(
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: _editing
                              ? Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: DropdownButtonFormField<String>(
                                    value: _selectedGender,
                                    decoration: const InputDecoration(
                                      labelText: 'Gender',
                                      prefixIcon: Icon(Icons.wc),
                                      border: OutlineInputBorder(),
                                    ),
                                    items: const [
                                      DropdownMenuItem(value: 'male', child: Text('Male')),
                                      DropdownMenuItem(value: 'female', child: Text('Female')),
                                      DropdownMenuItem(value: 'other', child: Text('Other')),
                                    ],
                                    onChanged: (value) {
                                      setState(() => _selectedGender = value);
                                    },
                                  ),
                                )
                              : ListTile(
                                  leading: const Icon(Icons.wc, color: AdaptivColors.primary),
                                  title: Text('Gender', style: AdaptivTypography.caption),
                                  subtitle: Text(
                                    _userProfile?['gender'] ?? 'Not set',
                                    style: AdaptivTypography.body,
                                  ),
                                ),
                        ),
                        const SizedBox(height: 12),

                        // Phone
                        Card(
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: _editing
                              ? Padding(
                                  padding: const EdgeInsets.all(16),
                                  child: TextFormField(
                                    controller: _phoneController,
                                    decoration: const InputDecoration(
                                      labelText: 'Phone',
                                      prefixIcon: Icon(Icons.phone_outlined),
                                      border: OutlineInputBorder(),
                                    ),
                                    keyboardType: TextInputType.phone,
                                  ),
                                )
                              : ListTile(
                                  leading: const Icon(Icons.phone_outlined, color: AdaptivColors.primary),
                                  title: Text('Phone', style: AdaptivTypography.caption),
                                  subtitle: Text(
                                    _userProfile?['phone'] ?? 'Not set',
                                    style: AdaptivTypography.body,
                                  ),
                                ),
                        ),
                        const SizedBox(height: 12),

                        // User Role (Read-only)
                        Card(
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: ListTile(
                            leading: const Icon(Icons.badge_outlined, color: AdaptivColors.primary),
                            title: Text('Role', style: AdaptivTypography.caption),
                            subtitle: Text(
                              _userProfile?['user_role'] ?? _userProfile?['role'] ?? 'Patient',
                              style: AdaptivTypography.body,
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),

                        if (_editing) ...[
                          const SizedBox(height: 24),
                          Row(
                            children: [
                              Expanded(
                                child: ElevatedButton(
                                  onPressed: _toggleEdit,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: Colors.grey,
                                    padding: const EdgeInsets.symmetric(vertical: 16),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                  ),
                                  child: const Text('Cancel'),
                                ),
                              ),
                              const SizedBox(width: 12),
                              Expanded(
                                child: ElevatedButton(
                                  onPressed: _saveProfile,
                                  style: ElevatedButton.styleFrom(
                                    backgroundColor: AdaptivColors.primary,
                                    padding: const EdgeInsets.symmetric(vertical: 16),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(8),
                                    ),
                                  ),
                                  child: const Text('Save'),
                                ),
                              ),
                            ],
                          ),
                        ],

                        const SizedBox(height: 24),

                        // Data Sharing Toggle
                        Card(
                          elevation: 2,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Row(
                                      children: [
                                        Icon(
                                          _shareState == 'SHARING_ON' ? Icons.share : Icons.lock_outline,
                                          color: _shareState == 'SHARING_ON' ? AdaptivColors.primary : Colors.orange,
                                        ),
                                        const SizedBox(width: 12),
                                        Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text('Share with Clinic', style: AdaptivTypography.caption),
                                            Text(
                                              _shareState == 'SHARING_ON'
                                                  ? 'Enabled'
                                                  : _shareState == 'SHARING_DISABLE_REQUESTED'
                                                      ? 'Pending approval'
                                                      : 'Disabled',
                                              style: AdaptivTypography.body.copyWith(
                                                color: _shareState == 'SHARING_ON' ? Colors.green : Colors.orange,
                                                fontWeight: FontWeight.w600,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ],
                                    ),
                                    _consentLoading
                                        ? const SizedBox(
                                            width: 24, height: 24,
                                            child: CircularProgressIndicator(strokeWidth: 2),
                                          )
                                        : Switch(
                                            value: _shareState == 'SHARING_ON',
                                            onChanged: _shareState == 'SHARING_DISABLE_REQUESTED'
                                                ? null
                                                : (_) => _toggleSharing(),
                                            activeColor: AdaptivColors.primary,
                                          ),
                                  ],
                                ),
                                if (_shareState == 'SHARING_DISABLE_REQUESTED')
                                  Padding(
                                    padding: const EdgeInsets.only(top: 8),
                                    child: Text(
                                      'Your request to disable sharing is pending clinician approval.',
                                      style: AdaptivTypography.caption.copyWith(color: Colors.orange),
                                    ),
                                  ),
                              ],
                            ),
                          ),
                        ),

                        const SizedBox(height: 24),

                        // Edge AI Model Info section
                        _buildEdgeAiSection(),

                        const SizedBox(height: 16),

                        // DEV mock wearable simulator controls
                        _buildMockVitalsSection(),

                        const SizedBox(height: 16),

                        // DEV onboarding reset
                        _buildDeveloperUtilities(),

                        const SizedBox(height: 24),

                        // Medication Reminders section
                        _buildMedicationRemindersSection(),

                        const SizedBox(height: 32),

                        // Logout button
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: () {
                              showDialog(
                                context: context,
                                builder: (context) => AlertDialog(
                                  title: const Text('Sign Out?'),
                                  content: const Text(
                                    'You will be logged out of your account. You can sign in again later.',
                                  ),
                                  actions: [
                                    TextButton(
                                      onPressed: () => Navigator.pop(context),
                                      child: const Text('Cancel'),
                                    ),
                                    TextButton(
                                      onPressed: () async {
                                        Navigator.pop(context); // close dialog
                                        await widget.apiClient.logout();
                                        // onLogout calls handleLogout in main.dart,
                                        // which sets _isLoggedIn=false and rebuilds
                                        // the entire widget tree to LoginScreen.
                                        widget.onLogout?.call();
                                      },
                                      child: const Text(
                                        'Sign Out',
                                        style: TextStyle(color: AdaptivColors.critical),
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            },
                            style: ElevatedButton.styleFrom(
                              backgroundColor: AdaptivColors.criticalUltralight,
                              foregroundColor: AdaptivColors.critical,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(8),
                                side: const BorderSide(color: AdaptivColors.criticalLight),
                              ),
                            ),
                            icon: const Icon(Icons.logout),
                            label: const Text('Sign Out'),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
            ),
          ),
        ],
      ),
    );
  }

  /// Edge AI model info section — shows model version, status, sync count
  Widget _buildEdgeAiSection() {
    final brightness = Theme.of(context).brightness;
    EdgeAiStore? edgeStore;
    try {
      edgeStore = Provider.of<EdgeAiStore>(context);
    } catch (_) {
      if (kDebugMode) debugPrint('EdgeAiStore provider not available in ProfileScreen');
      return const SizedBox.shrink();
    }

    final modelStatus = edgeStore.modelLoaded
        ? 'Active'
        : edgeStore.isInitializing
            ? 'Loading...'
            : 'Offline';
    final statusColor = edgeStore.modelLoaded ? AdaptivColors.stable : Colors.orange;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AdaptivColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.memory, color: AdaptivColors.primary, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('On-Device AI', style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600)),
                    Text(
                      'Edge ML model for offline risk detection',
                      style: AdaptivTypography.caption.copyWith(color: AdaptivColors.text600),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                decoration: BoxDecoration(
                  color: statusColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Container(
                      width: 6, height: 6,
                      decoration: BoxDecoration(shape: BoxShape.circle, color: statusColor),
                    ),
                    const SizedBox(width: 4),
                    Text(
                      modelStatus,
                      style: AdaptivTypography.caption.copyWith(
                        color: statusColor,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Divider(height: 1),
          const SizedBox(height: 12),
          // Model details
          _buildEdgeInfoRow('Model Version', 'v${edgeStore.modelVersion}'),
          _buildEdgeInfoRow('Inference Engine', 'Pure-Dart Random Forest'),
          _buildEdgeInfoRow('Pending Sync', '${edgeStore.pendingSyncCount} readings'),
          if (edgeStore.latestPrediction != null)
            _buildEdgeInfoRow(
              'Last Inference',
              '${edgeStore.latestPrediction!.inferenceTimeMs}ms',
            ),
          const SizedBox(height: 12),
          // Manual sync button
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: edgeStore.isSyncing
                  ? null
                  : () async {
                      final success = await edgeStore!.syncNow();
                      if (mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(success ? 'Synced successfully' : 'Sync failed — will retry'),
                            duration: const Duration(seconds: 2),
                          ),
                        );
                      }
                    },
              icon: edgeStore.isSyncing
                  ? const SizedBox(
                      width: 16, height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.sync, size: 18),
              label: Text(edgeStore.isSyncing ? 'Syncing...' : 'Sync Now'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AdaptivColors.primary,
                side: const BorderSide(color: AdaptivColors.primary),
                padding: const EdgeInsets.symmetric(vertical: 10),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => DevicePairingScreen(apiClient: widget.apiClient),
                ),
              ),
              icon: const Icon(Icons.bluetooth, size: 18),
              label: const Text('Connect Heart Rate Monitor'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AdaptivColors.primary,
                side: const BorderSide(color: AdaptivColors.primary),
                padding: const EdgeInsets.symmetric(vertical: 10),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () async {
                await NotificationService.instance.showAlert(
                  title: 'Test Notification',
                  body: 'Local notification is working on this device.',
                  payload: 'qa_test_notification',
                );

                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Test notification sent (DEV ONLY).'),
                    duration: Duration(seconds: 2),
                  ),
                );
              },
              icon: const Icon(Icons.notifications_active_outlined, size: 18),
              label: const Text('Send Test Notification (DEV ONLY)'),
              style: OutlinedButton.styleFrom(
                foregroundColor: Colors.deepOrange,
                side: const BorderSide(color: Colors.deepOrange),
                padding: const EdgeInsets.symmetric(vertical: 10),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMockVitalsSection() {
    final brightness = Theme.of(context).brightness;
    final hasEdgeStore = _hasEdgeStore();

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Wearable Simulator (DEV ONLY)',
            style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          Text(
            'Manual demo control. Does not auto-start on app launch.',
            style: AdaptivTypography.caption.copyWith(color: AdaptivColors.getSecondaryTextColor(brightness)),
          ),
          const SizedBox(height: 10),
          if (!hasEdgeStore)
            Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Text(
                'Edge AI provider not initialized yet. Sign in again if Start is disabled.',
                style: AdaptivTypography.caption.copyWith(color: Colors.orange),
              ),
            ),
          DropdownButtonFormField<MockScenario>(
            value: _mockMode,
            isExpanded: true,
            decoration: const InputDecoration(
              labelText: 'Simulation Scenario',
              border: OutlineInputBorder(),
              isDense: true,
            ),
            items: const [
              DropdownMenuItem(
                value: MockScenario.rest,
                child: Text('Rest — HR ~68, SpO₂ 97-99%, high HRV', overflow: TextOverflow.ellipsis),
              ),
              DropdownMenuItem(
                value: MockScenario.workout,
                child: Text('Workout — warmup → peak → cooldown (7 min)', overflow: TextOverflow.ellipsis),
              ),
              DropdownMenuItem(
                value: MockScenario.sleep,
                child: Text('Sleep — NREM/REM cycling, bradycardia', overflow: TextOverflow.ellipsis),
              ),
              DropdownMenuItem(
                value: MockScenario.emergency,
                child: Text('Emergency — critical HR/SpO₂/BP, all alerts fire', overflow: TextOverflow.ellipsis),
              ),
            ],
            onChanged: _mockRunning
                ? null
                : (MockScenario? value) {
                    if (value == null) return;
                    setState(() {
                      _mockMode = value;
                    });
                    _mockVitalsService?.setScenario(value);
                  },
          ),
          const SizedBox(height: 10),
          if (_lastMockReading != null)
            _buildEdgeInfoRow(
              'Last Mock Reading',
              'HR ${_lastMockReading!.heartRate} | SpO₂ ${_lastMockReading!.spo2}% | BP ${_lastMockReading!.bloodPressureSystolic}/${_lastMockReading!.bloodPressureDiastolic} | Phase: ${_lastMockReading!.phase}',
            ),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: (_mockBusy || _mockRunning || !hasEdgeStore)
                      ? null
                      : _startMockVitalsStream,
                  icon: _mockBusy && !_mockRunning
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.play_arrow, size: 18),
                  label: const Text('Start Stream'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton.icon(
                  onPressed: (_mockBusy || !_mockRunning)
                      ? null
                      : _stopMockVitalsStream,
                  icon: _mockBusy && _mockRunning
                      ? const SizedBox(
                          width: 16,
                          height: 16,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.stop, size: 18),
                  label: const Text('Stop Stream'),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AdaptivColors.critical,
                    side: const BorderSide(color: AdaptivColors.critical),
                  ),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildDeveloperUtilities() {
    final brightness = Theme.of(context).brightness;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Developer Utilities (DEV ONLY)',
            style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 6),
          Text(
            'Testing tools. Not shown in production builds.',
            style: AdaptivTypography.caption.copyWith(color: AdaptivColors.text600),
          ),
          const SizedBox(height: 12),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              onPressed: () async {
                // Reset onboarding flag for current user
                try {
                  final userProfile = await widget.apiClient.getCurrentUser();
                  final userEmail = userProfile['email'] as String?;
                  if (userEmail != null) {
                    await clearOnboardingFlag(userEmail);
                  } else {
                    // Fallback: clear all onboarding flags
                    await clearOnboardingFlag();
                  }
                } catch (e) {
                  if (kDebugMode) debugPrint('ERROR: Could not reset onboarding: $e');
                  // Fallback: clear all onboarding flags
                  await clearOnboardingFlag();
                }
                
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('✅ Onboarding reset! You will see it on next login.'),
                    backgroundColor: AdaptivColors.stable,
                  ),
                );
              },
              icon: const Icon(Icons.refresh, size: 18),
              label: const Text('Reset Onboarding'),
              style: OutlinedButton.styleFrom(
                foregroundColor: AdaptivColors.primary,
                side: BorderSide(color: AdaptivColors.primary),
              ),
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Use this to test the onboarding flow again without creating a new account.',
            style: AdaptivTypography.caption.copyWith(
              color: AdaptivColors.text500,
              fontStyle: FontStyle.italic,
            ),
          ),
        ],
      ),
    );
  }

  bool _hasEdgeStore() {
    if (_mockVitalsService != null) {
      return true;
    }
    try {
      Provider.of<EdgeAiStore>(context, listen: false);
      return true;
    } catch (_) {
      if (kDebugMode) {
        debugPrint('EdgeAiStore provider not available in ProfileScreen');
      }
      return false;
    }
  }

  Widget _buildEdgeInfoRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(label, style: AdaptivTypography.caption.copyWith(color: AdaptivColors.text600)),
          Text(value, style: AdaptivTypography.caption.copyWith(fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }

  /// Medication Reminders section with reminder settings and adherence tracking
  Widget _buildMedicationRemindersSection() {
    final brightness = Theme.of(context).brightness;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AdaptivColors.getSurfaceColor(brightness),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AdaptivColors.getBorderColor(brightness)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Section header
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  color: AdaptivColors.primary.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: const Icon(Icons.medication_outlined, color: AdaptivColors.primary, size: 20),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Medication Reminders', style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600)),
                    Text(
                      'Set daily reminders for your medications',
                      style: AdaptivTypography.caption.copyWith(color: AdaptivColors.text600),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // Loading state
          if (_medicationsLoading)
            const Center(child: CircularProgressIndicator())
          
          // Empty state
          else if (_medications.isEmpty)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AdaptivColors.background50,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Row(
                children: [
                  const Icon(Icons.info_outline, color: AdaptivColors.text500, size: 20),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'No medications found. Your clinician can add medications to your profile.',
                      style: AdaptivTypography.caption.copyWith(color: AdaptivColors.text600),
                    ),
                  ),
                ],
              ),
            )
          
          // Medications list
          else ...[
            // Each medication row
            ..._medications.map((med) => _buildMedicationRow(med)),
            
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),

            // Today's medications checklist
            Text(
              "Today's Medications",
              style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            ..._medications.where((m) => m['reminder_enabled'] == true).map((med) {
              final medId = med['medication_id'] as int;
              final drugName = med['drug_name'] as String? ?? 'Medication';
              final dose = med['dose'] as String? ?? '';
              final taken = _todayAdherence[medId];
              
              return CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                title: Text('$drugName${dose.isNotEmpty ? ' $dose' : ''}'),
                value: taken ?? false,
                onChanged: (value) {
                  if (value != null) {
                    _logMedicationAdherence(medId, value);
                  }
                },
                activeColor: AdaptivColors.stable,
                controlAffinity: ListTileControlAffinity.leading,
              );
            }),

            if (_medications.where((m) => m['reminder_enabled'] == true).isEmpty)
              Text(
                'Enable reminders for medications above to track daily adherence.',
                style: AdaptivTypography.caption.copyWith(color: AdaptivColors.text500),
              ),

            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 16),

            // Weekly adherence summary
            Text(
              'This Week',
              style: AdaptivTypography.body.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            _buildAdherenceSummary(),
          ],
        ],
      ),
    );
  }

  Widget _buildMedicationRow(Map<String, dynamic> med) {
    final medId = med['medication_id'] as int;
    final drugName = med['drug_name'] as String? ?? 'Medication';
    final dose = med['dose'] as String? ?? '';
    final reminderTime = med['reminder_time'] as String? ?? '08:00';
    final reminderEnabled = med['reminder_enabled'] as bool? ?? false;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          // Medication name and dose
          Expanded(
            flex: 3,
            child: Text(
              '$drugName${dose.isNotEmpty ? ' $dose' : ''}',
              style: AdaptivTypography.body,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          
          // Time picker
          Expanded(
            flex: 2,
            child: InkWell(
              onTap: () => _showTimePicker(med),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                decoration: BoxDecoration(
                  border: Border.all(color: AdaptivColors.border300),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.access_time, size: 16, color: AdaptivColors.text600),
                    const SizedBox(width: 4),
                    Text(
                      reminderTime,
                      style: AdaptivTypography.caption.copyWith(fontWeight: FontWeight.w500),
                    ),
                  ],
                ),
              ),
            ),
          ),
          
          const SizedBox(width: 8),
          
          // Enable/disable switch
          Switch(
            value: reminderEnabled,
            onChanged: (value) {
              _updateMedicationReminder(medId, enabled: value);
            },
            activeColor: AdaptivColors.primary,
          ),
        ],
      ),
    );
  }

  Widget _buildAdherenceSummary() {
    if (_adherenceHistory == null) {
      return const Text('Loading adherence data...');
    }

    final totalScheduled = _adherenceHistory!['total_scheduled'] as int? ?? 0;
    final totalTaken = _adherenceHistory!['total_taken'] as int? ?? 0;
    final adherencePercent = (_adherenceHistory!['adherence_percent'] as num? ?? 0).toDouble();

    // Color based on percentage
    Color progressColor;
    if (adherencePercent >= 80) {
      progressColor = AdaptivColors.stable;
    } else if (adherencePercent >= 50) {
      progressColor = AdaptivColors.warning;
    } else {
      progressColor = AdaptivColors.critical;
    }

    if (totalScheduled == 0) {
      return Text(
        'Enable reminders for your medications to track adherence.',
        style: AdaptivTypography.caption.copyWith(color: AdaptivColors.text500),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'You took $totalTaken of $totalScheduled scheduled doses (${adherencePercent.toStringAsFixed(0)}%)',
          style: AdaptivTypography.caption,
        ),
        const SizedBox(height: 8),
        LinearProgressIndicator(
          value: adherencePercent / 100,
          backgroundColor: AdaptivColors.border300,
          valueColor: AlwaysStoppedAnimation<Color>(progressColor),
          minHeight: 8,
          borderRadius: BorderRadius.circular(4),
        ),
      ],
    );
  }
}
