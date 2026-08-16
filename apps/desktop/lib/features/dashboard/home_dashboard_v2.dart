import 'package:flutter/material.dart';

import '../../app/ilaios_home_catalog.dart';
import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../navigation/desktop_section.dart';

class InteractiveHomeDashboardView extends StatelessWidget {
  const InteractiveHomeDashboardView({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.userSession,
    required this.onNavigate,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;
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
        final showRail = constraints.maxWidth >= 1160;
        final padding = constraints.maxWidth >= 1440 ? 18.0 : 14.0;
        final main = _MainColumn(
          model: model,
          onNavigate: onNavigate,
          onRefreshRequested: onRefreshRequested,
        );
        return SingleChildScrollView(
          padding: EdgeInsets.fromLTRB(padding, 14, padding, 18),
          child: showRail
              ? Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: main),
                    const SizedBox(width: 14),
                    SizedBox(
                      width: 276,
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

  bool get hasRuntimeEvent => latestEvent != null;
  List<Map<String, Object?>> get leases => _mapList(snapshot.schedulerState['leases']);
  List<Map<String, Object?>> get work => _mapList(snapshot.governanceState['work']);
  List<Map<String, Object?>> get admissions =>
      _mapList(snapshot.governanceState['admissions']);

  String get jobId => _text(latestEvent, const ['job_id']) ?? '—';
  String get started => _text(latestEvent, const ['started_at']) ?? '—';
  String get elapsed => _text(latestEvent, const ['elapsed', 'elapsed_time']) ?? '—';
  String get estimatedFinish =>
      _text(latestEvent, const ['estimated_finish', 'eta', 'finish_at']) ?? '—';
  String get currentPhase =>
      _text(latestEvent, const ['phase', 'stage', 'workflow_phase']) ?? 'Unavailable';
  String get executionStatus =>
      _text(latestEvent, const ['state', 'status', 'execution_status']) ?? 'Unavailable';

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

  String stageState(String stage) {
    final phase = _text(latestEvent, const ['phase', 'stage', 'workflow_phase']);
    if (phase == null) return 'Unavailable';
    if (_normalize(phase) != _normalize(stage)) return '—';
    return executionStatus;
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

  int get approvedCount => work.where((item) => item['status'] == 'approved').length;
  int get deniedCount => work.where((item) => item['status'] == 'denied').length;

  List<Map<String, Object?>> get costSources => <Map<String, Object?>>[
        snapshot.governanceState,
        snapshot.schedulerState,
        ..._mapList(snapshot.governanceState['costs']),
      ];

  String? get totalCost => _firstValue(costSources, const [
        'total_cost_usd',
        'cost_usd',
        'total_cost_minor',
        'spent_minor',
      ]);

  String? get budget => _firstValue(costSources, const [
        'budget_usd',
        'budget_minor',
        'hard_cap_minor',
      ]);

  String get badge {
    if (!projection.connected) return 'OFFLINE';
    if (!hasRuntimeEvent) return 'NO ACTIVE DATA';
    if (executionStatus == 'Unavailable') return 'STATE UNAVAILABLE';
    return executionStatus.toUpperCase();
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
          _WorkflowPanel(model: model, onNavigate: onNavigate),
          const SizedBox(height: 12),
          _LiveExecutionPanel(model: model, onNavigate: onNavigate),
          const SizedBox(height: 12),
          _WorkspacePanel(onNavigate: onNavigate),
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
          final compact = constraints.maxWidth < 620;
          final title = Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: 10,
                runSpacing: 7,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  Text(
                    _home(context, 'Active Workflow'),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                  ),
                  _StatusBadge(label: _home(context, model.badge)),
                ],
              ),
              const SizedBox(height: 4),
              Text(
                model.projection.connected
                    ? _localizedRuntimeStatus(context, model.status)
                    : _home(context, 'Runtime unavailable'),
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          );
          final actions = Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!model.hasRuntimeEvent)
                FilledButton.icon(
                  key: const Key('home-start-goal'),
                  onPressed: () => onNavigate(DesktopSection.goals),
                  icon: const Icon(Icons.add_circle_outline, size: 17),
                  label: Text(_isTr(context) ? 'Yeni hedef' : 'New goal'),
                ),
              if (!model.hasRuntimeEvent) const SizedBox(width: 7),
              IconButton(
                key: const Key('home-refresh-command'),
                tooltip: _home(context, 'Refresh authoritative state'),
                onPressed: onRefreshRequested,
                icon: const Icon(Icons.refresh, color: IlaiosTheme.enterpriseCyan),
              ),
            ],
          );
          if (compact) {
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                title,
                const SizedBox(height: 8),
                Align(alignment: Alignment.centerLeft, child: actions),
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: title),
              const SizedBox(width: 12),
              actions,
            ],
          );
        },
      );
}

