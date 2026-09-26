import 'dart:async';

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../deliveries/delivery_identity_scope.dart';
import '../navigation/desktop_section.dart';
import 'agent_runtime_status.dart';
import 'pixel_agent_presentation.dart';
import 'pixel_agent_sprite.dart';
import 'reference_agents_view.dart';

/// Presentation-only wrapper for the canonical Agents surface.
///
/// Identity, provisioning and runtime authority remain in [ReferenceAgentsView].
/// Summary cards and the workspace reference consume the same canonical runtime
/// projection without allowing the static workspace artwork to become runtime
/// truth.
class ReferenceAgentsSummaryView extends StatefulWidget {
  const ReferenceAgentsSummaryView({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.onRefreshRequested,
    this.now,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  /// Optional deterministic clock for freshness verification.
  final DateTime? now;
  static const _maximumTelemetryAge = Duration(minutes: 10);

  @override
  State<ReferenceAgentsSummaryView> createState() =>
      _ReferenceAgentsSummaryViewState();
}

class _ReferenceAgentsSummaryViewState
    extends State<ReferenceAgentsSummaryView> {
  Timer? _freshnessTimer;

  @override
  void initState() {
    super.initState();
    // Refresh even without incoming telemetry: old working states must expire.
    _freshnessTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _freshnessTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = DeliveryIdentityScope.maybeSessionOf(context);
    final checkedAt = widget.now ?? DateTime.now().toUtc();
    final presentationSnapshot = canonicalAgentPresentationSnapshot(
      widget.snapshot,
      runtimeConnected: widget.projection.connected,
      authorizedTenantId: session?.tenantId,
      now: checkedAt,
      maxAge: ReferenceAgentsSummaryView._maximumTelemetryAge,
    );
    final states = resolveCanonicalAgentRuntimeStates(
      widget.snapshot,
      runtimeConnected: widget.projection.connected,
      authorizedTenantId: session?.tenantId,
      now: checkedAt,
      maxAge: ReferenceAgentsSummaryView._maximumTelemetryAge,
    );

    return Stack(
      children: [
        Positioned.fill(
          child: ReferenceAgentsView(
            projection: widget.projection,
            snapshot: presentationSnapshot,
            status: widget.status,
            onNavigate: widget.onNavigate,
            onRefreshRequested: widget.onRefreshRequested,
            workspace: _VerifiedWorkingAgents(
              states: states,
              snapshot: widget.snapshot,
            ),
          ),
        ),
        Positioned(
          left: 14,
          right: 12,
          top: 60,
          height: 50,
          child: IgnorePointer(
            child: _AgentSummaryCards(
              snapshot: presentationSnapshot,
              states: states,
              runtimeConnected: widget.projection.connected,
            ),
          ),
        ),
      ],
    );
  }
}

class _VerifiedWorkingAgents extends StatelessWidget {
  const _VerifiedWorkingAgents({required this.states, required this.snapshot});

  final Map<String, AgentRuntimeDisplayState> states;
  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    final workingIds = states.entries
        .where((entry) => entry.value == AgentRuntimeDisplayState.working)
        .map((entry) => entry.key)
        .toList(growable: false);
    final records = snapshot.agentState['agents'];
    final names = <String, String>{};
    final teams = <String, String>{};
    if (records is List) {
      for (final record in records) {
        if (record is! Map) continue;
        final id = record['agent_id'];
        if (id is! String || !workingIds.contains(id)) continue;
        final alias = record['alias'];
        names[id] = alias is String && alias.trim().isNotEmpty ? alias : id;
        final team = record['team'];
        if (team is String && pixelAgentTeams.contains(team.toLowerCase())) {
          teams[id] = team.toLowerCase();
        }
      }
    }
    return LayoutBuilder(
      builder: (context, constraints) => Container(
        key: const Key('agents-verified-workspace'),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              tr
                  ? 'Ã‡alÄ±ÅŸan ajanlar: ${workingIds.length}'
                  : 'Working agents: ${workingIds.length}',
              key: const Key('agents-working-count'),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: GridView.builder(
                key: const Key('agents-empty-office'),
                physics: const NeverScrollableScrollPhysics(),
                itemCount: 8,
                gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                  crossAxisCount: constraints.maxWidth < 550 ? 2 : 4,
                  mainAxisSpacing: 5,
                  crossAxisSpacing: 5,
                  childAspectRatio: constraints.maxWidth < 550 ? 1.6 : 2.3,
                ),
                itemBuilder: (context, index) {
                  final team = pixelAgentTeams.elementAt(index);
                  final occupants = workingIds
                      .where((id) => teams[id] == team)
                      .toList();
                  return Container(
                    key: ValueKey('office-department-$team'),
                    padding: const EdgeInsets.all(3),
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Column(
                      children: [
                        Text(
                          team,
                          style: Theme.of(context).textTheme.labelSmall,
                        ),
                        const Icon(Icons.desktop_windows, size: 18),
                        Expanded(
                          child: occupants.isEmpty
                              ? const SizedBox.shrink()
                              : ListView(
                                  scrollDirection: Axis.horizontal,
                                  children: [
                                    for (final id in occupants)
                                      SizedBox(
                                        key: ValueKey('working-agent-$id'),
                                        width: 116,
                                        child: Row(
                                          children: [
                                            PixelAgentSprite(
                                              team: team,
                                              view: PixelAgentView.rear,
                                              motion: PixelAgentMotion.working,
                                              size: const Size(20, 22),
                                            ),
                                            Expanded(
                                              child: Text(
                                                names[id] ?? id,
                                                maxLines: 1,
                                                style: Theme.of(
                                                  context,
                                                ).textTheme.labelSmall,
                                                overflow: TextOverflow.ellipsis,
                                              ),
                                            ),
                                          ],
                                        ),
                                      ),
                                  ],
                                ),
                        ),
                      ],
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AgentSummaryCards extends StatelessWidget {
  const _AgentSummaryCards({
    required this.snapshot,
    required this.states,
    required this.runtimeConnected,
  });

  final OperationalSnapshot snapshot;
  final Map<String, AgentRuntimeDisplayState> states;
  final bool runtimeConnected;

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    final total = runtimeConnected
        ? (_int(snapshot.agentState, const ['canonical_count']) ??
              (states.isEmpty ? null : states.length))
        : null;
    final active = !runtimeConnected || states.isEmpty
        ? null
        : states.values
              .where((item) => item == AgentRuntimeDisplayState.active)
              .length;
    final busy = runtimeConnected
        ? states.values
              .where((item) => item == AgentRuntimeDisplayState.working)
              .length
        : null;
    final idle = !runtimeConnected || states.isEmpty
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
        value: busy?.toString() ?? '\u2014',
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
                padding: const EdgeInsets.symmetric(
                  horizontal: 11,
                  vertical: 7,
                ),
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
                          fontSize: 13,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                    const SizedBox(width: 6),
                    Text(
                      items[index].value,
                      style: const TextStyle(
                        fontSize: 14,
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
