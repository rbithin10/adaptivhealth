/*
In-memory store for AI Health Coach chat messages.

Keeps conversation history alive for the entire app session so that
closing and re-opening the chat bottom sheet does not lose messages.
The data is not persisted across app restarts.
*/

import 'package:flutter/foundation.dart';

/// A single chat message exchanged with the AI Health Coach.
class ChatMessage {
  final String text;
  final bool isUser;
  final DateTime timestamp;

  ChatMessage({
    required this.text,
    required this.isUser,
    required this.timestamp,
  });
}

/// Session-scoped store for chat messages.
///
/// Provided via [ChangeNotifierProvider] at the app level so the
/// conversation survives bottom-sheet dismissals.
class ChatStore extends ChangeNotifier {
  final List<ChatMessage> _messages = [];

  /// Whether the AI is currently generating a response.
  bool _isTyping = false;

  // ---------------------------------------------------------------------------
  // Public getters
  // ---------------------------------------------------------------------------

  /// Unmodifiable view of the current message list.
  List<ChatMessage> get messages => List.unmodifiable(_messages);

  bool get isTyping => _isTyping;

  // ---------------------------------------------------------------------------
  // Mutations
  // ---------------------------------------------------------------------------

  /// Seed the conversation with greeting messages.
  ///
  /// Only adds the greetings when the message list is empty, so re-opening
  /// the sheet after a conversation does not duplicate them.
  void ensureGreeting() {
    if (_messages.isNotEmpty) return;

    _messages.addAll([
      ChatMessage(
        text: "Hi! 👋 I'm your AI Health Coach.",
        isUser: false,
        timestamp: DateTime.now(),
      ),
      ChatMessage(
        text: "How can I help you today?",
        isUser: false,
        timestamp: DateTime.now(),
      ),
    ]);
    notifyListeners();
  }

  /// Append a message (user or bot) to the conversation.
  void addMessage(ChatMessage message) {
    _messages.add(message);
    notifyListeners();
  }

  /// Update the typing indicator state.
  void setTyping(bool value) {
    if (_isTyping == value) return;
    _isTyping = value;
    notifyListeners();
  }

  /// Remove all messages and reset typing state.
  ///
  /// Useful if you add a "clear chat" action later.
  void clear() {
    _messages.clear();
    _isTyping = false;
    notifyListeners();
  }
}
