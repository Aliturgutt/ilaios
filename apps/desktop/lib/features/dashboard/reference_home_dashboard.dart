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
    final model = _DashboardModel(
      projection: projection,
      snapshot: snapshot,
      status: status,
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= 900;
        final pad = constraints.maxWidth >= 1180 ? 18.0 : 14.0;
        final main = _MainColumn(
          model: model,
          onNavigate: onNavigate,
          onRefreshRequested: onRefreshRequested,
        );
        return SingleChildScrollView(
          key: const Key('reference-home-layout'),
          padding: EdgeInsets.fromLTRB(pad, 14, pad, 16),
          child: wide
              ? Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: main),
                    const SizedBox(width: 14),
                    SizedBox(
                      width: 294,
                      child: _RightRail(model: model, onNavigate: onNavigate),
                    ),
                  ],
                )
              : Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    main,
                    const SizedBox(height: 14),
                    _RightRail(model: model, onNavigate: onNavigate),
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
      (projection.connected ? status : 'Unavailable');

  double? get progress {
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
      progress == null ? '—' : '${(progress! * 100).round()}%';

  int? get stageIndex {
    final value = _normalize(currentPhase);
    if (value.isEmpty || value == 'unavailable') return null;
    const aliases = <List<String>>[
      ['goal', 'intake', 'admission'],
      ['plan', 'planning', 'planner'],
      ['execution', 'execute', 'worker'],
      ['verification', 'verify', 'testing', 'qa'],
      ['delivery', 'deliver', 'finished', 'complete'],
    ];
    for (var index = 0; index < aliases.length; index++) {
      if (aliases[index].any(value.contains)) return index;
    }
    return null;
  }

  String stageState(int index) {
    final current = stageIndex;
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

  List<Map<String, Object?>> get metricSources => [
        snapshot.governanceState,
        snapshot.schedulerState,
        ..._mapList(snapshot.governanceState['costs']),
      ];

  String? get totalCost => _firstValue(
        metricSources,
        const ['total_cost_usd', 'cost_usd', 'total_cost_minor', 'spent_minor'],
      );
  String? get budget => _firstValue(
        metricSources,
        const ['budget_usd', 'budget_minor', 'hard_cap_minor'],
      );
  String? get tokenUsage => _firstValue(
        metricSources,
        const ['token_usage', 'tokens_used', 'total_tokens'],
      );
  String? get gpuTime => _firstValue(
        metricSources,
        const ['gpu_time', 'gpu_seconds', 'gpu_duration'],
      );
  String? get previewUrl => _text(
        latestEvent,
        const ['preview_url', 'url', 'artifact_url'],
      );

  String get badge {
    if (!projection.connected) return 'OFFLINE';
    if (latestEvent == null) return 'READY';
    final value = executionStatus.trim();
    return value.isEmpty ? 'CONNECTED' : value.toUpperCase();
  }
}

class _MainColumn extends StatelessWidget {
  const _MainColumn({
    required this.model,
    required this.onNavigate,
    required this.onRefreshRequested,
  });

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Header(
            model: model,
            onNavigate: onNavigate,
            onRefreshRequested: onRefreshRequested,
          ),
          const SizedBox(height: 12),
          _Workflow(
            model: model,
            onNavigate: onNavigate,
          ),
          const SizedBox(height: 12),
          _LiveExecution(model: model, onNavigate: onNavigate),
          const SizedBox(height: 12),
          _Workspace(model: model, onNavigate: onNavigate),
          const SizedBox(height: 12),
          _BottomPanels(model: model, onNavigate: onNavigate),
        ],
      );
}

