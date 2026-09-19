import 'package:flutter/material.dart';

import '../../app/ilaios_home_catalog.dart';
import '../../app/ilaios_locale.dart';
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
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final showRightRail = constraints.maxWidth >= 940;
        final contentPadding = constraints.maxWidth >= 1200 ? 16.0 : 12.0;
        final main = _MainDashboardColumn(
          model: model,
          onRefreshRequested: onRefreshRequested,
        );

        return Scrollbar(
          thumbVisibility: false,
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(contentPadding, 12, contentPadding, 16),
            child: showRightRail
                ? Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(child: main),
                      const SizedBox(width: 12),
                      SizedBox(width: 258, child: _RightRail(model: model)),
                    ],
                  )
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      main,
                      const SizedBox(height: 12),
                      _RightRail(model: model),
                    ],
                  ),
          ),
        );
      },
    );
  }
}

class _MainDashboardColumn extends StatelessWidget {
  const _MainDashboardColumn({
    required this.model,
    required this.onRefreshRequested,
  });

  final _DashboardModel model;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Header(model: model, onRefreshRequested: onRefreshRequested),
          const SizedBox(height: 10),
          _WorkflowPanel(model: model),
          const SizedBox(height: 10),
          _LiveExecutionPanel(model: model),
          const SizedBox(height: 10),
          _WorkspacePreview(model: model),
          const SizedBox(height: 10),
          _BottomPanels(model: model),
        ],
      );
}

