import 'package:flutter/material.dart';

class AiCoachPositionStore {
  static Offset? _position;

  static Offset? get position => _position;

  static void setPosition(Offset value) {
    _position = value;
  }

  static void clear() {
    _position = null;
  }
}
