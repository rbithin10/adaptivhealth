import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../features/ai/ai_store.dart';
import 'ai_plan_screen.dart';

class AiHomeScreen extends StatefulWidget {
  const AiHomeScreen({super.key});
  @override
  State<AiHomeScreen> createState() => _AiHomeScreenState();
}

class _AiHomeScreenState extends State<AiHomeScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => context.read<AiStore>().loadHome());
    Future.microtask(() => context.read<AiStore>().loadAICoachSummaries());
  }

  @override
  Widget build(BuildContext context) {
    final store = context.watch<AiStore>();

    return Scaffold(
      appBar: AppBar(title: const Text('Adaptiv Home')),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: store.loading
            ? const Center(child: CircularProgressIndicator())
            : store.error != null
                ? _ErrorBox(message: store.error!, onRetry: store.loadHome)
                : ListView(
                    children: [
                      _VitalsCard(vitals: store.latestVitals),
                      const SizedBox(height: 12),
                      _RiskCard(risk: store.latestRisk),
                      const SizedBox(height: 12),
                      ElevatedButton(
                        onPressed: store.computeAiAndRefresh,
                        child: const Text('Compute AI Now'),
                      ),
                      const SizedBox(height: 12),
                      OutlinedButton(
                        onPressed: () {
                          Navigator.push(
                            context,
                            MaterialPageRoute(builder: (_) => const AiPlanScreen()),
                          );
                        },
                        child: const Text('View Today\'s Plan'),
                      )
                    ],
                  ),
      ),
    );
  }
}

class _VitalsCard extends StatelessWidget {
  final Map<String, dynamic>? vitals;
  const _VitalsCard({required this.vitals});

  @override
  Widget build(BuildContext context) {
    if (vitals == null) {
      return const Card(child: Padding(padding: EdgeInsets.all(16), child: Text("No vitals yet.")));
    }

    final hr = vitals!['heart_rate']?.toString() ?? '-';
    final spo2 = vitals!['spo2']?.toString() ?? '-';
    final bpSys = vitals!['systolic_bp']?.toString() ?? '-';
    final bpDia = vitals!['diastolic_bp']?.toString() ?? '-';
    final ts = vitals!['timestamp']?.toString() ?? '-';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('Latest Vitals', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('HR: $hr bpm'),
          Text('SpO₂: $spo2 %'),
          Text('BP: $bpSys / $bpDia'),
          const SizedBox(height: 8),
          Text('Updated: $ts', style: const TextStyle(fontSize: 12)),
        ]),
      ),
    );
  }
}

class _RiskCard extends StatelessWidget {
  final Map<String, dynamic>? risk;
  const _RiskCard({required this.risk});

  @override
  Widget build(BuildContext context) {
    if (risk == null) {
      return const Card(child: Padding(padding: EdgeInsets.all(16), child: Text("No risk assessment yet.")));
    }

    final level = (risk!['risk_level']?.toString() ?? 'unknown').toUpperCase();
    final score = risk!['risk_score']?.toString() ?? '-';
    final drivers = (risk!['drivers'] as List?)?.map((e) => e.toString()).toList() ?? [];

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('AI Risk Status', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          Text('Level: $level'),
          Text('Score: $score'),
          const SizedBox(height: 8),
          const Text('Why?', style: TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 6),
          if (drivers.isEmpty) const Text('No drivers available.'),
          for (final d in drivers) Text('• $d'),
        ]),
      ),
    );
  }
}

class _ErrorBox extends StatelessWidget {
  final String message;
  final Future<void> Function() onRetry;

  const _ErrorBox({required this.message, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(message, textAlign: TextAlign.center),
        const SizedBox(height: 12),
        ElevatedButton(onPressed: onRetry, child: const Text("Retry"))
      ]),
    );
  }
}
