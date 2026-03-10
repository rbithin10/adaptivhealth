/*
Recipe Library Screen.

Shows heart-healthy recipes that patients can browse and cook. Recipes are
loaded from a local JSON file bundled with the app. Users can filter by
tags like "Heart Healthy", "High Fiber", or "Omega-3 Rich", and log a
meal directly from a recipe.
*/

import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../services/api_client.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../widgets/ai_coach_overlay.dart';

class RecipeLibraryScreen extends StatefulWidget {
  final ApiClient apiClient;

  const RecipeLibraryScreen({super.key, required this.apiClient});

  @override
  State<RecipeLibraryScreen> createState() => _RecipeLibraryScreenState();
}

class _RecipeLibraryScreenState extends State<RecipeLibraryScreen> {
  // Tags the user can filter recipes by
  static const List<String> _availableTags = [
    'Heart Healthy',
    'High Fiber',
    'Omega-3 Rich',
    'Anti-Inflammatory',
  ];

  // Screen state
  bool _isLoading = true;
  String? _errorMessage;
  List<Map<String, dynamic>> _recipes = [];
  String _activeFilter = 'Heart Healthy';
  // Tracks whether a meal was logged so we can refresh the parent screen
  bool _hasLoggedMeal = false;

  // Load recipes from the server when the screen opens
  @override
  void initState() {
    super.initState();
    _loadRecipes();
  }

  // Load recipes from the bundled JSON asset file
  Future<void> _loadRecipes() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final rawJson = await rootBundle.loadString('assets/data/recipes.json');
      final decoded = jsonDecode(rawJson);

      // Support both the legacy array format and the v2 versioned-object format
      final List<dynamic> rawList;
      if (decoded is List) {
        rawList = decoded;
      } else if (decoded is Map && decoded['recipes'] is List) {
        rawList = decoded['recipes'] as List<dynamic>;
      } else {
        throw Exception('Invalid recipes format');
      }

      final recipes = rawList
          .whereType<Map<String, dynamic>>()
          .map((recipe) => Map<String, dynamic>.from(recipe))
          .toList();

