# Visual Studio Copilot AI - Complete Project Refactor Prompt
## For Adaptiv Health Flutter App - Production Grade

---

## 🎯 PROJECT REFACTOR REQUEST

I am working on a **Flutter cardiac rehabilitation monitoring app called "Adaptiv Health"** that currently has code organization and structure issues. I need you to help me refactor the entire project to be **production-ready, enterprise-grade, and presentable to stakeholders**.

**Current State:** Code is scattered, some files are unused, navigation is confusing, and there are logic redundancies.

**Goal:** Clean, organized, professional project structure with clear navigation, consistent patterns, and no technical debt.

---

## 📋 PART 1: PROJECT AUDIT & ANALYSIS

First, I need you to analyze the current project structure and create an audit report.

### Analyze My Project:

```
Project Location: C:\Users\hp\Desktop\AdpativHealth\mobile-app

Please scan the entire project and provide:

1. FILE INVENTORY
   - List all .dart files currently in the project
   - Identify unused files (dead code)
   - Identify duplicate functionality
   - Identify incomplete/stub files
   - Identify files that are improperly organized

2. FOLDER STRUCTURE AUDIT
   - Current folder structure
   - Which folders are correctly organized
   - Which folders need reorganization
   - Identify missing logical groupings
   - Identify unclear naming conventions

3. CODE QUALITY ISSUES
   - Identify logic redundancies (same logic in multiple places)
   - Identify overly complex solutions that should be simplified
   - Identify missing error handling
   - Identify inconsistent naming conventions
   - Identify missing documentation/comments
   - Identify unused imports
   - Identify state management inconsistencies

4. SYNCHRONIZATION ISSUES
   - Identify files that reference non-existent files
   - Identify model mismatches between screens and services
   - Identify navigation routing issues
   - Identify API integration inconsistencies
   - Identify provider/state management conflicts

5. GENERATE A REFACTOR ROADMAP
   - Priority list of changes needed
   - Estimated effort for each change
   - Dependencies between changes
   - Suggested order of implementation

Output this as a structured JSON report I can reference.
```

---

## 📋 PART 2: NEW PROJECT STRUCTURE

Once analyzed, refactor the project to this **professional enterprise structure**:

