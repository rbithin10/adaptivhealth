/*
Floating AI Health Coach Widget

A draggable floating button that provides quick access to the AI chatbot.
The button can be dragged to any screen edge and snaps to the nearest
horizontal side on release. Chat history is maintained in ChatStore
(provided via Provider) so messages survive bottom-sheet dismissals
within the same app session.
*/

// Flutter's UI toolkit
import 'package:flutter/material.dart';
import 'package:flutter/gestures.dart';
// Text-to-speech — reads AI responses aloud
import 'package:flutter_tts/flutter_tts.dart';
// Opens the phone camera to take pictures
import 'package:image_picker/image_picker.dart';
// Beautiful line-style icons
import 'package:lucide_icons/lucide_icons.dart';
// State management — lets widgets share data
import 'package:provider/provider.dart';
// Handles phone permissions (microphone, camera, etc.)
import 'package:permission_handler/permission_handler.dart';
// Speech-to-text — converts voice to typed text
import 'package:speech_to_text/speech_to_text.dart';
// File I/O for sending camera images
import 'dart:io';
// Our custom brand colors
import '../theme/colors.dart';
// Our custom text styles
import '../theme/typography.dart';
// HTTP client for talking to the backend server
import '../services/api_client.dart';
// Stores chat message history in memory
import '../services/chat_store.dart';

// The size of the floating round button (56 pixels diameter)
const double _kFabSize = 56.0;

// The draggable floating button that opens the AI chat
class FloatingChatbot extends StatefulWidget {
  // The HTTP client used to send messages to the AI backend
  final ApiClient apiClient;

  // Current X and Y position on screen (managed by the parent)
  final double posX;
  final double posY;

  // Called whenever the button moves (drag or snap animation)
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
  // Controls the smooth animation when the button snaps to a screen edge
  AnimationController? _snapController;
  // The animation that moves the button from its current spot to the edge
  Animation<Offset>? _snapAnimation;

