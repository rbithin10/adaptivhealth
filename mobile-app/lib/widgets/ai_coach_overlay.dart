import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

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
  bool _positioned = false;

  @override
  void initState() {
    super.initState();
    final saved = AiCoachPositionStore.position;
    if (saved != null) {
      _fabX = saved.dx;
      _fabY = saved.dy;
      _positioned = true;
    }
  }

  void _initPosition(BoxConstraints constraints) {
    const double fabSize = 56.0;
    const double horizontalMargin = 16.0;
    const double topMargin = 8.0;
    const double bottomMargin = 16.0;

    final double maxFabX =
        (constraints.maxWidth - fabSize).clamp(0.0, double.infinity);
    final double minFabY = topMargin;
    final double maxFabY = (constraints.maxHeight - fabSize - bottomMargin)
        .clamp(minFabY, double.infinity);

    final double x = (constraints.maxWidth - fabSize - horizontalMargin)
        .clamp(0.0, maxFabX);
    final double y = (constraints.maxHeight - fabSize - bottomMargin)
        .clamp(minFabY, maxFabY);

    // Schedule state update after this build frame completes.
    SchedulerBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      setState(() {
        _fabX = x;
        _fabY = y;
        _positioned = true;
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

        final double minFabX = 0.0;
        final double maxFabX =
            (constraints.maxWidth - fabSize).clamp(0.0, double.infinity);
        final double minFabY = topMargin;
        final double maxFabY = (constraints.maxHeight - fabSize - bottomMargin)
            .clamp(minFabY, double.infinity);

        if (!_positioned) {
          _initPosition(constraints);
          // Return child only on the very first frame before position is known.
          return widget.child;
        }

        // Clamp to current constraints (e.g. after rotation).
        final double fabX = _fabX.clamp(minFabX, maxFabX);
        final double fabY = _fabY.clamp(minFabY, maxFabY);

        return Stack(
          children: [
            Positioned.fill(child: widget.child),
            Positioned(
              left: fabX,
              top: fabY,
              child: FloatingChatbot(
                apiClient: widget.apiClient,
                posX: fabX,
                posY: fabY,
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