class _WorkflowPanel extends StatelessWidget {
  const _WorkflowPanel({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  static const _stages = <_StageSpec>[
    _StageSpec('Goal Intake', 'Intent accepted', Icons.track_changes_outlined,
        DesktopSection.goals, IlaiosTheme.enterpriseCyan),
    _StageSpec('Planning', 'Workflow prepared', Icons.account_tree_outlined,
        DesktopSection.workflows, IlaiosTheme.coreBlue),
    _StageSpec('Execution', 'Agents executing', Icons.play_circle_outline,
        DesktopSection.agents, IlaiosTheme.violet),
    _StageSpec('Verification', 'Tests & evidence', Icons.verified_user_outlined,
        DesktopSection.evidence, IlaiosTheme.enterpriseCyan),
    _StageSpec('Delivery', 'Finished product', Icons.inventory_2_outlined,
        DesktopSection.artifacts, IlaiosTheme.coreBlue),
  ];

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final cardWidth = constraints.maxWidth >= 940
                    ? (constraints.maxWidth - 40) / 5
                    : constraints.maxWidth >= 520
                        ? (constraints.maxWidth - 10) / 2
                        : constraints.maxWidth;
                return Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    for (final stage in _stages)
                      SizedBox(
                        width: cardWidth,
                        child: _StageCard(
                          spec: stage,
                          state: model.stageState(stage.title),
                          onTap: () => onNavigate(stage.destination),
                        ),
                      ),
                  ],
                );
              },
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                Text(
                  _home(context, 'Overall Progress'),
                  style: Theme.of(context).textTheme.labelMedium,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(20),
                    child: LinearProgressIndicator(
                      value: model.progressValue ?? 0,
                      minHeight: 6,
                      backgroundColor:
                          Theme.of(context).colorScheme.surfaceContainerHighest,
                      color: IlaiosTheme.enterpriseCyan,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  width: 42,
                  child: Text(
                    model.progressLabel,
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: IlaiosTheme.enterpriseCyan,
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

class _StageSpec {
  const _StageSpec(this.title, this.subtitle, this.icon, this.destination, this.accent);
  final String title;
  final String subtitle;
  final IconData icon;
  final DesktopSection destination;
  final Color accent;
}

class _StageCard extends StatefulWidget {
  const _StageCard({required this.spec, required this.state, required this.onTap});
  final _StageSpec spec;
  final String state;
  final VoidCallback onTap;

  @override
  State<_StageCard> createState() => _StageCardState();
}

class _StageCardState extends State<_StageCard> {
  bool hovered = false;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final active = widget.state != '—' && widget.state != 'Unavailable';
    final accent = widget.spec.accent;
    return Semantics(
      button: true,
      label: '${_home(context, widget.spec.title)} — ${_home(context, widget.spec.subtitle)}',
      child: MouseRegion(
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: Material(
          color: active || hovered
              ? accent.withValues(alpha: .10)
              : scheme.surfaceContainerLowest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: active || hovered
                  ? accent.withValues(alpha: .72)
                  : scheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            key: ValueKey('home-stage-${widget.spec.destination.name}'),
            onTap: widget.onTap,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: ConstrainedBox(
                constraints: const BoxConstraints(minHeight: 88),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Row(
                      children: [
                        Container(
                          width: 34,
                          height: 34,
                          decoration: BoxDecoration(
                            color: accent.withValues(alpha: .15),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Icon(widget.spec.icon, size: 19, color: accent),
                        ),
                        const Spacer(),
                        Icon(
                          Icons.arrow_outward_rounded,
                          size: 15,
                          color: hovered ? accent : scheme.outline,
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      _home(context, widget.spec.title),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      widget.state == 'Unavailable'
                          ? _home(context, 'Unavailable')
                          : widget.state == '—'
                              ? _home(context, widget.spec.subtitle)
                              : widget.state,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LiveExecutionPanel extends StatelessWidget {
  const _LiveExecutionPanel({required this.model, required this.onNavigate});
  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionTitle(
              title: _home(context, 'LIVE EXECUTION'),
              trailing: '${model.leases.length} ${_home(context, 'active')}',
              accent: IlaiosTheme.violet,
            ),
            const SizedBox(height: 12),
            if (model.leases.isEmpty)
              _ActionEmpty(
                icon: Icons.groups_2_outlined,
                title: _isTr(context) ? 'Aktif ajan yok' : 'No active agents',
                body: _home(
                  context,
                  'No active worker leases are exposed by the scheduler.',
                ),
                onPrimary: () => onNavigate(DesktopSection.goals),
                onSecondary: () => onNavigate(DesktopSection.agents),
              )
            else
              Wrap(
                spacing: 10,
                runSpacing: 10,
                children: [
                  for (var i = 0; i < model.leases.length; i++)
                    _WorkerCard(worker: model.leases[i], index: i),
                ],
              ),
          ],
        ),
      );
}

class _ActionEmpty extends StatelessWidget {
  const _ActionEmpty({
    required this.icon,
    required this.title,
    required this.body,
    required this.onPrimary,
    required this.onSecondary,
  });
  final IconData icon;
  final String title;
  final String body;
  final VoidCallback onPrimary;
  final VoidCallback onSecondary;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final copy = Row(
            children: [
              Container(
                width: 46,
                height: 46,
                decoration: BoxDecoration(
                  color: IlaiosTheme.violet.withValues(alpha: .13),
                  borderRadius: BorderRadius.circular(13),
                ),
                child: Icon(icon, color: IlaiosTheme.violet),
              ),
              const SizedBox(width: 12),
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
          );
          final actions = Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              OutlinedButton(
                onPressed: onSecondary,
                child: Text(_isTr(context) ? 'Ajanları aç' : 'Open agents'),
              ),
              FilledButton(
                onPressed: onPrimary,
                child: Text(_isTr(context) ? 'Yeni hedef' : 'New goal'),
              ),
            ],
          );
          return Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerLowest,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
            ),
            child: constraints.maxWidth < 700
                ? Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [copy, const SizedBox(height: 12), actions],
                  )
                : Row(
                    children: [
                      Expanded(child: copy),
                      const SizedBox(width: 12),
                      actions,
                    ],
                  ),
          );
        },
      );
}

class _WorkerCard extends StatelessWidget {
  const _WorkerCard({required this.worker, required this.index});
  final Map<String, Object?> worker;
  final int index;

  @override
  Widget build(BuildContext context) {
    final title = _text(worker, const ['role', 'worker_type', 'worker_id']) ??
        '${_home(context, 'Worker')} ${index + 1}';
    final task = _text(worker, const ['task', 'task_id', 'request_id']) ??
        _home(context, 'Task unavailable');
    final state = _text(worker, const ['state', 'status', 'health']) ??
        _home(context, 'Active lease');
    return Container(
      width: 260,
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: IlaiosTheme.violet.withValues(alpha: .38)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.smart_toy_outlined, color: IlaiosTheme.violet),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(task, maxLines: 2, overflow: TextOverflow.ellipsis),
          const SizedBox(height: 5),
          Text(
            state,
            style: const TextStyle(
              color: IlaiosTheme.enterpriseCyan,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _WorkspacePanel extends StatelessWidget {
  const _WorkspacePanel({required this.onNavigate});
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionTitle(
              title: _home(context, 'LIVE WORKSPACE'),
              accent: IlaiosTheme.coreBlue,
              actionLabel: _isTr(context) ? 'Çalışma alanını aç →' : 'Open workspace →',
              onAction: () => onNavigate(DesktopSection.liveWorkspace),
            ),
            const SizedBox(height: 10),
            DefaultTabController(
              length: 6,
              child: Column(
                children: [
                  TabBar(
                    isScrollable: true,
                    tabAlignment: TabAlignment.start,
                    labelColor: IlaiosTheme.enterpriseCyan,
                    indicatorColor: IlaiosTheme.enterpriseCyan,
                    dividerColor: Colors.transparent,
                    tabs: [
                      Tab(text: _home(context, 'Live Code')),
                      Tab(text: _home(context, 'Terminal')),
                      Tab(text: _home(context, 'Browser')),
                      Tab(text: _home(context, 'Files')),
                      Tab(text: _home(context, 'Logs')),
                      Tab(text: _home(context, 'Events')),
                    ],
                  ),
                  const SizedBox(height: 10),
                  SizedBox(
                    height: 148,
                    child: TabBarView(
                      children: [
                        _WorkspaceState(Icons.code, _home(context, 'Live Code'),
                            _home(context, 'No source buffer is exposed by the current Desktop API.')),
                        _WorkspaceState(Icons.terminal, _home(context, 'Terminal'),
                            _home(context, 'No authoritative live events are available.')),
                        _WorkspaceState(Icons.public, _home(context, 'Browser'),
                            _home(context, 'No browser preview projection is exposed.')),
                        _WorkspaceState(Icons.folder_open_outlined, _home(context, 'Files'),
                            _isTr(context) ? 'Yetkili dosyalar sunulduğunda burada görünür.' : 'Authoritative files appear here when exposed.'),
                        _WorkspaceState(Icons.receipt_long_outlined, _home(context, 'Logs'),
                            _isTr(context) ? 'Canlı günlük kayıtları sunulduğunda burada görünür.' : 'Live log records appear here when exposed.'),
                        _WorkspaceState(Icons.bolt_outlined, _home(context, 'Events'),
                            _home(context, 'No authoritative live events are available.')),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _WorkspaceState extends StatelessWidget {
  const _WorkspaceState(this.icon, this.title, this.body);
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 25, color: IlaiosTheme.coreBlue),
                const SizedBox(height: 7),
                Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 4),
                Text(
                  body,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ],
            ),
          ),
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
          final artifacts = _ArtifactsPanel(model: model, onNavigate: onNavigate);
          final evidence = _EvidencePanel(model: model, onNavigate: onNavigate);
          if (constraints.maxWidth < 720) {
            return Column(children: [artifacts, const SizedBox(height: 12), evidence]);
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

class _ArtifactsPanel extends StatelessWidget {
  const _ArtifactsPanel({required this.model, required this.onNavigate});
  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final records = model.snapshot.evidenceRecords.reversed.take(2).toList();
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _SectionTitle(
            title: _home(context, 'LATEST ARTIFACTS'),
            accent: IlaiosTheme.coreBlue,
            actionLabel: _home(context, 'View all →'),
            onAction: () => onNavigate(DesktopSection.artifacts),
          ),
          const SizedBox(height: 10),
          if (records.isEmpty)
            _CompactEmpty(
              Icons.inventory_2_outlined,
              _home(context, 'No verified artifact evidence is available.'),
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
        margin: const EdgeInsets.only(bottom: 7),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            const Icon(Icons.verified_outlined, color: IlaiosTheme.enterpriseCyan),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                record.action,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700),
              ),
            ),
            Text('#${record.sequence}', style: Theme.of(context).textTheme.labelSmall),
          ],
        ),
      );
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel({required this.model, required this.onNavigate});
  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionTitle(
              title: _home(context, 'EVIDENCE & VERIFICATION'),
              accent: IlaiosTheme.enterpriseCyan,
              actionLabel: _home(context, 'View all →'),
              onAction: () => onNavigate(DesktopSection.evidence),
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _MiniEvidence(Icons.verified_user_outlined, _home(context, 'Verified'),
                    model.snapshot.evidenceCount > 0 ? _home(context, 'Available') : _home(context, 'Unavailable'), IlaiosTheme.enterpriseCyan),
                _MiniEvidence(Icons.policy_outlined, _home(context, 'Policy'),
                    model.projection.connected ? _home(context, 'Available') : _home(context, 'Unavailable'), IlaiosTheme.violet),
                _MiniEvidence(Icons.route_outlined, _home(context, 'Routes'),
                    model.snapshot.runtimeRouteCount > 0 ? '${model.snapshot.runtimeRouteCount}' : _home(context, 'Unavailable'), IlaiosTheme.coreBlue),
              ],
            ),
          ],
        ),
      );
}

class _CompactEmpty extends StatelessWidget {
  const _CompactEmpty(this.icon, this.text);
  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Icon(icon, color: IlaiosTheme.coreBlue),
            const SizedBox(width: 9),
            Expanded(child: Text(text, style: Theme.of(context).textTheme.bodySmall)),
          ],
        ),
      );
}

