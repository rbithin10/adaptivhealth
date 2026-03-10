/*
Widget Library — Re-exports all custom widgets.

Instead of importing each widget file individually, other files
can just import this one file to get access to everything.
*/
library;

// Each "export" makes a widget available to files that import this library
export 'vital_card.dart';           // Small card showing a single vital sign
export 'risk_badge.dart';           // Colored badge showing risk level
export 'recommendation_card.dart';  // Workout recommendation display
export 'target_zone_indicator.dart';// Heart rate target zone visual
export 'week_view.dart';            // Weekly calendar view
export 'floating_chatbot.dart';     // Draggable AI chatbot button
export 'edge_ai_status_card.dart';  // On-device AI status display