  // Open the chat panel as a bottom sheet
  void _openChat(BuildContext context) {
    // Grab the ChatStore before opening the sheet (the sheet's context
    // is outside the Provider tree, so we need to capture it here)
    final chatStore = Provider.of<ChatStore>(context, listen: false);
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      backgroundColor: Colors.transparent,
      builder: (_) => ChangeNotifierProvider<ChatStore>.value(
        value: chatStore,
        child: ChatBottomSheet(apiClient: widget.apiClient),
      ),
    );
  }

  // After the user stops dragging, smoothly animate the button to the nearest screen edge
  void _snapToEdge(Size screenSize) {
    // Figure out which side is closer (left or right)
    final double centreX = widget.posX + _kFabSize / 2;
    final double targetX = centreX < screenSize.width / 2
        ? 16.0
        : screenSize.width - _kFabSize - 16.0;

    // Keep the button within the screen's safe area
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
    // The draggable + tappable floating button
    return GestureDetector(
      // Start tracking drag position from touch-down, not after slop distance
      dragStartBehavior: DragStartBehavior.down,
      // User is dragging the button — move it with their finger
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
      // User stopped dragging — snap to the nearest edge
      onPanEnd: (_) => _snapToEdge(MediaQuery.of(context).size),
      // User tapped the button — open the chat
      onTap: () => _openChat(context),
      // The round floating button with the robot icon
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

// The chat panel that slides up from the bottom of the screen
class ChatBottomSheet extends StatefulWidget {
  // The HTTP client for sending messages to the AI
  final ApiClient apiClient;

  const ChatBottomSheet({super.key, required this.apiClient});

  @override
  State<ChatBottomSheet> createState() => _ChatBottomSheetState();
}

class _ChatBottomSheetState extends State<ChatBottomSheet>
    with SingleTickerProviderStateMixin {
  // The text field where the user types their message
  final TextEditingController _controller = TextEditingController();
  // Speech-to-text engine that listens to the user's voice
  late final SpeechToText _speech;
  // Text-to-speech engine that reads AI responses aloud
  late final FlutterTts _tts;
  // Whether the microphone is currently listening
  bool _isListening = false;
  // Whether speech recognition is available on this device
  bool _speechAvailable = false;
  // Whether the AI is currently speaking aloud
  bool _isSpeaking = false;
  // Whether text-to-speech was set up successfully
  bool _ttsReady = false;

  // Animation for the pulsing ring around the mic button while recording
  late final AnimationController _pulseController;
  late final Animation<double> _pulseScale;

  // Quick way to access the chat message store
  ChatStore get _chatStore => Provider.of<ChatStore>(context, listen: false);

  @override
  void initState() {
    super.initState();

    // Set up voice recognition (microphone → text)
    _speech = SpeechToText();
    _initializeSpeech();

    // Set up the pulsing animation for the mic button
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _pulseScale = Tween<double>(begin: 1.0, end: 1.7).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    // Set up text-to-speech (AI reads responses aloud)
    _tts = FlutterTts();
    _initializeTts();

    // Show a greeting message when the chat opens for the first time
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      _chatStore.ensureGreeting();
    });
  }

  // Set up the text-to-speech engine with language, speed, and volume
  Future<void> _initializeTts() async {
    try {
      // Wait for each speech to finish before starting the next
      await _tts.awaitSpeakCompletion(true);
      await _tts.setQueueMode(1);
      await _tts.setSharedInstance(true);
      await _tts.setLanguage('en-US');
      await _tts.setSpeechRate(0.48);
      await _tts.setVolume(1.0);
      await _tts.setPitch(1.0);
      _tts.setStartHandler(() {
        if (mounted) setState(() => _isSpeaking = true);
      });
      _tts.setCompletionHandler(() {
        if (mounted) setState(() => _isSpeaking = false);
      });
      _tts.setCancelHandler(() {
        if (mounted) setState(() => _isSpeaking = false);
      });
      _tts.setErrorHandler((_) {
        if (mounted) setState(() => _isSpeaking = false);
      });
      _ttsReady = true;
    } catch (_) {
      _ttsReady = false;
    }
  }

  // Read an AI response aloud, stripping any markdown formatting first
  Future<void> _speakResponse(String text) async {
    // Remove markdown symbols like *, _, `, #, etc.
    final clean = text
        .replaceAll(RegExp(r'[*_`#>\[\]]'), '')
        .replaceAll(RegExp(r'\s{2,}'), ' ')
        .trim();
    if (clean.isEmpty) return;
    if (!_ttsReady) {
      await _initializeTts();
      if (!_ttsReady) return;
    }
    await _tts.stop();
    await _tts.speak(clean);
  }

  // Stop any speech that's currently playing
  Future<void> _stopSpeaking() async {
    await _tts.stop();
    if (mounted) setState(() => _isSpeaking = false);
  }

  // Set up the speech-to-text engine (voice recognition)
  Future<void> _initializeSpeech() async {
    // First, ask the user for microphone permission
    final micStatus = await Permission.microphone.request();
    if (!micStatus.isGranted) {
      // No mic permission — voice input stays disabled
      return;
    }
    // Initialize the speech recognition engine
    final available = await _speech.initialize(
      onStatus: (status) {
        if (status == 'done' || status == 'notListening') {
          _pulseController.stop();
          _pulseController.reset();
          if (!mounted) return;
          setState(() {
            _isListening = false;
          });
        }
      },
      onError: (_) {
        _pulseController.stop();
        _pulseController.reset();
        if (!mounted) return;
        setState(() {
          _isListening = false;
        });
      },
    );
    if (!mounted) return;
    setState(() {
      _speechAvailable = available;
    });
  }

  // Show a brief message at the bottom of the screen
  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(message)));
  }

  // Send the user's typed message to the AI and show the response
  void _sendMessage() {
    final text = _controller.text.trim();
    if (text.isEmpty) return;

    // Add the user's message to the chat
    _chatStore.addMessage(ChatMessage(
      text: text,
      isUser: true,
      timestamp: DateTime.now(),
    ));
    _controller.clear();
    // Show the "typing..." indicator
    _chatStore.setTyping(true);

    // Send the message to the AI backend and get a response
    _getAIResponse(text).then((response) {
      if (mounted) {
        _chatStore.setTyping(false);
        _chatStore.addMessage(ChatMessage(
          text: response,
          isUser: false,
          timestamp: DateTime.now(),
        ));
        _speakResponse(response);
      }
    }).catchError((error) {
      if (mounted) {
        _chatStore.setTyping(false);
        const fallback =
            "Sorry, I couldn't reach the server right now. Please try again in a moment.";
        _chatStore.addMessage(ChatMessage(
          text: fallback,
          isUser: false,
          timestamp: DateTime.now(),
        ));
        _speakResponse(fallback);
      }
    });
  }

  // Toggle the microphone on/off for voice input
  Future<void> _toggleVoiceInput() async {
    if (!_speechAvailable) {
      await _initializeSpeech();
    }

    if (!_speechAvailable) {
      _showSnack('Microphone is unavailable. Please enable speech services and try again.');
      return;
    }

    // Stop any ongoing TTS before opening the mic.
    if (_isSpeaking) await _stopSpeaking();

    if (_isListening) {
      await _speech.stop();
      _pulseController.stop();
      _pulseController.reset();
      if (!mounted) return;
      setState(() {
        _isListening = false;
      });
      return;
    }

    final startedResult = await _speech.listen(
      listenMode: ListenMode.confirmation,
      partialResults: true,
      onResult: (result) {
        _controller.value = _controller.value.copyWith(
          text: result.recognizedWords,
          selection: TextSelection.collapsed(
            offset: result.recognizedWords.length,
          ),
        );
        if (result.finalResult) {
          _pulseController.stop();
          _pulseController.reset();
          if (mounted) setState(() => _isListening = false);
          _sendMessage();
        }
      },
    );

    final bool started = startedResult == true;

    if (!mounted) return;
    setState(() => _isListening = started);
    if (started) {
      _pulseController.repeat(reverse: true);
    } else {
      _showSnack('Could not start voice input. Please try again.');
    }
  }

  // Show options for what to photograph (food or pill)
  void _showCameraOptions() {
    showModalBottomSheet(
      context: context,
      builder: (sheetContext) {
        return SafeArea(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              ListTile(
                leading: const Icon(LucideIcons.utensils),
                title: const Text('Scan Food'),
                onTap: () => _captureAndAnalyze('food'),
              ),
              ListTile(
                leading: const Icon(LucideIcons.pill),
                title: const Text('Identify Pill'),
                onTap: () => _captureAndAnalyze('pill'),
              ),
            ],
          ),
        );
      },
    );
  }

  // Take a photo and send it to the AI for analysis (food or pill identification)
  Future<void> _captureAndAnalyze(String type) async {
    // Close the camera options menu
    Navigator.pop(context);

    // Open the phone camera to take a picture
    final image = await ImagePicker().pickImage(source: ImageSource.camera);
    if (image == null) return;

    _chatStore.addMessage(ChatMessage(
      text: '📷 [Analyzing $type...]',
      isUser: true,
      timestamp: DateTime.now(),
    ));
    _chatStore.setTyping(true);

    final history = _chatStore.messages
        .where((m) => m.text.isNotEmpty)
        .toList()
        .reversed
        .take(10)
        .toList()
        .reversed
        .map((m) => <String, String>{
              'role': m.isUser ? 'user' : 'assistant',
              'text': m.text,
            })
        .toList();

    try {
      final response = await widget.apiClient.postNLChatWithImage(
        File(image.path),
        'Analyze this image',
        type,
        history,
      );

      if (mounted) {
        _chatStore.addMessage(ChatMessage(
          text: response,
          isUser: false,
          timestamp: DateTime.now(),
        ));
        _speakResponse(response);
      }
    } catch (_) {
      if (mounted) {
        const fallback =
            'I could not analyze that image right now. Please try again.';
        _chatStore.addMessage(ChatMessage(
          text: fallback,
          isUser: false,
          timestamp: DateTime.now(),
        ));
        _speakResponse(fallback);
      }
    } finally {
      if (mounted) {
        _chatStore.setTyping(false);
      }
    }
  }

  // Send the user's message to the AI backend and return its response
  Future<String> _getAIResponse(String userMessage) async {
    // Build the conversation history (last 10 messages for context)
    final recentMessages = _chatStore.messages;
    final history = recentMessages
        .where((m) => m.text.isNotEmpty)
        .toList()
        .reversed
        .take(10)
        .toList()
        .reversed
        .map((m) => <String, String>{
              'role': m.isUser ? 'user' : 'assistant',
              'text': m.text,
            })
        .toList();

    try {
      final screenContext = _chatStore.currentScreen;
      final messageWithContext = '[Context: $screenContext] $userMessage';
      return await widget.apiClient.postNLChat(messageWithContext, history);
    } catch (e) {
      return "I'm having trouble connecting right now. Please try again in a moment.";
    }
  }

  @override
  void dispose() {
    if (_isListening) _speech.stop();
    _pulseController.dispose();
    _tts.stop();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Rebuild the chat UI whenever new messages arrive or typing state changes
    return Consumer<ChatStore>(
      builder: (context, store, _) {
        final messages = store.messages;
        final isTyping = store.isTyping;
        final mediaQuery = MediaQuery.of(context);
        // How much space the keyboard takes up
        final keyboardInset = mediaQuery.viewInsets.bottom;
        final screenHeight = mediaQuery.size.height;
        final safeTop = mediaQuery.padding.top;

        // The chat sheet takes 75% of the screen height
        const baseFactor = 0.75;
        double targetHeight = screenHeight * baseFactor;

        // How much room is left when the keyboard is open
        final availableHeight = screenHeight - keyboardInset - safeTop - 8;
        if (targetHeight > availableHeight) {
          targetHeight = availableHeight;
        }

        // Make sure the chat sheet doesn't get too small to use
        if (targetHeight < 260) {
          targetHeight = availableHeight > 260 ? 260 : availableHeight;
        }

        if (targetHeight < 0) {
          targetHeight = 0;
        }

        final colorScheme = Theme.of(context).colorScheme;
        return Container(
          decoration: BoxDecoration(
            color: colorScheme.surface,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
          ),
          child: AnimatedPadding(
            duration: const Duration(milliseconds: 180),
            curve: Curves.easeOut,
            padding: EdgeInsets.only(
              bottom: keyboardInset,
            ),
            child: SizedBox(
              height: targetHeight,
              child: Column(
            children: [
              // The small drag handle bar at the top of the sheet
              Container(
                margin: const EdgeInsets.symmetric(vertical: 12),
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Colors.grey[300],
                  borderRadius: BorderRadius.circular(2),
                ),
              ),

              // Chat header with AI icon, name, and online status
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
                                decoration: BoxDecoration(
                                  color: _isSpeaking
                                      ? Colors.blueAccent
                                      : AdaptivColors.stable,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 4),
                              Text(
                                _isSpeaking ? 'Speaking...' : 'Online',
                                style: AdaptivTypography.caption.copyWith(
                                  color: _isSpeaking
                                      ? Colors.blueAccent
                                      : AdaptivColors.stable,
                                ),
                              ),
                            ],
                          ),
                        ],
                      ),
                    ),
                    IconButton(
                      icon: Icon(Icons.close, color: colorScheme.onSurface),
                      onPressed: () => Navigator.pop(context),
                    ),
                    if (_isSpeaking)
                      IconButton(
                        tooltip: 'Stop speaking',
                        icon: const Icon(
                          Icons.volume_off_rounded,
                          color: Colors.redAccent,
                        ),
                        onPressed: _stopSpeaking,
                      ),
                  ],
                ),
              ),

              const Divider(height: 24),

              // Scrollable list of chat messages
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
                                    : colorScheme.surfaceContainerHighest,
                                borderRadius: BorderRadius.circular(16),
                              ),
                              child: Text(
                                message.text,
                                style: TextStyle(
                                  color: message.isUser
                                      ? Colors.white
                                      : colorScheme.onSurface,
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

              // Bottom input area with camera, mic, text field, and send button
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: colorScheme.surface,
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
                      // Camera button for food/pill scanning
                      IconButton(
                        icon: Icon(LucideIcons.camera, color: colorScheme.onSurface),
                        onPressed: isTyping ? null : _showCameraOptions,
                      ),
                      // Microphone button with pulsing ring while recording
                      SizedBox(
                        width: 48,
                        height: 48,
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            if (_isListening)
                              AnimatedBuilder(
                                animation: _pulseScale,
                                builder: (_, __) => Container(
                                  width: 40 * _pulseScale.value,
                                  height: 40 * _pulseScale.value,
                                  decoration: BoxDecoration(
                                    shape: BoxShape.circle,
                                    color: Colors.red.withValues(
                                      alpha:
                                          (1.8 - _pulseScale.value) * 0.25,
                                    ),
                                  ),
                                ),
                              ),
                            IconButton(
                              padding: EdgeInsets.zero,
                              icon: Icon(
                                _isListening
                                    ? LucideIcons.micOff
                                    : LucideIcons.mic,
                                color: _isListening ? Colors.red : colorScheme.onSurface,
                                size: 22,
                              ),
                              onPressed: isTyping ? null : _toggleVoiceInput,
                            ),
                          ],
                        ),
                      ),
                      // The text input where the user types their message
                      Expanded(
                        child: TextField(
                          controller: _controller,
                          maxLength: 500,
                          maxLines: null,
                          enabled: !isTyping,
                          decoration: InputDecoration(
                            hintText: 'Ask your health coach...',
                            filled: true,
                            fillColor: colorScheme.surfaceContainerHighest,
                            counterText: '',
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(24),
                              borderSide: BorderSide.none,
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 16,
                              vertical: 12,
                            ),
                          ),
                          onSubmitted: isTyping ? null : (_) => _sendMessage(),
                        ),
                      ),
                      const SizedBox(width: 8),
                      CircleAvatar(
                        backgroundColor: isTyping
                            ? Colors.grey
                            : AdaptivColors.primary,
                        child: IconButton(
                          icon: const Icon(Icons.send, color: Colors.white),
                          onPressed: isTyping ? null : _sendMessage,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
            ),
          ),
        );
      },
    );
  }
}
