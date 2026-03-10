/*
AI Coach Overlay.

Wraps any screen with a floating AI chatbot button that floats
on top of everything. The button can be dragged around by the user
and its position is remembered between screens.

This is placed near the top of the widget tree so the chatbot
button appears on every screen of the app.
*/

// Flutter's main UI toolkit
import 'package:flutter/material.dart';
// Lets us schedule work after the current frame finishes drawing
import 'package:flutter/scheduler.dart';

// Our HTTP client for talking to the server
import '../services/api_client.dart';
// Remembers where the user dragged the chatbot button
import 'ai_coach_position_store.dart';
// The actual floating chatbot button widget
import 'floating_chatbot.dart';

// Wraps a child screen and adds a draggable AI chatbot button on top
class AiCoachOverlay extends StatefulWidget {
  // The screen content that appears behind the chatbot button
  final Widget child;
  // The API client the chatbot uses to talk to the server
  final ApiClient apiClient;

  const AiCoachOverlay({
    super.key,
    required this.child,
    required this.apiClient,
  });

  @override
  State<AiCoachOverlay> createState() => _AiCoachOverlayState();
}

class _AiCoachOverlayState extends State<AiCoachOverlay> {
  // Current horizontal position of the floating button
  double _fabX = -1;
  // Current vertical position of the floating button
  double _fabY = -1;
  // Whether we've calculated the initial position yet
  bool _positioned = false;

  @override
  void initState() {
    super.initState();
    // Try to restore the button's last saved position
    final saved = AiCoachPositionStore.position;
    if (saved != null) {
      _fabX = saved.dx;
      _fabY = saved.dy;
      _positioned = true;
    }
  }

  // Calculate the default position for the floating button (bottom-right corner)
  void _initPosition(BoxConstraints constraints) {
    const double fabSize = 56.0;
    const double horizontalMargin = 16.0;
    const double topMargin = 8.0;
    const double bottomMargin = 16.0;

    // Calculate the boundaries the button can be placed within
    final double maxFabX =
        (constraints.maxWidth - fabSize).clamp(0.0, double.infinity);
    final double minFabY = topMargin;
    final double maxFabY = (constraints.maxHeight - fabSize - bottomMargin)
        .clamp(minFabY, double.infinity);

    // Default position: bottom-right corner with margin
    final double x = (constraints.maxWidth - fabSize - horizontalMargin)
        .clamp(0.0, maxFabX);
    final double y = (constraints.maxHeight - fabSize - bottomMargin)
        .clamp(minFabY, maxFabY);

    // Wait until the current frame is done drawing, then update position
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      setState(() {
        _fabX = x;
        _fabY = y;
        _positioned = true;
        // Save this position so it persists between screens
        AiCoachPositionStore.setPosition(Offset(_fabX, _fabY));
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const double fabSize = 56.0;
        const double topMargin = 8.0;
        const double bottomMargin = 16.0;

        // Calculate the allowed range for the button's position
        final double minFabX = 0.0;
        final double maxFabX =
            (constraints.maxWidth - fabSize).clamp(0.0, double.infinity);
        final double minFabY = topMargin;
        final double maxFabY = (constraints.maxHeight - fabSize - bottomMargin)
            .clamp(minFabY, double.infinity);

        // First frame: calculate default position and just show the child screen
        if (!_positioned) {
          _initPosition(constraints);
          return widget.child;
        }

        // Keep the button within screen boundaries (e.g. after phone rotation)
        final double fabX = _fabX.clamp(minFabX, maxFabX);
        final double fabY = _fabY.clamp(minFabY, maxFabY);

        // Stack the child screen and the floating button on top of each other
        return Stack(
          children: [
            // The actual screen content fills the entire area
            Positioned.fill(child: widget.child),
            // The floating chatbot button positioned wherever the user left it
            Positioned(
              left: fabX,
              top: fabY,
              child: FloatingChatbot(
                apiClient: widget.apiClient,
                posX: fabX,
                posY: fabY,
                // When the user drags the button, save its new position
                onPositionChanged: (offset) {
                  setState(() {
                    _fabX = offset.dx.clamp(minFabX, maxFabX);
                    _fabY = offset.dy.clamp(minFabY, maxFabY);
                    AiCoachPositionStore.setPosition(Offset(_fabX, _fabY));
                  });
                },
              ),
            ),
          ],
        );
      },
    );
  }
}
