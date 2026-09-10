import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'agent_runtime_status.dart';
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
    final states = resolveCanonicalAgentRuntimeStates(snapshot);
    final total = _int(snapshot.agentState, const ['canonical_count']) ??
        (states.isEmpty ? null : states.length);
    final active = states.isEmpty
        ? null
        : states.values
            .where((item) => item == AgentRuntimeDisplayState.active)
            .length;
    final busy = states.isEmpty
        ? null
        : states.values
            .where((item) => item == AgentRuntimeDisplayState.working)
            .length;
    final idle = states.isEmpty
        ? null
        : states.values
            .where((item) => item == AgentRuntimeDisplayState.idle)
            .length;
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

int? _int(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is int) return value;
    if (value is num) return value.round();
  }
  return null;
}
