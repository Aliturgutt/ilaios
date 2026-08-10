import 'package:flutter/material.dart';

import 'control_plane/client.dart';
import 'control_plane/config.dart';
import 'control_plane/projection.dart';

export 'control_plane/projection.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final config = await ControlPlaneConfig.fromEnvironment();
  runApp(DesktopBootstrap(config: config));
}

class DesktopBootstrap extends StatefulWidget {
  const DesktopBootstrap({required this.config, super.key});

  final ControlPlaneConfig? config;

  @override
  State<DesktopBootstrap> createState() => _DesktopBootstrapState();
}

class _DesktopBootstrapState extends State<DesktopBootstrap> {
  ControlPlaneProjection _projection = const ControlPlaneProjection.unavailable();
  ControlPlaneClient? _client;

  @override
  void initState() {
    super.initState();
    final config = widget.config;
    if (config != null) {
      try {
        _client = ControlPlaneClient(baseUri: config.baseUri, token: config.token);
        _refresh();
      } on ArgumentError {
        _projection = const ControlPlaneProjection.unavailable(
          status: 'Control plane configuration rejected',
        );
      }
    }
  }

  Future<void> _refresh() async {
    final client = _client;
    if (client == null) {
      return;
    }
    try {
      final projection = await client.fetchProjection();
      if (!mounted) {
        return;
      }
      setState(() => _projection = projection);
    } on ControlPlaneClientException catch (error) {
      if (!mounted) {
        return;
      }
      setState(
        () => _projection = ControlPlaneProjection.unavailable(
          status: error.message,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return IlaiosDesktopApp(
      projection: _projection,
      onRefreshRequested: _client == null ? null : _refresh,
    );
  }
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
              runSpacing: 16,
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