```
RECOMMENDED FOLDER STRUCTURE:

adaptiv_health/
├── lib/
│   ├── main.dart                              # App entry point with theme & navigation setup
│   ├── config/                                # Configuration files
│   │   ├── README.md                         # 📍 Navigation guide for /config folder
│   │   ├── app_config.dart                   # App constants, API endpoints, configuration
│   │   ├── app_theme.dart                    # Material Design 3 theme, colors, typography
│   │   └── app_routes.dart                   # Named routes and route management
│   │
│   ├── data/                                  # Data layer (models, API, local storage)
│   │   ├── README.md                         # 📍 Navigation guide for /data folder
│   │   ├── models/                           # Data models
│   │   │   ├── user_model.dart              # User/Patient data structure
│   │   │   ├── vital_signs_model.dart       # Heart rate, SpO2, BP, HRV
│   │   │   ├── activity_session_model.dart  # Workout session data
│   │   │   ├── recommendation_model.dart    # Fitness recommendations
│   │   │   ├── meal_model.dart              # Nutrition data
│   │   │   ├── message_model.dart           # Doctor/clinician messages
│   │   │   ├── alert_model.dart             # Health alerts
│   │   │   └── clinician_model.dart         # Care team members
│   │   │
│   │   ├── repositories/                     # Data access layer (abstraction)
│   │   │   ├── vital_signs_repository.dart  # Fetch/store vital signs
│   │   │   ├── activity_repository.dart     # Fetch/store workouts
│   │   │   ├── recommendation_repository.dart # Fetch recommendations
│   │   │   ├── nutrition_repository.dart    # Fetch/store meals
│   │   │   ├── messaging_repository.dart    # Fetch/store messages
│   │   │   ├── user_repository.dart         # User data management
│   │   │   └── base_repository.dart         # Base class with common methods
│   │   │
│   │   └── services/                         # External services
│   │       ├── api_service.dart             # HTTP client setup, API calls
│   │       ├── local_storage_service.dart   # SharedPreferences, local caching
│   │       ├── encryption_service.dart      # HIPAA-compliant encryption
│   │       ├── notification_service.dart    # Push notifications
│   │       └── analytics_service.dart       # Usage analytics (HIPAA safe)
│   │
│   ├── domain/                                # Business logic layer
│   │   ├── README.md                         # 📍 Navigation guide for /domain folder
│   │   ├── usecases/                         # Use cases (business logic)
│   │   │   ├── get_vital_signs_usecase.dart
│   │   │   ├── log_activity_usecase.dart
│   │   │   ├── get_recommendations_usecase.dart
│   │   │   ├── log_meal_usecase.dart
│   │   │   ├── send_message_usecase.dart
│   │   │   └── calculate_recovery_usecase.dart
│   │   │
│   │   └── entities/                         # Pure Dart objects (no Flutter dependency)
│   │       ├── user_entity.dart
│   │       ├── vital_signs_entity.dart
│   │       ├── activity_entity.dart
│   │       └── recommendation_entity.dart
│   │
│   ├── presentation/                         # UI layer (screens, widgets, state management)
│   │   ├── README.md                         # 📍 Navigation guide for /presentation folder
│   │   │
│   │   ├── providers/                        # Provider state management
│   │   │   ├── vital_signs_provider.dart    # Real-time vitals state
│   │   │   ├── activity_provider.dart       # Workout history state
│   │   │   ├── recommendation_provider.dart # Fitness plans state
│   │   │   ├── nutrition_provider.dart      # Nutrition state
│   │   │   ├── messaging_provider.dart      # Messages state
│   │   │   ├── user_provider.dart           # User profile state
│   │   │   └── ui_provider.dart             # Navigation, theme state
│   │   │
│   │   ├── screens/                          # Full-screen widgets (pages)
│   │   │   ├── README.md                     # 📍 Which screen does what
│   │   │   │
│   │   │   ├── home/
│   │   │   │   ├── home_screen.dart         # Home/Dashboard screen
│   │   │   │   └── widgets/
│   │   │   │       ├── vital_signs_grid.dart       # 4 vital cards display
│   │   │   │       ├── risk_status_card.dart       # Risk level indicator
│   │   │   │       ├── recommendation_card.dart    # Today's workout
│   │   │   │       ├── quick_actions_section.dart  # Chat, Message, Sounds
│   │   │   │       └── recent_activity_card.dart   # Last sessions
│   │   │   │
│   │   │   ├── fitness/
│   │   │   │   ├── fitness_plans_screen.dart      # Fitness & Recovery (segment control)
│   │   │   │   ├── workout_session_screen.dart    # During-workout monitoring
│   │   │   │   └── widgets/
│   │   │   │       ├── week_view_calendar.dart    # 7-day plan view
│   │   │   │       ├── target_zone_indicator.dart # HR zone visualization
│   │   │   │       ├── session_summary_card.dart  # Workout results
│   │   │   │       └── recovery_metrics.dart      # Recovery stats
│   │   │   │
│   │   │   ├── nutrition/
│   │   │   │   ├── nutrition_screen.dart          # Daily goals & meals
│   │   │   │   └── widgets/
│   │   │   │       ├── daily_goals_card.dart      # Calorie, sodium, water
│   │   │   │       ├── meal_recommendation_card.dart
│   │   │   │       ├── meal_log_dialog.dart       # Log meal modal
│   │   │   │       └── nutrition_progress.dart    # Weekly tracking
│   │   │   │
│   │   │   ├── messaging/
│   │   │   │   ├── messaging_screen.dart          # Clinician list
│   │   │   │   ├── conversation_screen.dart       # Message thread with doctor
│   │   │   │   └── widgets/
│   │   │   │       ├── clinician_card.dart        # Doctor/nurse card
│   │   │   │       ├── message_bubble.dart        # Individual message
│   │   │   │       └── message_input.dart         # Message composition
│   │   │   │
│   │   │   ├── health_coach/
│   │   │   │   ├── health_coach_screen.dart       # Floating or overlay
│   │   │   │   └── widgets/
│   │   │   │       ├── daily_briefing.dart        # AI summary
│   │   │   │       ├── chat_bubble.dart           # User/AI messages
│   │   │   │       ├── quick_questions.dart       # Common Q&A
│   │   │   │       └── insight_card.dart          # Health insights
│   │   │   │
│   │   │   └── profile/
│   │   │       ├── profile_screen.dart            # User settings
│   │   │       ├── care_team_screen.dart         # Clinician assignment
│   │   │       └── widgets/
│   │   │           ├── user_info_card.dart
│   │   │           └── preferences_section.dart
│   │   │
│   │   ├── shared/                           # Shared across screens
│   │   │   ├── README.md                     # 📍 Reusable components
│   │   │   ├── widgets/
│   │   │   │   ├── vital_card.dart           # Single vital display
│   │   │   │   ├── risk_badge.dart           # Risk indicator
│   │   │   │   ├── floating_chatbot.dart     # Floating AI widget
│   │   │   │   ├── custom_app_bar.dart       # Header with menu
│   │   │   │   ├── bottom_navigation.dart    # 5-tab navigation
│   │   │   │   └── loading_skeleton.dart     # Placeholder while loading
│   │   │   │
│   │   │   └── dialogs/
│   │   │       ├── alert_dialog.dart
│   │   │       └── confirmation_dialog.dart
│   │   │
│   │   └── navigation/
│   │       ├── main_navigation.dart          # Navigation setup & routing
│   │       └── navigation_observer.dart      # Analytics tracking
│   │
│   ├── utils/                                 # Utility functions & helpers
│   │   ├── README.md                         # 📍 Navigation guide for /utils
│   │   ├── constants.dart                    # App-wide constants
│   │   ├── validators.dart                   # Input validation functions
│   │   ├── formatters.dart                   # Date, number formatting
│   │   ├── extensions.dart                   # DateTime, String extensions
│   │   ├── logger.dart                       # Logging utility (no PII)
│   │   └── error_handler.dart                # Exception handling
│   │
│   └── l10n/                                  # Localization (if needed)
│       ├── app_en.arb
│       └── app_es.arb
│
├── assets/                                    # Static assets
│   ├── images/
│   ├── icons/
│   ├── animations/
│   └── fonts/
│
├── test/                                      # Unit & widget tests
│   ├── README.md
│   ├── unit/
│   ├── widget/
│   └── integration/
│
├── pubspec.yaml                               # Dependencies
├── pubspec.lock                               # Locked versions
├── analysis_options.yaml                      # Lint rules
├── .gitignore
├── README.md                                  # Project documentation
├── ARCHITECTURE.md                            # Architecture explanation
└── PROJECT_STRUCTURE.md                       # This structure explained
```

