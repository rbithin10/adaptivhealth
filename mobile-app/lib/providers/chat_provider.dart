/*
Chat Provider.

Manages the messaging conversation between the patient and their doctor.
Loads message history from the server, sends new messages, and keeps
the message list up to date so the chat screen always shows the latest.
*/

// Lets us notify the chat screen whenever new messages arrive
import 'package:flutter/foundation.dart';

// Our helper that talks to the backend server
import '../services/api_client.dart';

// Represents a single chat message between patient and doctor
class ChatMessage {
  final int? messageId;       // Unique ID for this message on the server
  final int senderId;         // Who sent it (user ID of sender)
  final int receiverId;       // Who it's going to (user ID of receiver)
  final String content;       // The actual message text
  final DateTime? sentAt;     // When the message was sent
  final bool isRead;          // Whether the receiver has seen this message

  const ChatMessage({
    this.messageId,
    required this.senderId,
    required this.receiverId,
    required this.content,
    this.sentAt,
    this.isRead = false,
  });

  // Build a ChatMessage from the JSON data the server sends back
  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      messageId: json['message_id'] as int?,
      // Convert to int safely — the server might send it as a decimal number
      senderId: (json['sender_id'] as num?)?.toInt() ?? 0,
      receiverId: (json['receiver_id'] as num?)?.toInt() ?? 0,
      // If content is missing, use an empty string so we don't crash
      content: (json['content'] as String?) ?? '',
      // Parse the date string into an actual date object (if present)
      sentAt: json['sent_at'] is String ? DateTime.tryParse(json['sent_at']) : null,
      isRead: json['is_read'] as bool? ?? false,
    );
  }
}

// This class manages the full chat conversation.
// The chat screen listens to it and updates automatically when messages change.
class ChatProvider extends ChangeNotifier {
  // The API helper we use to talk to the server
  final ApiClient _apiClient;

  ChatProvider({required ApiClient apiClient}) : _apiClient = apiClient;

  List<ChatMessage> messages = [];   // All messages in the current conversation
  bool isLoading = false;            // True while loading messages from the server
  String? errorMessage;              // Holds any error to show the user

  // Load the conversation history with a specific doctor
  Future<void> loadHistory({required int clinicianId, int limit = 50}) async {
    // Show a loading spinner while we fetch messages
    isLoading = true;
    errorMessage = null;
    notifyListeners(); // Tell the chat screen to show loading state

    try {
      // Ask the server for the latest messages with this doctor
      final response = await _apiClient.getMessageThread(clinicianId, limit: limit);
      // Convert each raw server response into a ChatMessage object
      messages = response
          .map((item) => ChatMessage.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    } catch (e) {
      // If something went wrong, save the error for the chat screen to display
      errorMessage = e.toString();
    } finally {
      // Stop showing the loading spinner
      isLoading = false;
      notifyListeners(); // Tell the chat screen to refresh with the new messages
    }
  }

  // Send a new message to the doctor and then reload the conversation
  Future<void> sendMessage({
    required int receiverId,
    required String content,
  }) async {
    try {
      // Send the message text to the server
      await _apiClient.sendMessage(receiverId: receiverId, content: content);
      // Reload the full conversation so the new message appears on screen
      await loadHistory(clinicianId: receiverId);
    } catch (e) {
      // If sending failed, save the error so the chat screen can show it
      errorMessage = e.toString();
      notifyListeners(); // Tell the chat screen to show the error
    }
  }
}