class _MiniEvidence extends StatelessWidget {
  const _MiniEvidence(this.icon, this.label, this.value, this.accent);
  final IconData icon;
  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) => Container(
        width: 126,
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: .07),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: accent.withValues(alpha: .28)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 18, color: accent),
            const SizedBox(height: 6),
            Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(height: 2),
            Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800)),
          ],
        ),
      );
}

class _RightRail extends StatelessWidget {
  const _RightRail({required this.model, required this.onNavigate});
  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final panels = <Widget>[
            _RailPanel(
              title: _home(context, 'STATUS'),
              accent: IlaiosTheme.coreBlue,
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
            _RailPanel(
              title: _home(context, 'COST & USAGE'),
              accent: IlaiosTheme.violet,
              onTap: () => onNavigate(DesktopSection.costs),
              rows: [
                (_home(context, 'Total cost'), model.totalCost ?? _home(context, 'Unavailable')),
                (_home(context, 'Budget'), model.budget ?? _home(context, 'Unavailable')),
                (_home(context, 'Token usage'), _home(context, 'Unavailable')),
                (_home(context, 'GPU time'), _home(context, 'Unavailable')),
              ],
            ),
            _RailPanel(
              title: _home(context, 'APPROVALS'),
              accent: IlaiosTheme.enterpriseCyan,
              onTap: () => onNavigate(DesktopSection.approvals),
              rows: [
                (_home(context, 'Pending'), '${model.pendingApprovals}'),
                (_home(context, 'Approved'), '${model.approvedCount}'),
                (_home(context, 'Denied'), '${model.deniedCount}'),
              ],
            ),
            _LogsPanel(model: model),
          ];
          if (constraints.maxWidth > 500) {
            return Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                for (final panel in panels)
                  SizedBox(width: (constraints.maxWidth - 10) / 2, child: panel),
              ],
            );
          }
          return Column(
            children: [
              for (var i = 0; i < panels.length; i++) ...[
                panels[i],
                if (i != panels.length - 1) const SizedBox(height: 10),
              ],
            ],
          );
        },
      );
}