class _DashboardModel {
  const _DashboardModel({
    required this.projection,
    required this.snapshot,
    required this.status,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;

  Map<String, Object?>? get latestEvent =>
      snapshot.liveEvents.isEmpty ? null : snapshot.liveEvents.last;
  bool get hasRuntimeEvent => latestEvent != null;
  List<Map<String, Object?>> get leases =>
      _mapList(snapshot.schedulerState['leases']);
  List<Map<String, Object?>>? get work =>
      _optionalMapList(snapshot.governanceState['work']);
  List<Map<String, Object?>>? get admissions =>
      _optionalMapList(snapshot.governanceState['admissions']);

  String get jobId => _firstText(latestEvent, const ['job_id']) ?? '—';
  String get started => _firstText(latestEvent, const ['started_at']) ?? '—';
  String get elapsed =>
      _firstText(latestEvent, const ['elapsed', 'elapsed_time']) ?? '—';
  String get estimatedFinish =>
      _firstText(latestEvent, const ['estimated_finish', 'eta', 'finish_at']) ??
      '—';
  String get currentPhase =>
      _firstText(latestEvent, const ['phase', 'stage', 'workflow_phase']) ??
      'Unavailable';
  String get executionStatus =>
      _firstText(latestEvent, const ['state', 'status', 'execution_status']) ??
      'Unavailable';

  String get workflowBadgeLabel {
    if (!projection.connected) return 'OFFLINE';
    if (!hasRuntimeEvent) return 'NO ACTIVE DATA';
    return executionStatus == 'Unavailable'
        ? 'STATE UNAVAILABLE'
        : executionStatus.toUpperCase();
  }

  Color get workflowBadgeColor {
    if (!projection.connected || !hasRuntimeEvent) return IlaiosTheme.muted;
    return _stateColor(executionStatus);
  }

  double? get progressValue {
    final value = _firstNumber(
      latestEvent,
      const ['progress', 'progress_percent', 'completion_percent'],
    );
    if (value == null) return null;
    final normalized = value <= 1 ? value * 100 : value;
    if (normalized < 0 || normalized > 100) return null;
    return normalized / 100;
  }

  String get progressLabel {
    final value = progressValue;
    return value == null ? '—' : '${(value * 100).round()}%';
  }

  int? get pendingApprovals {
    final projectedAdmissions = admissions;
    final projectedWork = work;
    if (projectedAdmissions == null || projectedWork == null) return null;
    final required = <String>{};
    for (final admission in projectedAdmissions) {
      if (admission['human_approval_required'] != true) continue;
      final id = admission['request_id'];
      if (id is String && id.isNotEmpty) required.add(id);
    }
    return projectedWork.where((item) {
      if (item['status'] != 'pending') return false;
      final id = item['request_id'];
      return id is String && required.contains(id);
    }).length;
  }

  int? get approvedCount {
    final projectedWork = work;
    if (projectedWork == null) return null;
    return projectedWork.where((item) => item['status'] == 'approved').length;
  }

  int? get deniedCount {
    final projectedWork = work;
    if (projectedWork == null) return null;
    return projectedWork.where((item) => item['status'] == 'denied').length;
  }

  String stageState(String stage) {
    final event = latestEvent;
    if (event == null) return 'Unavailable';
    final phase = _firstText(event, const ['phase', 'stage', 'workflow_phase']);
    if (phase == null) return 'Unavailable';
    if (_normalizePhase(phase) != _normalizePhase(stage)) return '—';
    return executionStatus;
  }

  String workerTitle(Map<String, Object?> worker, int index) =>
      _firstText(
        worker,
        const ['role', 'worker_type', 'executor_type', 'worker_id', 'lease_id'],
      ) ??
      'Worker ${index + 1}';
  String workerTask(Map<String, Object?> worker) =>
      _firstText(worker, const ['task', 'task_id', 'current_task', 'request_id']) ??
      'Task unavailable';
  String workerState(Map<String, Object?> worker) =>
      _firstText(worker, const ['state', 'status', 'health']) ?? 'Active lease';

  List<Map<String, Object?>> get costSources => <Map<String, Object?>>[
        snapshot.governanceState,
        snapshot.schedulerState,
        ..._mapList(snapshot.governanceState['costs']),
      ];

  String? get totalCostUsd =>
      _firstValue(costSources, const ['total_cost_usd', 'cost_usd']);
  String? get totalCostMinor => _firstValue(
        costSources,
        const ['total_cost_minor', 'spent_minor', 'used_minor'],
      );
  String? get budgetUsd => _firstValue(costSources, const ['budget_usd']);
  String? get budgetMinor =>
      _firstValue(costSources, const ['budget_minor', 'hard_cap_minor']);

  double? get budgetRatio {
    final cost = double.tryParse(totalCostUsd ?? '') ??
        double.tryParse(totalCostMinor ?? '');
    final budget = double.tryParse(budgetUsd ?? '') ??
        double.tryParse(budgetMinor ?? '');
    if (cost == null || budget == null || budget <= 0) return null;
    return (cost / budget).clamp(0, 1).toDouble();
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.model, required this.onRefreshRequested});
  final _DashboardModel model;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: Row(
              children: [
                Flexible(
                  child: Text(
                    _home(context, 'Active Workflow'),
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 19,
                      height: 1.1,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -.25,
                    ),
                  ),
                ),
                const SizedBox(width: 9),
                _StatusBadge(
                  label: _home(context, model.workflowBadgeLabel),
                  color: model.workflowBadgeColor,
                ),
                if (model.started != '—') ...[
                  const SizedBox(width: 11),
                  Flexible(
                    child: Text(
                      '${_home(context, 'Started')}: ${model.started}',
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: IlaiosTheme.muted,
                        fontSize: 9.5,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          Text(
            model.projection.connected
                ? model.status
                : _home(context, 'Runtime unavailable'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: IlaiosTheme.muted, fontSize: 9.5),
          ),
          const SizedBox(width: 8),
          IconButton(
            key: const Key('home-refresh-command'),
            tooltip: _home(context, 'Refresh authoritative state'),
            onPressed: onRefreshRequested,
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.refresh, size: 19),
          ),
        ],
      );
}

class _WorkflowPanel extends StatelessWidget {
  const _WorkflowPanel({required this.model});
  final _DashboardModel model;

  static const _stages = <(String, String, IconData)>[
    ('Goal Intake', 'Intent accepted', Icons.track_changes_outlined),
    ('Planning', 'Workflow prepared', Icons.account_tree_outlined),
    ('Execution', 'Agents executing', Icons.play_circle_outline),
    ('Verification', 'Tests & evidence', Icons.verified_user_outlined),
    ('Delivery', 'Finished product', Icons.inventory_2_outlined),
  ];

  @override
  Widget build(BuildContext context) => _Panel(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
        child: Column(
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                if (constraints.maxWidth >= 650) {
                  return Row(
                    children: [
                      for (var i = 0; i < _stages.length; i++) ...[
                        Expanded(
                          child: _StageCard(
                            title: _home(context, _stages[i].$1),
                            subtitle: _home(context, _stages[i].$2),
                            icon: _stages[i].$3,
                            state: model.stageState(_stages[i].$1),
                          ),
                        ),
                        if (i != _stages.length - 1) ...[
                          const SizedBox(width: 5),
                          const Icon(
                            Icons.arrow_forward,
                            size: 13,
                            color: IlaiosTheme.muted,
                          ),
                          const SizedBox(width: 5),
                        ],
                      ],
                    ],
                  );
                }
                return Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (final stage in _stages)
                      SizedBox(
                        width: (constraints.maxWidth - 8) / 2,
                        child: _StageCard(
                          title: _home(context, stage.$1),
                          subtitle: _home(context, stage.$2),
                          icon: stage.$3,
                          state: model.stageState(stage.$1),
                        ),
                      ),
                  ],
                );
              },
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Text(
                  _home(context, 'Overall Progress'),
                  style: const TextStyle(
                    color: IlaiosTheme.muted,
                    fontSize: 9.5,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: model.progressValue == null
                      ? Container(
                          key: const Key('progress-unavailable-track'),
                          height: 4,
                          decoration: BoxDecoration(
                            color: IlaiosTheme.surfaceRaised,
                            borderRadius: BorderRadius.circular(10),
                          ),
                        )
                      : ClipRRect(
                          borderRadius: BorderRadius.circular(10),
                          child: LinearProgressIndicator(
                            value: model.progressValue,
                            minHeight: 4,
                            backgroundColor: IlaiosTheme.surfaceRaised,
                            color: IlaiosTheme.cyan,
                          ),
                        ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  width: 34,
                  child: Text(
                    model.progressLabel,
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: IlaiosTheme.cyan,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}

class _StageCard extends StatelessWidget {
  const _StageCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.state,
  });
  final String title;
  final String subtitle;
  final IconData icon;
  final String state;

  @override
  Widget build(BuildContext context) {
    final current = state != '—' && state != 'Unavailable';
    final stateColor = current ? _stateColor(state) : IlaiosTheme.muted;
    return Container(
      height: 92,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: current
            ? IlaiosTheme.cyan.withValues(alpha: .055)
            : IlaiosTheme.canvas,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: current
              ? IlaiosTheme.cyan.withValues(alpha: .58)
              : IlaiosTheme.border,
        ),
        boxShadow: current
            ? [
                BoxShadow(
                  color: IlaiosTheme.cyan.withValues(alpha: .035),
                  blurRadius: 14,
                ),
              ]
            : null,
      ),
      child: Row(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              color: current
                  ? IlaiosTheme.cyan.withValues(alpha: .10)
                  : IlaiosTheme.surfaceRaised,
              shape: BoxShape.circle,
            ),
            child: Icon(
              icon,
              size: 16,
              color: current ? IlaiosTheme.cyan : IlaiosTheme.mutedStrong,
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontWeight: FontWeight.w700,
                    fontSize: 10.5,
                  ),
                ),
                const SizedBox(height: 3),
                Text(
                  state == 'Unavailable'
                      ? _home(context, 'Unavailable')
                      : subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    color: IlaiosTheme.muted,
                    fontSize: 8.5,
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.circle, size: 5, color: stateColor),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(
                        _localizedKnownValue(context, state),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: stateColor, fontSize: 8.2),
                      ),
                    ),
                  ],
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
        title: _home(context, 'LIVE EXECUTION'),
        trailing: Text(
          '${model.leases.length} ${_home(context, 'active')}',
          style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8.5),
        ),
        child: model.leases.isEmpty
            ? SizedBox(
                height: 96,
                child: _EmptyState(
                  icon: Icons.groups_2_outlined,
                  message: _home(
                    context,
                    'No active worker leases are exposed by the scheduler.',
                  ),
                ),
              )
            : SizedBox(
                height: 118,
                child: ListView.separated(
                  scrollDirection: Axis.horizontal,
                  itemCount: model.leases.length,
                  separatorBuilder: (_, _) => const SizedBox(width: 8),
                  itemBuilder: (context, index) => SizedBox(
                    width: 132,
                    child: _WorkerCard(
                      title: model.workerTitle(model.leases[index], index),
                      task: model.workerTask(model.leases[index]),
                      state: model.workerState(model.leases[index]),
                    ),
                  ),
                ),
              ),
      );
}