---

## 📍 README.md Files (Navigation Guides)

Create a **README.md in every major folder** with this format:

### Example: `lib/config/README.md`
```markdown
# /config Folder - Configuration & App Setup

## Purpose
This folder contains all app-wide configuration, theme, and routing setup.

## Files & Purpose

### app_config.dart
- App constants (API endpoints, timeouts, etc.)
- Feature flags
- Configuration switches
- Environment setup

### app_theme.dart
- Material Design 3 theme
- Color palette (blues, greens, reds, grays)
- Typography (Inter, JetBrains Mono)
- Custom theme data

### app_routes.dart
- Named routes for navigation
- Route definitions
- Deep linking setup

## How to Use

To add a new app constant:
1. Open `app_config.dart`
2. Add constant in appropriate section
3. Use `AppConfig.constantName` throughout app

To modify theme:
1. Edit `app_theme.dart`
2. Update `AppThemeData.lightTheme` or `AppThemeData.darkTheme`
3. Changes apply globally

## Common Tasks

- Change primary color → `app_theme.dart` (line X)
- Add API endpoint → `app_config.dart` (line Y)
- Add navigation route → `app_routes.dart` (line Z)
```

### Example: `lib/data/README.md`
```markdown
# /data Folder - Data Layer (Models, Repositories, Services)

## Purpose
This folder handles all data access: API calls, local storage, caching.

## Subfolders

### /models
Data structure definitions that mirror API responses.
- `vital_signs_model.dart` - HR, SpO2, BP, HRV
- `activity_session_model.dart` - Workout data
- `recommendation_model.dart` - AI fitness suggestions

### /repositories
**Abstraction layer** - Controllers that manage data source (API vs local).
- One repository per major data type
- Handles API calls and local caching
- Never directly import from models to screens

### /services
External service integrations.
- `api_service.dart` - HTTP client setup
- `local_storage_service.dart` - SharedPreferences
- `encryption_service.dart` - HIPAA encryption

## Architecture Rule
```
Screen → Provider → UseCase → Repository → API/LocalStorage
```

Never skip steps. Always go through proper layers.

## Common Tasks
- Add new vital sign type → `vital_signs_model.dart` + update `VitalSignsRepository`
- Add API endpoint → `api_service.dart` + create repository method
- Cache data locally → Use `local_storage_service.dart` in repository
```