class _RailPanel extends StatelessWidget {
  const _RailPanel({
    required this.title,
    required this.accent,
    required this.rows,
    required this.onTap,
  });
  final String title;
  final Color accent;
  final List<(String, String)> rows;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: accent.withValues(alpha: .24)),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(13),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Container(
                      width: 4,
                      height: 18,
                      decoration: BoxDecoration(
                        color: accent,
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(title,
                          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                fontWeight: FontWeight.w800,
                              )),
                    ),
                    Icon(Icons.chevron_right, size: 17, color: accent),
                  ],
                ),
                const SizedBox(height: 8),
                for (final row in rows)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 3),
                    child: Row(
                      children: [
                        Expanded(child: Text(row.$1, style: Theme.of(context).textTheme.bodySmall)),
                        const SizedBox(width: 8),
                        Flexible(
                          child: Text(row.$2, textAlign: TextAlign.right, maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context).textTheme.labelMedium),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ),
      );
}

class _LogsPanel extends StatelessWidget {
  const _LogsPanel({required this.model});
  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final events = model.snapshot.liveEvents.reversed.take(4).toList();
    return _Panel(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _SectionTitle(title: _home(context, 'LATEST LOGS'), accent: IlaiosTheme.violet),
          const SizedBox(height: 8),
          if (events.isEmpty)
            Text(_home(context, 'No live event records available.'),
                textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall)
          else
            for (final event in events)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 3),
                child: Text(
                  _text(event, const ['event_type', 'type', 'name']) ?? 'event',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
        ],
      ),
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child});
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(13),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: child,
      );
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.accent,
    this.trailing,
    this.actionLabel,
    this.onAction,
  });
  final String title;
  final Color accent;
  final String? trailing;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Container(
            width: 4,
            height: 18,
            decoration: BoxDecoration(color: accent, borderRadius: BorderRadius.circular(4)),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(title,
                style: Theme.of(context).textTheme.labelLarge?.copyWith(
                      fontWeight: FontWeight.w800,
                    )),
          ),
          if (trailing != null)
            Text(trailing!, style: Theme.of(context).textTheme.bodySmall),
          if (actionLabel != null && onAction != null)
            TextButton(onPressed: onAction, child: Text(actionLabel!)),
        ],
      );
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(
          color: IlaiosTheme.enterpriseCyan.withValues(alpha: .11),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: IlaiosTheme.enterpriseCyan.withValues(alpha: .44)),
        ),
        child: Text(label,
            style: const TextStyle(
              color: IlaiosTheme.enterpriseCyan,
              fontSize: 9,
              fontWeight: FontWeight.w800,
            )),
      );
}

bool _isTr(BuildContext context) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _home(BuildContext context, String english) =>
    IlaiosHomeCatalog.text(context.ilaiosLocale.locale.code, english);

String _localizedRuntimeStatus(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    'Control plane configured' => 'Kontrol düzlemi yapılandırıldı',
    _ => value,
  };
}

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