class _WorkerCard extends StatelessWidget {
  const _WorkerCard({
    required this.title,
    required this.task,
    required this.state,
  });
  final String title;
  final String task;
  final String state;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(9),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: IlaiosTheme.surfaceRaised,
                    borderRadius: BorderRadius.circular(7),
                  ),
                  child: const Icon(
                    Icons.smart_toy_outlined,
                    size: 16,
                    color: IlaiosTheme.cyan,
                  ),
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Text(
                    _localizedWorkerTitle(context, title),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w700,
                      fontSize: 9.5,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              _localizedKnownValue(context, task),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(
                color: IlaiosTheme.muted,
                fontSize: 8.5,
              ),
            ),
            const Spacer(),
            Row(
              children: [
                Icon(Icons.circle, size: 6, color: _stateColor(state)),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    _localizedKnownValue(context, state),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 8.5),
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
  Widget build(BuildContext context) => _Panel(
        title: _home(context, 'LIVE WORKSPACE'),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Wrap(
              spacing: 15,
              runSpacing: 6,
              children: [
                _MiniTab(
                  icon: Icons.code,
                  label: _home(context, 'Live Code'),
                  active: true,
                ),
                _MiniTab(
                  icon: Icons.terminal,
                  label: _home(context, 'Terminal'),
                ),
                _MiniTab(
                  icon: Icons.language,
                  label: _home(context, 'Browser'),
                ),
                _MiniTab(
                  icon: Icons.folder_outlined,
                  label: _home(context, 'Files'),
                ),
                _MiniTab(
                  icon: Icons.list_alt,
                  label: _home(context, 'Logs'),
                ),
                _MiniTab(
                  icon: Icons.bolt_outlined,
                  label: _home(context, 'Events'),
                ),
              ],
            ),
            const SizedBox(height: 10),
            LayoutBuilder(
              builder: (context, constraints) {
                final row = constraints.maxWidth >= 620;
                final panes = <Widget>[
                  _WorkspacePane(
                    title: _home(context, 'Live Code'),
                    icon: Icons.code,
                    child: _UnavailableProjection(
                      headline: _home(context, 'Code projection unavailable'),
                      detail: _home(
                        context,
                        'No source buffer is exposed by the current Desktop API.',
                      ),
                    ),
                  ),
                  _WorkspacePane(
                    title: _home(context, 'Terminal'),
                    icon: Icons.terminal,
                    child: _TerminalProjection(events: model.snapshot.liveEvents),
                  ),
                  _WorkspacePane(
                    title: _home(context, 'Browser'),
                    icon: Icons.language,
                    child: _UnavailableProjection(
                      headline: _home(context, 'Preview unavailable'),
                      detail: _home(
                        context,
                        'No browser preview projection is exposed.',
                      ),
                    ),
                  ),
                ];
                if (!row) {
                  return Column(
                    children: [
                      for (var i = 0; i < panes.length; i++) ...[
                        SizedBox(height: 138, child: panes[i]),
                        if (i != panes.length - 1)
                          const SizedBox(height: 8),
                      ],
                    ],
                  );
                }
                return SizedBox(
                  height: 180,
                  child: Row(
                    children: [
                      for (var i = 0; i < panes.length; i++) ...[
                        Expanded(child: panes[i]),
                        if (i != panes.length - 1)
                          const SizedBox(width: 8),
                      ],
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      );
}

class _MiniTab extends StatelessWidget {
  const _MiniTab({required this.icon, required this.label, this.active = false});
  final IconData icon;
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(vertical: 3),
        decoration: BoxDecoration(
          border: active
              ? const Border(
                  bottom: BorderSide(color: IlaiosTheme.cyan, width: 1.5),
                )
              : null,
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 13,
              color: active ? IlaiosTheme.cyan : IlaiosTheme.muted,
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(
                color: active ? IlaiosTheme.cyan : IlaiosTheme.muted,
                fontSize: 9.5,
                fontWeight: active ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ],
        ),
      );
}

class _WorkspacePane extends StatelessWidget {
  const _WorkspacePane({
    required this.title,
    required this.icon,
    required this.child,
  });
  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          children: [
            Container(
              height: 32,
              padding: const EdgeInsets.symmetric(horizontal: 9),
              decoration: const BoxDecoration(
                color: IlaiosTheme.surfaceSoft,
                border: Border(bottom: BorderSide(color: IlaiosTheme.border)),
              ),
              child: Row(
                children: [
                  Icon(icon, size: 13, color: IlaiosTheme.mutedStrong),
                  const SizedBox(width: 6),
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const Spacer(),
                  const Icon(
                    Icons.more_horiz,
                    size: 14,
                    color: IlaiosTheme.muted,
                  ),
                ],
              ),
            ),
            Expanded(child: child),
          ],
        ),
      );
}

class _UnavailableProjection extends StatelessWidget {
  const _UnavailableProjection({required this.headline, required this.detail});
  final String headline;
  final String detail;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                Icons.remove_circle_outline,
                size: 17,
                color: IlaiosTheme.muted,
              ),
              const SizedBox(height: 6),
              Text(
                headline,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 8.8,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 3),
              Text(
                detail,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: IlaiosTheme.muted,
                  fontSize: 7.8,
                ),
              ),
            ],
          ),
        ),
      );
}

