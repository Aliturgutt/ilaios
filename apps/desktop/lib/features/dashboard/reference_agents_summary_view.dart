import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../deliveries/delivery_identity_scope.dart';
import '../navigation/desktop_section.dart';
import 'agent_runtime_status.dart';
import 'reference_agents_view.dart';

/// Presentation-only wrapper for the canonical Agents surface.
///
/// Identity, provisioning and runtime authority remain in [ReferenceAgentsView].
/// Summary cards and the workspace reference consume the same canonical runtime
/// projection without allowing the static workspace artwork to become runtime
/// truth.
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

    return LayoutBuilder(
      builder: (context, constraints) {
        const officeAspectRatio = 1614 / 537;
        final workspaceHeight =
            (constraints.maxWidth / officeAspectRatio).clamp(220.0, 540.0);
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
              child: const _PixelWorkspacePanel(),
            ),
          ],
        );
      },
    );
  }
}

class _PixelWorkspacePanel extends StatefulWidget {
  const _PixelWorkspacePanel();

  @override
  State<_PixelWorkspacePanel> createState() => _PixelWorkspacePanelState();
}

class _PixelWorkspacePanelState extends State<_PixelWorkspacePanel> {
  static const _assetPayload =
      'assets/pixel_agents/workspace/office_reference.b64';

  late final Future<Uint8List> _officeBytes = _loadOfficeBytes();

  Future<Uint8List> _loadOfficeBytes() async {
    final payload = await rootBundle.loadString(_assetPayload, cache: true);
    final encoded = payload.replaceAll(RegExp(r'[^A-Za-z0-9+/=]'), '');
    if (encoded.isEmpty) {
      throw const FormatException('Empty pixel workspace payload.');
    }
    return base64Decode(encoded);
  }

  Widget _error(BuildContext context) => Center(
        child: Text(
          Localizations.localeOf(context).languageCode == 'tr'
              ? 'Pixel çalışma alanı yüklenemedi.'
              : 'Pixel workspace could not be loaded.',
          style: TextStyle(
            fontSize: 12.5,
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
      child: FutureBuilder<Uint8List>(
        future: _officeBytes,
        builder: (context, snapshot) {
          if (snapshot.hasError) return _error(context);
          final bytes = snapshot.data;
          if (bytes == null) return const SizedBox.shrink();
          return Image.memory(
            bytes,
            key: const Key('agents-pixel-workspace-image'),
            fit: BoxFit.contain,
            alignment: Alignment.center,
            filterQuality: FilterQuality.medium,
            gaplessPlayback: true,
            errorBuilder: (context, error, stackTrace) => _error(context),
          );
        },
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
                          fontSize: 12.5,
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