### Example: `lib/presentation/README.md`
```markdown
# /presentation Folder - UI Layer (Screens & Widgets)

## Purpose
All UI components, screens, and state management live here.

## Subfolders

### /providers
Provider state management classes.
- One provider per major feature
- Handle business logic & state
- Notify listeners of changes

### /screens
Full-page widgets (pages users navigate to).
- One folder per major screen
- Contains main screen file + its widgets subfolder
- Don't put widgets in screen folders

### /shared
Reusable components used across multiple screens.
- Vital cards, buttons, dialogs
- Custom app bar, navigation
- Loading skeletons

### /navigation
Navigation setup and routing.
- `main_navigation.dart` - All navigation logic
- Define navigation routes here

## File Naming Convention
- Screens: `*_screen.dart` (e.g., `home_screen.dart`)
- Widgets: `*_widget.dart` or just `*.dart` (e.g., `vital_card.dart`)
- Dialogs: `*_dialog.dart` (e.g., `alert_dialog.dart`)
- Providers: `*_provider.dart` (e.g., `vital_signs_provider.dart`)

## Common Tasks
- Add new screen → Create folder in /screens with `_screen.dart` file
- Add reusable widget → Create in /shared/widgets
- Add provider → Create in /providers with `_provider.dart` suffix
- Connect screen to data → Use provider in build() method

## Screen Structure Template
```dart
class HomeScreen extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: CustomAppBar(...),
      body: Consumer<VitalSignsProvider>(
        builder: (context, provider, _) {
          if (provider.isLoading) return LoadingSkeleton();
          if (provider.error != null) return ErrorWidget();
          return VitalSignsGrid(...);
        },
      ),
      bottomNavigationBar: BottomNavigation(...),
      floatingActionButton: FloatingChatbot(...),
    );
  }
}
```
```

---

## 🧹 PART 3: CODE CLEANUP & REFACTORING RULES

### Rule 1: Remove Dead Code
```
Search for:
- Unused imports
- Unused variables
- Commented-out code blocks
- Unused functions/classes
- Stub files with "TODO" comments

Action: Delete entirely
```