class _Header extends StatelessWidget {
  const _Header({
    required this.model,
    required this.onNavigate,
    required this.onRefreshRequested,
  });

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final title = Wrap(
            spacing: 10,
            runSpacing: 6,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(
                _home(context, 'Active Workflow'),
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontSize: 20,
                      fontWeight: FontWeight.w800,
                    ),
              ),
              _StatusPill(
                text: _home(context, model.badge),
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
                  _isTr(context) ? 'Çalışma Alanını Aç' : 'Open Workspace',
                ),
              ),
              const SizedBox(width: 5),
              IconButton(
                tooltip: _isTr(context) ? 'Durumu yenile' : 'Refresh state',
                onPressed: onRefreshRequested,
                icon: const Icon(Icons.refresh_rounded, size: 18),
              ),
            ],
          );
          if (constraints.maxWidth < 650) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [title, const SizedBox(height: 8), actions],
            );
          }
          return Row(
            children: [Expanded(child: title), actions],
          );
        },
      );
}

class _Workflow extends StatelessWidget {
  const _Workflow({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  static const stages = <_Stage>[
    _Stage('Goal Intake', Icons.track_changes_outlined, DesktopSection.goals),
    _Stage('Planning', Icons.account_tree_outlined, DesktopSection.workflows),
    _Stage('Execution', Icons.play_circle_outline, DesktopSection.agents),
    _Stage('Verification', Icons.verified_user_outlined, DesktopSection.evidence),
    _Stage('Delivery', Icons.inventory_2_outlined, DesktopSection.artifacts),
  ];

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('reference-workflow-pipeline'),
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 10),
        child: Column(
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                if (constraints.maxWidth < 620) {
                  final width = (constraints.maxWidth - 8) / 2;
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (var index = 0; index < stages.length; index++)
                        SizedBox(
                          width: width,
                          child: _StageCard(
                            stage: stages[index],
                            state: model.stageState(index),
                            active: model.stageIndex == index,
                            onTap: () => onNavigate(stages[index].destination),
                          ),
                        ),
                    ],
                  );
                }
                return Row(
                  children: [
                    for (var index = 0; index < stages.length; index++) ...[
                      Expanded(
                        child: _StageCard(
                          stage: stages[index],
                          state: model.stageState(index),
                          active: model.stageIndex == index,
                          onTap: () => onNavigate(stages[index].destination),
                        ),
                      ),
                      if (index != stages.length - 1)
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Icon(
                            Icons.arrow_forward_rounded,
                            size: 17,
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                    ],
                  ],
                );
              },
            ),
            const SizedBox(height: 11),
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
                      value: model.progress ?? 0,
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

class _Stage {
  const _Stage(this.title, this.icon, this.destination);

  final String title;
  final IconData icon;
  final DesktopSection destination;
}

class _StageCard extends StatelessWidget {
  const _StageCard({
    required this.stage,
    required this.state,
    required this.active,
    required this.onTap,
  });

  final _Stage stage;
  final String state;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final done = state == 'Done';
    final accent = active
        ? IlaiosTheme.enterpriseCyan
        : done
            ? IlaiosTheme.success
            : Theme.of(context).colorScheme.onSurfaceVariant;
    return Material(
      color: active
          ? IlaiosTheme.coreBlue.withValues(alpha: .08)
          : Theme.of(context).colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(
          color: active
              ? IlaiosTheme.enterpriseCyan
              : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          height: 82,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 8),
            child: Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: accent.withValues(alpha: .08),
                    border: Border.all(color: accent.withValues(alpha: .52)),
                  ),
                  child: Icon(stage.icon, size: 19, color: accent),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        _home(context, stage.title),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          fontSize: 10.8,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        _home(context, state),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 9, color: accent),
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