class _TerminalProjection extends StatelessWidget {
  const _TerminalProjection({required this.events});
  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) {
    final latest = events.reversed.take(5).toList();
    if (latest.isEmpty) {
      return Center(
        child: Text(
          _home(context, 'No authoritative live events are available.'),
          textAlign: TextAlign.center,
          style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8.2),
        ),
      );
    }
    return ListView.builder(
      padding: const EdgeInsets.all(8),
      itemCount: latest.length,
      itemBuilder: (context, index) {
        final event = latest[index];
        final type = _firstText(event, const ['event_type', 'type']) ?? 'event';
        final state = _firstText(event, const ['state', 'status']);
        return Padding(
          padding: const EdgeInsets.only(bottom: 5),
          child: Text(
            state == null ? '> $type' : '> $type  [$state]',
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              color: IlaiosTheme.mutedStrong,
              fontSize: 8.3,
              fontFamily: 'monospace',
            ),
          ),
        );
      },
    );
  }
}

class _RightRail extends StatelessWidget {
  const _RightRail({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          _SidePanel(
            title: _home(context, 'STATUS'),
            rows: <(String, String)>[
              (_home(context, 'Job ID'), model.jobId),
              (_home(context, 'Started'), model.started),
              (_home(context, 'Elapsed'), model.elapsed),
              (_home(context, 'Est. finish'), model.estimatedFinish),
              (_home(context, 'Phase'), model.currentPhase),
              (_home(context, 'Active workers'), '${model.leases.length}'),
              (_home(context, 'Status'), model.executionStatus),
            ],
            accentLast: true,
          ),
          const SizedBox(height: 9),
          _CostPanel(model: model),
          const SizedBox(height: 9),
          _SidePanel(
            title: _home(context, 'APPROVALS'),
            rows: <(String, String)>[
              (
                _home(context, 'Pending'),
                model.pendingApprovals?.toString() ?? 'Unavailable',
              ),
              (
                _home(context, 'Approved'),
                model.approvedCount?.toString() ?? 'Unavailable',
              ),
              (
                _home(context, 'Denied'),
                model.deniedCount?.toString() ?? 'Unavailable',
              ),
            ],
          ),
          const SizedBox(height: 9),
          _LatestEvents(model: model),
        ],
      );
}

