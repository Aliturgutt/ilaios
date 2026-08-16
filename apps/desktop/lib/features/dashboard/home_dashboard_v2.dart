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
        final showRightRail = constraints.maxWidth >= 1020;
        final padding = constraints.maxWidth >= 1440 ? 18.0 : 14.0;
        final main = _MainColumn(
          model: model,
          onNavigate: onNavigate,
          onRefreshRequested: onRefreshRequested,
        );
        return Scrollbar(
          thumbVisibility: false,
          child: SingleChildScrollView(
            padding: EdgeInsets.fromLTRB(padding, 14, padding, 18),
            child: showRightRail
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
          ),
        );
      },
    );
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
          _WorkspacePanel(model: model, onNavigate: onNavigate),
          const SizedBox(height: 12),
          _BottomPanels(model: model, onNavigate: onNavigate),
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
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                crossAxisAlignment: WrapCrossAlignment.center,
                spacing: 10,
                runSpacing: 8,
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
          ),
        ),
        if (!model.hasRuntimeEvent) ...[
          FilledButton.icon(
            key: const Key('home-start-goal'),
            onPressed: () => onNavigate(DesktopSection.goals),
            icon: const Icon(Icons.add_circle_outline, size: 18),
            label: Text(_isTr(context) ? 'Yeni hedef' : 'New goal'),
          ),
          const SizedBox(width: 8),
        ],
        IconButton(
          key: const Key('home-refresh-command'),
          tooltip: _home(context, 'Refresh authoritative state'),
          onPressed: onRefreshRequested,
          icon: Icon(Icons.refresh, color: scheme.primary),
        ),
      ],
    );
  }
}

