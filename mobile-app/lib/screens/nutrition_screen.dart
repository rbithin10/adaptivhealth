import 'dart:io';

import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../services/api_client.dart';
import 'recipe_library_screen.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';

class NutritionScreen extends StatefulWidget {
  final ApiClient apiClient;

  const NutritionScreen({super.key, required this.apiClient});

  @override
  State<NutritionScreen> createState() => _NutritionScreenState();
}

class _NutritionScreenState extends State<NutritionScreen> {
  bool _isLoading = false;
  bool _isProcessingScan = false;
  String? _errorMessage;
  List<Map<String, dynamic>> _entries = [];
  int _totalCount = 0;
  int _totalCaloriesToday = 0;
  int _totalProteinToday = 0;
  int _totalCarbsToday = 0;
  int _totalFatToday = 0;

  static const int _defaultGoalCalories = 2000; // default goals — personalise when profile available.
  static const int _defaultGoalProteinGrams = 120; // default goals — personalise when profile available.
  static const int _defaultGoalCarbsGrams = 250; // default goals — personalise when profile available.
  static const int _defaultGoalFatGrams = 70; // default goals — personalise when profile available.

  int _goalCalories = _defaultGoalCalories;
  int _goalProteinGrams = _defaultGoalProteinGrams;
  int _goalCarbsGrams = _defaultGoalCarbsGrams;
  int _goalFatGrams = _defaultGoalFatGrams;
  bool _usingDefaultGoals = true;

  @override
  void initState() {
    super.initState();
    _loadPersonalizedGoals();
    _loadNutritionEntries();
  }

  Future<void> _loadPersonalizedGoals() async {
    try {
      final profile = await widget.apiClient.getCurrentUser();

      final age = _toInt(profile['age']);
      final weightKg = _toDouble(profile['weight_kg']);
      final heightCm = _toDouble(profile['height_cm']);
      final gender = (profile['gender'] as String?)?.toLowerCase();
      final activityLevel = (profile['activity_level'] as String?)?.toLowerCase();

      if (age == null || weightKg == null || heightCm == null) {
        return;
      }

      final isMale = gender == 'male';
      final bmr = isMale
          ? (10 * weightKg) + (6.25 * heightCm) - (5 * age) + 5
          : (10 * weightKg) + (6.25 * heightCm) - (5 * age) - 161;

      final multiplier = _activityMultiplier(activityLevel);
      final tdee = bmr * multiplier;
      final calories = tdee.round();

      final protein = (weightKg * 1.6).round();
      final fat = (calories * 0.25 / 9).round();
      final carbs = ((calories - (protein * 4) - (fat * 9)) / 4).round();

      if (!mounted) return;
      setState(() {
        _goalCalories = calories.clamp(1400, 4000);
        _goalProteinGrams = protein.clamp(60, 260);
        _goalFatGrams = fat.clamp(40, 160);
        _goalCarbsGrams = carbs.clamp(80, 500);
        _usingDefaultGoals = false;
      });
    } catch (_) {
      // Keep default goals when profile is unavailable.
    }
  }

  double _activityMultiplier(String? activityLevel) {
    switch (activityLevel) {
      case 'very_active':
        return 1.725;
      case 'active':
        return 1.55;
      case 'lightly_active':
        return 1.375;
      case 'sedentary':
      default:
        return 1.2;
    }
  }

  double? _toDouble(dynamic value) {
    if (value is double) return value;
    if (value is int) return value.toDouble();
    if (value is String) return double.tryParse(value);
    return null;
  }

