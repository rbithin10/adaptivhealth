import 'package:flutter/material.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';

class NutritionScreen extends StatefulWidget {
  final ApiClient apiClient;

  const NutritionScreen({super.key, required this.apiClient});

  @override
  State<NutritionScreen> createState() => _NutritionScreenState();
}

class _NutritionScreenState extends State<NutritionScreen> {
  bool _isLoading = false;
  String? _errorMessage;
  List<Map<String, dynamic>> _entries = [];
  int _totalCount = 0;
  int _totalCaloriesToday = 0;
  int _totalProteinToday = 0;
  int _totalCarbsToday = 0;
  int _totalFatToday = 0;

  static const int _goalCalories = 2000;
  static const int _goalProteinGrams = 120;
  static const int _goalCarbsGrams = 250;
  static const int _goalFatGrams = 70;

  @override
  void initState() {
    super.initState();
    _loadNutritionEntries();
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

  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    return Scaffold(
      backgroundColor: AdaptivColors.getBackgroundColor(brightness),
      appBar: AppBar(
        backgroundColor: AdaptivColors.getSurfaceColor(brightness),
        elevation: 0,
        title: Text('Nutrition', style: AdaptivTypography.screenTitle),
        actions: [
          if (_totalCount > 0)
            Center(
              child: Padding(
                padding: const EdgeInsets.only(right: 16),
                child: Text(
                  '$_totalCount ${_totalCount == 1 ? 'entry' : 'entries'}',
                  style: AdaptivTypography.caption,
                ),
              ),
            ),
        ],
      ),
      body: _buildBody(),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _showAddEntryDialog,
        icon: const Icon(Icons.add),
        label: const Text('Log Meal'),
        backgroundColor: AdaptivColors.primary,
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
            const SizedBox(height: 12),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                _buildGoalItem('Calories', '${_totalCaloriesToday} / ${_goalCalories} kcal'),
                _buildGoalItem('Protein', '${_totalProteinToday} / ${_goalProteinGrams}g'),
                _buildGoalItem('Carbs', '${_totalCarbsToday} / ${_goalCarbsGrams}g'),
                _buildGoalItem('Fat', '${_totalFatToday} / ${_goalFatGrams}g'),
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
        Text(value, style: AdaptivTypography.metricValue),
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