class _WorkflowPanel extends StatelessWidget {
  const _WorkflowPanel({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  static const _stages = <_StageSpec>[
    _StageSpec(
      englishTitle: 'Goal Intake',
      englishSubtitle: 'Intent accepted',
      icon: Icons.track_changes_outlined,
      destination: DesktopSection.goals,
      accent: IlaiosTheme.enterpriseCyan,
    ),
    _StageSpec(
      englishTitle: 'Planning',
      englishSubtitle: 'Workflow prepared',
      icon: Icons.account_tree_outlined,
      destination: DesktopSection.workflows,
      accent: IlaiosTheme.coreBlue,
    ),
    _StageSpec(
      englishTitle: 'Execution',
      englishSubtitle: 'Agents executing',
      icon: Icons.play_circle_outline,
      destination: DesktopSection.agents,
      accent: IlaiosTheme.violet,
    ),
    _StageSpec(
      englishTitle: 'Verification',
      englishSubtitle: 'Tests & evidence',
      icon: Icons.verified_user_outlined,
      destination: DesktopSection.evidence,
      accent: IlaiosTheme.enterpriseCyan,
    ),
    _StageSpec(
      englishTitle: 'Delivery',
      englishSubtitle: 'Finished product',
      icon: Icons.inventory_2_outlined,
      destination: DesktopSection.artifacts,
      accent: IlaiosTheme.coreBlue,
    ),
  ];

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                if (constraints.maxWidth >= 760) {
                  return Row(
                    children: [
                      for (var i = 0; i < _stages.length; i++) ...[
                        Expanded(
                          child: _StageCard(
                            spec: _stages[i],
                            state: model.stageState(_stages[i].englishTitle),
                            onTap: () => onNavigate(_stages[i].destination),
                          ),
                        ),
                        if (i != _stages.length - 1)
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 5),
                            child: Icon(
                              Icons.arrow_forward_rounded,
                              size: 16,
                              color: Theme.of(context).colorScheme.outline,
                            ),
                          ),
                      ],
                    ],
                  );
                }
                return Wrap(
                  spacing: 10,
                  runSpacing: 10,
                  children: [
                    for (final stage in _stages)
                      SizedBox(
                        width: constraints.maxWidth >= 480
                            ? (constraints.maxWidth - 10) / 2
                            : constraints.maxWidth,
                        child: _StageCard(
                          spec: stage,
                          state: model.stageState(stage.englishTitle),
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
                      value: model.progressValue,
                      minHeight: 6,
                      backgroundColor:
                          Theme.of(context).colorScheme.surfaceContainerHighest,
                      color: IlaiosTheme.enterpriseCyan,
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  width: 40,
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
  const _StageSpec({
    required this.englishTitle,
    required this.englishSubtitle,
    required this.icon,
    required this.destination,
    required this.accent,
  });

  final String englishTitle;
  final String englishSubtitle;
  final IconData icon;
  final DesktopSection destination;
  final Color accent;
}

class _StageCard extends StatefulWidget {
  const _StageCard({
    required this.spec,
    required this.state,
    required this.onTap,
  });

  final _StageSpec spec;
  final String state;
  final VoidCallback onTap;

  @override
  State<_StageCard> createState() => _StageCardState();
}

class _StageCardState extends State<_StageCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final active = widget.state != '—' && widget.state != 'Unavailable';
    final accent = widget.spec.accent;
    return Semantics(
      button: true,
      label: '${_home(context, widget.spec.englishTitle)} — ${_home(context, widget.spec.englishSubtitle)}',
      child: MouseRegion(
        onEnter: (_) => setState(() => _hovered = true),
        onExit: (_) => setState(() => _hovered = false),
        child: Material(
          color: active || _hovered
              ? accent.withValues(alpha: Theme.of(context).brightness == Brightness.dark ? .11 : .08)
              : scheme.surfaceContainerLowest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: active || _hovered
                  ? accent.withValues(alpha: .78)
                  : scheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            key: ValueKey('home-stage-${widget.spec.destination.name}'),
            onTap: widget.onTap,
            overlayColor: WidgetStatePropertyAll(accent.withValues(alpha: .12)),
            child: SizedBox(
              height: 104,
              child: Padding(
                padding: const EdgeInsets.all(12),
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
                            color: accent.withValues(alpha: .16),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Icon(widget.spec.icon, size: 19, color: accent),
                        ),
                        const Spacer(),
                        Icon(
                          Icons.arrow_outward_rounded,
                          size: 15,
                          color: _hovered ? accent : scheme.outline,
                        ),
                      ],
                    ),
                    const SizedBox(height: 9),
                    Text(
                      _home(context, widget.spec.englishTitle),
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
                              ? _home(context, widget.spec.englishSubtitle)
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
              _EmptyActionState(
                icon: Icons.groups_2_outlined,
                title: _isTr(context) ? 'Aktif ajan yok' : 'No active agents',
                body: _home(
                  context,
                  'No active worker leases are exposed by the scheduler.',
                ),
                primaryLabel: _isTr(context) ? 'Yeni hedef oluştur' : 'Create a new goal',
                secondaryLabel: _isTr(context) ? 'Ajanları aç' : 'Open agents',
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
  const _WorkspacePanel({required this.model, required this.onNavigate});

  final _DashboardModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Panel(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _SectionTitle(
              title: _home(context, 'LIVE WORKSPACE'),
              actionLabel: _isTr(context) ? 'Çalışma alanını aç →' : 'Open workspace →',
              onAction: () => onNavigate(DesktopSection.liveWorkspace),
              accent: IlaiosTheme.coreBlue,
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
                    height: 160,
                    child: TabBarView(
                      children: [
                        _WorkspaceEmpty(
                          icon: Icons.code,
                          title: _home(context, 'Live Code'),
                          body: _home(
                            context,
                            'No source buffer is exposed by the current Desktop API.',
                          ),
                        ),
                        _WorkspaceEmpty(
                          icon: Icons.terminal,
                          title: _home(context, 'Terminal'),
                          body: _home(
                            context,
                            'No authoritative live events are available.',
                          ),
                        ),
                        _WorkspaceEmpty(
                          icon: Icons.public,
                          title: _home(context, 'Browser'),
                          body: _home(
                            context,
                            'No browser preview projection is exposed.',
                          ),
                        ),
                        _WorkspaceEmpty(
                          icon: Icons.folder_open_outlined,
                          title: _home(context, 'Files'),
                          body: _isTr(context)
                              ? 'Yetkili çalışma alanı dosyaları sunulduğunda burada görünür.'
                              : 'Authoritative workspace files appear here when exposed.',
                        ),
                        _WorkspaceEmpty(
                          icon: Icons.receipt_long_outlined,
                          title: _home(context, 'Logs'),
                          body: _isTr(context)
                              ? 'Canlı günlük kaydı sunulduğunda burada görünür.'
                              : 'Live log records appear here when exposed.',
                        ),
                        _WorkspaceEmpty(
                          icon: Icons.bolt_outlined,
                          title: _home(context, 'Events'),
                          body: _home(
                            context,
                            'No authoritative live events are available.',
                          ),
                        ),
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

class _WorkspaceEmpty extends StatelessWidget {
  const _WorkspaceEmpty({required this.icon, required this.title, required this.body});

  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 28, color: IlaiosTheme.coreBlue),
                const SizedBox(height: 8),
                Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
                const SizedBox(height: 5),
                Text(
                  body,
                  textAlign: TextAlign.center,
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
            actionLabel: _home(context, 'View all →'),
            onAction: () => onNavigate(DesktopSection.artifacts),
            accent: IlaiosTheme.coreBlue,
          ),
          const SizedBox(height: 12),
          if (records.isEmpty)
            _CompactEmpty(
              icon: Icons.inventory_2_outlined,
              text: _home(
                context,
                'No verified artifact evidence is available.',
              ),
            )
          else
            for (final record in records) _EvidenceArtifactRow(record: record),
        ],
      ),
    );
  }
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
              actionLabel: _home(context, 'View all →'),
              onAction: () => onNavigate(DesktopSection.evidence),
              accent: IlaiosTheme.enterpriseCyan,
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _MiniEvidence(
                  icon: Icons.verified_user_outlined,
                  label: _home(context, 'Verified'),
                  value: model.snapshot.evidenceCount > 0
                      ? _home(context, 'Available')
                      : _home(context, 'Unavailable'),
                  accent: IlaiosTheme.enterpriseCyan,
                ),
                _MiniEvidence(
                  icon: Icons.policy_outlined,
                  label: _home(context, 'Policy'),
                  value: model.projection.connected
                      ? _home(context, 'Available')
                      : _home(context, 'Unavailable'),
                  accent: IlaiosTheme.violet,
                ),
                _MiniEvidence(
                  icon: Icons.route_outlined,
                  label: _home(context, 'Routes'),
                  value: model.snapshot.runtimeRouteCount > 0
                      ? '${model.snapshot.runtimeRouteCount}'
                      : _home(context, 'Unavailable'),
                  accent: IlaiosTheme.coreBlue,
                ),
              ],
            ),
          ],
        ),
      );
}

class _EvidenceArtifactRow extends StatelessWidget {
  const _EvidenceArtifactRow({required this.record});

  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 8),
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
            const SizedBox(width: 8),
            Text(
              '#${record.sequence}',
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
        children: [
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
          const SizedBox(height: 10),
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
          const SizedBox(height: 10),
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
          const SizedBox(height: 10),
          _LogsPanel(model: model),
        ],
      );
}

class _RailPanel extends StatefulWidget {
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
  State<_RailPanel> createState() => _RailPanelState();
}

class _RailPanelState extends State<_RailPanel> {
  bool hovered = false;

