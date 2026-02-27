/*
Floating AI Health Coach Widget

A draggable floating button that provides quick access to the AI chatbot.
The button can be dragged to any screen edge and snaps to the nearest
horizontal side on release. Chat history is maintained in ChatStore
(provided via Provider) so messages survive bottom-sheet dismissals
within the same app session.
*/

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../services/chat_store.dart';

/// Button diameter used for the draggable AI coach FAB.
const double _kFabSize = 56.0;

class FloatingChatbot extends StatefulWidget {
  final ApiClient apiClient;

  /// Current position managed by the parent (HomeScreen).
  final double posX;
  final double posY;

  /// Called when the user drags or the snap animation updates position.
  final ValueChanged<Offset> onPositionChanged;

  const FloatingChatbot({
    super.key,
    required this.apiClient,
    required this.posX,
    required this.posY,
    required this.onPositionChanged,
  });

  @override
  State<FloatingChatbot> createState() => _FloatingChatbotState();
}

class _FloatingChatbotState extends State<FloatingChatbot>
    with SingleTickerProviderStateMixin {
  AnimationController? _snapController;
  Animation<Offset>? _snapAnimation;

  void _openChat(BuildContext context) {
    // Capture ChatStore from the outer context (where the Provider lives)
    // before opening the modal, because the modal's builder context sits
    // outside the Provider widget tree.
    final chatStore = Provider.of<ChatStore>(context, listen: false);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider<ChatStore>.value(
        value: chatStore,
        child: ChatBottomSheet(apiClient: widget.apiClient),
      ),
    );
  }

  /// Animate the button to the nearest horizontal edge after a drag ends.
  void _snapToEdge(Size screenSize) {
    final double centreX = widget.posX + _kFabSize / 2;
    final double targetX = centreX < screenSize.width / 2
        ? 16.0
        : screenSize.width - _kFabSize - 16.0;

    // Clamp vertical position within screen bounds.
    final double targetY = widget.posY.clamp(
      MediaQuery.of(context).padding.top + 8.0,
      screenSize.height - _kFabSize - 90.0,
    );

    _snapController?.dispose();
    _snapController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 250),
    );

    _snapAnimation = Tween<Offset>(
      begin: Offset(widget.posX, widget.posY),
      end: Offset(targetX, targetY),
    ).animate(CurvedAnimation(
      parent: _snapController!,
      curve: Curves.easeOut,
    ));

    _snapController!.addListener(() {
      if (_snapAnimation != null) {
        widget.onPositionChanged(_snapAnimation!.value);
      }
    });

    _snapController!.forward();
  }

  @override
  void dispose() {
    _snapController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onPanUpdate: (details) {
        final size = MediaQuery.of(context).size;
        final padding = MediaQuery.of(context).padding;
        final double newX = (widget.posX + details.delta.dx).clamp(
          0.0,
          size.width - _kFabSize,
        );
        final double newY = (widget.posY + details.delta.dy).clamp(
          padding.top + 8.0,
          size.height - _kFabSize - 90.0,
        );
        widget.onPositionChanged(Offset(newX, newY));
      },
      onPanEnd: (_) => _snapToEdge(MediaQuery.of(context).size),
      onTap: () => _openChat(context),
      child: Material(
        elevation: 4,
        shape: const CircleBorder(),
        color: AdaptivColors.primary,
        child: SizedBox(
          width: _kFabSize,
          height: _kFabSize,
          child: const Center(
            child: Icon(
              Icons.smart_toy_outlined,
              color: Colors.white,
              size: 28,
            ),
          ),
        ),
      ),
    );
  }
}

// Bottom sheet chat interface
class ChatBottomSheet extends StatefulWidget {
  final ApiClient apiClient;

  const ChatBottomSheet({super.key, required this.apiClient});

  @override
  State<ChatBottomSheet> createState() => _ChatBottomSheetState();
}

