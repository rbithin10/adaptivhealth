/*
INTEGRATION GUIDE: Adding Theme Settings to Profile Screen

This file shows exactly how to integrate the ThemeSettingsDialog
into your existing profile_screen.dart.

STEPS:
1. Import the ThemeSettingsDialog
2. Add a theme settings tile/button in the profile UI
3. Show the dialog when tapped

CODE EXAMPLE:
*/

import 'package:flutter/material.dart';
import '../widgets/theme_settings_dialog.dart';

// In your profile screen build method, add this tile:

  // THEME SETTINGS SECTION
  const SizedBox(height: 24),
  Semantics(
    heading: true,
    label: 'Display Settings',
    child: Text(
      'Display Settings',
      style: Theme.of(context).textTheme.titleMedium,
    ),
  ),
  const SizedBox(height: 12),
  
  // Theme Mode Tile
  Semantics(
    button: true,
    enabled: true,
    label: 'Theme Settings',
    onTap: () {
      showModalBottomSheet(
        context: context,
        builder: (context) => const ThemeSettingsDialog(),
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
        ),
      );
    },
    child: ListTile(
      leading: const Icon(Icons.palette),
      title: const Text('Theme'),
      subtitle: const Text('Light, Dark, or System'),
      trailing: const Icon(Icons.arrow_forward_ios, size: 16),
      onTap: () {
        showModalBottomSheet(
          context: context,
          builder: (context) => const ThemeSettingsDialog(),
          shape: const RoundedRectangleBorder(
            borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
          ),
        );
      },
    ),
  ),

// Alternative: Icon button in AppBar
// AppBar(
//   actions: [
//     Semantics(
//       button: true,
//       label: 'Theme Settings',
//       onTap: () => _showThemeDialog(context),
//       child: IconButton(
//         icon: const Icon(Icons.palette),
//         tooltip: 'Theme Settings',
//         onPressed: () => _showThemeDialog(context),
//       ),
//     ),
//   ],
// )

// Helper method:
void _showThemeDialog(BuildContext context) {
  showModalBottomSheet(
    context: context,
    builder: (context) => const ThemeSettingsDialog(),
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(12)),
    ),
  );
}
