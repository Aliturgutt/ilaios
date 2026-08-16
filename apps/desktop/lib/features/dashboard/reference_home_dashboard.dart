import 'package:flutter/material.dart';

import '../../app/ilaios_home_catalog.dart';
import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';

class ReferenceHomeDashboardView extends StatelessWidget {
  const ReferenceHomeDashboardView({
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
    final model = _ReferenceDashboardModel(
      projection: projection,
      snapshot: snapshot,
      status: status,
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final showRightRail = constraints.maxWidth >= 900;
        final horizontalPadding = constraints.maxWidth >= 1180 ? 18.0 : 14.0;
        return SingleChildScrollView(
          key: const Key('reference-home-layout'),
          padding: EdgeInsets.fromLTRB(
            horizontalPadding,
            14,
            horizontalPadding,
            16,
          ),
          child: showRightRail
              ? Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: _ReferenceMainColumn(
                        model: model,
                        onNavigate: onNavigate,
                        onRefreshRequested: onRefreshRequested,
                      ),
                    ),
                    const SizedBox(width: 14),
                    SizedBox(
                      width: 294,
                      child: _ReferenceRightRail(
                        model: model,
                        onNavigate: onNavigate,
                      ),
                    ),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _ReferenceMainColumn(
                      model: model,
                      onNavigate: onNavigate,
                      onRefreshRequested: onRefreshRequested,
                    ),
                    const SizedBox(height: 14),
                    _ReferenceRightRail(
                      model: model,
                      onNavigate: onNavigate,
                    ),
                  ],
                ),
        );
      },
    );
  }
}

