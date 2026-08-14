import 'package:flutter/material.dart';

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
        title: 'Live Execution',
        icon: Icons.play_circle_outline,
        status: status,
        footer:
            'Displayed values are read-only projections of authenticated backend state. Desktop does not schedule or execute work from this surface.',
        child: Wrap(spacing: 14, runSpacing: 14, children: [
          _OperationalCard(
              label: 'Runtime routes', value: '${snapshot.runtimeRouteCount}'),
          _OperationalCard(
              label: 'Live events', value: '${snapshot.liveEventCount}'),
          _OperationalCard(
              label: 'Active leases',
              value: '${_listLength(snapshot.schedulerState, 'leases')}'),
          _OperationalCard(
              label: 'Recorded effects',
              value: '${_listLength(snapshot.schedulerState, 'effects')}'),
          _OperationalCard(label: 'Last live event', value: _lastEventType()),
          _OperationalCard(
              label: 'Control plane',
              value: projection.connected ? 'Connected' : 'Offline'),
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
      title: 'Evidence & Audit',
      icon: Icons.fact_check_outlined,
      status: status,
      footer:
          'The backend verifies the provenance chain before these records are returned. Desktop displays metadata only; artifact bytes, base64 payloads and secret material are not requested or rendered.',
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 14, runSpacing: 14, children: [
          _OperationalCard(
              label: 'Verified records', value: '${snapshot.evidenceCount}'),
          _OperationalCard(
              label: 'Displayed records', value: '${records.length}'),
          _OperationalCard(
              label: 'Verification',
              value: status == 'Operational APIs connected'
                  ? 'Verified'
                  : 'Unavailable'),
        ]),
        const SizedBox(height: 22),
        if (records.isEmpty)
          const Text('No verified evidence records available.',
              style: TextStyle(color: IlaiosTheme.muted))
        else
          for (final record in records)
            _EvidenceRow(record: record, short: _short),
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
            child: Text('#${record.sequence}',
                style: const TextStyle(
                    color: IlaiosTheme.cyan, fontWeight: FontWeight.w700)),
          ),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(record.action,
                  style: const TextStyle(fontWeight: FontWeight.w700)),
              const SizedBox(height: 4),
              Text('Execution: ${record.executionId}',
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      color: IlaiosTheme.muted, fontSize: 12)),
            ]),
          ),
          const SizedBox(width: 12),
          SizedBox(
            width: 185,
            child: Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text(short(record.artifactDigest),
                  key: ValueKey('evidence-digest-${record.sequence}'),
                  style: const TextStyle(fontSize: 12)),
              const SizedBox(height: 4),
              Text('chain ${short(record.recordHash)}',
                  style: const TextStyle(
                      color: IlaiosTheme.muted, fontSize: 11)),
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
    this.authenticatedPrincipalId,
    this.onDecision,
    super.key,
  });
  final OperationalSnapshot snapshot;
  final String status;
  final String? approverId;
  final String? authenticatedPrincipalId;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onDecision;

  int _grantListLength(String key) {
    final value = snapshot.grantsState[key];
    return value is List<Object?> ? value.length : 0;
  }

  List<Map<String, Object?>> _pendingWork() {
    final raw = snapshot.governanceState['work'];
    if (raw is! List<Object?>) return const <Map<String, Object?>>[];
    final pending = <Map<String, Object?>>[];
    for (final item in raw) {
      if (item is Map<String, dynamic> && item['status'] == 'pending') {
        pending.add(Map<String, Object?>.from(item));
      }
    }
    return pending;
  }

  @override
  Widget build(BuildContext context) {
    final pending = _pendingWork();
    return _SurfaceFrame(
      title: 'Governance',
      icon: Icons.admin_panel_settings_outlined,
      status: status,
      footer:
          'Coordinator execution requests derive the approver from a verified ILAIOS session. Legacy governed work may use the configured operator approver. The server rechecks independence and tenant scope before accepting a decision.',
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Wrap(spacing: 14, runSpacing: 14, children: [
          _OperationalCard(
              label: 'Registered grants', value: '${_grantListLength('grants')}'),
          _OperationalCard(
              label: 'Revoked grants', value: '${_grantListLength('revoked')}'),
          _OperationalCard(
              label: 'Stopped subjects', value: '${_grantListLength('stopped')}'),
          _OperationalCard(
              label: 'Pending approvals', value: '${pending.length}'),
        ]),
        const SizedBox(height: 22),
        if (pending.isEmpty)
          const Text('No pending governed work.',
              style: TextStyle(color: IlaiosTheme.muted))
        else
          for (final request in pending)
            _ApprovalRow(
              request: request,
              legacyApproverId: approverId,
              authenticatedPrincipalId: authenticatedPrincipalId,
              onDecision: onDecision,
            ),
      ]),
    );
  }
}

