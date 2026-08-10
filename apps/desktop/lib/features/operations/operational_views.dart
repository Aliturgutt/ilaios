import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';

class LiveExecutionView extends StatelessWidget {
  const LiveExecutionView({
    required this.projection,
    required this.snapshot,
    required this.status,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;

  int _listLength(Map<String, Object?> source, String key) {
    final value = source[key];
    return value is List<Object?> ? value.length : 0;
  }

  String _lastEventType() {
    if (snapshot.liveEvents.isEmpty) {
      return '—';
    }
    final value = snapshot.liveEvents.last['event_type'];
    return value is String ? value : '—';
  }

  @override
  Widget build(BuildContext context) {
    return _SurfaceFrame(
      title: 'Live Execution',
      icon: Icons.play_circle_outline,
      status: status,
      child: Wrap(
        spacing: 14,
        runSpacing: 14,
        children: [
          _OperationalCard(label: 'Runtime routes', value: '${snapshot.runtimeRouteCount}'),
          _OperationalCard(label: 'Live events', value: '${snapshot.liveEventCount}'),
          _OperationalCard(label: 'Active leases', value: '${_listLength(snapshot.schedulerState, 'leases')}'),
          _OperationalCard(label: 'Recorded effects', value: '${_listLength(snapshot.schedulerState, 'effects')}'),
          _OperationalCard(label: 'Last live event', value: _lastEventType()),
          _OperationalCard(label: 'Control plane', value: projection.connected ? 'Connected' : 'Offline'),
        ],
      ),
    );
  }
}

class EvidenceView extends StatelessWidget {
  const EvidenceView({required this.snapshot, required this.status, super.key});

  final OperationalSnapshot snapshot;
  final String status;

  String _lastDigest() {
    if (snapshot.evidenceRecords.isEmpty) {
      return '—';
    }
    final value = snapshot.evidenceRecords.last['digest'];
    if (value is! String || value.isEmpty) {
      return 'Verified record present';
    }
    return value.length <= 18 ? value : '${value.substring(0, 18)}…';
  }

  @override
  Widget build(BuildContext context) {
    return _SurfaceFrame(
      title: 'Evidence',
      icon: Icons.fact_check_outlined,
      status: status,
      child: Wrap(
        spacing: 14,
        runSpacing: 14,
        children: [
          _OperationalCard(label: 'Verified records', value: '${snapshot.evidenceCount}'),
          _OperationalCard(label: 'Latest digest', value: _lastDigest()),
        ],
      ),
    );
  }
}

class GovernanceView extends StatelessWidget {
  const GovernanceView({required this.snapshot, required this.status, super.key});

  final OperationalSnapshot snapshot;
  final String status;

  int _listLength(String key) {
    final value = snapshot.grantsState[key];
    return value is List<Object?> ? value.length : 0;
  }

  @override
  Widget build(BuildContext context) {
    return _SurfaceFrame(
      title: 'Governance',
      icon: Icons.admin_panel_settings_outlined,
      status: status,
      child: Wrap(
        spacing: 14,
        runSpacing: 14,
        children: [
          _OperationalCard(label: 'Registered grants', value: '${_listLength('grants')}'),
          _OperationalCard(label: 'Revoked grants', value: '${_listLength('revoked')}'),
          _OperationalCard(label: 'Stopped subjects', value: '${_listLength('stopped')}'),
          _OperationalCard(label: 'Governance fields', value: '${snapshot.governanceState.length}'),
        ],
      ),
    );
  }
}

class _SurfaceFrame extends StatelessWidget {
  const _SurfaceFrame({
    required this.title,
    required this.icon,
    required this.status,
    required this.child,
  });

  final String title;
  final IconData icon;
  final String status;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1200),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(26),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: IlaiosTheme.cyan),
                      const SizedBox(width: 10),
                      Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(status, style: const TextStyle(color: IlaiosTheme.muted)),
                  const SizedBox(height: 22),
                  child,
                  const SizedBox(height: 20),
                  const Text(
                    'Displayed values are read-only projections of authenticated backend state. Desktop does not authorize, approve, schedule, revoke or mutate these records.',
                    style: TextStyle(color: IlaiosTheme.muted, height: 1.5),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _OperationalCard extends StatelessWidget {
  const _OperationalCard({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 220,
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: IlaiosTheme.canvas,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: IlaiosTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12)),
          const SizedBox(height: 8),
          Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}