class _ReferenceDashboardModel {
  const _ReferenceDashboardModel({
    required this.projection,
    required this.snapshot,
    required this.status,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;

  Map<String, Object?>? get latestEvent =>
      snapshot.liveEvents.isEmpty ? null : snapshot.liveEvents.last;

  List<Map<String, Object?>> get leases =>
      _mapList(snapshot.schedulerState['leases']);
  List<Map<String, Object?>> get work =>
      _mapList(snapshot.governanceState['work']);
  List<Map<String, Object?>> get admissions =>
      _mapList(snapshot.governanceState['admissions']);

  bool get hasRuntimeEvent => latestEvent != null;
  String get jobId => _text(latestEvent, const ['job_id']) ?? '—';
  String get started => _text(
        latestEvent,
        const ['started_at', 'start_time', 'created_at'],
      ) ??
      '—';
  String get elapsed =>
      _text(latestEvent, const ['elapsed', 'elapsed_time']) ?? '—';
  String get estimatedFinish =>
      _text(latestEvent, const ['estimated_finish', 'eta', 'finish_at']) ?? '—';
  String get currentPhase =>
      _text(latestEvent, const ['phase', 'stage', 'workflow_phase']) ??
      'Unavailable';
  String get executionStatus =>
      _text(latestEvent, const ['state', 'status', 'execution_status']) ??
      (projection.connected ? 'Connected' : 'Unavailable');

  double? get progressValue {
    final raw = _number(
      latestEvent,
      const ['progress', 'progress_percent', 'completion_percent'],
    );
    if (raw == null) return null;
    final percent = raw <= 1 ? raw * 100 : raw;
    if (percent < 0 || percent > 100) return null;
    return percent / 100;
  }

  String get progressLabel =>
      progressValue == null ? '—' : '${(progressValue! * 100).round()}%';

  int? get currentStageIndex {
    final phase = _normalize(currentPhase);
    if (phase.isEmpty || phase == 'unavailable') return null;
    const groups = <List<String>>[
      ['goal', 'goalintake', 'intake', 'admission'],
      ['plan', 'planning', 'planner'],
      ['execution', 'execute', 'executing', 'worker'],
      ['verification', 'verify', 'testing', 'qa'],
      ['delivery', 'deliver', 'finished', 'complete', 'completed'],
    ];
    for (var index = 0; index < groups.length; index++) {
      if (groups[index].any((value) => phase.contains(value))) return index;
    }
    return null;
  }

  String stageState(int index) {
    final current = currentStageIndex;
    if (current == null) return 'Unavailable';
    if (index < current) return 'Done';
    if (index == current) return executionStatus;
    return 'Pending';
  }

  int get pendingApprovals {
    final required = <String>{};
    for (final item in admissions) {
      if (item['human_approval_required'] != true) continue;
      final id = item['request_id'];
      if (id is String && id.isNotEmpty) required.add(id);
    }
    return work.where((item) {
      if (item['status'] != 'pending') return false;
      final id = item['request_id'];
      return id is String && required.contains(id);
    }).length;
  }

  int get approvedCount =>
      work.where((item) => item['status'] == 'approved').length;
  int get deniedCount =>
      work.where((item) => item['status'] == 'denied').length;

  String? get totalCost => _firstValue(
        [
          snapshot.governanceState,
          snapshot.schedulerState,
          ..._mapList(snapshot.governanceState['costs']),
        ],
        const ['total_cost_usd', 'cost_usd', 'total_cost_minor', 'spent_minor'],
      );

  String? get budget => _firstValue(
        [
          snapshot.governanceState,
          snapshot.schedulerState,
          ..._mapList(snapshot.governanceState['costs']),
        ],
        const ['budget_usd', 'budget_minor', 'hard_cap_minor'],
      );

  String? get tokenUsage => _firstValue(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['token_usage', 'tokens_used', 'total_tokens'],
      );

  String? get gpuTime => _firstValue(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['gpu_time', 'gpu_seconds', 'gpu_duration'],
      );

  String? get previewUrl => _text(
        latestEvent,
        const ['preview_url', 'url', 'artifact_url'],
      );

  String get runBadge {
    if (!projection.connected) return 'OFFLINE';
    if (!hasRuntimeEvent) return 'READY';
    if (executionStatus == 'Unavailable') return 'CONNECTED';
    return executionStatus.toUpperCase();
  }
}

class _ReferenceMainColumn extends StatelessWidget {
  const _ReferenceMainColumn({
    required this.model,
    required this.onNavigate,
    required this.onRefreshRequested,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ReferenceWorkflowHeader(
            model: model,
            onNavigate: onNavigate,
            onRefreshRequested: onRefreshRequested,
          ),
          const SizedBox(height: 12),
          _ReferenceWorkflowPipeline(
            model: model,
            onNavigate: onNavigate,
          ),
          const SizedBox(height: 12),
          _ReferenceLiveExecution(
            model: model,
            onNavigate: onNavigate,
          ),
          const SizedBox(height: 12),
          _ReferenceWorkspace(
            model: model,
            onNavigate: onNavigate,
          ),
          const SizedBox(height: 12),
          _ReferenceBottomPanels(
            model: model,
            onNavigate: onNavigate,
          ),
        ],
      );
}

class _ReferenceWorkflowHeader extends StatelessWidget {
  const _ReferenceWorkflowHeader({
    required this.model,
    required this.onNavigate,
    required this.onRefreshRequested,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final title = Wrap(
            spacing: 10,
            runSpacing: 7,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                _home(context, 'Active Workflow'),
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
              ),
              _ReferenceStatusPill(
                text: _home(context, model.runBadge),
                accent: model.projection.connected
                    ? IlaiosTheme.success
                    : Theme.of(context).colorScheme.outline,
              ),
              if (model.started != '—')
                Text(
                  '${_isTr(context) ? 'Başlangıç' : 'Started'}: ${model.started}',
                  style: Theme.of(context).textTheme.bodySmall,
                ),
            ],
          );
          final actions = Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              OutlinedButton.icon(
                onPressed: () => onNavigate(DesktopSection.liveWorkspace),
                icon: const Icon(Icons.open_in_full_rounded, size: 15),
                label: Text(
                  _isTr(context) ? 'Tam Ekranda Aç' : 'Open in Fullscreen',
                ),
              ),
              const SizedBox(width: 6),
              IconButton(
                tooltip: _isTr(context)
                    ? 'Yetkili durumu yenile'
                    : 'Refresh authoritative state',
                onPressed: onRefreshRequested,
                icon: const Icon(Icons.more_vert_rounded, size: 19),
              ),
            ],
          );
          if (constraints.maxWidth < 720) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                title,
                const SizedBox(height: 8),
                actions,
              ],
            );
          }
          return Row(
            children: [
              Expanded(child: title),
              actions,
            ],
          );
        },
      );
}