class _ApprovalRow extends StatelessWidget {
  const _ApprovalRow({
    required this.request,
    required this.legacyApproverId,
    required this.authenticatedPrincipalId,
    required this.onDecision,
  });
  final Map<String, Object?> request;
  final String? legacyApproverId;
  final String? authenticatedPrincipalId;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onDecision;

  @override
  Widget build(BuildContext context) {
    final requestId = request['request_id'];
    final requesterId = request['requester_id'];
    final valid = requestId is String && requestId.isNotEmpty;
    final coordinatorRequest = valid && requestId.startsWith('exec-');
    final effectiveApprover =
        coordinatorRequest ? authenticatedPrincipalId : legacyApproverId;
    final independent = effectiveApprover != null && effectiveApprover != requesterId;
    final enabled = valid && independent && onDecision != null;
    final safeRequestId = valid ? requestId : 'Malformed request';
    final reason = _decisionReason(
      coordinatorRequest: coordinatorRequest,
      effectiveApprover: effectiveApprover,
      requesterId: requesterId,
    );
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
            Text(safeRequestId,
                style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 4),
            Text(
                requesterId is String
                    ? 'Requester: $requesterId'
                    : 'Requester unavailable',
                style: const TextStyle(
                    color: IlaiosTheme.muted, fontSize: 12)),
            if (reason != null)
              Text(reason,
                  key: ValueKey('approval-reason-$safeRequestId'),
                  style: const TextStyle(
                      color: IlaiosTheme.muted, fontSize: 12)),
          ]),
        ),
        const SizedBox(width: 12),
        OutlinedButton(
            key: ValueKey('deny-$safeRequestId'),
            onPressed: enabled
                ? () => onDecision!(safeRequestId, GovernanceDecision.denied)
                : null,
            child: const Text('Deny')),
        const SizedBox(width: 8),
        FilledButton(
            key: ValueKey('approve-$safeRequestId'),
            onPressed: enabled
                ? () => onDecision!(safeRequestId, GovernanceDecision.approved)
                : null,
            child: const Text('Approve')),
      ]),
    );
  }
}

String? _decisionReason({
  required bool coordinatorRequest,
  required String? effectiveApprover,
  required Object? requesterId,
}) {
  if (effectiveApprover == null) {
    return coordinatorRequest
        ? 'Sign in as an independent approver to decide this execution.'
        : 'Independent operator approver is not configured.';
  }
  if (effectiveApprover == requesterId) {
    return 'Requester cannot approve their own governed execution.';
  }
  return null;
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
                    Text(title,
                        style: const TextStyle(
                            fontSize: 22, fontWeight: FontWeight.w700)),
                  ]),
                  const SizedBox(height: 10),
                  Text(status,
                      style: const TextStyle(color: IlaiosTheme.muted)),
                  const SizedBox(height: 22),
                  child,
                  const SizedBox(height: 20),
                  Text(footer,
                      style: const TextStyle(
                          color: IlaiosTheme.muted, height: 1.5)),
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
          Text(label,
              style: const TextStyle(
                  color: IlaiosTheme.muted, fontSize: 12)),
          const SizedBox(height: 8),
          Text(value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style:
                  const TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
        ]),
      );
}
