import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_surface_catalog.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
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
    if (snapshot.liveEvents.isEmpty) return '—';
    final value = snapshot.liveEvents.last['event_type'];
    return value is String ? value : '—';
  }

  @override
  Widget build(BuildContext context) {
    final leases = _listLength(snapshot.schedulerState, 'leases');
    final effects = _listLength(snapshot.schedulerState, 'effects');
    final noActivity = leases == 0 && snapshot.liveEventCount == 0;
    return _SurfaceFrame(
      title: _surface(context, 'live.title'),
      icon: Icons.play_circle_outline,
      status: _localizedStatus(context, status),
      footer: _surface(context, 'live.footer'),
      accent: IlaiosTheme.violet,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _OperationalCard(
                label: _surface(context, 'live.runtimeRoutes'),
                value: '${snapshot.runtimeRouteCount}',
                icon: Icons.route_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
              _OperationalCard(
                label: _surface(context, 'live.liveEvents'),
                value: '${snapshot.liveEventCount}',
                icon: Icons.bolt_outlined,
                accent: IlaiosTheme.enterpriseCyan,
              ),
              _OperationalCard(
                label: _surface(context, 'live.activeLeases'),
                value: '$leases',
                icon: Icons.groups_2_outlined,
                accent: IlaiosTheme.violet,
              ),
              _OperationalCard(
                label: _surface(context, 'live.recordedEffects'),
                value: '$effects',
                icon: Icons.hub_outlined,
                accent: IlaiosTheme.enterpriseCyan,
              ),
              _OperationalCard(
                label: _surface(context, 'live.lastEvent'),
                value: _lastEventType(),
                icon: Icons.history_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
              _OperationalCard(
                label: _surface(context, 'live.controlPlane'),
                value: projection.connected
                    ? context.tr('shell.connected')
                    : context.tr('shell.offline'),
                icon: Icons.dns_outlined,
                accent: projection.connected
                    ? IlaiosTheme.enterpriseCyan
                    : Theme.of(context).colorScheme.outline,
              ),
            ],
          ),
          if (noActivity) ...[
            const SizedBox(height: 20),
            _EmptyState(
              icon: Icons.smart_toy_outlined,
              accent: IlaiosTheme.violet,
              title: _isTr(context) ? 'Yürütme bekleniyor' : 'Waiting for execution',
              body: _isTr(context)
                  ? 'Henüz aktif kiralama veya canlı olay yok. Bir hedef yürütmeye alındığında ajanlar, rotalar ve olaylar burada gerçek zamanlı görünür.'
                  : 'No active lease or live event exists yet. When governed work starts, agents, routes and events appear here in real time.',
            ),
          ],
        ],
      ),
    );
  }
}

class EvidenceView extends StatelessWidget {
  const EvidenceView({required this.snapshot, required this.status, super.key});

  final OperationalSnapshot snapshot;
  final String status;

  String _short(String value) => value.length <= 18 ? value : '${value.substring(0, 18)}…';

  @override
  Widget build(BuildContext context) {
    final records = snapshot.evidenceRecords.reversed.take(100).toList();
    return _SurfaceFrame(
      title: _surface(context, 'evidence.title'),
      icon: Icons.fact_check_outlined,
      status: _localizedStatus(context, status),
      footer: _surface(context, 'evidence.footer'),
      accent: IlaiosTheme.enterpriseCyan,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _OperationalCard(
                label: _surface(context, 'evidence.verifiedRecords'),
                value: '${snapshot.evidenceCount}',
                icon: Icons.verified_outlined,
                accent: IlaiosTheme.enterpriseCyan,
              ),
              _OperationalCard(
                label: _surface(context, 'evidence.displayedRecords'),
                value: '${records.length}',
                icon: Icons.visibility_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
              _OperationalCard(
                label: _surface(context, 'evidence.verification'),
                value: status == 'Operational APIs connected'
                    ? _surface(context, 'evidence.verified')
                    : _surface(context, 'evidence.unavailable'),
                icon: Icons.shield_outlined,
                accent: IlaiosTheme.violet,
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (records.isEmpty)
            _EmptyState(
              icon: Icons.fact_check_outlined,
              accent: IlaiosTheme.enterpriseCyan,
              title: _surface(context, 'evidence.empty'),
              body: _isTr(context)
                  ? 'Bir yürütme doğrulanmış kanıt ürettiğinde kayıt zinciri, hash ve provenance metadata burada görünür.'
                  : 'When an execution produces verified evidence, its chain, hashes and provenance metadata appear here.',
            )
          else
            for (final record in records) _EvidenceRow(record: record, short: _short),
        ],
      ),
    );
  }
}