  @override
  Widget build(BuildContext context) => MouseRegion(
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: Material(
          color: hovered
              ? widget.accent.withValues(alpha: .07)
              : Theme.of(context).colorScheme.surfaceContainerLow,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: hovered
                  ? widget.accent.withValues(alpha: .65)
                  : Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: widget.onTap,
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
                          color: widget.accent,
                          borderRadius: BorderRadius.circular(4),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          widget.title,
                          style: Theme.of(context).textTheme.labelLarge?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                      ),
                      Icon(Icons.chevron_right, size: 17, color: widget.accent),
                    ],
                  ),
                  const SizedBox(height: 10),
                  for (final row in widget.rows)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 4),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(row.$1, style: Theme.of(context).textTheme.bodySmall),
                          ),
                          const SizedBox(width: 8),
                          Flexible(
                            child: Text(
                              row.$2,
                              textAlign: TextAlign.right,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context).textTheme.labelMedium,
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
          _SectionTitle(
            title: _home(context, 'LATEST LOGS'),
            accent: IlaiosTheme.violet,
          ),
          const SizedBox(height: 10),
          if (events.isEmpty)
            Text(
              _home(context, 'No live event records available.'),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall,
            )
          else
            for (final event in events)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
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
          boxShadow: [
            BoxShadow(
              color: IlaiosTheme.coreBlue.withValues(alpha: .025),
              blurRadius: 18,
              offset: const Offset(0, 4),
            ),
          ],
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
            decoration: BoxDecoration(
              color: accent,
              borderRadius: BorderRadius.circular(4),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              title,
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                    fontWeight: FontWeight.w800,
                  ),
            ),
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
          border: Border.all(
            color: IlaiosTheme.enterpriseCyan.withValues(alpha: .44),
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: IlaiosTheme.enterpriseCyan,
            fontSize: 9,
            fontWeight: FontWeight.w800,
            letterSpacing: .2,
          ),
        ),
      );
}

class _EmptyActionState extends StatelessWidget {
  const _EmptyActionState({
    required this.icon,
    required this.title,
    required this.body,
    required this.primaryLabel,
    required this.secondaryLabel,
    required this.onPrimary,
    required this.onSecondary,
  });

  final IconData icon;
  final String title;
  final String body;
  final String primaryLabel;
  final String secondaryLabel;
  final VoidCallback onPrimary;
  final VoidCallback onSecondary;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              width: 48,
              height: 48,
              decoration: BoxDecoration(
                color: IlaiosTheme.violet.withValues(alpha: .13),
                borderRadius: BorderRadius.circular(14),
              ),
              child: Icon(icon, color: IlaiosTheme.violet),
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
            const SizedBox(width: 14),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                OutlinedButton(onPressed: onSecondary, child: Text(secondaryLabel)),
                FilledButton(onPressed: onPrimary, child: Text(primaryLabel)),
              ],
            ),
          ],
        ),
      );
}

class _CompactEmpty extends StatelessWidget {
  const _CompactEmpty({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Icon(icon, color: IlaiosTheme.coreBlue),
            const SizedBox(width: 10),
            Expanded(child: Text(text, style: Theme.of(context).textTheme.bodySmall)),
          ],
        ),
      );
}

class _MiniEvidence extends StatelessWidget {
  const _MiniEvidence({
    required this.icon,
    required this.label,
    required this.value,
    required this.accent,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color accent;

  @override
  Widget build(BuildContext context) => Container(
        width: 132,
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: .07),
          borderRadius: BorderRadius.circular(11),
          border: Border.all(color: accent.withValues(alpha: .28)),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icon, size: 19, color: accent),
            const SizedBox(height: 7),
            Text(label, style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(height: 3),
            Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800),
            ),
          ],
        ),
      );
}

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;

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

String _normalize(String value) => value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '');

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