class _CostPanel extends StatelessWidget {
  const _CostPanel({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final ratio = model.budgetRatio;
    return _Panel(
      title: _home(context, 'COST & USAGE'),
      padding: const EdgeInsets.all(11),
      child: Column(
        children: [
          _SideRow(
            label: _home(context, 'Total cost'),
            value: model.totalCostUsd ?? 'Unavailable',
          ),
          const SizedBox(height: 7),
          _SideRow(
            label: _home(context, 'Budget'),
            value: model.budgetUsd ?? 'Unavailable',
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: LinearProgressIndicator(
              value: ratio ?? 0,
              minHeight: 5,
              backgroundColor: IlaiosTheme.surfaceRaised,
              color: ratio == null
                  ? IlaiosTheme.surfaceRaised
                  : IlaiosTheme.cyan,
            ),
          ),
          const SizedBox(height: 9),
          _SideRow(
            label: _home(context, 'Token usage'),
            value: 'Unavailable',
          ),
          const SizedBox(height: 7),
          _SideRow(
            label: _home(context, 'GPU time'),
            value: 'Unavailable',
          ),
        ],
      ),
    );
  }
}

class _SidePanel extends StatelessWidget {
  const _SidePanel({
    required this.title,
    required this.rows,
    this.accentLast = false,
  });
  final String title;
  final List<(String, String)> rows;
  final bool accentLast;

