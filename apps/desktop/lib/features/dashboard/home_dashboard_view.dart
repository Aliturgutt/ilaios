import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';

class HomeDashboardView extends StatelessWidget {
  const HomeDashboardView({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.userSession,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) {
    final model = _DashboardModel(
      projection: projection,
      snapshot: snapshot,
      status: status,
      userSession: userSession,
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final narrow = constraints.maxWidth < 1180;
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(
            narrow ? 18 : 22,
            18,
            narrow ? 18 : 22,
            24,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _Header(model: model, onRefreshRequested: onRefreshRequested),
              const SizedBox(height: 16),
              _WorkflowPanel(model: model),
              const SizedBox(height: 16),
              if (narrow) ...[
                _LiveExecutionPanel(model: model),
                const SizedBox(height: 16),
                _WorkspacePreview(model: model),
                const SizedBox(height: 16),
                _RightRail(model: model),
              ] else
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      flex: 7,
                      child: Column(
                        children: [
                          _LiveExecutionPanel(model: model),
                          const SizedBox(height: 16),
                          _WorkspacePreview(model: model),
                        ],
                      ),
                    ),
                    const SizedBox(width: 16),
                    SizedBox(width: 306, child: _RightRail(model: model)),
                  ],
                ),
              const SizedBox(height: 16),
              _BottomPanels(model: model),
            ],
          ),
        );
      },
    );
  }
}

class _DashboardModel {
  const _DashboardModel({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.userSession,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;

  Map<String, Object?>? get latestEvent =>
      snapshot.liveEvents.isEmpty ? null : snapshot.liveEvents.last;

  List<Map<String, Object?>> get leases =>
      _mapList(snapshot.schedulerState['leases']);

  List<Map<String, Object?>> get work =>
      _mapList(snapshot.governanceState['work']);

  List<Map<String, Object?>> get admissions =>
      _mapList(snapshot.governanceState['admissions']);

  String get projectLabel {
    final event = latestEvent;
    return _firstText(event, const <String>['project_name', 'project_id']) ??
        'Current workspace';
  }

  String get jobId =>
      _firstText(latestEvent, const <String>['job_id', 'request_id', 'execution_id']) ??
      '—';

  String get started =>
      _firstText(latestEvent, const <String>['started_at', 'created_at', 'timestamp']) ??
      '—';

  String get elapsed =>
      _firstText(latestEvent, const <String>['elapsed', 'elapsed_time']) ?? '—';

  String get currentPhase =>
      _firstText(latestEvent, const <String>['phase', 'stage', 'workflow_phase']) ??
      'Unavailable';

  String get executionStatus =>
      _firstText(latestEvent, const <String>['state', 'status', 'execution_status']) ??
      (projection.connected ? status : 'Offline');

  String get progress {
    final value = _firstNumber(
      latestEvent,
      const <String>['progress', 'progress_percent', 'completion_percent'],
    );
    if (value == null) return '—';
    final normalized = value <= 1 ? value * 100 : value;
    if (normalized < 0 || normalized > 100) return '—';
    return '${normalized.round()}%';
  }

  int get pendingApprovals {
    final required = <String>{};
    for (final admission in admissions) {
      if (admission['human_approval_required'] == true) {
        final id = admission['request_id'];
        if (id is String && id.isNotEmpty) required.add(id);
      }
    }
    var count = 0;
    for (final item in work) {
      if (item['status'] != 'pending') continue;
      final id = item['request_id'];
      if (required.isEmpty || (id is String && required.contains(id))) {
        count += 1;
      }
    }
    return count;
  }

  int get approvedCount =>
      work.where((item) => item['status'] == 'approved').length;

  int get deniedCount => work.where((item) => item['status'] == 'denied').length;

  String stageState(String stage) {
    final event = latestEvent;
    if (event == null) return 'Unavailable';
    final phase = _firstText(
      event,
      const <String>['phase', 'stage', 'workflow_phase'],
    );
    if (phase == null) return 'Unavailable';
    if (_normalizePhase(phase) != _normalizePhase(stage)) return '—';
    return _firstText(
          event,
          const <String>['state', 'status', 'execution_status'],
        ) ??
        'Current';
  }

  String workerTitle(Map<String, Object?> worker, int index) =>
      _firstText(
        worker,
        const <String>[
          'role',
          'worker_type',
          'executor_type',
          'worker_id',
          'lease_id',
        ],
      ) ??
      'Worker ${index + 1}';

  String workerTask(Map<String, Object?> worker) =>
      _firstText(
        worker,
        const <String>['task', 'task_id', 'current_task', 'request_id'],
      ) ??
      'Task unavailable';

  String workerState(Map<String, Object?> worker) =>
      _firstText(worker, const <String>['state', 'status', 'health']) ?? 'Active lease';

  String? get totalCost => _costText(
        const <String>['total_cost', 'cost', 'cost_usd', 'spent'],
      );

  String? get budget => _costText(
        const <String>['budget', 'budget_usd', 'hard_cap', 'hard_cap_minor'],
      );

  String? _costText(List<String> keys) {
    final candidates = <Map<String, Object?>>[
      snapshot.governanceState,
      snapshot.schedulerState,
      ..._mapList(snapshot.governanceState['costs']),
    ];
    for (final candidate in candidates) {
      for (final key in keys) {
        final value = candidate[key];
        if (value is num) return value.toString();
        if (value is String && value.trim().isNotEmpty) return value.trim();
      }
    }
    return null;
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.model, required this.onRefreshRequested});
  final _DashboardModel model;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Text(
                      'Active Workflow',
                      style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(width: 10),
                    _StatusBadge(
                      label: model.projection.connected ? 'LIVE' : 'OFFLINE',
                      active: model.projection.connected,
                    ),
                  ],
                ),
                const SizedBox(height: 5),
                Text(
                  model.projection.connected
                      ? model.status
                      : 'Authoritative runtime data is unavailable.',
                  style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
                ),
              ],
            ),
          ),
          IconButton(
            key: const Key('home-refresh-command'),
            tooltip: 'Refresh authoritative state',
            onPressed: onRefreshRequested,
            icon: const Icon(Icons.refresh),
          ),
        ],
      );
}