### Rule 2: Simplify Logic Forests
```
Pattern to look for:
❌ BAD - Multiple nested if/else statements
if (condition1) {
  if (condition2) {
    if (condition3) {
      // 10 lines of logic
    }
  }
}

✅ GOOD - Early returns
if (!condition1) return;
if (!condition2) return;
if (!condition3) return;
// logic here
```

### Rule 3: Consolidate Duplicates
```
Pattern to look for:
- Same function in 2 places → Create in utils/ and import
- Same API call in 2 places → Create in repository
- Same widget in 2 places → Move to /shared/widgets

Action: Create one source of truth, import everywhere
```

### Rule 4: Consistent Naming
```
✅ Correct:
- Screen files: `home_screen.dart`
- Widgets: `vital_card.dart`
- Providers: `vital_signs_provider.dart`
- Models: `vital_signs_model.dart`
- Repositories: `vital_signs_repository.dart`

❌ Wrong:
- `HomeScreen.dart` (PascalCase filename)
- `vitals.dart` (unclear what it is)
- `vs_provider.dart` (abbreviated names)
```

### Rule 5: Documentation Standards
```
Every file should start with:

/// Handles fetching vital signs from API
/// 
/// This class is responsible for:
/// - Fetching real-time vital signs
/// - Caching locally
/// - Handling errors
///
/// Used by: VitalSignsProvider

Every function should have:

/// Fetches latest vital signs for current user
/// 
/// Returns a list of vital readings from the past hour
/// Throws [ApiException] if API call fails
Future<List<VitalSigns>> getLatestVitals()
```

---

## 🔗 PART 4: SYNCHRONIZATION & INTEGRATION RULES

### Rule 1: Model Consistency
```
Rule: Every API response should have a corresponding model
- API returns: { hr: 105, spo2: 98 }
- Model defined: VitalSignsModel with hr, spo2 fields
- Repository uses model: List<VitalSignsModel>
- Provider uses model: StateNotifier<List<VitalSignsModel>>
- Screen uses model: Consumer<VitalSignsProvider> displays model fields
```

### Rule 2: Provider Consistency
```
Rule: Only one provider handles each data type
- Vital signs: VitalSignsProvider (only place fetching vitals)
- Activities: ActivityProvider (only place managing workouts)
- No scattered API calls in screens

Pattern:
Screen → Calls provider.fetchVitals() → Provider calls repository → Repository calls API
```

### Rule 3: Naming Consistency Across Layers
```
API Endpoint: /vital-signs
Model: VitalSignsModel
Repository: VitalSignsRepository
Provider: VitalSignsProvider
Screen widget: VitalSignsGrid
Folder: /vital_signs (if needed)

All use same base name: vital_signs
```

### Rule 4: Error Handling Consistency
```
All data layer errors:
- Caught in Repository
- Converted to user-friendly messages
- Passed to Provider
- Provider updates error state
- Screen shows error widget

Never let errors propagate to screen without handling
```

### Rule 5: Caching Strategy
```
Real-time data (vitals): Cache for 10 seconds
Session data (activities): Cache for 1 hour
User profile: Cache for 24 hours
Recommendations: Cache for 6 hours

Use local_storage_service.dart for all caching
```

---

## 🧩 PART 5: NEW NAVIGATION STRUCTURE

After refactoring, implement this **5-tab navigation** (no more 7+ tabs):

```dart
// lib/presentation/shared/widgets/bottom_navigation.dart

class BottomNavigation extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Consumer<NavigationProvider>(
      builder: (context, navProvider, _) {
        return BottomNavigationBar(
          currentIndex: navProvider.currentIndex,
          onTap: (index) => navProvider.setIndex(index),
          items: [
            BottomNavigationBarItem(
              icon: Icon(Icons.home_outlined),
              activeIcon: Icon(Icons.home),
              label: 'Home',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.directions_run_outlined),
              activeIcon: Icon(Icons.directions_run),
              label: 'Fitness',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.nutrition),
              activeIcon: Icon(Icons.nutrition),
              label: 'Nutrition',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.message_outlined),
              activeIcon: Icon(Icons.message),
              label: 'Messages',
            ),
            BottomNavigationBarItem(
              icon: Icon(Icons.person_outline),
              activeIcon: Icon(Icons.person),
              label: 'Profile',
            ),
          ],
        );
      },
    );
  }
}
```

