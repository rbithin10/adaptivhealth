import 'package:flutter/material.dart';

import '../services/api_client.dart';
import 'ai_coach_position_store.dart';
import 'floating_chatbot.dart';

class AiCoachOverlay extends StatefulWidget {
  final Widget child;
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
  double _fabX = -1;
  double _fabY = -1;

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        const double fabSize = 56.0;
        const double horizontalMargin = 16.0;
        const double topMargin = 8.0;
        const double bottomMargin = 16.0;

        final double minFabX = 0.0;
        final double maxFabX =
            (constraints.maxWidth - fabSize).clamp(0.0, double.infinity);
        final double minFabY = topMargin;
        final double maxFabY = (constraints.maxHeight - fabSize - bottomMargin)
            .clamp(minFabY, double.infinity);

        final sharedPosition = AiCoachPositionStore.position;
        if (sharedPosition != null) {
          _fabX = sharedPosition.dx;
          _fabY = sharedPosition.dy;
        }

        if (_fabX < 0 || _fabY < 0) {
          _fabX = (constraints.maxWidth - fabSize - horizontalMargin)
              .clamp(minFabX, maxFabX);
          _fabY = (constraints.maxHeight - fabSize - bottomMargin)
              .clamp(minFabY, maxFabY);
        } else {
          _fabX = _fabX.clamp(minFabX, maxFabX);
          _fabY = _fabY.clamp(minFabY, maxFabY);
        }

        AiCoachPositionStore.setPosition(Offset(_fabX, _fabY));

        return Stack(
          children: [
            Positioned.fill(child: widget.child),
            Positioned(
              left: _fabX,
              top: _fabY,
              child: FloatingChatbot(
                apiClient: widget.apiClient,
                posX: _fabX,
                posY: _fabY,
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
