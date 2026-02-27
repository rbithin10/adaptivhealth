# AdaptivHealth Mobile App

A Flutter-based mobile application for cardiovascular health monitoring with an enhanced, user-friendly UI following Human-Computer Interaction (HCI) principles, plus full dark mode support.

## ✨ Recent UI Enhancements

The app has been significantly enhanced with modern UI design principles:

### 🎨 Visual Design
- **Gradient Backgrounds**: Professional blue gradients for login, calming blue gradients for patient dashboard
- **Glass Morphism**: Semi-transparent cards with blur effects for a modern look
- **Enhanced Components**: Improved cards, buttons, and interactive elements
- **Better Visual Hierarchy**: Clear information architecture with proper spacing and sizing

### 🌓 Dark Mode Support (NEW)
- ✅ **Three Theme Modes**: System (default), Light, Dark
- ✅ **Persistent Preference**: Theme choice saved to local storage
- ✅ **Instant Theme Switching**: Changes apply immediately
- ✅ **WCAG AA Compliant**: All colors meet accessibility contrast standards
- ✅ **Clinical Colors Optimized**: Risk levels remain distinguishable in both modes
- See [DARK_MODE_GUIDE.md](./DARK_MODE_GUIDE.md) for details

### ♿ Accessibility Features
- ✅ **Minimum Tap Targets**: All buttons ≥ 48x48 logical pixels
- ✅ **Screen Reader Support**: Semantics annotations for TalkBack/VoiceOver
- ✅ **Contrast Verified**: 7.5:1+ ratios for text/background pairs
- ✅ **Keyboard Navigation**: All controls accessible via keyboard
- See [DARK_MODE_GUIDE.md#accessibility](./DARK_MODE_GUIDE.md) for details

### 🎯 HCI Principles Applied
- ✅ **Visual Hierarchy**: Important metrics prominently displayed
- ✅ **Immediate Feedback**: Clear loading states and error messages
- ✅ **Consistency**: Unified design language throughout
- ✅ **Accessibility**: WCAG AA compliant color contrast, large touch targets
- ✅ **Clarity**: Clear labels and status indicators

### 📱 Enhanced Screens
1. **Login Screen**
   - Professional gradient background
   - Enhanced logo with shadow effects
   - Glass morphism form design
   - Improved error handling and visual feedback

2. **Patient Dashboard**
   - Calming gradient background
   - Enhanced heart rate ring with glow effects
   - Modern card designs for vital signs
   - Status badges with icons
   - Actionable recommendation cards

### 📚 Documentation
- See [UI_ENHANCEMENTS.md](./UI_ENHANCEMENTS.md) for detailed documentation
- See [UI_VISUAL_GUIDE.md](./UI_VISUAL_GUIDE.md) for visual before/after comparisons
- See [DARK_MODE_GUIDE.md](./DARK_MODE_GUIDE.md) for dark mode & accessibility details
- See [DARK_MODE_IMPLEMENTATION.md](./DARK_MODE_IMPLEMENTATION.md) for implementation summary

## 🌓 Dark Mode & Theme Toggle

### How to Use Dark Mode

The app automatically respects your device's theme preference. To override:

1. Open the app and navigate to **Profile** tab
2. Look for **Theme Settings** (button to be added in profile screen)
3. Choose:
   - **System**: Follow device theme (default)
   - **Light**: Force light mode
   - **Dark**: Force dark mode
4. Your preference is saved and persists across app restarts

### For Developers

**Color Helper Methods** (use these instead of hard-coded colors):
```dart
final brightness = MediaQuery.of(context).platformBrightness;
AdaptivColors.getTextColor(brightness)              // Adaptive text
AdaptivColors.getSurfaceColor(brightness)           // Card backgrounds
AdaptivColors.getBackgroundColor(brightness)        // Page backgrounds
AdaptivColors.getRiskColorForBrightness(level, brightness)  // Clinical colors
```

**Migration Guide**: See [DARK_MODE_BEST_PRACTICES.dart](./DARK_MODE_BEST_PRACTICES.dart)

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Lab: Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Cookbook: Useful Flutter samples](https://docs.flutter.dev/cookbook)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.

## Key Features

- 💙 **Cardiovascular Monitoring**: Real-time heart rate and vital signs tracking
- 📊 **Health Dashboard**: Comprehensive view of health metrics
- 🎯 **Risk Assessment**: AI-powered health risk evaluation
- 🏃 **Activity Tracking**: Workout and recovery monitoring
- 📈 **Historical Data**: Track health trends over time
- 👤 **User Profile**: Personalized health management

## Design Philosophy

The app follows modern health app design conventions inspired by popular applications like:
- Apple Health (gradient backgrounds, card-based design)
- Fitbit (prominent metric display, status rings)
- MyFitnessPal (clear visual hierarchy)
- Calm (soothing color palettes, rounded elements)

All while maintaining accessibility standards and following HCI best practices.