  @override
  Widget build(BuildContext context) => _Panel(
        title: title,
        padding: const EdgeInsets.all(11),
        child: Column(
          children: [
            for (var i = 0; i < rows.length; i++) ...[
              _SideRow(
                label: rows[i].$1,
                value: rows[i].$2,
                accent: accentLast && i == rows.length - 1,
              ),
              if (i != rows.length - 1) const SizedBox(height: 7),
            ],
          ],
        ),
      );
}

class _SideRow extends StatelessWidget {
  const _SideRow({
    required this.label,
    required this.value,
    this.accent = false,
  });
  final String label;
  final String value;
  final bool accent;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 82,
            child: Text(
              label,
              style: const TextStyle(
                color: IlaiosTheme.muted,
                fontSize: 9,
              ),
            ),
          ),
          Expanded(
            child: Text(
              _localizedKnownValue(context, value),
              textAlign: TextAlign.right,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                color: accent && value != 'Unavailable'
                    ? IlaiosTheme.success
                    : IlaiosTheme.text,
                fontSize: 9,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      );
}

class _LatestEvents extends StatelessWidget {
  const _LatestEvents({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(5).toList();
    return _Panel(
      title: _home(context, 'LATEST LOGS'),
      padding: const EdgeInsets.all(11),
      child: events.isEmpty
          ? SizedBox(
              height: 54,
              child: Center(
                child: Text(
                  _home(context, 'No live event records available.'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: IlaiosTheme.muted,
                    fontSize: 8.5,
                  ),
                ),
              ),
            )
          : Column(
              children: [for (final event in events) _EventRow(event: event)],
            ),
    );
  }
}

class _BottomPanels extends StatelessWidget {
  const _BottomPanels({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final sideBySide = constraints.maxWidth >= 660;
          final artifacts = _ArtifactsPanel(model: model);
          final evidence = _EvidencePanel(model: model);
          if (!sideBySide) {
            return Column(
              children: [
                artifacts,
                const SizedBox(height: 9),
                evidence,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 6, child: artifacts),
              const SizedBox(width: 9),
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
    final records = model.snapshot.evidenceRecords.reversed.take(3).toList();
    return _Panel(
      title: _home(context, 'LATEST ARTIFACTS'),
      trailing: Text(
        _home(context, 'View all →'),
        style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8.5),
      ),
      child: records.isEmpty
          ? SizedBox(
              height: 84,
              child: _EmptyState(
                icon: Icons.inventory_2_outlined,
                message: _home(
                  context,
                  'No verified artifact evidence is available.',
                ),
              ),
            )
          : LayoutBuilder(
              builder: (context, constraints) => Row(
                children: [
                  for (var i = 0; i < records.length; i++) ...[
                    Expanded(child: _ArtifactCard(record: records[i])),
                    if (i != records.length - 1)
                      const SizedBox(width: 7),
                  ],
                ],
              ),
            ),
    );
  }
}

class _ArtifactCard extends StatelessWidget {
  const _ArtifactCard({required this.record});
  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Container(
        height: 84,
        padding: const EdgeInsets.all(9),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Row(
          children: [
            Container(
              width: 35,
              height: 48,
              decoration: BoxDecoration(
                color: IlaiosTheme.surfaceRaised,
                borderRadius: BorderRadius.circular(6),
              ),
              child: const Icon(
                Icons.insert_drive_file_outlined,
                size: 19,
                color: IlaiosTheme.cyan,
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    record.action,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      fontSize: 8.5,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _short(record.executionId),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: IlaiosTheme.muted,
                      fontSize: 7.5,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        title: _home(context, 'EVIDENCE & VERIFICATION'),
        trailing: Text(
          _home(context, 'View all →'),
          style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8.5),
        ),
        child: Row(
          children: [
            Expanded(
              child: _VerificationCard(
                icon: Icons.verified_user_outlined,
                label: _home(context, 'Verified'),
                value: model.projection.connected
                    ? '${model.snapshot.evidenceCount}'
                    : 'Unavailable',
              ),
            ),
            const SizedBox(width: 7),
            Expanded(
              child: _VerificationCard(
                icon: Icons.policy_outlined,
                label: _home(context, 'Policy'),
                value: model.snapshot.governanceState.isEmpty
                    ? 'Unavailable'
                    : 'Available',
              ),
            ),
            const SizedBox(width: 7),
            Expanded(
              child: _VerificationCard(
                icon: Icons.route_outlined,
                label: _home(context, 'Routes'),
                value: model.projection.connected
                    ? '${model.snapshot.runtimeRouteCount}'
                    : 'Unavailable',
              ),
            ),
          ],
        ),
      );
}

class _VerificationCard extends StatelessWidget {
  const _VerificationCard({
    required this.icon,
    required this.label,
    required this.value,
  });
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    final available = value != 'Unavailable';
    return Container(
      height: 90,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: IlaiosTheme.canvas,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: IlaiosTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            icon,
            size: 20,
            color: available ? IlaiosTheme.success : IlaiosTheme.muted,
          ),
          const Spacer(),
          Text(
            label,
            style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 2),
          Text(
            _localizedKnownValue(context, value),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: available ? IlaiosTheme.success : IlaiosTheme.muted,
              fontSize: 7.8,
            ),
          ),
        ],
      ),
    );
  }
}

class _EventRow extends StatelessWidget {
  const _EventRow({required this.event});
  final Map<String, Object?> event;

