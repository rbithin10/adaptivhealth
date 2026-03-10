/*
AI Coach Position Store.

Remembers where the user dragged the floating AI coach button on screen.
This way, if the user moves the button to a different corner, it stays
there even when switching between screens.
*/

import 'package:flutter/material.dart';

// Simple storage for the AI coach button's position on screen.
// Only one position is tracked for the whole app (shared across all screens).
class AiCoachPositionStore {
  // The saved position (x, y coordinates) — null means "use the default spot"
  static Offset? _position;

  // Let other parts of the app read where the button should be
  static Offset? get position => _position;

  // Save a new position when the user drags the button somewhere
  static void setPosition(Offset value) {
    _position = value;
  }

  // Reset the position back to the default (used when logging out)
  static void clear() {
    _position = null;
  }
}
