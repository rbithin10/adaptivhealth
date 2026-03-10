# widgets/ — Reusable UI Components

Shared building blocks used by multiple screens. These keep the app consistent and avoid duplicating code.

## Files

| File | Purpose |
|------|---------|
| `widgets.dart` | Export file — lets other files import all widgets with a single line |
| `vital_card.dart` | Small card showing one vital sign (heart rate, SpO2, etc.) with an icon, value, status color, and mini trend line |
| `risk_badge.dart` | Colored label showing cardiovascular risk level (Low / Moderate / High / Critical) |
| `recommendation_card.dart` | Card displaying an AI-recommended workout with activity type, duration, target heart rate zone, and a start button |
| `target_zone_indicator.dart` | Visual gauge showing whether the user's current heart rate is in the target exercise zone |
| `floating_chatbot.dart` | Draggable floating button that opens the AI health coach chat overlay |
| `ai_coach_overlay.dart` | The chat window that appears when the floating AI coach button is tapped |
| `ai_coach_position_store.dart` | Remembers where the user dragged the AI coach button so it stays in place |
| `edge_ai_status_card.dart` | Card showing the status of the on-device AI system (loading, ready, or error) |
| `sos_button.dart` | Emergency SOS button — sends a critical alert to the care team and optionally calls the emergency contact |
| `week_view.dart` | Horizontal row of 7 days (Mon–Sun) where the user taps to select a day |
