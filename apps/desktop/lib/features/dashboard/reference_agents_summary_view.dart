import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

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
/// Summary cards, the workspace reference and pixel sprites consume the same
/// canonical state resolver; the workspace image never becomes runtime truth.
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
  Widget build(BuildContext context) {
    final session = DeliveryIdentityScope.maybeSessionOf(context);
    final presentationSnapshot = canonicalAgentPresentationSnapshot(
      snapshot,
      runtimeConnected: projection.connected,
      authorizedTenantId: session?.tenantId,
    );
    final states = resolveCanonicalAgentRuntimeStates(
      snapshot,
      runtimeConnected: projection.connected,
      authorizedTenantId: session?.tenantId,
    );
    final teams = _teamsById(presentationSnapshot);

    return LayoutBuilder(
      builder: (context, constraints) {
        final workspaceHeight = (constraints.maxHeight * .34).clamp(180.0, 310.0);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Stack(
                children: [
                  Positioned.fill(
                    child: ReferenceAgentsView(
                      projection: projection,
                      snapshot: presentationSnapshot,
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
                      child: _AgentSummaryCards(
                        snapshot: presentationSnapshot,
                        states: states,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: workspaceHeight,
              child: _PixelWorkspacePanel(states: states, teams: teams),
            ),
          ],
        );
      },
    );
  }
}

class _PixelWorkspacePanel extends StatelessWidget {
  const _PixelWorkspacePanel({required this.states, required this.teams});

  static const _assetPayload =
      'assets/pixel_agents/workspace/office_reference.b64';

  final Map<String, AgentRuntimeDisplayState> states;
  final Map<String, String> teams;

  Widget _error(BuildContext context) => Center(
        child: Text(
          Localizations.localeOf(context).languageCode == 'tr'
              ? 'Pixel çalışma alanı yüklenemedi.'
              : 'Pixel workspace could not be loaded.',
          style: TextStyle(
            fontSize: 9,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('agents-pixel-workspace'),
      margin: const EdgeInsets.fromLTRB(14, 0, 12, 8),
      clipBehavior: Clip.antiAlias,
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: FutureBuilder<String>(
              future: rootBundle.loadString(_assetPayload),
              builder: (context, snapshot) {
                if (snapshot.hasError) return _error(context);
                final encoded = snapshot.data?.replaceAll(
                  RegExp(r'[^A-Za-z0-9+/=]'),
                  '',
                );
                if (encoded == null) return const SizedBox.shrink();
                if (encoded.isEmpty) return _error(context);
                try {
                  final bytes = base64Decode(encoded);
                  return Image.memory(
                    bytes,
                    key: const Key('agents-pixel-workspace-image'),
                    fit: BoxFit.contain,
                    alignment: Alignment.center,
                    filterQuality: FilterQuality.medium,
                    errorBuilder: (context, error, stackTrace) => _error(context),
                  );
                } on FormatException {
                  return _error(context);
                }
              },
            ),
          ),
          if (states.isNotEmpty) ...[
            Divider(
              height: 1,
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
            SizedBox(
              height: 70,
              child: _RearPixelStrip(states: states, teams: teams),
            ),
          ],
        ],
      ),
    );
  }
}

class _AgentSummaryCards extends StatelessWidget {
  const _AgentSummaryCards({required this.snapshot, required this.states});

  final OperationalSnapshot snapshot;
  final Map<String, AgentRuntimeDisplayState> states;

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode == 'tr';
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
      (id: 'total', label: tr ? 'Toplam' : 'Total', value: total?.toString() ?? '—'),
      (id: 'active', label: tr ? 'Aktif' : 'Active', value: active?.toString() ?? '—'),
      (id: 'busy', label: tr ? 'Meşgul' : 'Busy', value: busy?.toString() ?? '—'),
      (id: 'idle', label: tr ? 'Boşta' : 'Idle', value: idle?.toString() ?? '—'),
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

class _RearPixelStrip extends StatelessWidget {
  const _RearPixelStrip({required this.states, required this.teams});

  final Map<String, AgentRuntimeDisplayState> states;
  final Map<String, String> teams;

  @override
  Widget build(BuildContext context) {
    final byTeam = <String, AgentRuntimeDisplayState>{};
    const priority = <AgentRuntimeDisplayState, int>{
      AgentRuntimeDisplayState.offline: 0,
      AgentRuntimeDisplayState.active: 1,
      AgentRuntimeDisplayState.idle: 1,
      AgentRuntimeDisplayState.waiting: 2,
      AgentRuntimeDisplayState.working: 3,
    };
    for (final entry in states.entries) {
      final team = teams[entry.key];
      if (team == null || !pixelAgentTeams.contains(team)) continue;
      final current = byTeam[team];
      if (current == null || priority[entry.value]! > priority[current]!) {
        byTeam[team] = entry.value;
      }
    }
    const order = <String>[
      'core',
      'engineering',
      'security',
      'web',
      'media',
      'intelligence',
      'operations',
      'meta',
    ];
    final visible = order.where(byTeam.containsKey).toList(growable: false);
    if (visible.isEmpty) return const SizedBox.shrink();
    return Container(
      key: const Key('agents-rear-pixel-strip'),
      color: Theme.of(context).scaffoldBackgroundColor,
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceEvenly,
        children: [
          for (final team in visible)
            PixelAgentSprite(
              key: ValueKey('agents-pixel-$team'),
              team: team,
              view: PixelAgentView.rear,
              motion: pixelMotionForRuntimeState(byTeam[team]!),
              size: const Size(48, 60),
            ),
        ],
      ),
    );
  }
}

Map<String, String> _teamsById(OperationalSnapshot snapshot) {
  final result = <String, String>{};
  final raw = snapshot.agentState['agents'];
  if (raw is! List<Object?>) return result;
  for (final item in raw.whereType<Map<String, Object?>>()) {
    final id = _text(item, const ['agent_id']);
    final team = _text(item, const ['team']);
    if (id == null || team == null) continue;
    final normalized = team.toLowerCase();
    if (pixelAgentTeams.contains(normalized)) result[id] = normalized;
  }
  return result;
}

String? _text(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
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
