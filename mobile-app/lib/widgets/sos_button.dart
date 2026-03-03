import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../services/api_client.dart';
import '../services/edge_ai_store.dart';

class SOSButton extends StatefulWidget {
  final ApiClient apiClient;

  const SOSButton({super.key, required this.apiClient});

  @override
  State<SOSButton> createState() => _SOSButtonState();
}

class _SOSButtonState extends State<SOSButton> {
  bool _isSending = false;

  Future<void> _handleTap() async {
    if (_isSending) return;

    final shouldSend = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Emergency SOS'),
          content: const Text(
            'Are you having a cardiac emergency? This will alert your care team and emergency contact.',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            FilledButton(
              style: FilledButton.styleFrom(
                backgroundColor: Colors.red,
                foregroundColor: Colors.white,
              ),
              onPressed: () => Navigator.pop(dialogContext, true),
              child: const Text('Send SOS'),
            ),
          ],
        );
      },
    );

    if (shouldSend != true || !mounted) return;

    setState(() {
      _isSending = true;
    });

    try {
      await widget.apiClient.createAlert(
        alertType: 'SOS',
        severity: 'CRITICAL',
        notes: 'Manual SOS triggered by patient',
      );

      try {
        final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
        await (edgeStore as dynamic).captureEmergencyLocation();
      } catch (_) {
        // Optional capability; continue SOS flow without failing.
      }

      try {
        final profile = await widget.apiClient.getCurrentUser();
        final emergencyPhone =
            (profile['emergency_contact_phone'] ?? profile['emergencyContactPhone'])
                ?.toString()
                .trim();

        if (emergencyPhone != null && emergencyPhone.isNotEmpty) {
          final telUri = Uri.parse('tel:$emergencyPhone');
          if (await canLaunchUrl(telUri)) {
            await launchUrl(telUri);
          }
        }
      } catch (_) {
        // Phone call is best-effort only.
      }

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('SOS alert sent. Your care team has been notified.'),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to send SOS alert: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() {
          _isSending = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(right: 8),
      child: Material(
        color: Colors.red,
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          onTap: _isSending ? null : _handleTap,
          child: SizedBox(
            width: 36,
            height: 36,
            child: Center(
              child: _isSending
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(
                      LucideIcons.phoneCall,
                      size: 16,
                      color: Colors.white,
                    ),
            ),
          ),
        ),
      ),
    );
  }
}