  @override
  Widget build(BuildContext context) {
    final type = _firstText(event, const ['event_type', 'type']) ?? 'event';
    final time = _firstText(event, const ['timestamp', 'created_at', 'occurred_at']);
    final state = _firstText(event, const ['state', 'status']);
    return Padding(
      padding: const EdgeInsets.only(bottom: 7),
      child: Row(
        children: [
          Icon(
            Icons.circle,
            size: 5,
            color: state == null ? IlaiosTheme.muted : _stateColor(state),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              state == null ? type : '$type · $state',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 8.3),
            ),
          ),
          if (time != null) ...[
            const SizedBox(width: 5),
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 64),
              child: Text(
                time,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(
                  color: IlaiosTheme.muted,
                  fontSize: 7.5,
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
    this.title,
    this.trailing,
    this.padding = const EdgeInsets.all(11),
    required this.child,
  });
  final String? title;
  final Widget? trailing;
  final EdgeInsetsGeometry padding;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: padding,
        decoration: BoxDecoration(
          color: IlaiosTheme.surface,
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: IlaiosTheme.border),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withValues(alpha: .14),
              blurRadius: 16,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (title != null) ...[
              Row(
                children: [
                  Expanded(
                    child: Text(
                      title!,
                      style: const TextStyle(
                        fontSize: 10,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  ?trailing,
                ],
              ),
              const SizedBox(height: 9),
            ],
            child,
          ],
        ),
      );
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: color.withValues(alpha: .18)),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            color: color,
            fontSize: 8.5,
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
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, color: IlaiosTheme.muted, size: 21),
              const SizedBox(height: 7),
              Text(
                message,
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: IlaiosTheme.muted,
                  fontSize: 9,
                ),
              ),
            ],
          ),
        ),
      );
}