class _ReferenceWorkflowPipeline extends StatelessWidget {
  const _ReferenceWorkflowPipeline({
    required this.model,
    required this.onNavigate,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  static const _stages = <_ReferenceStageSpec>[
    _ReferenceStageSpec(
      'Goal Intake',
      'Intent accepted',
      Icons.track_changes_outlined,
      DesktopSection.goals,
    ),
    _ReferenceStageSpec(
      'Planning',
      'Workflow prepared',
      Icons.account_tree_outlined,
      DesktopSection.workflows,
    ),
    _ReferenceStageSpec(
      'Execution',
      'Agents executing',
      Icons.play_circle_outline_rounded,
      DesktopSection.agents,
    ),
    _ReferenceStageSpec(
      'Verification',
      'Tests & evidence',
      Icons.verified_user_outlined,
      DesktopSection.evidence,
    ),
    _ReferenceStageSpec(
      'Delivery',
      'Finished product',
      Icons.inventory_2_outlined,
      DesktopSection.artifacts,
    ),
  ];

  @override
  Widget build(BuildContext context) => _ReferencePanel(
        key: const Key('reference-workflow-pipeline'),
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                if (constraints.maxWidth < 620) {
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (var index = 0; index < _stages.length; index++)
                        SizedBox(
                          width: (constraints.maxWidth - 8) / 2,
                          child: _ReferenceStageCard(
                            spec: _stages[index],
                            state: model.stageState(index),
                            active: model.currentStageIndex == index,
                            onTap: () => onNavigate(_stages[index].destination),
                          ),
                        ),
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.center,
                  children: [
                    for (var index = 0; index < _stages.length; index++) ...[
                      Expanded(
                        child: _ReferenceStageCard(
                          spec: _stages[index],
                          state: model.stageState(index),
                          active: model.currentStageIndex == index,
                          onTap: () => onNavigate(_stages[index].destination),
                        ),
                      ),
                      if (index != _stages.length - 1)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 5),
                          child: Icon(
                            Icons.arrow_forward_rounded,
                            size: 18,
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                    ],
                  ],
                );
              },
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Text(
                  _home(context, 'Overall Progress'),
                  style: Theme.of(context).textTheme.labelSmall,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(999),
                    child: LinearProgressIndicator(
                      value: model.progressValue ?? 0,
                      minHeight: 5,
                      backgroundColor:
                          Theme.of(context).colorScheme.surfaceContainerHighest,
                      color: IlaiosTheme.enterpriseCyan,
                    ),
                  ),
                ),
                const SizedBox(width: 9),
                SizedBox(
                  width: 40,
                  child: Text(
                    model.progressLabel,
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: IlaiosTheme.enterpriseCyan,
                      fontSize: 12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}

class _ReferenceStageSpec {
  const _ReferenceStageSpec(
    this.title,
    this.subtitle,
    this.icon,
    this.destination,
  );

  final String title;
  final String subtitle;
  final IconData icon;
  final DesktopSection destination;
}

class _ReferenceStageCard extends StatelessWidget {
  const _ReferenceStageCard({
    required this.spec,
    required this.state,
    required this.active,
    required this.onTap,
  });

  final _ReferenceStageSpec spec;
  final String state;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final done = state == 'Done';
    final pending = state == 'Pending';
    final accent = active
        ? IlaiosTheme.coreBlue
        : done
            ? IlaiosTheme.success
            : pending
                ? Theme.of(context).colorScheme.outline
                : IlaiosTheme.enterpriseCyan;
    return Material(
      color: active
          ? IlaiosTheme.coreBlue.withValues(alpha: .08)
          : Theme.of(context).colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(9),
        side: BorderSide(
          color: active
              ? IlaiosTheme.enterpriseCyan
              : Theme.of(context).colorScheme.outlineVariant,
          width: active ? 1.2 : 1,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          height: 84,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
            child: Row(
              children: [
                Container(
                  width: 38,
                  height: 38,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: accent.withValues(alpha: .58)),
                    color: accent.withValues(alpha: .08),
                  ),
                  child: Icon(spec.icon, size: 20, color: accent),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _home(context, spec.title),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 11.5,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        state == 'Unavailable'
                            ? _home(context, 'Unavailable')
                            : state,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 9.5,
                          color: done
                              ? IlaiosTheme.success
                              : active
                                  ? IlaiosTheme.enterpriseCyan
                                  : Theme.of(context)
                                      .colorScheme
                                      .onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ReferenceLiveExecution extends StatelessWidget {
  const _ReferenceLiveExecution({
    required this.model,
    required this.onNavigate,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _ReferencePanel(
        key: const Key('reference-live-execution'),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _ReferenceSectionHeader(
              title: _home(context, 'LIVE EXECUTION'),
              trailing: model.leases.isEmpty
                  ? _home(context, 'No active agents')
                  : '${model.leases.length} ${_home(context, 'active')}',
              onTap: () => onNavigate(DesktopSection.agents),
            ),
            const SizedBox(height: 9),
            LayoutBuilder(
              builder: (context, constraints) {
                if (model.leases.isEmpty) {
                  return _ReferenceTruthEmpty(
                    icon: Icons.groups_2_outlined,
                    title: _isTr(context) ? 'Aktif ajan yok' : 'No active agents',
                    body: _isTr(context)
                        ? 'Scheduler şu anda yetkili aktif worker lease verisi sunmuyor.'
                        : 'The scheduler currently exposes no authoritative active worker leases.',
                  );
                }
                final maxColumns = constraints.maxWidth >= 820
                    ? 7
                    : constraints.maxWidth >= 600
                        ? 5
                        : constraints.maxWidth >= 420
                            ? 3
                            : 2;
                final columns = model.leases.length < maxColumns
                    ? model.leases.length
                    : maxColumns;
                final cardWidth =
                    (constraints.maxWidth - ((columns - 1) * 8)) / columns;
                return Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (var index = 0; index < model.leases.length; index++)
                      SizedBox(
                        width: cardWidth,
                        child: _ReferenceWorkerCard(
                          worker: model.leases[index],
                          index: index,
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      );
}

class _ReferenceWorkerCard extends StatelessWidget {
  const _ReferenceWorkerCard({
    required this.worker,
    required this.index,
  });

  final Map<String, Object?> worker;
  final int index;

  @override
  Widget build(BuildContext context) {
    final role = _text(worker, const ['role', 'worker_type', 'worker_id']) ??
        '${_home(context, 'Worker')} ${index + 1}';
    final state = _text(worker, const ['state', 'status', 'health']) ??
        _home(context, 'Active lease');
    final task = _text(worker, const ['task', 'task_id', 'request_id']) ?? '—';
    final active = !state.toLowerCase().contains('pending');
    final accent = active ? IlaiosTheme.success : IlaiosTheme.warning;
    return Container(
      height: 124,
      padding: const EdgeInsets.all(9),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: index == modelSafeIndex(worker)
              ? IlaiosTheme.enterpriseCyan
              : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Align(
            alignment: Alignment.centerLeft,
            child: Row(
              children: [
                Icon(Icons.circle, size: 8, color: accent),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    role,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 8),
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: IlaiosTheme.coreBlue.withValues(alpha: .10),
              borderRadius: BorderRadius.circular(11),
              border: Border.all(
                color: IlaiosTheme.coreBlue.withValues(alpha: .32),
              ),
            ),
            child: const Icon(
              Icons.smart_toy_outlined,
              color: IlaiosTheme.enterpriseCyan,
              size: 23,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            task,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelSmall,
          ),
          Text(
            state,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: accent,
              fontSize: 9,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

int modelSafeIndex(Map<String, Object?> worker) {
  final raw = worker['priority'];
  if (raw is int && raw >= 0) return raw;
  return -1;
}

class _ReferenceWorkspace extends StatelessWidget {
  const _ReferenceWorkspace({
    required this.model,
    required this.onNavigate,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _ReferencePanel(
        key: const Key('reference-workspace'),
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 8, 12, 0),
              child: Row(
                children: [
                  const Icon(
                    Icons.tune_rounded,
                    color: IlaiosTheme.enterpriseCyan,
                    size: 17,
                  ),
                  const SizedBox(width: 7),
                  _ReferenceWorkspaceTab(
                    icon: Icons.code_rounded,
                    label: _home(context, 'Live Code'),
                    selected: true,
                  ),
                  _ReferenceWorkspaceTab(
                    icon: Icons.terminal_rounded,
                    label: _home(context, 'Terminal'),
                  ),
                  _ReferenceWorkspaceTab(
                    icon: Icons.public_rounded,
                    label: _home(context, 'Browser'),
                  ),
                  if (MediaQuery.sizeOf(context).width >= 1320) ...[
                    _ReferenceWorkspaceTab(
                      icon: Icons.folder_open_outlined,
                      label: _home(context, 'Files'),
                    ),
                    _ReferenceWorkspaceTab(
                      icon: Icons.receipt_long_outlined,
                      label: _home(context, 'Logs'),
                    ),
                    _ReferenceWorkspaceTab(
                      icon: Icons.bolt_outlined,
                      label: _home(context, 'Events'),
                    ),
                  ],
                  const Spacer(),
                  TextButton(
                    onPressed: () => onNavigate(DesktopSection.liveWorkspace),
                    child: Text(
                      _isTr(context) ? 'Aç →' : 'Open →',
                      style: const TextStyle(fontSize: 10.5),
                    ),
                  ),
                ],
              ),
            ),
            const Divider(height: 1),
            SizedBox(
              height: 260,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  if (constraints.maxWidth < 690) {
                    return _ReferenceTerminalPane(model: model);
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      SizedBox(
                        width: constraints.maxWidth * .20,
                        child: const _ReferenceFilePane(),
                      ),
                      const VerticalDivider(width: 1),
                      Expanded(
                        flex: 45,
                        child: _ReferenceTerminalPane(model: model),
                      ),
                      const VerticalDivider(width: 1),
                      Expanded(
                        flex: 35,
                        child: _ReferenceBrowserPane(model: model),
                      ),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      );
}

class _ReferenceWorkspaceTab extends StatelessWidget {
  const _ReferenceWorkspaceTab({
    required this.icon,
    required this.label,
    this.selected = false,
  });

  final IconData icon;
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(right: 13),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 14,
              color: selected
                  ? IlaiosTheme.enterpriseCyan
                  : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(
                fontSize: 10,
                color: selected
                    ? IlaiosTheme.enterpriseCyan
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
}

class _ReferenceFilePane extends StatelessWidget {
  const _ReferenceFilePane();

  @override
  Widget build(BuildContext context) => Container(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        padding: const EdgeInsets.fromLTRB(10, 10, 8, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.keyboard_arrow_down_rounded, size: 15),
                const SizedBox(width: 4),
                Text('src/', style: Theme.of(context).textTheme.labelSmall),
              ],
            ),
            const SizedBox(height: 8),
            for (final item in const [
              ('components/', Icons.folder_outlined),
              ('pages/', Icons.folder_outlined),
              ('api/', Icons.folder_outlined),
              ('styles/', Icons.folder_outlined),
              ('data/', Icons.folder_outlined),
            ])
              Padding(
                padding: const EdgeInsets.only(left: 12, bottom: 9),
                child: Row(
                  children: [
                    Icon(item.$2, size: 14, color: IlaiosTheme.coreBlue),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        item.$1,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                  ],
                ),
              ),
            const Spacer(),
            Text(
              _isTr(context)
                  ? 'Dosya ağacı yalnızca görsel kabuktur; yetkili dosya içeriği sunulmadıkça sentetik kod gösterilmez.'
                  : 'Visual shell only; no synthetic source is shown until authoritative file contents are exposed.',
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      );
}

class _ReferenceTerminalPane extends StatelessWidget {
  const _ReferenceTerminalPane({required this.model});

  final _ReferenceDashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(7).toList();
    return Container(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            height: 34,
            padding: const EdgeInsets.symmetric(horizontal: 10),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              border: Border(
                bottom: BorderSide(
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
            ),
            child: Row(
              children: [
                const Icon(Icons.terminal_rounded, size: 14),
                const SizedBox(width: 7),
                Text(
                  _isTr(context) ? 'Terminal / Canlı Olaylar' : 'Terminal / Live Events',
                  style: Theme.of(context).textTheme.labelSmall,
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(10),
              child: events.isEmpty
                  ? _ReferenceTruthEmpty(
                      icon: Icons.terminal_rounded,
                      title: _isTr(context)
                          ? 'Canlı terminal verisi yok'
                          : 'No live terminal data',
                      body: _isTr(context)
                          ? 'Desktop API yetkili terminal veya olay satırı sunmadı.'
                          : 'The Desktop API has not exposed authoritative terminal or event lines.',
                    )
                  : ListView.separated(
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: events.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 4),
                      itemBuilder: (context, index) {
                        final event = events[index];
                        final name = _text(
                              event,
                              const ['event_type', 'type', 'name', 'status'],
                            ) ??
                            'event';
                        final timestamp = _text(
                              event,
                              const ['timestamp', 'created_at', 'time'],
                            ) ??
                            '';
                        return Row(
                          children: [
                            const Icon(
                              Icons.check_rounded,
                              size: 12,
                              color: IlaiosTheme.success,
                            ),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                timestamp.isEmpty ? name : '$timestamp  $name',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontFamily: 'monospace',
                                  fontSize: 9.5,
                                ),
                              ),
                            ),
                          ],
                        );
                      },
                    ),
            ),
          ),
        ],
      ),
    );
  }
}

class _ReferenceBrowserPane extends StatelessWidget {
  const _ReferenceBrowserPane({required this.model});

  final _ReferenceDashboardModel model;

  @override
  Widget build(BuildContext context) => Container(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        child: Column(
          children: [
            Container(
              height: 34,
              padding: const EdgeInsets.symmetric(horizontal: 9),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLow,
                border: Border(
                  bottom: BorderSide(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
              ),
              child: Row(
                children: [
                  const Icon(Icons.search_rounded, size: 14),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      model.previewUrl ??
                          (_isTr(context)
                              ? 'Önizleme URL’si mevcut değil'
                              : 'Preview URL unavailable'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(18),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 62,
                        height: 62,
                        decoration: BoxDecoration(
                          color: IlaiosTheme.enterpriseCyan.withValues(alpha: .08),
                          borderRadius: BorderRadius.circular(15),
                          border: Border.all(
                            color: IlaiosTheme.enterpriseCyan.withValues(alpha: .25),
                          ),
                        ),
                        child: const Icon(
                          Icons.public_rounded,
                          color: IlaiosTheme.enterpriseCyan,
                          size: 31,
                        ),
                      ),
                      const SizedBox(height: 10),
                      Text(
                        model.previewUrl == null
                            ? (_isTr(context)
                                ? 'Yetkili tarayıcı önizlemesi sunulmadı.'
                                : 'No authoritative browser preview is exposed.')
                            : (_isTr(context)
                                ? 'Yetkili önizleme URL’si hazır.'
                                : 'Authoritative preview URL is available.'),
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      );
}

class _ReferenceBottomPanels extends StatelessWidget {
  const _ReferenceBottomPanels({
    required this.model,
    required this.onNavigate,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final artifacts = _ReferenceArtifactsPanel(
            model: model,
            onNavigate: onNavigate,
          );
          final evidence = _ReferenceEvidencePanel(
            model: model,
            onNavigate: onNavigate,
          );
          if (constraints.maxWidth < 680) {
            return Column(
              children: [
                artifacts,
                const SizedBox(height: 12),
                evidence,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: artifacts),
              const SizedBox(width: 12),
              Expanded(child: evidence),
            ],
          );
        },
      );
}

class _ReferenceArtifactsPanel extends StatelessWidget {
  const _ReferenceArtifactsPanel({
    required this.model,
    required this.onNavigate,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final records = model.snapshot.evidenceRecords.reversed.take(3).toList();
    return _ReferencePanel(
      key: const Key('reference-latest-artifacts'),
      padding: const EdgeInsets.all(11),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _ReferenceSectionHeader(
            title: _home(context, 'LATEST ARTIFACTS'),
            actionLabel: _home(context, 'View all →'),
            onTap: () => onNavigate(DesktopSection.artifacts),
          ),
          const SizedBox(height: 8),
          if (records.isEmpty)
            _ReferenceTruthEmpty(
              icon: Icons.inventory_2_outlined,
              title: _home(context, 'Unavailable'),
              body: _home(
                context,
                'No verified artifact evidence is available.',
              ),
            )
          else
            for (final record in records)
              _ReferenceEvidenceRecordRow(record: record),
        ],
      ),
    );
  }
}

class _ReferenceEvidenceRecordRow extends StatelessWidget {
  const _ReferenceEvidenceRecordRow({required this.record});

  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 6),
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.verified_outlined,
              size: 17,
              color: IlaiosTheme.enterpriseCyan,
            ),
            const SizedBox(width: 7),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    record.action,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    record.artifactDigest,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
            Text(
              '#${record.sequence}',
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
        ),
      );
}

class _ReferenceEvidencePanel extends StatelessWidget {
  const _ReferenceEvidencePanel({
    required this.model,
    required this.onNavigate,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _ReferencePanel(
        key: const Key('reference-evidence-verification'),
        padding: const EdgeInsets.all(11),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _ReferenceSectionHeader(
              title: _home(context, 'EVIDENCE & VERIFICATION'),
              actionLabel: _home(context, 'View all →'),
              onTap: () => onNavigate(DesktopSection.evidence),
            ),
            const SizedBox(height: 8),
            LayoutBuilder(
              builder: (context, constraints) {
                final width = constraints.maxWidth >= 390
                    ? (constraints.maxWidth - 14) / 3
                    : constraints.maxWidth;
                return Wrap(
                  spacing: 7,
                  runSpacing: 7,
                  children: [
                    _ReferenceProofTile(
                      width: width,
                      icon: Icons.fact_check_outlined,
                      title: _isTr(context) ? 'QA Kanıtı' : 'QA Evidence',
                      value: model.snapshot.evidenceCount > 0
                          ? _home(context, 'Available')
                          : _home(context, 'Unavailable'),
                    ),
                    _ReferenceProofTile(
                      width: width,
                      icon: Icons.security_outlined,
                      title: _isTr(context) ? 'Güvenlik' : 'Security',
                      value: model.projection.connected
                          ? _home(context, 'Available')
                          : _home(context, 'Unavailable'),
                    ),
                    _ReferenceProofTile(
                      width: width,
                      icon: Icons.policy_outlined,
                      title: _isTr(context) ? 'Politika' : 'Policy',
                      value: model.snapshot.runtimeRouteCount > 0
                          ? '${model.snapshot.runtimeRouteCount}'
                          : _home(context, 'Unavailable'),
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      );
}

class _ReferenceProofTile extends StatelessWidget {
  const _ReferenceProofTile({
    required this.width,
    required this.icon,
    required this.title,
    required this.value,
  });

  final double width;
  final IconData icon;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        width: width,
        height: 86,
        padding: const EdgeInsets.all(9),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 20, color: IlaiosTheme.success),
            const Spacer(),
            Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 2),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 9,
                color: value == _home(context, 'Unavailable')
                    ? Theme.of(context).colorScheme.onSurfaceVariant
                    : IlaiosTheme.success,
              ),
            ),
          ],
        ),
      );
}

class _ReferenceRightRail extends StatelessWidget {
  const _ReferenceRightRail({
    required this.model,
    required this.onNavigate,
  });

  final _ReferenceDashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => Column(
        key: const Key('reference-right-rail'),
        children: [
          _ReferenceRailCard(
            title: _home(context, 'STATUS'),
            onTap: () => onNavigate(DesktopSection.workflows),
            rows: [
              (_home(context, 'Job ID'), model.jobId),
              (_home(context, 'Started'), model.started),
              (_home(context, 'Elapsed'), model.elapsed),
              (_home(context, 'Est. finish'), model.estimatedFinish),
              (_home(context, 'Phase'), _home(context, model.currentPhase)),
              (_home(context, 'Active workers'), '${model.leases.length}'),
              (_home(context, 'Status'), _home(context, model.executionStatus)),
            ],
          ),
          const SizedBox(height: 10),
          _ReferenceCostCard(
            model: model,
            onTap: () => onNavigate(DesktopSection.costs),
          ),
          const SizedBox(height: 10),
          _ReferenceRailCard(
            title: _home(context, 'APPROVALS'),
            onTap: () => onNavigate(DesktopSection.approvals),
            rows: [
              (_home(context, 'Pending'), '${model.pendingApprovals}'),
              (_home(context, 'Approved'), '${model.approvedCount}'),
              (_home(context, 'Denied'), '${model.deniedCount}'),
            ],
            footerLabel: _isTr(context) ? 'Onayları Görüntüle' : 'View approvals',
          ),
          const SizedBox(height: 10),
          _ReferenceLogsCard(model: model),
        ],
      );
}

class _ReferenceRailCard extends StatelessWidget {
  const _ReferenceRailCard({
    required this.title,
    required this.rows,
    required this.onTap,
    this.footerLabel,
  });

  final String title;
  final List<(String, String)> rows;
  final VoidCallback onTap;
  final String? footerLabel;

  @override
  Widget build(BuildContext context) => _ReferencePanel(
        padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title,
              style: const TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w800,
                letterSpacing: .1,
              ),
            ),
            const SizedBox(height: 9),
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        row.$1,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        row.$2,
                        textAlign: TextAlign.right,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w600,
                          color: row.$1 == _home(context, 'Status')
                              ? IlaiosTheme.success
                              : Theme.of(context).colorScheme.onSurface,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            if (footerLabel != null) ...[
              const SizedBox(height: 9),
              OutlinedButton(
                onPressed: onTap,
                child: Text(
                  footerLabel!,
                  style: const TextStyle(fontSize: 10.5),
                ),
              ),
            ],
          ],
        ),
      );
}

class _ReferenceCostCard extends StatelessWidget {
  const _ReferenceCostCard({
    required this.model,
    required this.onTap,
  });

  final _ReferenceDashboardModel model;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final cost = model.totalCost ?? _home(context, 'Unavailable');
    final budget = model.budget ?? _home(context, 'Unavailable');
    final fraction = _fractionFromCost(cost, budget);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(9),
      child: _ReferencePanel(
        padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _home(context, 'COST & USAGE'),
              style: const TextStyle(
                fontSize: 13.5,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 9),
            _ReferenceValueRow(
              label: _home(context, 'Total cost'),
              value: cost,
            ),
            _ReferenceValueRow(
              label: _home(context, 'Budget'),
              value: budget,
            ),
            const SizedBox(height: 7),
            ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: fraction,
                minHeight: 7,
                backgroundColor:
                    Theme.of(context).colorScheme.surfaceContainerHighest,
                color: IlaiosTheme.enterpriseCyan,
              ),
            ),
            const SizedBox(height: 10),
            _ReferenceValueRow(
              label: _home(context, 'Token usage'),
              value: model.tokenUsage ?? _home(context, 'Unavailable'),
            ),
            _ReferenceValueRow(
              label: _home(context, 'GPU time'),
              value: model.gpuTime ?? _home(context, 'Unavailable'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ReferenceValueRow extends StatelessWidget {
  const _ReferenceValueRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3.5),
        child: Row(
          children: [
            Expanded(
              child: Text(label, style: Theme.of(context).textTheme.bodySmall),
            ),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      );
}

class _ReferenceLogsCard extends StatelessWidget {
  const _ReferenceLogsCard({required this.model});

  final _ReferenceDashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(6).toList();
    return _ReferencePanel(
      padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _home(context, 'LATEST LOGS'),
            style: const TextStyle(
              fontSize: 13.5,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 9),
          if (events.isEmpty)
            Text(
              _home(context, 'No live event records available.'),
              style: Theme.of(context).textTheme.bodySmall,
            )
          else
            for (final event in events)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        _text(
                              event,
                              const ['event_type', 'type', 'name', 'status'],
                            ) ??
                            'event',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                    const Icon(
                      Icons.circle,
                      size: 7,
                      color: IlaiosTheme.success,
                    ),
                  ],
                ),
              ),
        ],
      ),
    );
  }
}

class _ReferencePanel extends StatelessWidget {
  const _ReferencePanel({
    required this.child,
    this.padding = const EdgeInsets.all(12),
    super.key,
  });

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) => Container(
        padding: padding,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: child,
      );
}

class _ReferenceSectionHeader extends StatelessWidget {
  const _ReferenceSectionHeader({
    required this.title,
    this.trailing,
    this.actionLabel,
    this.onTap,
  });

  final String title;
  final String? trailing;
  final String? actionLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: Text(
              title,
              style: const TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w800,
                letterSpacing: .15,
              ),
            ),
          ),
          if (trailing != null)
            Text(trailing!, style: Theme.of(context).textTheme.labelSmall),
          if (actionLabel != null && onTap != null)
            TextButton(
              onPressed: onTap,
              child: Text(
                actionLabel!,
                style: const TextStyle(fontSize: 10),
              ),
            ),
        ],
      );
}

class _ReferenceStatusPill extends StatelessWidget {
  const _ReferenceStatusPill({required this.text, required this.accent});

  final String text;
  final Color accent;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: .10),
          borderRadius: BorderRadius.circular(5),
        ),
        child: Text(
          text,
          style: TextStyle(
            color: accent,
            fontSize: 9.5,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

class _ReferenceTruthEmpty extends StatelessWidget {
  const _ReferenceTruthEmpty({
    required this.icon,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Icon(icon, color: IlaiosTheme.coreBlue, size: 22),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 10.5,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(body, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      );
}

double? _fractionFromCost(String cost, String budget) {
  final costValue = double.tryParse(cost.replaceAll(RegExp(r'[^0-9.]'), ''));
  final budgetValue = double.tryParse(budget.replaceAll(RegExp(r'[^0-9.]'), ''));
  if (costValue == null || budgetValue == null || budgetValue <= 0) return null;
  final value = costValue / budgetValue;
  return value.clamp(0, 1).toDouble();
}

bool _isTr(BuildContext context) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _home(BuildContext context, String english) =>
    IlaiosHomeCatalog.text(context.ilaiosLocale.locale.code, english);

String _normalize(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '');

String? _text(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
  }
  return null;
}

double? _number(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is num) return value.toDouble();
    if (value is String) {
      final parsed = double.tryParse(value);
      if (parsed != null) return parsed;
    }
  }
  return null;
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return <Map<String, Object?>>[
    for (final item in value)
      if (item is Map<String, dynamic>) Map<String, Object?>.from(item),
  ];
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