class _ChatBottomSheetState extends State<ChatBottomSheet> {
  final TextEditingController _controller = TextEditingController();
  late final ChatStore _chatStore;
  bool _initialized = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (!_initialized) {
      _chatStore = Provider.of<ChatStore>(context, listen: false);
      // Seed greeting only when the conversation is brand-new
      _chatStore.ensureGreeting();
      _initialized = true;
    }
  }

  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    _chatStore.addMessage(ChatMessage(
      text: text,
      isUser: true,
      timestamp: DateTime.now(),
    ));
    _controller.clear();
    _chatStore.setTyping(true);

    // Get AI response from backend
    _getAIResponse(text).then((response) {
      if (mounted) {
        _chatStore.setTyping(false);
        _chatStore.addMessage(ChatMessage(
          text: response,
          isUser: false,
          timestamp: DateTime.now(),
        ));
      }
    }).catchError((error) {
      if (mounted) {
        _chatStore.setTyping(false);
        _chatStore.addMessage(ChatMessage(
          text: "Sorry, I couldn't reach the server right now. Please try again in a moment.",
          isUser: false,
          timestamp: DateTime.now(),
        ));
      }
    });
  }

  Future<String> _getAIResponse(String userMessage) async {
    final lowerMessage = userMessage.toLowerCase();
    
    // For health/risk/heart questions, get personalized summary from backend
    if (lowerMessage.contains('heart') ||
        lowerMessage.contains('health') ||
        lowerMessage.contains('risk') ||
        lowerMessage.contains('safe') ||
        lowerMessage.contains('status') ||
        lowerMessage.contains('how am i') ||
        lowerMessage.contains('doing')) {
      try {
        return await widget.apiClient.getNLRiskSummary();
      } catch (e) {
        return "I can access your health data, but I'm having trouble connecting right now. Your latest vitals are available on the home screen.";
      }
    }

    if (lowerMessage.contains('workout') ||
        lowerMessage.contains('exercise') ||
        lowerMessage.contains('activity') ||
        lowerMessage.contains('moving') ||
        lowerMessage.contains('today\'s plan')) {
      try {
        return await widget.apiClient.getNLTodaysWorkout();
      } catch (e) {
        return "Check the Fitness tab for your personalized workout plan based on your current health status.";
      }
    } else if (lowerMessage.contains('alert') ||
        lowerMessage.contains('warning') ||
        lowerMessage.contains('problem') ||
        lowerMessage.contains('wrong')) {
      try {
        return await widget.apiClient.getNLAlertExplanation();
      } catch (e) {
        return "You can view all your health alerts by tapping the bell icon on the home screen. I'll help explain any specific alert you're concerned about.";
      }
    } else if (lowerMessage.contains('progress') ||
        lowerMessage.contains('improve') ||
        lowerMessage.contains('better') ||
        lowerMessage.contains('trend') ||
        lowerMessage.contains('how am i doing')) {
      try {
        final range = lowerMessage.contains('month') ? '30d' : '7d';
        return await widget.apiClient.getNLProgressSummary(range: range);
      } catch (e) {
        return "You're making positive progress! Keep up your current routine for the best results.";
      }
    } else if (lowerMessage.contains('sleep')) {
      return "Good sleep is essential for heart recovery. Aim for 7-8 hours and try to maintain a consistent schedule. It helps stabilize your heart rate.";
    } else if (lowerMessage.contains('nutrition') ||
        lowerMessage.contains('food') ||
        lowerMessage.contains('eat') ||
        lowerMessage.contains('diet')) {
      try {
        return await widget.apiClient.getNLNutritionPlan();
      } catch (e) {
        return "Visit the Nutrition tab for meal recommendations tailored to your cardiovascular health. Focus on low-sodium foods and heart-healthy nutrients.";
      }
    } else if (lowerMessage.contains('doctor') ||
        lowerMessage.contains('clinician') ||
        lowerMessage.contains('message') ||
        lowerMessage.contains('contact care')) {
      return "You can reach your care team through the Messaging tab. They typically respond within a few hours during business hours.";
    } else if (lowerMessage.contains('help') ||
        lowerMessage.contains('what can you do') ||
        lowerMessage.contains('features')) {
      return "I'm your AI health coach. I can help you understand:\n"
          "• Your current heart health status\n"
          "• Today's recommended activity\n"
          "• Explanations for any health alerts\n"
          "• Your progress and improvements\n\n"
          "Just ask about your health, workouts, nutrition, or progress!";
    }

    return "I can help you understand your heart health status, workout plans, nutrition guidance, and alerts. What would you like to know?";
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Rebuild whenever ChatStore notifies (new messages, typing state)
    return Consumer<ChatStore>(
      builder: (context, store, _) {
        final messages = store.messages;
        final isTyping = store.isTyping;

        return Container(
          height: MediaQuery.of(context).size.height * 0.7,
          decoration: const BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: Column(
            children: [
              // Handle bar
              Container(
                margin: const EdgeInsets.symmetric(vertical: 12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),

              // Header
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: AdaptivColors.primary.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.smart_toy,
                        color: AdaptivColors.primary,
                        size: 24,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'AI Health Coach',
                            style: AdaptivTypography.subtitle1,
                          ),
                          Row(
                            children: [
                              Container(
                                width: 8,
                                height: 8,
                                decoration: const BoxDecoration(
                                  color: AdaptivColors.stable,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 4),
                              Text(
                                'Online',
                                style: AdaptivTypography.caption.copyWith(
                                  color: AdaptivColors.stable,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: const Icon(Icons.close),
                      onPressed: () => Navigator.pop(context),
                    ),
                  ],
                ),
              ),

              const Divider(height: 24),

              // Messages list
              Expanded(
                child: ListView.builder(
                  padding: const EdgeInsets.symmetric(horizontal: 16),
                  itemCount: messages.length + (isTyping ? 1 : 0),
                  itemBuilder: (context, index) {
                    if (index == messages.length && isTyping) {
                      return const Padding(
                        padding: EdgeInsets.only(bottom: 12),
                        child: Row(
                          children: [
                            SizedBox(width: 40),
                            Text('Typing...', style: TextStyle(color: Colors.grey)),
                          ],
                        ),
                      );
                    }
                    final message = messages[index];
                    return Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Row(
                        mainAxisAlignment: message.isUser
                            ? MainAxisAlignment.end
                            : MainAxisAlignment.start,
                        children: [
                          if (!message.isUser) ...[
                            CircleAvatar(
                              radius: 16,
                              backgroundColor: AdaptivColors.primary.withOpacity(0.1),
                              child: const Icon(
                                Icons.smart_toy,
                                size: 18,
                                color: AdaptivColors.primary,
                              ),
                            ),
                            const SizedBox(width: 8),
                          ],
                          Flexible(
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 16,
                                vertical: 12,
                              ),
                              decoration: BoxDecoration(
                                color: message.isUser
                                    ? AdaptivColors.primary
                                    : Colors.grey[100],
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: Text(
                                message.text,
                                style: TextStyle(
                                  color: message.isUser ? Colors.white : Colors.black87,
                                ),
                              ),
                            ),
                          ),
                          if (message.isUser) const SizedBox(width: 40),
                        ],
                      ),
                    );
                  },
                ),
              ),

              // Input field
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  boxShadow: [
                    BoxShadow(
                      color: Colors.black.withOpacity(0.05),
                      blurRadius: 10,
                      offset: const Offset(0, -2),
                    ),
                  ],
                ),
                child: SafeArea(
                  child: Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: _controller,
                          decoration: InputDecoration(
                            hintText: 'Ask your health coach...',
                            filled: true,
                            fillColor: Colors.grey[100],
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(24),
                              borderSide: BorderSide.none,
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 12,
                            ),
                          ),
                          onSubmitted: (_) => _sendMessage(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      CircleAvatar(
                        backgroundColor: AdaptivColors.primary,
                        child: IconButton(
                          icon: const Icon(Icons.send, color: Colors.white),
                          onPressed: _sendMessage,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
