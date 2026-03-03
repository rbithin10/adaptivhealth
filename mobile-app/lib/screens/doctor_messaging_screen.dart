import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'dart:async';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';
import '../theme/colors.dart';
import '../theme/typography.dart';
import '../services/api_client.dart';
import '../providers/chat_provider.dart';

class DoctorMessagingScreen extends StatefulWidget {
  final ApiClient apiClient;

  const DoctorMessagingScreen({super.key, required this.apiClient});

  @override
  State<DoctorMessagingScreen> createState() => _DoctorMessagingScreenState();
}

class _DoctorMessagingScreenState extends State<DoctorMessagingScreen> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();

  bool _isLoading = false;
  bool _isSending = false;
  bool _isLoadingClinician = true;
  String? _errorMessage;
  int? _currentUserId;
  int? _clinicianId; // Real clinician ID from backend
  String _clinicianName = 'Loading...';
  List<Map<String, dynamic>> _messages = [];
  Timer? _autoRefreshTimer;

  @override
  void initState() {
    super.initState();
    _loadClinicianAndThread();
    // Auto-refresh every 10 seconds
    _autoRefreshTimer = Timer.periodic(
      const Duration(seconds: 10),
      (_) => _refreshThreadSilently(),
    );
  }

  /// Load assigned clinician, then fetch message thread.
  /// Gets clinician from GET /users/me/clinician endpoint.
  /// Returns 404 if no clinician assigned (admin needs to assign one).
  Future<void> _loadClinicianAndThread() async {
    setState(() {
      _isLoadingClinician = true;
      _errorMessage = null;
    });

    try {
      // Fetch assigned clinician from backend
      final clinicianData = await widget.apiClient.getAssignedClinician();
      
      if (clinicianData == null) {
        if (!mounted) return;
        setState(() {
          _errorMessage = 'No clinician assigned. Please contact your healthcare provider or administrator.';
          _isLoadingClinician = false;
        });
        return;
      }

      final clinicianId = clinicianData['user_id'] as int?;
      final clinicianName = clinicianData['full_name'] as String? ?? 'Your Clinician';

      if (clinicianId == null) {
        if (!mounted) return;
        setState(() {
          _errorMessage = 'Invalid clinician data. Please contact support.';
          _isLoadingClinician = false;
        });
        return;
      }

      if (!mounted) return;
      setState(() {
        _clinicianId = clinicianId;
        _clinicianName = clinicianName;
        _isLoadingClinician = false;
      });

      // Now load the message thread
      await _loadThread();
    } catch (e) {
      if (!mounted) return;
      // Parse error message for better UX
      String errorMsg = 'Unable to connect to clinician';
      if (e.toString().contains('403')) {
        errorMsg = 'Unable to load clinician. Your access may have changed.';
      } else if (e.toString().contains('404')) {
        errorMsg = 'No clinician assigned. Please contact your healthcare provider or administrator.';
      } else if (e.toString().contains('Connection')) {
        errorMsg = 'Connection error. Please check your internet.';
      }
      setState(() {
        _errorMessage = errorMsg;
        _isLoadingClinician = false;
      });
    }
  }

  @override
  void dispose() {
    _autoRefreshTimer?.cancel();
    _messageController.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _loadThread() async {
    // Don't load thread if clinician not assigned
    if (_clinicianId == null) {
      return;
    }

    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final user = await widget.apiClient.getCurrentUser();
      final userId = user['user_id'] as int? ?? user['id'] as int?;
      final chatProvider = context.read<ChatProvider>();
      await chatProvider.loadHistory(clinicianId: _clinicianId!, limit: 50);
      final messages = chatProvider.messages
          .map((message) => <String, dynamic>{
                'message_id': message.messageId,
                'sender_id': message.senderId,
                'receiver_id': message.receiverId,
                'content': message.content,
                'sent_at': message.sentAt?.toIso8601String(),
                'is_read': message.isRead,
              })
          .toList();

      if (!mounted) return;
      setState(() {
        _currentUserId = userId;
        _messages = messages;
        _isLoading = false;
      });

      _scrollToBottom();
      // Mark unread messages as read
      _markUnreadMessagesAsRead();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _errorMessage = e.toString();
        _isLoading = false;
      });
    }
  }

  /// Refresh thread without showing loading indicator (for auto-refresh)
  Future<void> _refreshThreadSilently() async {
    if (_clinicianId == null || _isLoading || _isSending) {
      return;
    }

    try {
      final chatProvider = context.read<ChatProvider>();
      await chatProvider.loadHistory(clinicianId: _clinicianId!, limit: 50);
      final messages = chatProvider.messages
          .map((message) => <String, dynamic>{
                'message_id': message.messageId,
                'sender_id': message.senderId,
                'receiver_id': message.receiverId,
                'content': message.content,
                'sent_at': message.sentAt?.toIso8601String(),
                'is_read': message.isRead,
              })
          .toList();

      if (!mounted) return;
      
      // Only update if we have new messages
      if (messages.length != _messages.length) {
        setState(() {
          _messages = messages;
        });
        _scrollToBottom();
        _markUnreadMessagesAsRead();
      }
    } catch (e) {
      // Silently ignore errors during auto-refresh
      if (kDebugMode) debugPrint('Auto-refresh failed: $e');
    }
  }

  /// Mark all unread messages from clinician as read
  Future<void> _markUnreadMessagesAsRead() async {
    if (_currentUserId == null || _clinicianId == null) return;

    for (final message in _messages) {
      final isRead = message['is_read'] as bool? ?? false;
      final senderId = message['sender_id'] as int?;
      final messageId = message['message_id'] as int?;

      // Mark as read if:
      // 1. Message is not read
      // 2. Message is from clinician (not sent by us)
      // 3. We have a valid message ID
      if (!isRead && senderId == _clinicianId && messageId != null) {
        try {
          await widget.apiClient.markMessageRead(messageId);
          // Update local state
          message['is_read'] = true;
          message['read_at'] = DateTime.now().toIso8601String();
        } catch (e) {
          if (kDebugMode) {
            debugPrint('Failed to mark message $messageId as read: $e');
          }
        }
      }
    }
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _isSending || _clinicianId == null) return;

    setState(() {
      _isSending = true;
    });

    try {
      final chatProvider = context.read<ChatProvider>();
      await chatProvider.sendMessage(
        receiverId: _clinicianId!,
        content: text,
      );
      _messageController.clear();
      await _loadThread();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Error: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  void _scrollToBottom() {
    if (!_scrollController.hasClients) return;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      _scrollController.animateTo(
        _scrollController.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    });
  }

  bool _isSentByCurrentUser(Map<String, dynamic> message) {
    final senderId = message['sender_id'] as int?;
    return _currentUserId != null && senderId == _currentUserId;
  }

  @override
  Widget build(BuildContext context) {
    final brightness = MediaQuery.of(context).platformBrightness;
    return Container(
      color: AdaptivColors.getBackgroundColor(brightness),
      child: Column(
        children: [
          // Inline header (replaces AppBar for tab embedding)
          Container(
            color: AdaptivColors.getSurfaceColor(brightness),
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              children: [
                Text('Messages', style: AdaptivTypography.screenTitle),
              ],
            ),
          ),
          _buildCareTeamHeader(),
          Expanded(child: _buildThreadBody()),
          _buildMessageComposer(),
        ],
      ),
    );
  }

  Widget _buildCareTeamHeader() {
    return Card(
      margin: const EdgeInsets.all(16),
      child: ListTile(
        leading: const Icon(Icons.medical_services, color: AdaptivColors.primary),
        title: const Text('Care Team'),
        subtitle: _isLoadingClinician
            ? const Text('Loading clinician...')
            : Text(_clinicianName),
        trailing: _clinicianId != null
            ? TextButton(
                onPressed: _loadThread,
                child: const Text('Refresh'),
              )
            : null,
      ),
    );
  }

  Widget _buildThreadBody() {
    // Show loading state while fetching clinician
    if (_isLoadingClinician) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(),
            SizedBox(height: 16),
            Text('Loading your care team...'),
          ],
        ),
      );
    }

    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.error_outline,
                size: 64,
                color: AdaptivColors.critical,
              ),
              const SizedBox(height: 16),
              Text(
                _clinicianId == null ? 'No Clinician Assigned' : 'Failed to load messages',
                style: AdaptivTypography.sectionTitle,
              ),
              const SizedBox(height: 8),
              Text(_errorMessage!, style: AdaptivTypography.body, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton.icon(
                onPressed: _clinicianId == null ? _loadClinicianAndThread : _loadThread,
                icon: const Icon(Icons.refresh),
                label: const Text('Retry'),
              ),
            ],
          ),
        ),
      );
    }

    if (_messages.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.chat_bubble_outline,
                size: 64,
                color: AdaptivColors.text400,
              ),
              const SizedBox(height: 16),
              Text(
                'No messages yet',
                style: AdaptivTypography.sectionTitle,
              ),
              const SizedBox(height: 8),
              Text(
                'Start a conversation with your clinician',
                style: AdaptivTypography.body.copyWith(
                  color: AdaptivColors.text600,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: _loadThread,
      child: ListView.builder(
        controller: _scrollController,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        itemCount: _messages.length,
        itemBuilder: (context, index) {
          final message = _messages[index];
          return _buildMessageBubble(message);
        },
      ),
    );
  }

  Widget _buildMessageBubble(Map<String, dynamic> message) {
    final isSent = _isSentByCurrentUser(message);
    final content = message['content'] as String? ?? '';
    final sentAt = message['sent_at'] as String?;
    final isRead = message['is_read'] as bool? ?? false;
    final readAt = message['read_at'] as String?;
    
    final timestamp = sentAt != null ? DateTime.tryParse(sentAt) : null;
    final timeLabel = _formatTimestamp(timestamp);

    return Align(
      alignment: isSent ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        constraints: const BoxConstraints(maxWidth: 280),
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isSent ? AdaptivColors.primary : AdaptivColors.white,
          borderRadius: BorderRadius.circular(12),
          border: isSent ? null : Border.all(color: AdaptivColors.border300),
        ),
        child: Column(
          crossAxisAlignment: isSent ? CrossAxisAlignment.end : CrossAxisAlignment.start,
          children: [
            Text(
              content,
              style: AdaptivTypography.body.copyWith(
                color: isSent ? AdaptivColors.white : AdaptivColors.text900,
              ),
            ),
            const SizedBox(height: 4),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  timeLabel,
                  style: AdaptivTypography.caption.copyWith(
                    color: isSent ? AdaptivColors.primaryLight : AdaptivColors.text500,
                  ),
                ),
                if (isSent) ...[
                  const SizedBox(width: 4),
                  Icon(
                    isRead ? Icons.done_all : Icons.done,
                    size: 14,
                    color: isRead ? AdaptivColors.stable : AdaptivColors.primaryLight,
                  ),
                ],
              ],
            ),
          ],
        ),
      ),
    );
  }

  String _formatTimestamp(DateTime? timestamp) {
    if (timestamp == null) return '';
    
    final now = DateTime.now();
    final today = DateTime(now.year, now.month, now.day);
    final messageDate = DateTime(timestamp.year, timestamp.month, timestamp.day);
    
    if (messageDate == today) {
      // Today: show time only
      return DateFormat('HH:mm').format(timestamp);
    } else if (messageDate == today.subtract(const Duration(days: 1))) {
      // Yesterday
      return 'Yesterday ${DateFormat('HH:mm').format(timestamp)}';
    } else if (now.difference(timestamp).inDays < 7) {
      // Last 7 days: show day name
      return DateFormat('EEE HH:mm').format(timestamp);
    } else {
      // Older: show date
      return DateFormat('MMM d, HH:mm').format(timestamp);
    }
  }

  Widget _buildMessageComposer() {
    final canSend = _clinicianId != null && !_isSending;
    final placeholder = _clinicianId == null
        ? 'No clinician assigned'
        : 'Type your message...';

    return SafeArea(
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: AdaptivColors.white,
          border: Border(top: BorderSide(color: AdaptivColors.border300)),
        ),
        child: Row(
          children: [
            Expanded(
              child: TextField(
                controller: _messageController,
                enabled: _clinicianId != null,
                decoration: InputDecoration(
                  hintText: placeholder,
                  border: const OutlineInputBorder(),
                  isDense: true,
                ),
                minLines: 1,
                maxLines: 3,
                textInputAction: TextInputAction.send,
                onSubmitted: canSend ? (_) => _sendMessage() : null,
              ),
            ),
            const SizedBox(width: 8),
            ElevatedButton(
              onPressed: canSend ? _sendMessage : null,
              child: _isSending
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Send'),
            ),
          ],
        ),
      ),
    );
  }
}