List<Map<String, Object?>> _mapList(Object? value) =>
    _optionalMapList(value) ?? const <Map<String, Object?>>[];

List<Map<String, Object?>>? _optionalMapList(Object? value) {
  if (value is! List<Object?>) return null;
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

String? _firstValue(List<Map<String, Object?>> sources, List<String> keys) {
  for (final source in sources) {
    for (final key in keys) {
      final value = source[key];
      if (value is num) return value.toString();
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
  }
  return null;
}

Color _stateColor(String value) {
  final normalized = value.toLowerCase();
  if (normalized.contains('fail') ||
      normalized.contains('error') ||
      normalized.contains('unhealthy') ||
      normalized.contains('denied')) {
    return IlaiosTheme.danger;
  }
  if (normalized.contains('block') ||
      normalized.contains('warn') ||
      normalized.contains('pending')) {
    return IlaiosTheme.warning;
  }
  if (normalized.contains('complete') ||
      normalized.contains('success') ||
      normalized.contains('healthy') ||
      normalized.contains('passed')) {
    return IlaiosTheme.success;
  }
  if (normalized.contains('running') ||
      normalized.contains('active') ||
      normalized.contains('working') ||
      normalized.contains('lease')) {
    return IlaiosTheme.cyan;
  }
  return IlaiosTheme.muted;
}

String _normalizePhase(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');
String _short(String value) =>
    value.length <= 18 ? value : '${value.substring(0, 18)}…';

String _home(BuildContext context, String english) => IlaiosHomeCatalog.text(
      context.ilaiosLocale.locale.code,
      english,
    );

String _localizedKnownValue(BuildContext context, String value) =>
    _home(context, value);

String _localizedWorkerTitle(BuildContext context, String value) {
  if (context.ilaiosLocale.locale.code != 'tr' || !value.startsWith('Worker ')) {
    return value;
  }
  return value.replaceFirst('Worker ', '${_home(context, 'Worker')} ');
}