  /// Load recent nutrition entries from backend
  Future<void> _loadNutritionEntries() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final data = await widget.apiClient.getRecentNutrition(limit: 20);
      final entries = List<Map<String, dynamic>>.from(data['entries'] ?? []);
      final totals = _calculateTodayTotals(entries);
      setState(() {
        _entries = entries;
        _totalCount = data['total_count'] ?? 0;
        _totalCaloriesToday = totals['calories'] ?? 0;
        _totalProteinToday = totals['protein'] ?? 0;
        _totalCarbsToday = totals['carbs'] ?? 0;
        _totalFatToday = totals['fat'] ?? 0;
        _isLoading = false;
      });
    } catch (e) {
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  Map<String, int> _calculateTodayTotals(List<Map<String, dynamic>> entries) {
    final now = DateTime.now();
    final startOfDay = DateTime(now.year, now.month, now.day);
    final endOfDay = startOfDay.add(const Duration(days: 1));

    int calories = 0;
    int protein = 0;
    int carbs = 0;
    int fat = 0;

    for (final entry in entries) {
      final entryTime = _parseEntryTimestamp(entry);
      if (entryTime == null) {
        continue;
      }
      if (entryTime.isBefore(startOfDay) || !entryTime.isBefore(endOfDay)) {
        continue;
      }

      calories += _toInt(entry['calories']);
      protein += _toInt(entry['protein_grams']);
      carbs += _toInt(entry['carbs_grams']);
      fat += _toInt(entry['fat_grams']);
    }

    return {
      'calories': calories,
      'protein': protein,
      'carbs': carbs,
      'fat': fat,
    };
  }

  DateTime? _parseEntryTimestamp(Map<String, dynamic> entry) {
    final raw = entry['timestamp'] ?? entry['created_at'];
    if (raw is String) {
      final parsed = DateTime.tryParse(raw);
      return parsed?.toLocal();
    }
    if (raw is DateTime) {
      return raw.toLocal();
    }
    return null;
  }

  int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.round();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  /// Show dialog to create new nutrition entry
  Future<void> _showAddEntryDialog() async {
    String mealType = 'breakfast';
    final caloriesController = TextEditingController();
    final descriptionController = TextEditingController();
    final proteinController = TextEditingController();
    final carbsController = TextEditingController();
    final fatController = TextEditingController();

    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Log Meal'),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                value: mealType,
                decoration: const InputDecoration(labelText: 'Meal Type'),
                items: const [
                  DropdownMenuItem(value: 'breakfast', child: Text('Breakfast')),
                  DropdownMenuItem(value: 'lunch', child: Text('Lunch')),
                  DropdownMenuItem(value: 'dinner', child: Text('Dinner')),
                  DropdownMenuItem(value: 'snack', child: Text('Snack')),
                  DropdownMenuItem(value: 'other', child: Text('Other')),
                ],
                onChanged: (value) {
                  mealType = value!;
                },
              ),
              const SizedBox(height: 8),
              TextField(
                controller: caloriesController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Calories *',
                  hintText: 'e.g., 350',
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: descriptionController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Description (optional)',
                  hintText: 'e.g., Oatmeal with berries',
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: proteinController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Protein (g)',
                        hintText: 'g',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: carbsController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Carbs (g)',
                        hintText: 'g',
                      ),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: fatController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(
                        labelText: 'Fat (g)',
                        hintText: 'g',
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final calories = int.tryParse(caloriesController.text);
              if (calories == null || calories <= 0) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Please enter valid calories')),
                );
                return;
              }

              try {
                await widget.apiClient.createNutritionEntry(
                  mealType: mealType,
                  calories: calories,
                  description: descriptionController.text.isEmpty
                      ? null
                      : descriptionController.text,
                  proteinGrams: int.tryParse(proteinController.text),
                  carbsGrams: int.tryParse(carbsController.text),
                  fatGrams: int.tryParse(fatController.text),
                );
                if (context.mounted) {
                  Navigator.pop(context, true);
                }
              } catch (e) {
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('Error: $e'),
                      backgroundColor: Colors.red,
                    ),
                  );
                }
              }
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );

    if (result == true) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Meal logged successfully!')),
      );
      _loadNutritionEntries();
    }
  }

  /// Delete nutrition entry
  Future<void> _deleteEntry(int entryId) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Entry'),
        content: const Text('Are you sure you want to delete this entry?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            child: const Text('Delete'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      await widget.apiClient.deleteNutritionEntry(entryId);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Entry deleted')),
      );
      _loadNutritionEntries();
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _scanFoodFromCamera() async {
    if (_isProcessingScan) return;

    final picker = ImagePicker();
    final photo = await picker.pickImage(source: ImageSource.camera, imageQuality: 85);
    if (photo == null) {
      return;
    }

    setState(() {
      _isProcessingScan = true;
    });

    try {
      final response = await widget.apiClient.analyzeFoodImage(File(photo.path));
      if (!mounted) return;

      final payload = _extractDetectedNutrition(
        response,
        fallbackDescription: 'Scanned meal',
      );
      final logged = await _showNutritionConfirmationDialog(
        title: 'Review Scanned Food',
        initialData: payload,
      );

      if (logged == true) {
        _loadNutritionEntries();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Food scan failed: $e'),
          backgroundColor: AdaptivColors.critical,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isProcessingScan = false;
        });
      }
    }
  }

  Future<void> _scanFoodByBarcode() async {
    if (_isProcessingScan) return;

    final barcode = await Navigator.push<String>(
      context,
      MaterialPageRoute(
        builder: (context) => const MobileScannerWidget(),
      ),
    );

    if (barcode == null || barcode.isEmpty) {
      return;
    }

    setState(() {
      _isProcessingScan = true;
    });

    try {
      final response = await widget.apiClient.lookupBarcode(barcode);
      if (!mounted) return;

      final payload = _extractDetectedNutrition(
        response,
        fallbackDescription: 'Barcode item: $barcode',
      );
      final logged = await _showNutritionConfirmationDialog(
        title: 'Review Barcode Result',
        initialData: payload,
      );

      if (logged == true) {
        _loadNutritionEntries();
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Barcode lookup failed: $e'),
          backgroundColor: AdaptivColors.critical,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isProcessingScan = false;
        });
      }
    }
  }

  Map<String, dynamic> _extractDetectedNutrition(
    Map<String, dynamic> raw, {
    required String fallbackDescription,
  }) {
    final nutrition = raw['nutrition'] is Map<String, dynamic>
        ? Map<String, dynamic>.from(raw['nutrition'] as Map<String, dynamic>)
        : raw['nutrition_data'] is Map<String, dynamic>
            ? Map<String, dynamic>.from(raw['nutrition_data'] as Map<String, dynamic>)
            : raw['detected_nutrition'] is Map<String, dynamic>
                ? Map<String, dynamic>.from(raw['detected_nutrition'] as Map<String, dynamic>)
                : raw;

    return {
      'meal_type': (raw['meal_type'] ?? nutrition['meal_type'] ?? 'other').toString(),
      'description': (raw['food_name'] ??
              raw['name'] ??
              raw['description'] ??
              nutrition['food_name'] ??
              nutrition['name'] ??
              fallbackDescription)
          .toString(),
      'calories': _toInt(
        raw['calories'] ?? nutrition['calories'] ?? nutrition['calories_kcal'] ?? nutrition['energy_kcal'],
      ),
      'protein_grams': _toInt(
        raw['protein_grams'] ?? nutrition['protein_grams'] ?? nutrition['protein'],
      ),
      'carbs_grams': _toInt(
        raw['carbs_grams'] ?? nutrition['carbs_grams'] ?? nutrition['carbs'] ?? nutrition['carbohydrates'],
      ),
      'fat_grams': _toInt(
        raw['fat_grams'] ?? nutrition['fat_grams'] ?? nutrition['fat'],
      ),
    };
  }

  Future<bool?> _showNutritionConfirmationDialog({
    required String title,
    required Map<String, dynamic> initialData,
  }) async {
    String mealType = initialData['meal_type']?.toString() ?? 'other';
    if (!['breakfast', 'lunch', 'dinner', 'snack', 'other'].contains(mealType)) {
      mealType = 'other';
    }

    final caloriesController = TextEditingController(
      text: initialData['calories'].toString(),
    );
    final descriptionController = TextEditingController(
      text: initialData['description']?.toString() ?? '',
    );
    final proteinController = TextEditingController(
      text: initialData['protein_grams'].toString(),
    );
    final carbsController = TextEditingController(
      text: initialData['carbs_grams'].toString(),
    );
    final fatController = TextEditingController(
      text: initialData['fat_grams'].toString(),
    );

    final result = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(title),
        content: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              DropdownButtonFormField<String>(
                value: mealType,
                decoration: const InputDecoration(labelText: 'Meal Type'),
                items: const [
                  DropdownMenuItem(value: 'breakfast', child: Text('Breakfast')),
                  DropdownMenuItem(value: 'lunch', child: Text('Lunch')),
                  DropdownMenuItem(value: 'dinner', child: Text('Dinner')),
                  DropdownMenuItem(value: 'snack', child: Text('Snack')),
                  DropdownMenuItem(value: 'other', child: Text('Other')),
                ],
                onChanged: (value) {
                  mealType = value ?? 'other';
                },
              ),
              const SizedBox(height: 8),
              TextField(
                controller: descriptionController,
                maxLines: 2,
                decoration: const InputDecoration(
                  labelText: 'Description',
                ),
              ),
              const SizedBox(height: 8),
              TextField(
                controller: caloriesController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Calories *',
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: proteinController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Protein (g)'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: carbsController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Carbs (g)'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: TextField(
                      controller: fatController,
                      keyboardType: TextInputType.number,
                      decoration: const InputDecoration(labelText: 'Fat (g)'),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text('Cancel'),
          ),
          ElevatedButton(
            onPressed: () async {
              final calories = int.tryParse(caloriesController.text);
              if (calories == null || calories <= 0) {
                ScaffoldMessenger.of(dialogContext).showSnackBar(
                  const SnackBar(content: Text('Please enter valid calories')),
                );
                return;
              }

              try {
                await widget.apiClient.createNutritionEntry(
                  mealType: mealType,
                  calories: calories,
                  description: descriptionController.text.trim().isEmpty
                      ? null
                      : descriptionController.text.trim(),
                  proteinGrams: int.tryParse(proteinController.text),
                  carbsGrams: int.tryParse(carbsController.text),
                  fatGrams: int.tryParse(fatController.text),
                );

                if (dialogContext.mounted) {
                  Navigator.pop(dialogContext, true);
                }
              } catch (e) {
                if (dialogContext.mounted) {
                  ScaffoldMessenger.of(dialogContext).showSnackBar(
                    SnackBar(
                      content: Text('Error: $e'),
                      backgroundColor: AdaptivColors.critical,
                    ),
                  );
                }
              }
            },
            child: const Text('Log'),
          ),
        ],
      ),
    );

    if (result == true && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Meal logged successfully!')),
      );
    }
    return result;
  }

  Widget _buildNutritionActionRow() {
    return Row(
      children: [
        Expanded(
          child: _buildNutritionActionButton(
            label: 'Scan Food',
            icon: Icons.camera_alt,
            onTap: _scanFoodFromCamera,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _buildNutritionActionButton(
            label: 'Scan Barcode',
            icon: Icons.qr_code_scanner,
            onTap: _scanFoodByBarcode,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _buildNutritionActionButton(
            label: 'Recipes',
            icon: Icons.menu_book,
            onTap: () async {
              final loggedMeal = await Navigator.push<bool>(
                context,
                MaterialPageRoute(
                  builder: (context) => RecipeLibraryScreen(apiClient: widget.apiClient),
                ),
              );
              if (loggedMeal == true) {
                _loadNutritionEntries();
              }
            },
          ),
        ),
      ],
    );
  }

  Widget _buildNutritionActionButton({
    required String label,
    required IconData icon,
    required VoidCallback onTap,
  }) {
    return OutlinedButton.icon(
      onPressed: _isProcessingScan ? null : onTap,
      icon: Icon(icon, size: 18),
      label: Text(
        label,
        style: AdaptivTypography.caption.copyWith(fontWeight: FontWeight.w600),
      ),
      style: OutlinedButton.styleFrom(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;
    return Container(
      decoration: BoxDecoration(
        image: DecorationImage(
          image: const AssetImage('assets/images/health_bg2.png'),
          fit: BoxFit.cover,
          colorFilter: ColorFilter.mode(
            brightness == Brightness.dark
                ? Colors.black.withOpacity(0.6)
                : Colors.white.withOpacity(0.85),
            brightness == Brightness.dark ? BlendMode.darken : BlendMode.lighten,
          ),
        ),
      ),
      child: Stack(
        children: [
          Column(
            children: [
              // Inline header (replaces AppBar for tab embedding)
              Container(
                color: AdaptivColors.getSurfaceColor(brightness),
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
                child: Row(
                  children: [
                    Text('Nutrition', style: AdaptivTypography.screenTitle),
                    const Spacer(),
                    if (_totalCount > 0)
                      Text(
                        '$_totalCount ${_totalCount == 1 ? 'entry' : 'entries'}',
                        style: AdaptivTypography.caption,
                      ),
                  ],
                ),
              ),
              Expanded(child: _buildBody()),
            ],
          ),
          Positioned(
            right: 16,
            bottom: 16,
            child: FloatingActionButton.extended(
              onPressed: _showAddEntryDialog,
              icon: const Icon(Icons.add),
              label: const Text('Log Meal'),
              backgroundColor: AdaptivColors.primary,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(),
      );
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(
                Icons.error_outline,
                size: 64,
                color: AdaptivColors.critical,
              ),
              const SizedBox(height: 16),
              Text(
                'Could not load nutrition data',
                style: AdaptivTypography.sectionTitle,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                _errorMessage!,
                style: AdaptivTypography.body,
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              ElevatedButton.icon(
                onPressed: _loadNutritionEntries,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadNutritionEntries,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildNutritionActionRow(),
          if (_isProcessingScan) ...[
            const SizedBox(height: 8),
            const LinearProgressIndicator(),
          ],
          const SizedBox(height: 16),
          _buildDailyGoalsCard(),
          const SizedBox(height: 16),
          if (_entries.isEmpty)
            _buildEmptyEntriesState()
          else
            ..._entries.map(_buildNutritionCard).toList(),
        ],
      ),
    );
  }

  Widget _buildDailyGoalsCard() {
    final progress = (_totalCaloriesToday / _goalCalories).clamp(0.0, 1.0);

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Daily Nutrition Goals', style: AdaptivTypography.sectionTitle),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: _usingDefaultGoals
                      ? AdaptivColors.warning.withOpacity(0.15)
                      : AdaptivColors.stable.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  _usingDefaultGoals ? 'Using default goals' : 'Personalized goals',
                  style: AdaptivTypography.caption.copyWith(
                    color: _usingDefaultGoals
                        ? AdaptivColors.warning
                        : AdaptivColors.stable,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Expanded(child: _buildGoalItem('Calories', '$_totalCaloriesToday / $_goalCalories kcal')),
                Expanded(child: _buildGoalItem('Protein', '$_totalProteinToday / ${_goalProteinGrams}g')),
                Expanded(child: _buildGoalItem('Carbs', '$_totalCarbsToday / ${_goalCarbsGrams}g')),
                Expanded(child: _buildGoalItem('Fat', '$_totalFatToday / ${_goalFatGrams}g')),
              ],
            ),
            const SizedBox(height: 12),
            LinearProgressIndicator(
              value: progress,
              backgroundColor: AdaptivColors.bg200,
              valueColor: AlwaysStoppedAnimation(AdaptivColors.primary),
              minHeight: 10,
            ),
            const SizedBox(height: 8),
            Text(
              '${_totalCaloriesToday} / ${_goalCalories} kcal consumed today',
              style: AdaptivTypography.caption,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGoalItem(String label, String value) {
    return Column(
      children: [
        Text(
          value,
          style: AdaptivTypography.metricValue,
          textAlign: TextAlign.center,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
        ),
        Text(label, style: AdaptivTypography.caption),
      ],
    );
  }

  Widget _buildEmptyEntriesState() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 32),
      child: Column(
        children: [
          const Icon(
            Icons.restaurant_menu,
            size: 64,
            color: AdaptivColors.text500,
          ),
          const SizedBox(height: 16),
          Text(
            'No nutrition entries yet',
            style: AdaptivTypography.sectionTitle,
          ),
          const SizedBox(height: 8),
          Text(
            'Tap "Log Meal" below to start tracking your nutrition',
            style: AdaptivTypography.body,
            textAlign: TextAlign.center,
          ),
        ],
      ),
    );
  }

  Widget _buildNutritionCard(Map<String, dynamic> entry) {
    final entryId = entry['entry_id'] as int;
    final mealType = entry['meal_type'] as String;
    final description = entry['description'] as String?;
    final calories = entry['calories'] as int;
    final proteinGrams = entry['protein_grams'] as int?;
    final carbsGrams = entry['carbs_grams'] as int?;
    final fatGrams = entry['fat_grams'] as int?;
    final timestamp = DateTime.parse(entry['timestamp'] as String);

    // Format timestamp
    final now = DateTime.now();
    final difference = now.difference(timestamp);
    String timeAgo;
    if (difference.inDays > 0) {
      timeAgo = '${difference.inDays}d ago';
    } else if (difference.inHours > 0) {
      timeAgo = '${difference.inHours}h ago';
    } else if (difference.inMinutes > 0) {
      timeAgo = '${difference.inMinutes}m ago';
    } else {
      timeAgo = 'Just now';
    }

    IconData icon;
    Color iconColor;
    switch (mealType) {
      case 'breakfast':
        icon = Icons.breakfast_dining;
        iconColor = AdaptivColors.warning;
        break;
      case 'lunch':
        icon = Icons.lunch_dining;
        iconColor = AdaptivColors.primary;
        break;
      case 'dinner':
        icon = Icons.dinner_dining;
        iconColor = AdaptivColors.critical;
        break;
      case 'snack':
        icon = Icons.emoji_food_beverage;
        iconColor = AdaptivColors.stable;
        break;
      default:
        icon = Icons.restaurant;
        iconColor = AdaptivColors.text500;
    }

    // Build macros text
    final macros = <String>[];
    if (proteinGrams != null) macros.add('${proteinGrams}g protein');
    if (carbsGrams != null) macros.add('${carbsGrams}g carbs');
    if (fatGrams != null) macros.add('${fatGrams}g fat');
    final macrosText = macros.isEmpty ? null : macros.join(' • ');

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Dismissible(
        key: Key('nutrition_$entryId'),
        direction: DismissDirection.endToStart,
        background: Container(
          color: Colors.red,
          alignment: Alignment.centerRight,
          padding: const EdgeInsets.only(right: 16),
          child: const Icon(Icons.delete, color: Colors.white),
        ),
        confirmDismiss: (direction) async {
          return await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Delete Entry'),
              content: const Text('Are you sure you want to delete this entry?'),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Cancel'),
                ),
                TextButton(
                  onPressed: () => Navigator.pop(context, true),
                  style: TextButton.styleFrom(foregroundColor: Colors.red),
                  child: const Text('Delete'),
                ),
              ],
            ),
          );
        },
        onDismissed: (direction) {
          widget.apiClient.deleteNutritionEntry(entryId).then((_) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Entry deleted')),
            );
            _loadNutritionEntries();
          }).catchError((error) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text('Error: $error'),
                backgroundColor: Colors.red,
              ),
            );
            _loadNutritionEntries();
          });
        },
        child: ListTile(
          leading: CircleAvatar(
            backgroundColor: iconColor.withOpacity(0.2),
            child: Icon(icon, color: iconColor),
          ),
          title: Row(
            children: [
              Text(
                _capitalize(mealType),
                style: AdaptivTypography.cardTitle,
              ),
              const SizedBox(width: 8),
              Text(
                '• $timeAgo',
                style: AdaptivTypography.caption,
              ),
            ],
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (description != null && description.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(description, style: AdaptivTypography.body),
              ],
              if (macrosText != null) ...[
                const SizedBox(height: 4),
                Text(macrosText, style: AdaptivTypography.caption),
              ],
            ],
          ),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '$calories',
                style: AdaptivTypography.metricValue.copyWith(fontSize: 20),
              ),
              Text('kcal', style: AdaptivTypography.caption),
            ],
          ),
          onLongPress: () => _deleteEntry(entryId),
        ),
      ),
    );
  }

  String _capitalize(String text) {
    if (text.isEmpty) return text;
    return text[0].toUpperCase() + text.substring(1);
  }
}

class MobileScannerWidget extends StatefulWidget {
  const MobileScannerWidget({super.key});

  @override
  State<MobileScannerWidget> createState() => _MobileScannerWidgetState();
}

class _MobileScannerWidgetState extends State<MobileScannerWidget> {
  final MobileScannerController _scannerController = MobileScannerController();
  bool _didDetectBarcode = false;

  @override
  void dispose() {
    _scannerController.dispose();
    super.dispose();
  }

  void _handleBarcodeCapture(BarcodeCapture capture) {
    if (_didDetectBarcode) {
      return;
    }

    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue;
      if (value != null && value.isNotEmpty) {
        _didDetectBarcode = true;
        Navigator.pop(context, value);
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Scan Barcode'),
      ),
      body: Stack(
        children: [
          MobileScanner(
            controller: _scannerController,
            onDetect: _handleBarcodeCapture,
          ),
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              color: Colors.black54,
              child: const Text(
                'Align barcode within the camera frame',
                textAlign: TextAlign.center,
                style: TextStyle(color: Colors.white),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
