import 'package:flutter/material.dart';

void main() {
  runApp(const IlaiosDesktopApp());
}

@immutable
class ControlPlaneProjection {
  const ControlPlaneProjection({
    required this.connected,
    required this.status,
    required this.goalCount,
    required this.jobCount,
    required this.lastEvent,
  });

  const ControlPlaneProjection.unavailable()
    : connected = false,
      status = 'Authoritative control plane unavailable',
      goalCount = null,
      jobCount = null,
      lastEvent = null;

  final bool connected;
  final String status;
  final int? goalCount;
  final int? jobCount;
  final String? lastEvent;
}

class IlaiosDesktopApp extends StatelessWidget {
  const IlaiosDesktopApp({
    super.key,
    this.projection = const ControlPlaneProjection.unavailable(),
    this.onRefreshRequested,
  });

  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'ILAIOS Desktop',
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF3154A4)),
      ),
      home: DesktopShell(
        projection: projection,
        onRefreshRequested: onRefreshRequested,
      ),
    );
  }
}

class DesktopShell extends StatelessWidget {
  const DesktopShell({
    required this.projection,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;

  String _count(int? value) => value?.toString() ?? '—';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('ILAIOS Control Desktop')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Semantics(
              label: 'Control plane connection status',
              child: Text(
                projection.status,
                key: const Key('connection-status'),
                style: Theme.of(context).textTheme.titleLarge,
              ),
            ),
            const SizedBox(height: 24),
            Wrap(
              spacing: 16,
              children: [
                _ProjectionCard(
                  label: 'Goals',
                  value: _count(projection.goalCount),
                ),
                _ProjectionCard(
                  label: 'Jobs',
                  value: _count(projection.jobCount),
                ),
                _ProjectionCard(
                  label: 'Last event',
                  value: projection.lastEvent ?? '—',
                ),
              ],
            ),
            const SizedBox(height: 24),
            FilledButton.icon(
              key: const Key('refresh-command'),
              onPressed: projection.connected ? onRefreshRequested : null,
              icon: const Icon(Icons.refresh),
              label: const Text('Request authoritative refresh'),
            ),
            const SizedBox(height: 12),
            const Text(
              'This desktop is a command/query/event projection. '
              'It does not own authoritative goal or job state.',
            ),
          ],
        ),
      ),
    );
  }
}

class _ProjectionCard extends StatelessWidget {
  const _ProjectionCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        width: 180,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label),
              const SizedBox(height: 8),
              Text(value, style: Theme.of(context).textTheme.headlineSmall),
            ],
          ),
        ),
      ),
    );
  }
}
