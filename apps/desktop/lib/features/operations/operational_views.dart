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
  Widget build(BuildContext context) => _SurfaceFrame(
        title: _surface(context, 'live.title'),
        icon: Icons.play_circle_outline,
        status: status,
        footer: _surface(context, 'live.footer'),
        child: Wrap(spacing: 14, runSpacing: 14, children: [
          _OperationalCard(
            label: _surface(context, 'live.runtimeRoutes'),
            value: '${snapshot.runtimeRouteCount}',
          ),
          _OperationalCard(
            label: _surface(context, 'live.liveEvents'),
            value: '${snapshot.liveEventCount}',
          ),
          _OperationalCard(
            label: _surface(context, 'live.activeLeases'),
            value: '${_listLength(snapshot.schedulerState, 'leases')}',
          ),
          _OperationalCard(
            label: _surface(context, 'live.recordedEffects'),
            value: '${_listLength(snapshot.schedulerState, 'effects')}',
          ),
          _OperationalCard(
            label: _surface(context, 'live.lastEvent'),
            value: _lastEventType(),
          ),
          _OperationalCard(
            label: _surface(context, 'live.controlPlane'),
            value: projection.connected
                ? context.tr('shell.connected')
                : context.tr('shell.offline'),
          ),
        ]),
      );
}

class EvidenceView extends StatelessWidget {
  const EvidenceView({required this.snapshot, required this.status, super.key});
  final OperationalSnapshot snapshot;
  final String status;

  String _short(String value) =>
      value.length <= 18 ? value : '${value.substring(0, 18)}…';

  @override
  Widget build(BuildContext context) {
    final records = snapshot.evidenceRecords.reversed.take(100).toList();
    return _SurfaceFrame(
      title: _surface(context, 'evidence.title'),
      icon: Icons.fact_check_outlined,
      status: status,
      footer: _surface(context, 'evidence.footer'),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 14, runSpacing: 14, children: [
          _OperationalCard(
            label: _surface(context, 'evidence.verifiedRecords'),
            value: '${snapshot.evidenceCount}',
          ),
          _OperationalCard(
            label: _surface(context, 'evidence.displayedRecords'),
            value: '${records.length}',
          ),
          _OperationalCard(
            label: _surface(context, 'evidence.verification'),
            value: status == 'Operational APIs connected'
                ? _surface(context, 'evidence.verified')
                : _surface(context, 'evidence.unavailable'),
          ),
        ]),
        const SizedBox(height: 22),
        if (records.isEmpty)
          Text(
            _surface(context, 'evidence.empty'),
            style: const TextStyle(color: IlaiosTheme.muted),
          )
        else
          for (final record in records) _EvidenceRow(record: record, short: _short),
      ]),
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
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Row(children: [
          SizedBox(
            width: 48,
            child: Text(
              '#${record.sequence}',
              style: const TextStyle(
                color: IlaiosTheme.cyan,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(
                record.action,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 4),
              Text(
                '${_surface(context, 'evidence.execution')}: ${record.executionId}',
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
              ),
            ]),
          ),
          const SizedBox(width: 12),
          SizedBox(
            width: 185,
            child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text(
                short(record.artifactDigest),
                key: ValueKey('evidence-digest-${record.sequence}'),
                style: const TextStyle(fontSize: 12),
              ),
              const SizedBox(height: 4),
              Text(
                '${_surface(context, 'evidence.chain')} ${short(record.recordHash)}',
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11),
              ),
            ]),
          ),
        ]),
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
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onDecision;

  int _grantListLength(String key) {
    final value = snapshot.grantsState[key];
    return value is List<Object?> ? value.length : 0;
  }

  Set<String>? _approvalRequiredRequestIds() {
    final raw = snapshot.governanceState['admissions'];
    if (raw is! List<Object?>) return null;
    final required = <String>{};
    for (final item in raw) {
      if (item is Map<String, dynamic> &&
          item['human_approval_required'] == true) {
        final requestId = item['request_id'];
        if (requestId is String && requestId.isNotEmpty) {
          required.add(requestId);
        }
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
      if (item is! Map<String, dynamic> || item['status'] != 'pending') {
        continue;
      }
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
      status: status,
      footer: _surface(context, 'governance.footer'),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 14, runSpacing: 14, children: [
          _OperationalCard(
            label: _surface(context, 'governance.registeredGrants'),
            value: '${_grantListLength('grants')}',
          ),
          _OperationalCard(
            label: _surface(context, 'governance.revokedGrants'),
            value: '${_grantListLength('revoked')}',
          ),
          _OperationalCard(
            label: _surface(context, 'governance.stoppedSubjects'),
            value: '${_grantListLength('stopped')}',
          ),
          _OperationalCard(
            label: _surface(context, 'governance.pendingApprovals'),
            value: '${pending.length}',
          ),
        ]),
        const SizedBox(height: 22),
        if (pending.isEmpty)
          Text(
            _surface(context, 'governance.empty'),
            style: const TextStyle(color: IlaiosTheme.muted),
          )
        else ...[
          if (approverId == null || onDecision == null)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: Text(
                _surface(context, 'governance.noApprover'),
                style: const TextStyle(color: IlaiosTheme.muted),
              ),
            ),
          for (final request in pending)
            _ApprovalRow(
              request: request,
              approverId: approverId,
              onDecision: onDecision,
            ),
        ],
      ]),
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
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onDecision;

  @override
  Widget build(BuildContext context) {
    final requestId = request['request_id'];
    final requesterId = request['requester_id'];
    final valid = requestId is String && requestId.isNotEmpty;
    final independent = approverId != null && approverId != requesterId;
    final enabled = valid && independent && onDecision != null;
    final safeRequestId = valid
        ? requestId
        : _surface(context, 'governance.malformed');
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: IlaiosTheme.canvas,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: IlaiosTheme.border),
      ),
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(
              safeRequestId,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 4),
            Text(
              requesterId is String
                  ? '${_surface(context, 'governance.requester')}: $requesterId'
                  : _surface(context, 'governance.requesterUnavailable'),
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
            ),
            if (!independent)
              Text(
                _surface(context, 'governance.independentRequired'),
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
              ),
          ]),
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
      ]),
    );
  }
}

class _SurfaceFrame extends StatelessWidget {
  const _SurfaceFrame({
    required this.title,
    required this.icon,
    required this.status,
    required this.footer,
    required this.child,
  });
  final String title;
  final IconData icon;
  final String status;
  final String footer;
  final Widget child;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: const EdgeInsets.all(28),
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1200),
            child: Card(
              child: Padding(
                padding: const EdgeInsets.all(26),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Icon(icon, color: IlaiosTheme.cyan),
                    const SizedBox(width: 10),
                    Text(
                      title,
                      style: const TextStyle(
                        fontSize: 22,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ]),
                  const SizedBox(height: 10),
                  Text(status, style: const TextStyle(color: IlaiosTheme.muted)),
                  const SizedBox(height: 22),
                  child,
                  const SizedBox(height: 20),
                  Text(
                    footer,
                    style: const TextStyle(color: IlaiosTheme.muted, height: 1.5),
                  ),
                ]),
              ),
            ),
          ),
        ),
      );
}

class _OperationalCard extends StatelessWidget {
  const _OperationalCard({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        width: 220,
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
            label,
            style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
        ]),
      );
}

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;