class _EvidenceRow extends StatelessWidget {
  const _EvidenceRow({required this.record, required this.short});

  final EvidenceRecord record;
  final String Function(String value) short;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              width: 42,
              height: 42,
              decoration: BoxDecoration(
                color: IlaiosTheme.enterpriseCyan.withValues(alpha: .12),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Center(
                child: Text(
                  '#${record.sequence}',
                  style: const TextStyle(
                    color: IlaiosTheme.enterpriseCyan,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(record.action, style: const TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(
                    '${_surface(context, 'evidence.execution')}: ${record.executionId}',
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            SizedBox(
              width: 185,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    short(record.artifactDigest),
                    key: ValueKey('evidence-digest-${record.sequence}'),
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${_surface(context, 'evidence.chain')} ${short(record.recordHash)}',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class GovernanceView extends StatelessWidget {
  const GovernanceView({
    required this.snapshot,
    required this.status,
    this.approverId,
    this.onDecision,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final String? approverId;
  final Future<void> Function(String requestId, GovernanceDecision decision)? onDecision;

  int _grantListLength(String key) {
    final value = snapshot.grantsState[key];
    return value is List<Object?> ? value.length : 0;
  }

  Set<String>? _approvalRequiredRequestIds() {
    final raw = snapshot.governanceState['admissions'];
    if (raw is! List<Object?>) return null;
    final required = <String>{};
    for (final item in raw) {
      if (item is Map<String, dynamic> && item['human_approval_required'] == true) {
        final requestId = item['request_id'];
        if (requestId is String && requestId.isNotEmpty) required.add(requestId);
      }
    }
    return required;
  }

  List<Map<String, Object?>> _pendingWork() {
    final raw = snapshot.governanceState['work'];
    if (raw is! List<Object?>) return const <Map<String, Object?>>[];
    final required = _approvalRequiredRequestIds();
    final pending = <Map<String, Object?>>[];
    for (final item in raw) {
      if (item is! Map<String, dynamic> || item['status'] != 'pending') continue;
      final requestId = item['request_id'];
      if (required != null &&
          (requestId is! String || !required.contains(requestId))) {
        continue;
      }
      pending.add(Map<String, Object?>.from(item));
    }
    return pending;
  }

  @override
  Widget build(BuildContext context) {
    final pending = _pendingWork();
    return _SurfaceFrame(
      title: _surface(context, 'governance.title'),
      icon: Icons.admin_panel_settings_outlined,
      status: _localizedStatus(context, status),
      footer: _surface(context, 'governance.footer'),
      accent: IlaiosTheme.violet,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _OperationalCard(
                label: _surface(context, 'governance.registeredGrants'),
                value: '${_grantListLength('grants')}',
                icon: Icons.key_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
              _OperationalCard(
                label: _surface(context, 'governance.revokedGrants'),
                value: '${_grantListLength('revoked')}',
                icon: Icons.block_outlined,
                accent: IlaiosTheme.violet,
              ),
              _OperationalCard(
                label: _surface(context, 'governance.stoppedSubjects'),
                value: '${_grantListLength('stopped')}',
                icon: Icons.stop_circle_outlined,
                accent: IlaiosTheme.enterpriseCyan,
              ),
              _OperationalCard(
                label: _surface(context, 'governance.pendingApprovals'),
                value: '${pending.length}',
                icon: Icons.task_alt_outlined,
                accent: IlaiosTheme.violet,
              ),
            ],
          ),
          const SizedBox(height: 20),
          if (pending.isEmpty)
            _EmptyState(
              icon: Icons.verified_user_outlined,
              accent: IlaiosTheme.violet,
              title: _surface(context, 'governance.empty'),
              body: _isTr(context)
                  ? 'İnsan onayı gerektiren yetkili bir iş oluştuğunda burada açık karar kontrolleri görünür.'
                  : 'When backend-admitted work requires human approval, explicit decision controls appear here.',
            )
          else ...[
            if (approverId == null || onDecision == null)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(
                  _surface(context, 'governance.noApprover'),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
              ),
            for (final request in pending)
              _ApprovalRow(
                request: request,
                approverId: approverId,
                onDecision: onDecision,
              ),
          ],
        ],
      ),
    );
  }
}

class _ApprovalRow extends StatelessWidget {
  const _ApprovalRow({
    required this.request,
    required this.approverId,
    required this.onDecision,
  });

  final Map<String, Object?> request;
  final String? approverId;
  final Future<void> Function(String requestId, GovernanceDecision decision)? onDecision;

  @override
  Widget build(BuildContext context) {
    final requestId = request['request_id'];
    final requesterId = request['requester_id'];
    final valid = requestId is String && requestId.isNotEmpty;
    final independent = approverId != null && approverId != requesterId;
    final enabled = valid && independent && onDecision != null;
    final safeRequestId = valid ? requestId : _surface(context, 'governance.malformed');
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: IlaiosTheme.violet.withValues(alpha: .30)),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(safeRequestId, style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(
                  requesterId is String
                      ? '${_surface(context, 'governance.requester')}: $requesterId'
                      : _surface(context, 'governance.requesterUnavailable'),
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                if (!independent)
                  Text(
                    _surface(context, 'governance.independentRequired'),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          OutlinedButton(
            key: ValueKey('deny-$safeRequestId'),
            onPressed: enabled
                ? () => onDecision!(safeRequestId, GovernanceDecision.denied)
                : null,
            child: Text(_surface(context, 'governance.deny')),
          ),
          const SizedBox(width: 8),
          FilledButton(
            key: ValueKey('approve-$safeRequestId'),
            onPressed: enabled
                ? () => onDecision!(safeRequestId, GovernanceDecision.approved)
                : null,
            child: Text(_surface(context, 'governance.approve')),
          ),
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
    required this.footer,
    required this.accent,
    required this.child,
  });

  final String title;
  final IconData icon;
  final String status;
  final String footer;
  final Color accent;
  final Widget child;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1240),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: accent.withValues(alpha: .12),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(icon, color: accent),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title,
                              style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 3),
                            Text(status, style: Theme.of(context).textTheme.bodySmall),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 22),
                  child,
                  const SizedBox(height: 20),
                  Text(footer, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ),
        ),
      );
}

class _OperationalCard extends StatefulWidget {
  const _OperationalCard({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  State<_OperationalCard> createState() => _OperationalCardState();
}

class _OperationalCardState extends State<_OperationalCard> {
  bool hovered = false;

  @override
  Widget build(BuildContext context) => MouseRegion(
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: Material(
          color: hovered
              ? widget.accent.withValues(alpha: .08)
              : Theme.of(context).colorScheme.surfaceContainerLowest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: hovered
                  ? widget.accent.withValues(alpha: .55)
                  : Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => _showMetricDetail(context, widget.label, widget.value, widget.icon, widget.accent),
            child: SizedBox(
              width: 220,
              height: 112,
              child: Padding(
                padding: const EdgeInsets.all(15),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(widget.icon, color: widget.accent, size: 20),
                        const Spacer(),
                        Icon(Icons.arrow_outward, size: 15, color: hovered ? widget.accent : Theme.of(context).colorScheme.outline),
                      ],
                    ),
                    const Spacer(),
                    Text(widget.label, style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 4),
                    Text(
                      widget.value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({
    required this.icon,
    required this.accent,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final Color accent;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: .055),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: accent.withValues(alpha: .22)),
        ),
        child: Row(
          children: [
            Container(
              width: 46,
              height: 46,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: .13),
                borderRadius: BorderRadius.circular(13),
              ),
              child: Icon(icon, color: accent),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(body, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      );
}

Future<void> _showMetricDetail(
  BuildContext context,
  String label,
  String value,
  IconData icon,
  Color accent,
) => showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: Icon(icon, color: accent),
        title: Text(label),
        content: SelectableText(value),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_isTr(context) ? 'Kapat' : 'Close'),
          ),
        ],
      ),
    );

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;

String _localizedStatus(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    _ => value,
  };
}

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;
