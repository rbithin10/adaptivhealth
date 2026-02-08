/*
Profile screen.

Shows user profile information like name, age, gender, email.
Users can update their profile details and view their account settings.
*/

import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';

class ProfileScreen extends StatefulWidget {
  final ApiClient apiClient;

  const ProfileScreen({
    super.key,
    required this.apiClient,
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

  @override
  void initState() {
    super.initState();
    _nameController = TextEditingController();
    _ageController = TextEditingController();
    _phoneController = TextEditingController();
    _loadProfile();
    _loadConsentStatus();
  }

  @override
  void dispose() {
    _nameController.dispose();
    _ageController.dispose();
    _phoneController.dispose();
    super.dispose();
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
      debugPrint('Could not load consent status: $e');
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
        fullName: _nameController.text.trim().isNotEmpty ? _nameController.text.trim() : null,
        age: _ageController.text.trim().isNotEmpty ? int.parse(_ageController.text.trim()) : null,
        gender: _selectedGender,
        phone: _phoneController.text.trim().isNotEmpty ? _phoneController.text.trim() : null,
      );

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
    return Scaffold(
      backgroundColor: AdaptivColors.background50,
      appBar: AppBar(
        title: Text('Profile', style: AdaptivTypography.screenTitle),
        backgroundColor: Colors.white,
        elevation: 0,
        automaticallyImplyLeading: false,
        actions: [
          if (!_loading && _userProfile != null)
            IconButton(
              icon: Icon(_editing ? Icons.close : Icons.edit),
              onPressed: _toggleEdit,
            ),
        ],
      ),
      body: _loading
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
                      ],
                    ),
                  ),
                ),
    );
  }
}
