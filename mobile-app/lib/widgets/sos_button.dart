/*
SOS Emergency Button.

A red circular button that appears in the app bar. When pressed, it:
1. Asks the user to confirm they're having an emergency
2. Sends a CRITICAL alert to the care team via the server
3. Tries to capture the user's GPS location for emergency services
4. Tries to call the user's emergency contact phone number

Each step is optional — if one fails, the others still run.
*/

import 'package:flutter/material.dart';
// Lucide icons library for the phone-call icon
import 'package:lucide_icons/lucide_icons.dart';
// Provider lets us access shared app services
import 'package:provider/provider.dart';
// url_launcher lets us open the phone dialer
import 'package:url_launcher/url_launcher.dart';

// Our server communication helper
import '../services/api_client.dart';
// Edge AI service that can capture GPS location
import '../services/edge_ai_store.dart';

// The SOS button widget — shows a red circle in the top bar
class SOSButton extends StatefulWidget {
  // We need the API client to send the SOS alert to the server
  final ApiClient apiClient;

  const SOSButton({super.key, required this.apiClient});

  @override
  State<SOSButton> createState() => _SOSButtonState();
}

class _SOSButtonState extends State<SOSButton> {
  // Tracks whether an SOS is currently being sent (prevents double-taps)
  bool _isSending = false;

  // Called when the user taps the SOS button
  Future<void> _handleTap() async {
    // If we're already sending an SOS, ignore extra taps
    if (_isSending) return;

    // Show a confirmation dialog — we don't want accidental SOS alerts
    final shouldSend = await showDialog<bool>(
      context: context,
      builder: (dialogContext) {
        return AlertDialog(
          title: const Text('Emergency SOS'),
          content: const Text(
            'Are you having a cardiac emergency? This will alert your care team and emergency contact.',
          ),
          actions: [
            // Cancel button — just closes the dialog without doing anything
            TextButton(
              onPressed: () => Navigator.pop(dialogContext, false),
              child: const Text('Cancel'),
            ),
            // Confirm button — returns true to trigger the SOS
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

    // If user cancelled or the screen is no longer visible, stop here
    if (shouldSend != true || !mounted) return;

    // Mark that we're now sending — this disables the button and shows a spinner
    setState(() {
      _isSending = true;
    });

    try {
      // Step 1: Send the SOS alert to the server (notifies care team)
      await widget.apiClient.createAlert(
        alertType: 'SOS',
        severity: 'CRITICAL',
        notes: 'Manual SOS triggered by patient',
      );

      // Step 2: Try to capture and send the user's GPS location
      try {
        final edgeStore = Provider.of<EdgeAiStore>(context, listen: false);
        await (edgeStore as dynamic).captureEmergencyLocation();
      } catch (_) {
        // GPS is optional — if it fails, the SOS alert was already sent above
      }

      // Step 3: Try to call the user's emergency contact phone number
      try {
        // Get the user's profile to find their emergency contact
        final profile = await widget.apiClient.getCurrentUser();
        // The field name varies between server versions, so we check both
        final emergencyPhone =
            (profile['emergency_contact_phone'] ?? profile['emergencyContactPhone'])
                ?.toString()
                .trim();

        // If we found a phone number, open the phone dialer
        if (emergencyPhone != null && emergencyPhone.isNotEmpty) {
          final telUri = Uri.parse('tel:$emergencyPhone');
          // Check if the phone can make calls before trying
          if (await canLaunchUrl(telUri)) {
            await launchUrl(telUri);
          }
        }
      } catch (_) {
        // Phone call is best-effort — don't let it block the SOS flow
      }

      // Show a success message at the bottom of the screen
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('SOS alert sent. Your care team has been notified.'),
          ),
        );
      }
    } catch (e) {
      // If the main SOS alert failed, show an error message
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to send SOS alert: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    } finally {
      // Reset the button so it can be used again
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
      // Red circular button
      child: Material(
        color: Colors.red,
        shape: const CircleBorder(),
        child: InkWell(
          customBorder: const CircleBorder(),
          // Disable taps while an SOS is being sent
          onTap: _isSending ? null : _handleTap,
          child: SizedBox(
            width: 36,
            height: 36,
            child: Center(
              // Show a spinner while sending, or the phone icon when ready
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