---

## 📝 PART 6: REFACTORING CHECKLIST

Complete these in order:

### Phase 1: Structure Setup (Day 1)
- [ ] Create new folder structure as defined
- [ ] Create README.md in each major folder
- [ ] Create ARCHITECTURE.md explaining the structure
- [ ] Create PROJECT_STRUCTURE.md with this diagram

### Phase 2: Move & Consolidate (Days 2-3)
- [ ] Move all models to /data/models
- [ ] Move all repositories to /data/repositories
- [ ] Move all services to /data/services
- [ ] Move all screens to /presentation/screens
- [ ] Move all shared widgets to /presentation/shared
- [ ] Move all providers to /presentation/providers
- [ ] Consolidate utilities to /utils

### Phase 3: Delete Dead Code (Day 4)
- [ ] Remove unused files
- [ ] Remove commented-out code
- [ ] Remove stub/incomplete files
- [ ] Delete unused imports from all files

### Phase 4: Fix Synchronization (Days 5-6)
- [ ] Update all imports to new paths
- [ ] Verify all model usages are consistent
- [ ] Verify all provider usages are consistent
- [ ] Verify all API calls go through repositories
- [ ] Verify error handling is consistent

### Phase 5: Add Documentation (Day 7)
- [ ] Add /// comments to all public classes
- [ ] Add /// comments to all public methods
- [ ] Verify naming conventions throughout
- [ ] Final code review

---

## 🎯 FINAL DELIVERABLES

After refactoring, the project should have:

✅ **Clean folder structure** - Easy to navigate
✅ **Clear file naming** - Know what each file does
✅ **Proper layering** - Data/Domain/Presentation separation
✅ **Consistent naming** - vital_signs everywhere
✅ **Documentation** - README.md in each folder
✅ **No dead code** - Every file has purpose
✅ **Synchronized models** - One API → One Model → One Provider
✅ **Clear navigation** - Users see only 5 tabs + floating AI
✅ **Professional quality** - Ready to show stakeholders

---

## 🚀 HOW TO PROCEED

When you're ready to refactor, use this prompt with these specific requests:

1. **"Help me move all models to /data/models"**
   - Ask me to verify each move
   - Update imports automatically

2. **"Find and fix all logic forests in the codebase"**
   - Show me complex nested if/else
   - Simplify to early returns

3. **"Consolidate duplicate functions"**
   - Find functions with same purpose
   - Create one version in /utils
   - Update all references

4. **"Update all imports for new structure"**
   - Search all files for old import paths
   - Replace with new paths
   - Verify compilation

5. **"Add documentation to all public classes"**
   - Add /// comments to every class
   - Add /// comments to every public method
   - Verify format is correct

6. **"Create README.md for each folder"**
   - Generate using template above
   - Customize for each folder
   - Add to git

---

## 💡 PRO TIPS FOR THE REFACTOR

1. **Do one section at a time** - Move all models, then all repos, then screens
2. **Test after each phase** - Run `flutter pub get` and `flutter analyze`
3. **Use Find & Replace wisely** - Search old paths, replace with new paths
4. **Keep git clean** - Commit after each major phase
5. **Ask AI for help** - "Help me move this file and update all references"
6. **Verify structure** - Check no file is import from wrong place

---

**This is everything you need for a production-grade refactor. Copy this entire prompt into Visual Studio Copilot and work through it systematically.**

Would you like me to create:
1. Specific prompts for each phase?
2. Example files showing correct structure?
3. Refactoring checklist in checklist format?
4. Git workflow for the refactor?