class _WorkflowPanel extends StatelessWidget {
  const _WorkflowPanel({required this.model});
  final _DashboardModel model;

  static const _stages = <(String, IconData)>[
    ('Goal Intake', Icons.track_changes_outlined),
    ('Planning', Icons.account_tree_outlined),
    ('Execution', Icons.play_circle_outline),
    ('Verification', Icons.verified_user_outlined),
    ('Delivery', Icons.inventory_2_outlined),
  ];

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final width = constraints.maxWidth;
                final columns = width >= 950 ? 5 : (width >= 560 ? 2 : 1);
                final spacing = 10.0;
                final cardWidth =
                    (width - ((columns - 1) * spacing)) / columns;
                return Wrap(
                  spacing: spacing,
                  runSpacing: spacing,
                  children: [
                    for (final stage in _stages)
                      SizedBox(
                        width: cardWidth,
                        child: _StageCard(
                          title: stage.$1,
                          icon: stage.$2,
                          state: model.stageState(stage.$1),
                        ),
                      ),
                  ],
                );
              },
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                const Text(
                  'Overall Progress',
                  style: TextStyle(color: IlaiosTheme.muted, fontSize: 12),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: LinearProgressIndicator(
                      value: _progressValue(model.progress),
                      minHeight: 5,
                      backgroundColor: IlaiosTheme.surfaceRaised,
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                SizedBox(
                  width: 42,
                  child: Text(
                    model.progress,
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: IlaiosTheme.cyan,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      );

  static double? _progressValue(String progress) {
    if (!progress.endsWith('%')) return null;
    final parsed = double.tryParse(progress.substring(0, progress.length - 1));
    if (parsed == null || parsed < 0 || parsed > 100) return null;
    return parsed / 100;
  }
}

class _StageCard extends StatelessWidget {
  const _StageCard({required this.title, required this.icon, required this.state});
  final String title;
  final IconData icon;
  final String state;

  @override
  Widget build(BuildContext context) {
    final active = state != '—' && state != 'Unavailable';
    return Container(
      height: 84,
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: active
            ? IlaiosTheme.cyan.withValues(alpha: .06)
            : IlaiosTheme.canvas,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: active
              ? IlaiosTheme.cyan.withValues(alpha: .55)
              : IlaiosTheme.border,
        ),
      ),
      child: Row(
        children: [
          Icon(icon, color: active ? IlaiosTheme.cyan : IlaiosTheme.muted),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
                ),
                const SizedBox(height: 5),
                Text(
                  state,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _LiveExecutionPanel extends StatelessWidget {
  const _LiveExecutionPanel({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        title: 'LIVE EXECUTION',
        child: model.leases.isEmpty
            ? const _EmptyState(
                icon: Icons.groups_2_outlined,
                message: 'No active worker leases are exposed by the scheduler.',
              )
            : LayoutBuilder(
                builder: (context, constraints) {
                  final columns = constraints.maxWidth >= 800 ? 4 : 2;
                  final spacing = 10.0;
                  final width =
                      (constraints.maxWidth - ((columns - 1) * spacing)) / columns;
                  return Wrap(
                    spacing: spacing,
                    runSpacing: spacing,
                    children: [
                      for (var index = 0; index < model.leases.length; index += 1)
                        SizedBox(
                          width: width,
                          child: _WorkerCard(
                            title: model.workerTitle(model.leases[index], index),
                            task: model.workerTask(model.leases[index]),
                            state: model.workerState(model.leases[index]),
                          ),
                        ),
                    ],
                  );
                },
              ),
      );
}

class _WorkerCard extends StatelessWidget {
  const _WorkerCard({required this.title, required this.task, required this.state});
  final String title;
  final String task;
  final String state;

  @override
  Widget build(BuildContext context) => Container(
        height: 108,
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.smart_toy_outlined, size: 18, color: IlaiosTheme.cyan),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 10),
            Text(
              task,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11),
            ),
            const Spacer(),
            Row(
              children: [
                const Icon(Icons.circle, size: 7, color: IlaiosTheme.success),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    state,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}

class _WorkspacePreview extends StatelessWidget {
  const _WorkspacePreview({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(6).toList();
    return _Panel(
      title: 'LIVE WORKSPACE',
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Wrap(
            spacing: 18,
            runSpacing: 8,
            children: [
              _MiniTab(icon: Icons.code, label: 'Live Code'),
              _MiniTab(icon: Icons.terminal, label: 'Terminal'),
              _MiniTab(icon: Icons.language, label: 'Browser'),
              _MiniTab(icon: Icons.folder_outlined, label: 'Files'),
              _MiniTab(icon: Icons.list_alt, label: 'Logs'),
              _MiniTab(icon: Icons.bolt_outlined, label: 'Events'),
            ],
          ),
          const SizedBox(height: 14),
          Container(
            width: double.infinity,
            constraints: const BoxConstraints(minHeight: 150),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: IlaiosTheme.canvas,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: IlaiosTheme.border),
            ),
            child: events.isEmpty
                ? const _EmptyState(
                    icon: Icons.bolt_outlined,
                    message: 'No authoritative live events are available.',
                  )
                : Column(
                    children: [
                      for (final event in events) _EventRow(event: event),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class _MiniTab extends StatelessWidget {
  const _MiniTab({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: IlaiosTheme.muted),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11)),
        ],
      );
}

class _RightRail extends StatelessWidget {
  const _RightRail({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          _SidePanel(
            title: 'STATUS',
            rows: <(String, String)>[
              ('Job ID', model.jobId),
              ('Started', model.started),
              ('Elapsed', model.elapsed),
              ('Phase', model.currentPhase),
              ('Workers', '${model.leases.length}'),
              ('Status', model.executionStatus),
            ],
          ),
          const SizedBox(height: 12),
          _SidePanel(
            title: 'COST & USAGE',
            rows: <(String, String)>[
              ('Total cost', model.totalCost ?? 'Unavailable'),
              ('Budget', model.budget ?? 'Unavailable'),
              ('Token usage', 'Unavailable'),
              ('GPU/runtime', 'Unavailable'),
            ],
            note: model.totalCost == null && model.budget == null
                ? 'The current Desktop API exposes no authoritative cost projection.'
                : null,
          ),
          const SizedBox(height: 12),
          _SidePanel(
            title: 'APPROVALS',
            rows: <(String, String)>[
              ('Pending', '${model.pendingApprovals}'),
              ('Approved', '${model.approvedCount}'),
              ('Denied', '${model.deniedCount}'),
            ],
          ),
          const SizedBox(height: 12),
          _LatestLogs(model: model),
        ],
      );
}

class _SidePanel extends StatelessWidget {
  const _SidePanel({required this.title, required this.rows, this.note});
  final String title;
  final List<(String, String)> rows;
  final String? note;

  @override
  Widget build(BuildContext context) => _Panel(
        title: title,
        child: Column(
          children: [
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SizedBox(
                      width: 92,
                      child: Text(
                        row.$1,
                        style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        row.$2,
                        textAlign: TextAlign.right,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
            if (note != null) ...[
              const Divider(height: 18),
              Text(
                note!,
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 10, height: 1.4),
              ),
            ],
          ],
        ),
      );
}

class _LatestLogs extends StatelessWidget {
  const _LatestLogs({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(5).toList();
    return _Panel(
      title: 'LATEST EVENTS',
      child: events.isEmpty
          ? const Text(
              'No live event records available.',
              style: TextStyle(color: IlaiosTheme.muted, fontSize: 11),
            )
          : Column(children: [for (final event in events) _EventRow(event: event)]),
    );
  }
}

class _BottomPanels extends StatelessWidget {
  const _BottomPanels({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 900;
          final artifacts = _ArtifactsPanel(model: model);
          final evidence = _EvidencePanel(model: model);
          if (stacked) {
            return Column(children: [artifacts, const SizedBox(height: 16), evidence]);
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 6, child: artifacts),
              const SizedBox(width: 16),
              Expanded(flex: 5, child: evidence),
            ],
          );
        },
      );
}

class _ArtifactsPanel extends StatelessWidget {
  const _ArtifactsPanel({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final records = model.snapshot.evidenceRecords.reversed.take(4).toList();
    return _Panel(
      title: 'LATEST VERIFIED ARTIFACTS',
      child: records.isEmpty
          ? const _EmptyState(
              icon: Icons.inventory_2_outlined,
              message: 'No verified artifact evidence is available.',
            )
          : Column(
              children: [for (final record in records) _ArtifactRow(record: record)],
            ),
    );
  }
}

class _ArtifactRow extends StatelessWidget {
  const _ArtifactRow({required this.record});
  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 9),
        child: Row(
          children: [
            const Icon(Icons.insert_drive_file_outlined, size: 18, color: IlaiosTheme.cyan),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    record.action,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 11),
                  ),
                  Text(
                    '${record.executionId} · ${_short(record.artifactDigest)}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: IlaiosTheme.muted, fontSize: 10),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            const Icon(Icons.verified_outlined, size: 17, color: IlaiosTheme.success),
          ],
        ),
      );
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        title: 'EVIDENCE & VERIFICATION',
        child: Column(
          children: [
            _VerificationRow(
              icon: Icons.verified_user_outlined,
              label: 'Verified records',
              value: model.projection.connected
                  ? '${model.snapshot.evidenceCount}'
                  : 'Unavailable',
            ),
            _VerificationRow(
              icon: Icons.policy_outlined,
              label: 'Governance state',
              value: model.snapshot.governanceState.isEmpty
                  ? 'Unavailable'
                  : 'Available',
            ),
            _VerificationRow(
              icon: Icons.route_outlined,
              label: 'Runtime routes',
              value: model.projection.connected
                  ? '${model.snapshot.runtimeRouteCount}'
                  : 'Unavailable',
            ),
          ],
        ),
      );
}

class _VerificationRow extends StatelessWidget {
  const _VerificationRow({required this.icon, required this.label, required this.value});
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 9),
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Row(
          children: [
            Icon(icon, size: 18, color: IlaiosTheme.success),
            const SizedBox(width: 9),
            Expanded(child: Text(label, style: const TextStyle(fontSize: 11))),
            Text(value, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11)),
          ],
        ),
      );
}

class _EventRow extends StatelessWidget {
  const _EventRow({required this.event});
  final Map<String, Object?> event;

  @override
  Widget build(BuildContext context) {
    final type = _firstText(event, const <String>['event_type', 'type']) ?? 'event';
    final time = _firstText(event, const <String>['timestamp', 'created_at', 'occurred_at']);
    final state = _firstText(event, const <String>['state', 'status']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          const Icon(Icons.circle, size: 7, color: IlaiosTheme.success),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              state == null ? type : '$type · $state',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11),
            ),
          ),
          if (time != null) ...[
            const SizedBox(width: 8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 120),
              child: Text(
                time,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 10),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({this.title, required this.child});
  final String? title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          color: IlaiosTheme.surface,
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title != null) ...[
              Text(
                title!,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 13),
            ],
            child,
          ],
        ),
      );
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.active});
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: active
              ? IlaiosTheme.success.withValues(alpha: .12)
              : IlaiosTheme.surfaceRaised,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? IlaiosTheme.success : IlaiosTheme.muted,
            fontSize: 10,
            fontWeight: FontWeight.w700,
          ),
        ),
      );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.message});
  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 18),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: IlaiosTheme.muted, size: 24),
              const SizedBox(height: 8),
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11),
              ),
            ],
          ),
        ),
      );
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return <Map<String, Object?>>[
    for (final item in value)
      if (item is Map<String, dynamic>) Map<String, Object?>.from(item),
  ];
}

String? _firstText(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return value.toString();
  }
  return null;
}

num? _firstNumber(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is num) return value;
    if (value is String) {
      final parsed = num.tryParse(value);
      if (parsed != null) return parsed;
    }
  }
  return null;
}

String _normalizePhase(String value) => value
    .toLowerCase()
    .replaceAll(RegExp(r'[^a-z0-9]+'), '')
    .replaceAll('goalintake', 'goalintake')
    .replaceAll('planning', 'planning')
    .replaceAll('execution', 'execution')
    .replaceAll('verification', 'verification')
    .replaceAll('delivery', 'delivery');

String _short(String value) =>
    value.length <= 18 ? value : '${value.substring(0, 18)}…';
