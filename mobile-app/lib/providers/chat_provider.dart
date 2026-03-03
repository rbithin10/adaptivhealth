import 'package:flutter/foundation.dart';

import '../services/api_client.dart';

class ChatMessage {
  final int? messageId;
  final int senderId;
  final int receiverId;
  final String content;
  final DateTime? sentAt;
  final bool isRead;

  const ChatMessage({
    this.messageId,
    required this.senderId,
    required this.receiverId,
    required this.content,
    this.sentAt,
    this.isRead = false,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      messageId: json['message_id'] as int?,
      senderId: (json['sender_id'] as num?)?.toInt() ?? 0,
      receiverId: (json['receiver_id'] as num?)?.toInt() ?? 0,
      content: (json['content'] as String?) ?? '',
      sentAt: json['sent_at'] is String ? DateTime.tryParse(json['sent_at']) : null,
      isRead: json['is_read'] as bool? ?? false,
    );
  }
}

class ChatProvider extends ChangeNotifier {
  final ApiClient _apiClient;

  ChatProvider({required ApiClient apiClient}) : _apiClient = apiClient;

  List<ChatMessage> messages = [];
  bool isLoading = false;
  String? errorMessage;

  Future<void> loadHistory({required int clinicianId, int limit = 50}) async {
    isLoading = true;
    errorMessage = null;
    notifyListeners();

    try {
      final response = await _apiClient.getMessageThread(clinicianId, limit: limit);
      messages = response
          .map((item) => ChatMessage.fromJson(Map<String, dynamic>.from(item)))
          .toList();
    } catch (e) {
      errorMessage = e.toString();
    } finally {
      isLoading = false;
      notifyListeners();
    }
  }

  Future<void> sendMessage({
    required int receiverId,
    required String content,
  }) async {
    try {
      await _apiClient.sendMessage(receiverId: receiverId, content: content);
      await loadHistory(clinicianId: receiverId);
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
    }
  }
}
