import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'reference_agents_view.dart';

/// Presentation-only wrapper for the canonical Agents surface.
///
/// Identity, provisioning and runtime authority remain in [ReferenceAgentsView].
/// The wrapper only projects four distinct summary cards from the same canonical
/// agent registry plus matched scheduler/runtime telemetry.
class ReferenceAgentsSummaryView extends StatelessWidget {
  const ReferenceAgentsSummaryView({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Stack(
        children: [
          Positioned.fill(
            child: ReferenceAgentsView(
              projection: projection,
              snapshot: snapshot,
              status: status,
              onNavigate: onNavigate,
              onRefreshRequested: onRefreshRequested,
            ),
          ),
          Positioned(
            left: 14,
            right: 12,
            top: 60,
            height: 50,
            child: IgnorePointer(
              child: _AgentSummaryCards(snapshot: snapshot),
            ),
          ),
        ],
      );
}

class _AgentSummaryCards extends StatelessWidget {
  const _AgentSummaryCards({required this.snapshot});

  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    final agents = _canonicalAgents(snapshot);
    final total = _int(snapshot.agentState, const ['canonical_count']) ??
        (agents.isEmpty ? null : agents.length);
    final active = agents.isEmpty
        ? null
        : agents.where((item) => item == _AgentSummaryState.active).length;
    final busy = agents.isEmpty
        ? null
        : agents.where((item) => item == _AgentSummaryState.busy).length;
    final idle = agents.isEmpty
        ? null
        : agents.where((item) => item == _AgentSummaryState.idle).length;
    final items = <({String id, String label, String value})>[
      (
        id: 'total',
        label: tr ? 'Toplam' : 'Total',
        value: total?.toString() ?? '—',
      ),
      (
        id: 'active',
        label: tr ? 'Aktif' : 'Active',
        value: active?.toString() ?? '—',
      ),
      (
        id: 'busy',
        label: tr ? 'Meşgul' : 'Busy',
        value: busy?.toString() ?? '—',
      ),
      (
        id: 'idle',
        label: tr ? 'Boşta' : 'Idle',
        value: idle?.toString() ?? '—',
      ),
    ];

    return Container(
      color: Theme.of(context).scaffoldBackgroundColor,
      child: Row(
        children: [
          for (var index = 0; index < items.length; index++) ...[
            if (index > 0) const SizedBox(width: 8),
            Expanded(
              child: Container(
                key: ValueKey('agents-summary-${items[index].id}'),
                padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerLowest,
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                  borderRadius: BorderRadius.circular(7),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        items[index].label,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 8.5,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      items[index].value,
                      style: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

enum _AgentSummaryState { active, busy, idle, other }

List<_AgentSummaryState> _canonicalAgents(OperationalSnapshot snapshot) {
  final merged = <String, Map<String, Object?>>{};
  for (final item in _maps(snapshot.agentState['agents'])) {
    final id = _text(item, const ['agent_id']);
    if (id == null || !id.startsWith('ilaios.agent.')) continue;
    merged[id] = Map<String, Object?>.of(item);
  }

  void mergeTelemetry(Map<String, Object?> item) {
    String? canonicalId;
    for (final key in const [
      'agent_id',
      'worker_id',
      'executor_id',
      'agent',
      'worker',
      'id',
    ]) {
      final candidate = _text(item, [key]);
      if (candidate != null && merged.containsKey(candidate)) {
        canonicalId = candidate;
        break;
      }
    }
    if (canonicalId == null) return;
    final status = _text(item, const [
      'agent_status',
      'worker_status',
      'status',
      'state',
      'lease_state',
    ]);
    if (status != null) merged[canonicalId]!['status'] = status;
  }

  for (final key in const ['agents', 'workers', 'executors', 'leases']) {
    for (final item in _maps(snapshot.schedulerState[key])) {
      mergeTelemetry(item);
    }
  }
  for (final item in snapshot.runtimeRoutes) {
    mergeTelemetry(item);
  }
  for (final item in snapshot.liveEvents) {
    mergeTelemetry(item);
  }

  return merged.values.map((item) {
    final registered = item['registered'] is bool ? item['registered'] as bool : true;
    final raw = _text(item, const [
          'agent_status',
          'worker_status',
          'status',
          'state',
          'lease_state',
        ]) ??
        (registered ? 'active' : 'offline');
    final value = _normalize(raw);
    if (value.contains('busy') ||
        value.contains('running') ||
        value.contains('executing') ||
        value.contains('working')) {
      return _AgentSummaryState.busy;
    }
    if (value.contains('idle') ||
        value.contains('available') ||
        value.contains('free')) {
      return _AgentSummaryState.idle;
    }
    if (value.contains('offline') ||
        value.contains('disabled') ||
        value.contains('stopped') ||
        value.contains('dead') ||
        value.contains('unregistered') ||
        value.contains('review') ||
        value.contains('approval')) {
      return _AgentSummaryState.other;
    }
    return _AgentSummaryState.active;
  }).toList(growable: false);
}

List<Map<String, Object?>> _maps(Object? raw) {
  if (raw is! List<Object?>) return const [];
  return raw.whereType<Map<String, Object?>>().toList(growable: false);
}

String? _text(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return '$value';
  }
  return null;
}

int? _int(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is int) return value;
    if (value is num) return value.round();
  }
  return null;
}

String _normalize(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');