      if (!mounted) return;
      setState(() {
        _recipes = recipes;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  // Only show recipes that match the currently selected tag filter
  List<Map<String, dynamic>> get _filteredRecipes {
    return _recipes.where((recipe) {
      final tags = (recipe['tags'] as List<dynamic>?)
              ?.map((tag) => tag.toString())
              .toList() ??
          [];
      return tags.contains(_activeFilter);
    }).toList();
  }

  // Log a recipe as a meal entry in the nutrition tracker
  Future<void> _logRecipeMeal(Map<String, dynamic> recipe) async {
    try {
      await widget.apiClient.createNutritionEntry(
        mealType: (recipe['meal_type'] as String?) ?? 'other',
        calories: _toInt(recipe['calories']),
        description: recipe['name'] as String?,
        proteinGrams: _toInt(recipe['protein']),
        carbsGrams: _toInt(recipe['carbs']),
        fatGrams: _toInt(recipe['fat']),
      );

      if (!mounted) return;
      _hasLoggedMeal = true;
      Navigator.pop(context);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('${recipe['name']} logged successfully'),
        ),
      );
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to log meal: $e'),
          backgroundColor: AdaptivColors.critical,
        ),
      );
    }
  }

  int _toInt(dynamic value) {
    if (value is int) return value;
    if (value is num) return value.round();
    if (value is String) return int.tryParse(value) ?? 0;
    return 0;
  }

  // Main screen layout
  @override
  Widget build(BuildContext context) {
    final brightness = Theme.of(context).brightness;

    return WillPopScope(
      onWillPop: () async {
        Navigator.pop(context, _hasLoggedMeal);
        return false;
      },
      child: AiCoachOverlay(
        apiClient: widget.apiClient,
        child: Scaffold(
          backgroundColor: AdaptivColors.getBackgroundColor(brightness),
          appBar: AppBar(
            leading: IconButton(
              icon: const Icon(Icons.arrow_back),
              onPressed: () {
                Navigator.pop(context, _hasLoggedMeal);
              },
            ),
            title: Text('Recipe Library', style: AdaptivTypography.screenTitle),
            backgroundColor: AdaptivColors.getSurfaceColor(brightness),
            elevation: 0,
          ),
          body: Container(
            decoration: BoxDecoration(
              image: DecorationImage(
                image: const AssetImage('assets/images/health_bg5.png'),
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
            child: _buildBody(),
          ),
        ),
      ),
    );
  }

  // Body content: loading spinner, error message, or recipe list
  Widget _buildBody() {
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 56, color: AdaptivColors.critical),
              const SizedBox(height: 12),
              Text('Unable to load recipes', style: AdaptivTypography.sectionTitle),
              const SizedBox(height: 8),
              Text(_errorMessage!, style: AdaptivTypography.body, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _loadRecipes,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    final recipes = _filteredRecipes;

    return Column(
      children: [
        // Horizontal scrollable row of filter chips
        SizedBox(
          height: 56,
          child: ListView.separated(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            scrollDirection: Axis.horizontal,
            itemBuilder: (context, index) {
              final tag = _availableTags[index];
              return ChoiceChip(
                label: Text(tag),
                selected: _activeFilter == tag,
                onSelected: (_) {
                  setState(() {
                    _activeFilter = tag;
                  });
                },
              );
            },
            separatorBuilder: (_, __) => const SizedBox(width: 8),
            itemCount: _availableTags.length,
          ),
        ),
        Expanded(
          child: recipes.isEmpty
              ? Center(
                  child: Text(
                    'No recipes match this filter yet.',
                    style: AdaptivTypography.body,
                  ),
                )
              : ListView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
                  itemCount: recipes.length,
                  itemBuilder: (context, index) {
                    final recipe = recipes[index];
                    return Card(
                      margin: const EdgeInsets.only(bottom: 12),
                      child: ListTile(
                        title: Text(
                          recipe['name'] as String? ?? 'Recipe',
                          style: AdaptivTypography.cardTitle,
                        ),
                        subtitle: Text(
                          '${recipe['calories']} kcal • ${recipe['protein']}g protein • ${recipe['prep_time_minutes']} min',
                          style: AdaptivTypography.caption,
                        ),
                        trailing: const Icon(Icons.chevron_right),
                        onTap: () => _showRecipeDetailSheet(recipe),
                      ),
                    );
                  },
                ),
        ),
      ],
    );
  }

  // Bottom sheet showing full recipe details and a "Log This Meal" button
  Future<void> _showRecipeDetailSheet(Map<String, dynamic> recipe) async {
    final ingredients = (recipe['ingredients'] as List<dynamic>?)
            ?.map((item) => item.toString())
            .toList() ??
        [];
    final instructions = (recipe['instructions'] as List<dynamic>?)
            ?.map((item) => item.toString())
            .toList() ??
        [];

    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) {
        return SafeArea(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  recipe['name'] as String? ?? 'Recipe Details',
                  style: AdaptivTypography.sectionTitle,
                ),
                const SizedBox(height: 8),
                Text(
                  '${recipe['calories']} kcal • ${recipe['protein']}g protein • ${recipe['carbs']}g carbs • ${recipe['fat']}g fat',
                  style: AdaptivTypography.caption,
                ),
                const SizedBox(height: 16),
                Text('Ingredients', style: AdaptivTypography.cardTitle),
                const SizedBox(height: 6),
                ...ingredients.map((ingredient) => Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text('• $ingredient', style: AdaptivTypography.body),
                    )),
                const SizedBox(height: 12),
                Text('Instructions', style: AdaptivTypography.cardTitle),
                const SizedBox(height: 6),
                ...instructions.asMap().entries.map(
                      (entry) => Padding(
                        padding: const EdgeInsets.only(bottom: 6),
                        child: Text(
                          '${entry.key + 1}. ${entry.value}',
                          style: AdaptivTypography.body,
                        ),
                      ),
                    ),
                const SizedBox(height: 16),
                SizedBox(
                  width: double.infinity,
                  child: ElevatedButton.icon(
                    onPressed: () => _logRecipeMeal(recipe),
                    icon: const Icon(Icons.add_task),
                    label: const Text('Log This Meal'),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