class _LiveExecution extends StatelessWidget {
  const _LiveExecution({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('reference-live-execution'),
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionHeader(
              title: _home(context, 'LIVE EXECUTION'),
              trailing: model.leases.isEmpty
                  ? _home(context, 'No active agents')
                  : '${model.leases.length} ${_home(context, 'active')}',
              onTap: () => onNavigate(DesktopSection.agents),
            ),
            const SizedBox(height: 9),
            if (model.leases.isEmpty)
              _TruthEmpty(
                icon: Icons.groups_2_outlined,
                title: _isTr(context) ? 'Aktif ajan yok' : 'No active agents',
                body: _isTr(context)
                    ? 'Scheduler yetkili aktif worker lease verisi sunmuyor.'
                    : 'The scheduler exposes no authoritative active worker leases.',
              )
            else
              LayoutBuilder(
                builder: (context, constraints) {
                  final columns = constraints.maxWidth >= 780
                      ? 7
                      : constraints.maxWidth >= 560
                          ? 5
                          : 3;
                  final visibleColumns = model.leases.length < columns
                      ? model.leases.length
                      : columns;
                  final width = (constraints.maxWidth -
                          ((visibleColumns - 1) * 8)) /
                      visibleColumns;
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (var index = 0; index < model.leases.length; index++)
                        SizedBox(
                          width: width,
                          child: _WorkerCard(
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

class _WorkerCard extends StatelessWidget {
  const _WorkerCard({required this.worker, required this.index});

  final Map<String, Object?> worker;
  final int index;

  @override
  Widget build(BuildContext context) {
    final role = _text(worker, const ['role', 'worker_type', 'worker_id']) ??
        '${_home(context, 'Worker')} ${index + 1}';
    final state = _text(worker, const ['state', 'status', 'health']) ??
        _home(context, 'Active lease');
    final task = _text(worker, const ['task', 'task_id', 'request_id']) ?? '—';
    final pending = state.toLowerCase().contains('pending');
    final accent = pending ? IlaiosTheme.warning : IlaiosTheme.success;
    return Container(
      height: 118,
      padding: const EdgeInsets.all(9),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Icon(Icons.circle, size: 7, color: accent),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  role,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            width: 40,
            height: 40,
            decoration: BoxDecoration(
              color: IlaiosTheme.coreBlue.withValues(alpha: .10),
              borderRadius: BorderRadius.circular(10),
              border: Border.all(
                color: IlaiosTheme.coreBlue.withValues(alpha: .30),
              ),
            ),
            child: const Icon(
              Icons.smart_toy_outlined,
              color: IlaiosTheme.enterpriseCyan,
              size: 22,
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
              fontSize: 8.8,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _Workspace extends StatelessWidget {
  const _Workspace({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('reference-workspace'),
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 38,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Row(
                  children: [
                    _WorkspaceTab(
                      icon: Icons.code_rounded,
                      label: _home(context, 'Live Code'),
                      selected: true,
                    ),
                    _WorkspaceTab(
                      icon: Icons.terminal_rounded,
                      label: _home(context, 'Terminal'),
                    ),
                    _WorkspaceTab(
                      icon: Icons.public_rounded,
                      label: _home(context, 'Browser'),
                    ),
                    if (MediaQuery.sizeOf(context).width >= 1320) ...[
                      _WorkspaceTab(
                        icon: Icons.folder_open_outlined,
                        label: _home(context, 'Files'),
                      ),
                      _WorkspaceTab(
                        icon: Icons.receipt_long_outlined,
                        label: _home(context, 'Logs'),
                      ),
                      _WorkspaceTab(
                        icon: Icons.bolt_outlined,
                        label: _home(context, 'Events'),
                      ),
                    ],
                    const Spacer(),
                    TextButton(
                      onPressed: () => onNavigate(DesktopSection.liveWorkspace),
                      child: Text(
                        _isTr(context) ? 'Aç →' : 'Open →',
                        style: const TextStyle(fontSize: 10),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const Divider(height: 1),
            SizedBox(
              height: 244,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  if (constraints.maxWidth < 680) {
                    return _EventPane(model: model);
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      SizedBox(
                        width: constraints.maxWidth * .20,
                        child: const _FileShellPane(),
                      ),
                      const VerticalDivider(width: 1),
                      Expanded(flex: 45, child: _EventPane(model: model)),
                      const VerticalDivider(width: 1),
                      Expanded(flex: 35, child: _PreviewPane(model: model)),
                    ],
                  );
                },
              ),
            ),
          ],
        ),
      );
}

class _WorkspaceTab extends StatelessWidget {
  const _WorkspaceTab({
    required this.icon,
    required this.label,
    this.selected = false,
  });

  final IconData icon;
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(right: 12),
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
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 9.7,
                color: selected
                    ? IlaiosTheme.enterpriseCyan
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
}

class _FileShellPane extends StatelessWidget {
  const _FileShellPane();

  @override
  Widget build(BuildContext context) => Container(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.folder_open_outlined, size: 15),
                const SizedBox(width: 6),
                Text(
                  _isTr(context) ? 'Dosyalar' : 'Files',
                  style: Theme.of(context).textTheme.labelMedium,
                ),
              ],
            ),
            const SizedBox(height: 12),
            _TruthEmpty(
              icon: Icons.account_tree_outlined,
              title: _isTr(context) ? 'Dosya ağacı bekleniyor' : 'File tree pending',
              body: _isTr(context)
                  ? 'Yetkili Desktop API dosya ağacı sunmadı.'
                  : 'The authoritative Desktop API has not exposed a file tree.',
              compact: true,
            ),
          ],
        ),
      );
}

class _EventPane extends StatelessWidget {
  const _EventPane({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(7).toList();
    return Container(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            height: 32,
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
                const Icon(Icons.terminal_rounded, size: 14),
                const SizedBox(width: 6),
                Text(
                  _isTr(context) ? 'Terminal / Canlı Olaylar' : 'Terminal / Live Events',
                  style: Theme.of(context).textTheme.labelSmall,
                ),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(9),
              child: events.isEmpty
                  ? _TruthEmpty(
                      icon: Icons.terminal_rounded,
                      title: _isTr(context)
                          ? 'Canlı terminal verisi yok'
                          : 'No live terminal data',
                      body: _isTr(context)
                          ? 'Yetkili çalışma zamanı terminal veya olay satırı sunmadı.'
                          : 'The authoritative runtime exposes no terminal or event lines.',
                      compact: true,
                    )
                  : ListView.builder(
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: events.length,
                      itemBuilder: (context, index) {
                        final event = events[index];
                        final name = _text(
                              event,
                              const ['event_type', 'type', 'name', 'status'],
                            ) ??
                            'event';
                        final time = _text(
                              event,
                              const ['timestamp', 'created_at', 'time'],
                            ) ??
                            '';
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 5),
                          child: Row(
                            children: [
                              const Icon(
                                Icons.check_rounded,
                                size: 12,
                                color: IlaiosTheme.success,
                              ),
                              const SizedBox(width: 5),
                              Expanded(
                                child: Text(
                                  time.isEmpty ? name : '$time  $name',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontFamily: 'monospace',
                                    fontSize: 9.2,
                                  ),
                                ),
                              ),
                            ],
                          ),
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

class _PreviewPane extends StatelessWidget {
  const _PreviewPane({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => Container(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        child: Column(
          children: [
            Container(
              height: 32,
              padding: const EdgeInsets.symmetric(horizontal: 8),
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
                  const SizedBox(width: 5),
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
                child: _TruthEmpty(
                  icon: Icons.public_rounded,
                  title: model.previewUrl == null
                      ? (_isTr(context) ? 'Önizleme yok' : 'No preview')
                      : (_isTr(context) ? 'Önizleme hazır' : 'Preview available'),
                  body: model.previewUrl == null
                      ? (_isTr(context)
                          ? 'Yetkili tarayıcı önizlemesi sunulmadı.'
                          : 'No authoritative browser preview is exposed.')
                      : model.previewUrl!,
                  compact: true,
                ),
              ),
            ),
          ],
        ),
      );
}

class _BottomPanels extends StatelessWidget {
  const _BottomPanels({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final artifacts = _Artifacts(model: model, onNavigate: onNavigate);
          final evidence = _Evidence(model: model, onNavigate: onNavigate);
          if (constraints.maxWidth < 680) {
            return Column(
              children: [artifacts, const SizedBox(height: 12), evidence],
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

class _Artifacts extends StatelessWidget {
  const _Artifacts({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final records = model.snapshot.evidenceRecords.reversed.take(3).toList();
    return _Panel(
      key: const Key('reference-latest-artifacts'),
      padding: const EdgeInsets.all(11),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _SectionHeader(
            title: _home(context, 'LATEST ARTIFACTS'),
            actionLabel: _home(context, 'View all →'),
            onTap: () => onNavigate(DesktopSection.artifacts),
          ),
          const SizedBox(height: 7),
          if (records.isEmpty)
            _TruthEmpty(
              icon: Icons.inventory_2_outlined,
              title: _home(context, 'Unavailable'),
              body: _home(
                context,
                'No verified artifact evidence is available.',
              ),
              compact: true,
            )
          else
            for (final record in records) _ArtifactRow(record: record),
        ],
      ),
    );
  }
}

class _ArtifactRow extends StatelessWidget {
  const _ArtifactRow({required this.record});

  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 5),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            const Icon(
              Icons.verified_outlined,
              size: 16,
              color: IlaiosTheme.enterpriseCyan,
            ),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                record.action,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 9.8, fontWeight: FontWeight.w700),
              ),
            ),
            Text('#${record.sequence}', style: Theme.of(context).textTheme.labelSmall),
          ],
        ),
      );
}

class _Evidence extends StatelessWidget {
  const _Evidence({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('reference-evidence-verification'),
        padding: const EdgeInsets.all(11),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionHeader(
              title: _home(context, 'EVIDENCE & VERIFICATION'),
              actionLabel: _home(context, 'View all →'),
              onTap: () => onNavigate(DesktopSection.evidence),
            ),
            const SizedBox(height: 7),
            LayoutBuilder(
              builder: (context, constraints) {
                final width = constraints.maxWidth >= 390
                    ? (constraints.maxWidth - 14) / 3
                    : constraints.maxWidth;
                return Wrap(
                  spacing: 7,
                  runSpacing: 7,
                  children: [
                    _ProofTile(
                      width: width,
                      icon: Icons.fact_check_outlined,
                      label: _isTr(context) ? 'QA Kanıtı' : 'QA Evidence',
                      value: model.snapshot.evidenceCount > 0
                          ? _home(context, 'Available')
                          : _home(context, 'Unavailable'),
                    ),
                    _ProofTile(
                      width: width,
                      icon: Icons.security_outlined,
                      label: _isTr(context) ? 'Güvenlik' : 'Security',
                      value: model.projection.connected
                          ? _home(context, 'Available')
                          : _home(context, 'Unavailable'),
                    ),
                    _ProofTile(
                      width: width,
                      icon: Icons.policy_outlined,
                      label: _isTr(context) ? 'Politika' : 'Policy',
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

class _ProofTile extends StatelessWidget {
  const _ProofTile({
    required this.width,
    required this.icon,
    required this.label,
    required this.value,
  });

  final double width;
  final IconData icon;
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        width: width,
        height: 78,
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.verified_user_outlined, size: 18, color: IlaiosTheme.success),
            const Spacer(),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w700),
            ),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
        ),
      );
}

class _RightRail extends StatelessWidget {
  const _RightRail({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => Column(
        key: const Key('reference-right-rail'),
        children: [
          _RailCard(
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
          _CostCard(model: model, onTap: () => onNavigate(DesktopSection.costs)),
          const SizedBox(height: 10),
          _RailCard(
            title: _home(context, 'APPROVALS'),
            onTap: () => onNavigate(DesktopSection.approvals),
            rows: [
              (_home(context, 'Pending'), '${model.pendingApprovals}'),
              (_home(context, 'Approved'), '${model.approvedCount}'),
              (_home(context, 'Denied'), '${model.deniedCount}'),
            ],
            footer: _isTr(context) ? 'Onayları Görüntüle' : 'View approvals',
          ),
          const SizedBox(height: 10),
          _LogsCard(model: model),
        ],
      );
}

class _RailCard extends StatelessWidget {
  const _RailCard({
    required this.title,
    required this.rows,
    required this.onTap,
    this.footer,
  });

  final String title;
  final List<(String, String)> rows;
  final VoidCallback onTap;
  final String? footer;

  @override
  Widget build(BuildContext context) => _Panel(
        padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              title,
              style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3.5),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(row.$1, style: Theme.of(context).textTheme.bodySmall),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        row.$2,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.right,
                        style: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
            if (footer != null) ...[
              const SizedBox(height: 8),
              OutlinedButton(
                onPressed: onTap,
                child: Text(footer!, style: const TextStyle(fontSize: 10)),
              ),
            ],
          ],
        ),
      );
}

class _CostCard extends StatelessWidget {
  const _CostCard({required this.model, required this.onTap});

  final _DashboardModel model;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final cost = model.totalCost ?? _home(context, 'Unavailable');
    final budget = model.budget ?? _home(context, 'Unavailable');
    final fraction = _costFraction(cost, budget);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(9),
      child: _Panel(
        padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _home(context, 'COST & USAGE'),
              style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800),
            ),
            const SizedBox(height: 8),
            _ValueRow(label: _home(context, 'Total cost'), value: cost),
            _ValueRow(label: _home(context, 'Budget'), value: budget),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(999),
              child: LinearProgressIndicator(
                value: fraction ?? 0,
                minHeight: 6,
                backgroundColor:
                    Theme.of(context).colorScheme.surfaceContainerHighest,
                color: IlaiosTheme.enterpriseCyan,
              ),
            ),
            const SizedBox(height: 8),
            _ValueRow(
              label: _home(context, 'Token usage'),
              value: model.tokenUsage ?? _home(context, 'Unavailable'),
            ),
            _ValueRow(
              label: _home(context, 'GPU time'),
              value: model.gpuTime ?? _home(context, 'Unavailable'),
            ),
          ],
        ),
      ),
    );
  }
}

class _ValueRow extends StatelessWidget {
  const _ValueRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            Expanded(child: Text(label, style: Theme.of(context).textTheme.bodySmall)),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      );
}

class _LogsCard extends StatelessWidget {
  const _LogsCard({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(6).toList();
    return _Panel(
      padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _home(context, 'LATEST LOGS'),
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800),
          ),
          const SizedBox(height: 8),
          if (events.isEmpty)
            Text(
              _home(context, 'No live event records available.'),
              style: Theme.of(context).textTheme.bodySmall,
            )
          else
            for (final event in events)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3.5),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        _text(event, const ['event_type', 'type', 'name', 'status']) ??
                            'event',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                    const Icon(Icons.circle, size: 7, color: IlaiosTheme.success),
                  ],
                ),
              ),
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
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

class _SectionHeader extends StatelessWidget {
  const _SectionHeader({
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
                fontSize: 12.3,
                fontWeight: FontWeight.w800,
                letterSpacing: .12,
              ),
            ),
          ),
          if (trailing != null)
            Text(trailing!, style: Theme.of(context).textTheme.labelSmall),
          if (actionLabel != null && onTap != null)
            TextButton(
              onPressed: onTap,
              child: Text(actionLabel!, style: const TextStyle(fontSize: 10)),
            ),
        ],
      );
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.text, required this.accent});

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
            fontSize: 9.3,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

class _TruthEmpty extends StatelessWidget {
  const _TruthEmpty({
    required this.icon,
    required this.title,
    required this.body,
    this.compact = false,
  });

  final IconData icon;
  final String title;
  final String body;
  final bool compact;

  @override
  Widget build(BuildContext context) => Container(
        padding: EdgeInsets.all(compact ? 9 : 12),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Icon(icon, color: IlaiosTheme.coreBlue, size: compact ? 18 : 22),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 9.8, fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    body,
                    maxLines: compact ? 2 : 3,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

double? _costFraction(String cost, String budget) {
  final costValue = double.tryParse(cost.replaceAll(RegExp(r'[^0-9.]'), ''));
  final budgetValue = double.tryParse(budget.replaceAll(RegExp(r'[^0-9.]'), ''));
  if (costValue == null || budgetValue == null || budgetValue <= 0) return null;
  return (costValue / budgetValue).clamp(0, 1).toDouble();
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
