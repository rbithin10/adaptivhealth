/*
Chat Store.

Keeps the AI Health Coach conversation in memory while the app is open.
When the user closes the chat window and reopens it, all messages are
still there. Messages are NOT saved between app restarts.
*/

// Lets us notify screens when new messages arrive
import 'package:flutter/foundation.dart';

// Represents one message in the chat (either from the user or the AI)
class ChatMessage {
  // The actual text of the message
  final String text;
  // True if the user sent this message, false if the AI sent it
  final bool isUser;
  // When the message was sent
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}

// Stores all chat messages and tells the chat screen to update when new ones arrive
class ChatStore extends ChangeNotifier {
  // The list of all messages in the conversation
  final List<ChatMessage> _messages = [];

  // Whether the AI is currently thinking of a response
  bool _isTyping = false;

  // Which screen the user is on right now (helps the AI give relevant answers)
  String _currentScreen = 'home';

  // ---- Read-only access to the data ----

  // Get a copy of all messages (screens can read but not modify directly)
  List<ChatMessage> get messages => List.unmodifiable(_messages);

  // Check if the AI is currently typing a response
  bool get isTyping => _isTyping;

  // Get which screen the user is currently viewing
  String get currentScreen => _currentScreen;

  // Update which screen the user is on (so the AI can give context-aware help)
  set currentScreen(String value) {
    // Don't bother updating if it's the same screen
    if (_currentScreen == value) return;
    _currentScreen = value;
    // Tell the chat screen about the change
    notifyListeners();
  }

  // ---- Add and manage messages ----

  // Add a welcome greeting if the conversation is empty (first time opening chat)
  void ensureGreeting() {
    // Only add greetings if no messages exist yet
    if (_messages.isNotEmpty) return;

    // Add two welcome messages from the AI coach
    _messages.addAll([
      ChatMessage(
        text: "Hi! I'm your AI Health Coach.",
        isUser: false,
        timestamp: DateTime.now(),
      ),
      ChatMessage(
        text: "How can I help you today?",
        isUser: false,
        timestamp: DateTime.now(),
      ),
    ]);
    // Tell the chat screen to show the new messages
    notifyListeners();
  }

  // Add a new message to the conversation (from either the user or the AI)
  void addMessage(ChatMessage message) {
    _messages.add(message);
    // Tell the chat screen to show the new message
    notifyListeners();
  }

  // Show or hide the "AI is typing..." indicator
  void setTyping(bool value) {
    // Don't bother updating if the value hasn't changed
    if (_isTyping == value) return;
    _isTyping = value;
    // Tell the chat screen to update the typing indicator
    notifyListeners();
  }

  // Delete all messages and reset — used if a "clear chat" button is added later
  void clear() {
    _messages.clear();
    _isTyping = false;
    // Tell the chat screen to refresh (now empty)
    notifyListeners();
  }
}
