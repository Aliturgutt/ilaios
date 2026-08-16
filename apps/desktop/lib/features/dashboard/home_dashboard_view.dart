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
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final stacked = constraints.maxWidth < 1040;
        final main = Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _WorkflowHeader(
              model: model,
              onRefreshRequested: onRefreshRequested,
            ),
            const SizedBox(height: 10),
            _WorkflowPanel(model: model),
            const SizedBox(height: 10),
            _LiveExecutionPanel(model: model),
            const SizedBox(height: 10),
            _WorkspacePanel(model: model),
            const SizedBox(height: 10),
            _BottomPanels(model: model),
          ],
        );

        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 14),
          child: stacked
              ? Column(
                  children: [
                    main,
                    const SizedBox(height: 12),
                    _RightRail(model: model),
                  ],
                )
              : Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: main),
                    const SizedBox(width: 12),
                    SizedBox(width: 286, child: _RightRail(model: model)),
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

  String get estimatedCompletion => _firstText(
        latestEvent,
        const ['estimated_completion', 'eta', 'estimated_finish'],
      ) ??
      '—';

  String get currentPhase => _firstText(
        latestEvent,
        const ['phase', 'stage', 'workflow_phase'],
      ) ??
      'Unavailable';

  String get executionStatus => _firstText(
        latestEvent,
        const ['state', 'status', 'execution_status'],
      ) ??
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
    if (_normalizePhase(phase) != _normalizePhase(stage)) return 'Waiting';
    return executionStatus;
  }

  String workerTitle(Map<String, Object?> worker, int index) =>
      _firstText(
        worker,
        const ['role', 'worker_type', 'executor_type', 'worker_id', 'lease_id'],
      ) ??
      'Worker ${index + 1}';

  String workerTask(Map<String, Object?> worker) =>
      _firstText(
        worker,
        const ['task', 'task_id', 'current_task', 'request_id'],
      ) ??
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

  double? get budgetUsage {
    final spent = _firstNumberFromSources(
      costSources,
      const ['total_cost_usd', 'cost_usd'],
    );
    final budget = _firstNumberFromSources(costSources, const ['budget_usd']);
    if (spent == null || budget == null || budget <= 0) return null;
    return (spent / budget).clamp(0, 1).toDouble();
  }

  String? get tokenUsage => _firstValue(
        costSources,
        const ['token_usage', 'tokens_used', 'total_tokens'],
      );

  List<Map<String, Object?>> get latestLogs => snapshot.liveEvents.reversed
      .where((event) =>
          _firstText(event, const ['message', 'log', 'detail', 'event_type']) !=
          null)
      .take(5)
      .toList();
}

class _WorkflowHeader extends StatelessWidget {
  const _WorkflowHeader({
    required this.model,
    required this.onRefreshRequested,
  });

  final _DashboardModel model;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          const Text(
            'Active Workflow',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
          ),
          const SizedBox(width: 10),
          _StatusBadge(
            label: model.workflowBadgeLabel,
            color: model.workflowBadgeColor,
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              model.started == '—' ? model.status : 'Started: ${model.started}',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 10),
            ),
          ),
          const Spacer(),
          _ChromeButton(
            icon: Icons.open_in_full,
            label: 'Open in Fullscreen',
            tooltip: 'Fullscreen command is not exposed by the current Desktop API',
          ),
          const SizedBox(width: 7),
          IconButton(
            key: const Key('home-refresh-command'),
            tooltip: 'Refresh authoritative state',
            onPressed: onRefreshRequested,
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.refresh, size: 20),
          ),
        ],
      );
}

class _ChromeButton extends StatelessWidget {
  const _ChromeButton({
    required this.icon,
    required this.label,
    required this.tooltip,
  });

  final IconData icon;
  final String label;
  final String tooltip;

  @override
  Widget build(BuildContext context) => Tooltip(
        message: tooltip,
        child: Container(
          height: 32,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color: IlaiosTheme.canvas,
            borderRadius: BorderRadius.circular(7),
            border: Border.all(color: IlaiosTheme.border),
          ),
          child: Row(
            children: [
              Icon(icon, size: 14, color: IlaiosTheme.muted),
              const SizedBox(width: 6),
              Text(
                label,
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 10),
              ),
            ],
          ),
        ),
      );
}

class _WorkflowPanel extends StatelessWidget {
  const _WorkflowPanel({required this.model});

  final _DashboardModel model;

  static const _stages = <(String, String, IconData)>[
    ('Goal Intake', 'Goal captured', Icons.track_changes_outlined),
    ('Planning', 'Workflow created', Icons.account_tree_outlined),
    ('Execution', 'Agents execute', Icons.play_circle_outline),
    ('Verification', 'Test & verify', Icons.verified_user_outlined),
    ('Delivery', 'Verified output', Icons.inventory_2_outlined),
  ];

  @override
  Widget build(BuildContext context) => _Panel(
        padding: const EdgeInsets.all(10),
        child: Column(
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                if (constraints.maxWidth < 760) {
                  return Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      for (final stage in _stages)
                        SizedBox(
                          width: constraints.maxWidth < 500
                              ? constraints.maxWidth
                              : (constraints.maxWidth - 8) / 2,
                          child: _StageCard(
                            title: stage.$1,
                            subtitle: stage.$2,
                            icon: stage.$3,
                            state: model.stageState(stage.$1),
                          ),
                        ),
                    ],
                  );
                }

                return Row(
                  children: [
                    for (var index = 0; index < _stages.length; index += 1) ...[
                      Expanded(
                        child: _StageCard(
                          title: _stages[index].$1,
                          subtitle: _stages[index].$2,
                          icon: _stages[index].$3,
                          state: model.stageState(_stages[index].$1),
                        ),
                      ),
                      if (index != _stages.length - 1)
                        const Padding(
                          padding: EdgeInsets.symmetric(horizontal: 5),
                          child: Icon(
                            Icons.arrow_forward,
                            size: 15,
                            color: IlaiosTheme.muted,
                          ),
                        ),
                    ],
                  ],
                );
              },
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                const Text(
                  'Overall Progress',
                  style: TextStyle(color: IlaiosTheme.muted, fontSize: 10),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(10),
                    child: model.progressValue == null
                        ? Container(
                            key: const Key('progress-unavailable-track'),
                            height: 5,
                            color: IlaiosTheme.surfaceRaised,
                          )
                        : LinearProgressIndicator(
                            value: model.progressValue,
                            minHeight: 5,
                            backgroundColor: IlaiosTheme.surfaceRaised,
                            color: IlaiosTheme.cyan,
                          ),
                  ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  width: 38,
                  child: Text(
                    model.progressLabel,
                    textAlign: TextAlign.right,
                    style: const TextStyle(
                      color: IlaiosTheme.cyan,
                      fontSize: 16,
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
    final active = state != 'Waiting' && state != 'Unavailable';
    final color = active ? _stateColor(state) : IlaiosTheme.muted;
    return Container(
      height: 82,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: active
            ? IlaiosTheme.cyan.withValues(alpha: .055)
            : IlaiosTheme.canvas,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: active
              ? IlaiosTheme.cyan.withValues(alpha: .7)
              : IlaiosTheme.border,
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 31,
            height: 31,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: color.withValues(alpha: .08),
              shape: BoxShape.circle,
            ),
            child: Icon(icon, size: 18, color: color),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: IlaiosTheme.muted, fontSize: 9),
                ),
                const Spacer(),
                Row(
                  children: [
                    Icon(Icons.circle, size: 6, color: color),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        state,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: color, fontSize: 9),
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

  static const _slots = <(String, String, Color)>[
    ('Architect Agent', 'Planning', Color(0xFF49D37D)),
    ('Frontend Dev', 'Coding', Color(0xFF49D37D)),
    ('Backend Dev', 'Coding', Color(0xFF49D37D)),
    ('Test Engineer', 'Testing', Color(0xFFF3C64E)),
    ('Security Agent', 'Scanning', Color(0xFF49D37D)),
    ('Browser Agent', 'QA', Color(0xFF49D37D)),
    ('Deploy Agent', 'Deploying', Color(0xFF23CBE6)),
  ];

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(2, 0, 0, 7),
            child: Text(
              'LIVE EXECUTION',
              style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
            ),
          ),
          LayoutBuilder(
            builder: (context, constraints) {
              if (constraints.maxWidth < 760) {
                return Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    for (var index = 0; index < _slots.length; index += 1)
                      SizedBox(
                        width: constraints.maxWidth < 480
                            ? constraints.maxWidth
                            : (constraints.maxWidth - 8) / 2,
                        child: _AgentCard(
                          model: model,
                          index: index,
                          fallbackTitle: _slots[index].$1,
                          fallbackTask: _slots[index].$2,
                          accent: _slots[index].$3,
                        ),
                      ),
                  ],
                );
              }

              return Row(
                children: [
                  for (var index = 0; index < _slots.length; index += 1) ...[
                    Expanded(
                      child: _AgentCard(
                        model: model,
                        index: index,
                        fallbackTitle: _slots[index].$1,
                        fallbackTask: _slots[index].$2,
                        accent: _slots[index].$3,
                      ),
                    ),
                    if (index != _slots.length - 1) const SizedBox(width: 6),
                  ],
                ],
              );
            },
          ),
        ],
      );
}

class _AgentCard extends StatelessWidget {
  const _AgentCard({
    required this.model,
    required this.index,
    required this.fallbackTitle,
    required this.fallbackTask,
    required this.accent,
  });

  final _DashboardModel model;
  final int index;
  final String fallbackTitle;
  final String fallbackTask;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final hasLease = index < model.leases.length;
    final lease = hasLease ? model.leases[index] : null;
    final title = lease == null ? fallbackTitle : model.workerTitle(lease, index);
    final task = lease == null ? fallbackTask : model.workerTask(lease);
    final state = lease == null ? 'No lease' : model.workerState(lease);
    final stateColor = hasLease ? _stateColor(state) : IlaiosTheme.muted;

    return Container(
      height: 132,
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 6),
      decoration: BoxDecoration(
        color: IlaiosTheme.surface,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(
          color: hasLease && index == model.leases.length - 1
              ? IlaiosTheme.cyan.withValues(alpha: .75)
              : IlaiosTheme.border,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.circle, size: 7, color: stateColor),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                ),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Padding(
            padding: const EdgeInsets.only(left: 12),
            child: Text(
              task,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8),
            ),
          ),
          const Spacer(),
          Center(
            child: SizedBox(
              height: 76,
              width: 86,
              child: CustomPaint(
                painter: _PixelAgentPainter(
                  accent: accent,
                  active: hasLease,
                  variant: index,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _PixelAgentPainter extends CustomPainter {
  const _PixelAgentPainter({
    required this.accent,
    required this.active,
    required this.variant,
  });

  final Color accent;
  final bool active;
  final int variant;

  @override
  void paint(Canvas canvas, Size size) {
    final muted = active ? 1.0 : .52;
    final outline = Paint()
      ..color = const Color(0xFF06101A).withValues(alpha: muted)
      ..style = PaintingStyle.fill;
    final desk = Paint()
      ..color = const Color(0xFF132B38).withValues(alpha: muted)
      ..style = PaintingStyle.fill;
    final skin = Paint()
      ..color = const Color(0xFFD18A57).withValues(alpha: muted)
      ..style = PaintingStyle.fill;
    final hair = Paint()
      ..color = (variant == 5
              ? const Color(0xFF9A482A)
              : variant == 3
                  ? const Color(0xFF3C2B1E)
                  : const Color(0xFF5A2D18))
          .withValues(alpha: muted)
      ..style = PaintingStyle.fill;
    final shirt = Paint()
      ..color = accent.withValues(alpha: .78 * muted)
      ..style = PaintingStyle.fill;
    final screen = Paint()
      ..color = IlaiosTheme.cyan.withValues(alpha: .8 * muted)
      ..style = PaintingStyle.fill;

    canvas.drawRect(Rect.fromLTWH(8, 61, 70, 7), outline);
    canvas.drawRect(Rect.fromLTWH(12, 55, 62, 8), desk);
    canvas.drawRect(Rect.fromLTWH(20, 68, 5, 7), outline);
    canvas.drawRect(Rect.fromLTWH(63, 68, 5, 7), outline);

    canvas.drawRect(Rect.fromLTWH(49, 36, 25, 17), outline);
    canvas.drawRect(Rect.fromLTWH(52, 39, 19, 11), screen);
    canvas.drawRect(Rect.fromLTWH(58, 53, 6, 5), outline);

    canvas.drawRect(Rect.fromLTWH(25, 35, 24, 22), shirt);
    canvas.drawRect(Rect.fromLTWH(28, 24, 19, 15), skin);
    canvas.drawRect(Rect.fromLTWH(27, 19, 21, 8), hair);
    canvas.drawRect(Rect.fromLTWH(26, 24, 4, 9), hair);
    canvas.drawRect(Rect.fromLTWH(44, 23, 5, 7), hair);
    canvas.drawRect(Rect.fromLTWH(33, 29, 3, 3), outline);
    canvas.drawRect(Rect.fromLTWH(41, 29, 3, 3), outline);
    canvas.drawRect(Rect.fromLTWH(36, 35, 8, 2), outline);

    canvas.drawRect(Rect.fromLTWH(18, 42, 10, 6), shirt);
    canvas.drawRect(Rect.fromLTWH(16, 47, 13, 5), skin);
    canvas.drawRect(Rect.fromLTWH(45, 44, 11, 5), skin);

    if (active) {
      final glow = Paint()
        ..color = accent.withValues(alpha: .16)
        ..style = PaintingStyle.fill;
      canvas.drawCircle(const Offset(62, 43), 15, glow);
    }
  }

  @override
  bool shouldRepaint(covariant _PixelAgentPainter oldDelegate) =>
      oldDelegate.accent != accent ||
      oldDelegate.active != active ||
      oldDelegate.variant != variant;
}

class _WorkspacePanel extends StatelessWidget {
  const _WorkspacePanel({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        padding: EdgeInsets.zero,
        child: Column(
          children: [
            const SizedBox(
              height: 35,
              child: Padding(
                padding: EdgeInsets.symmetric(horizontal: 10),
                child: Row(
                  children: [
                    _WorkspaceTab(
                      icon: Icons.code,
                      label: 'Live Code',
                      active: true,
                    ),
                    _WorkspaceTab(icon: Icons.terminal, label: 'Terminal'),
                    _WorkspaceTab(icon: Icons.language, label: 'Browser'),
                    _WorkspaceTab(icon: Icons.folder_outlined, label: 'Files'),
                    _WorkspaceTab(icon: Icons.list_alt, label: 'Logs'),
                    _WorkspaceTab(icon: Icons.bolt_outlined, label: 'Events'),
                  ],
                ),
              ),
            ),
            const Divider(height: 1),
            LayoutBuilder(
              builder: (context, constraints) {
                final narrow = constraints.maxWidth < 760;
                if (narrow) {
                  return Column(
                    children: [
                      _CodePane(model: model),
                      const Divider(height: 1),
                      _TerminalPane(model: model),
                      const Divider(height: 1),
                      _BrowserPane(model: model),
                    ],
                  );
                }
                return SizedBox(
                  height: 306,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(flex: 10, child: _CodePane(model: model)),
                      const VerticalDivider(width: 1),
                      Expanded(flex: 8, child: _TerminalPane(model: model)),
                      const VerticalDivider(width: 1),
                      Expanded(flex: 9, child: _BrowserPane(model: model)),
                    ],
                  ),
                );
              },
            ),
          ],
        ),
      );
}

class _WorkspaceTab extends StatelessWidget {
  const _WorkspaceTab({
    required this.icon,
    required this.label,
    this.active = false,
  });

  final IconData icon;
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(right: 18),
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
                fontSize: 9,
              ),
            ),
          ],
        ),
      );
}

class _CodePane extends StatelessWidget {
  const _CodePane({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Container(
            width: 112,
            color: IlaiosTheme.canvas.withValues(alpha: .65),
            padding: const EdgeInsets.fromLTRB(10, 10, 7, 8),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _TreeRow(icon: Icons.expand_more, label: 'src/'),
                _TreeRow(icon: Icons.folder_outlined, label: 'components/'),
                _TreeRow(icon: Icons.code, label: 'Hero.tsx', active: true),
                _TreeRow(icon: Icons.code, label: 'Menu.tsx'),
                _TreeRow(icon: Icons.code, label: 'About.tsx'),
                SizedBox(height: 5),
                _TreeRow(icon: Icons.folder_outlined, label: 'pages/'),
                _TreeRow(icon: Icons.folder_outlined, label: 'api/'),
                _TreeRow(icon: Icons.folder_outlined, label: 'styles/'),
                _TreeRow(icon: Icons.folder_outlined, label: 'data/'),
                Spacer(),
                _TreeRow(icon: Icons.data_object, label: 'package.json'),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.all(11),
              child: model.hasRuntimeEvent
                  ? _RuntimeCodeProjection(event: model.latestEvent!)
                  : const _UnavailableCodeProjection(),
            ),
          ),
        ],
      );
}

class _TreeRow extends StatelessWidget {
  const _TreeRow({
    required this.icon,
    required this.label,
    this.active = false,
  });

  final IconData icon;
  final String label;
  final bool active;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 4),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
        decoration: BoxDecoration(
          color: active ? IlaiosTheme.cyan.withValues(alpha: .08) : null,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              size: 11,
              color: active ? IlaiosTheme.cyan : IlaiosTheme.muted,
            ),
            const SizedBox(width: 5),
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  color: active ? IlaiosTheme.text : IlaiosTheme.muted,
                  fontSize: 8,
                ),
              ),
            ),
          ],
        ),
      );
}

class _UnavailableCodeProjection extends StatelessWidget {
  const _UnavailableCodeProjection();

  @override
  Widget build(BuildContext context) => const Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _CodeLine(number: '1', text: '// Live code projection unavailable'),
          _CodeLine(number: '2', text: ''),
          _CodeLine(number: '3', text: 'awaiting_authoritative_runtime_stream();'),
          _CodeLine(number: '4', text: ''),
          _CodeLine(number: '5', text: '// No synthetic code is rendered here.'),
          Spacer(),
          Text(
            'No live code stream is exposed by the current Desktop API.',
            style: TextStyle(color: IlaiosTheme.muted, fontSize: 8),
          ),
        ],
      );
}

class _RuntimeCodeProjection extends StatelessWidget {
  const _RuntimeCodeProjection({required this.event});

  final Map<String, Object?> event;

  @override
  Widget build(BuildContext context) {
    final type = _firstText(event, const ['event_type', 'type']) ?? 'runtime_event';
    final phase = _firstText(event, const ['phase', 'stage']) ?? 'unknown';
    final state = _firstText(event, const ['state', 'status']) ?? 'unknown';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const _CodeLine(number: '1', text: '// Authoritative runtime event'),
        _CodeLine(number: '2', text: 'event: $type'),
        _CodeLine(number: '3', text: 'phase: $phase'),
        _CodeLine(number: '4', text: 'state: $state'),
        const Spacer(),
        const Text(
          'Projection only — no editable shell or code execution is exposed.',
          style: TextStyle(color: IlaiosTheme.muted, fontSize: 8),
        ),
      ],
    );
  }
}

class _CodeLine extends StatelessWidget {
  const _CodeLine({required this.number, required this.text});

  final String number;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 20,
              child: Text(
                number,
                textAlign: TextAlign.right,
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8),
              ),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Text(
                text,
                style: TextStyle(
                  color: text.startsWith('//')
                      ? IlaiosTheme.muted
                      : IlaiosTheme.text,
                  fontFamily: 'monospace',
                  fontSize: 8.5,
                ),
              ),
            ),
          ],
        ),
      );
}

class _TerminalPane extends StatelessWidget {
  const _TerminalPane({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final logs = model.latestLogs.take(9).toList();
    return Column(
      children: [
        Container(
          height: 33,
          padding: const EdgeInsets.symmetric(horizontal: 9),
          decoration: const BoxDecoration(
            border: Border(bottom: BorderSide(color: IlaiosTheme.border)),
          ),
          child: const Row(
            children: [
              Icon(Icons.terminal, size: 13, color: IlaiosTheme.muted),
              SizedBox(width: 6),
              Text(
                'Terminal (PowerShell)',
                style: TextStyle(color: IlaiosTheme.muted, fontSize: 8.5),
              ),
            ],
          ),
        ),
        Expanded(
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: logs.isEmpty
                ? const Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'PS> ILAIOS live terminal projection',
                        style: TextStyle(
                          color: IlaiosTheme.text,
                          fontFamily: 'monospace',
                          fontSize: 8.5,
                        ),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'No terminal stream is exposed by the current Desktop API.',
                        style: TextStyle(
                          color: IlaiosTheme.warning,
                          fontFamily: 'monospace',
                          fontSize: 8.5,
                        ),
                      ),
                      SizedBox(height: 8),
                      Text(
                        'Read-only. No shell is executed from this view.',
                        style: TextStyle(
                          color: IlaiosTheme.muted,
                          fontFamily: 'monospace',
                          fontSize: 8.5,
                        ),
                      ),
                    ],
                  )
                : ListView(
                    padding: EdgeInsets.zero,
                    children: [
                      for (final event in logs)
                        Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Text(
                            _eventLine(event),
                            style: TextStyle(
                              color: _stateColor(
                                _firstText(event, const ['state', 'status']) ?? '',
                              ),
                              fontFamily: 'monospace',
                              fontSize: 8.5,
                            ),
                          ),
                        ),
                    ],
                  ),
          ),
        ),
      ],
    );
  }
}

class _BrowserPane extends StatelessWidget {
  const _BrowserPane({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Container(
            height: 33,
            padding: const EdgeInsets.symmetric(horizontal: 9),
            decoration: const BoxDecoration(
              border: Border(bottom: BorderSide(color: IlaiosTheme.border)),
            ),
            child: Row(
              children: [
                const Icon(Icons.language, size: 13, color: IlaiosTheme.muted),
                const SizedBox(width: 6),
                const Text(
                  'Browser (Isolated)',
                  style: TextStyle(color: IlaiosTheme.muted, fontSize: 8.5),
                ),
                const Spacer(),
                Icon(
                  Icons.circle,
                  size: 6,
                  color: model.hasRuntimeEvent
                      ? IlaiosTheme.cyan
                      : IlaiosTheme.muted,
                ),
              ],
            ),
          ),
          Expanded(
            child: Container(
              margin: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: IlaiosTheme.canvas,
                borderRadius: BorderRadius.circular(6),
                border: Border.all(color: IlaiosTheme.border),
              ),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  const CustomPaint(painter: _PreviewScenePainter()),
                  Padding(
                    padding: const EdgeInsets.all(13),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Container(
                              width: 16,
                              height: 16,
                              decoration: BoxDecoration(
                                border: Border.all(color: IlaiosTheme.cyan),
                                shape: BoxShape.circle,
                              ),
                              child: const Icon(
                                Icons.hub_outlined,
                                size: 10,
                                color: IlaiosTheme.cyan,
                              ),
                            ),
                            const SizedBox(width: 6),
                            const Text(
                              'ILAIOS',
                              style: TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                            ),
                          ],
                        ),
                        const Spacer(),
                        const Text(
                          'LIVE BROWSER',
                          style: TextStyle(fontSize: 17, fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          model.hasRuntimeEvent
                              ? 'Runtime event available. Browser pixels are not exposed.'
                              : 'Preview unavailable until an authoritative browser stream is exposed.',
                          style: const TextStyle(
                            color: IlaiosTheme.muted,
                            fontSize: 8.5,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                          decoration: BoxDecoration(
                            color: IlaiosTheme.cyan.withValues(alpha: .12),
                            borderRadius: BorderRadius.circular(4),
                            border: Border.all(
                              color: IlaiosTheme.cyan.withValues(alpha: .35),
                            ),
                          ),
                          child: const Text(
                            'AWAITING STREAM',
                            style: TextStyle(
                              color: IlaiosTheme.cyan,
                              fontSize: 7.5,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
}

class _PreviewScenePainter extends CustomPainter {
  const _PreviewScenePainter();

  @override
  void paint(Canvas canvas, Size size) {
    final background = Paint()
      ..shader = const LinearGradient(
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
        colors: [Color(0xFF071827), Color(0xFF020912)],
      ).createShader(Offset.zero & size);
    canvas.drawRect(Offset.zero & size, background);

    final horizon = Paint()
      ..color = const Color(0xFF0C2C3B)
      ..style = PaintingStyle.fill;
    final path = Path()
      ..moveTo(0, size.height * .72)
      ..lineTo(size.width * .22, size.height * .58)
      ..lineTo(size.width * .38, size.height * .69)
      ..lineTo(size.width * .55, size.height * .49)
      ..lineTo(size.width * .73, size.height * .66)
      ..lineTo(size.width, size.height * .52)
      ..lineTo(size.width, size.height)
      ..lineTo(0, size.height)
      ..close();
    canvas.drawPath(path, horizon);

    final tower = Paint()
      ..color = const Color(0xFF0B1A24)
      ..style = PaintingStyle.fill;
    canvas.drawRect(
      Rect.fromLTWH(
        size.width * .68,
        size.height * .34,
        size.width * .09,
        size.height * .4,
      ),
      tower,
    );

    final cyan = Paint()
      ..color = IlaiosTheme.cyan.withValues(alpha: .65)
      ..strokeWidth = 1.5;
    canvas.drawLine(
      Offset(size.width * .735, size.height * .43),
      Offset(size.width * .735, size.height * .67),
      cyan,
    );

    final glow = Paint()
      ..color = Colors.white.withValues(alpha: .18)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(
      Offset(size.width * .61, size.height * .25),
      size.shortestSide * .09,
      glow,
    );
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}

class _BottomPanels extends StatelessWidget {
  const _BottomPanels({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final stacked = constraints.maxWidth < 760;
          final artifacts = _ArtifactsPanel(model: model);
          final evidence = _EvidencePanel(model: model);
          if (stacked) {
            return Column(
              children: [
                artifacts,
                const SizedBox(height: 10),
                evidence,
              ],
            );
          }
          return Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 11, child: artifacts),
              const SizedBox(width: 10),
              Expanded(flex: 10, child: evidence),
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
      title: 'LATEST ARTIFACTS',
      trailing: 'View all →',
      child: SizedBox(
        height: 88,
        child: records.isEmpty
            ? const Row(
                children: [
                  Expanded(
                    child: _ArtifactPlaceholder(label: 'Awaiting verified artifact'),
                  ),
                  SizedBox(width: 7),
                  Expanded(
                    child: _ArtifactPlaceholder(label: 'Awaiting verified artifact'),
                  ),
                  SizedBox(width: 7),
                  Expanded(
                    child: _ArtifactPlaceholder(label: 'Awaiting verified artifact'),
                  ),
                ],
              )
            : Row(
                children: [
                  for (var index = 0; index < records.length; index += 1) ...[
                    Expanded(child: _ArtifactCard(record: records[index])),
                    if (index != records.length - 1) const SizedBox(width: 7),
                  ],
                ],
              ),
      ),
    );
  }
}

class _ArtifactPlaceholder extends StatelessWidget {
  const _ArtifactPlaceholder({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(
              Icons.inventory_2_outlined,
              size: 20,
              color: IlaiosTheme.muted,
            ),
            const Spacer(),
            Text(
              label,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8),
            ),
          ],
        ),
      );
}

class _ArtifactCard extends StatelessWidget {
  const _ArtifactCard({required this.record});

  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(
              Icons.insert_drive_file_outlined,
              size: 20,
              color: IlaiosTheme.cyan,
            ),
            const Spacer(),
            Text(
              record.action,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),
            ),
            Text(
              _short(record.artifactDigest),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 7.5),
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
        title: 'EVIDENCE & VERIFICATION',
        trailing: 'View all →',
        child: SizedBox(
          height: 88,
          child: Row(
            children: [
              Expanded(
                child: _VerificationCard(
                  icon: Icons.verified_user_outlined,
                  label: 'Verified Records',
                  value: model.projection.connected
                      ? '${model.snapshot.evidenceCount}'
                      : 'Unavailable',
                ),
              ),
              const SizedBox(width: 7),
              Expanded(
                child: _VerificationCard(
                  icon: Icons.policy_outlined,
                  label: 'Governance',
                  value: model.snapshot.governanceState.isEmpty
                      ? 'Unavailable'
                      : 'Available',
                ),
              ),
              const SizedBox(width: 7),
              Expanded(
                child: _VerificationCard(
                  icon: Icons.route_outlined,
                  label: 'Runtime Routes',
                  value: model.projection.connected
                      ? '${model.snapshot.runtimeRouteCount}'
                      : 'Unavailable',
                ),
              ),
            ],
          ),
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
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: IlaiosTheme.canvas,
        borderRadius: BorderRadius.circular(6),
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
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),
          ),
          Text(
            value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: available ? IlaiosTheme.success : IlaiosTheme.muted,
              fontSize: 7.5,
            ),
          ),
        ],
      ),
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
            title: 'STATUS',
            rows: <(String, String)>[
              ('Job ID', model.jobId),
              ('Started', model.started),
              ('Elapsed', model.elapsed),
              ('Est. finish', model.estimatedCompletion),
              ('Workers', model.leases.isEmpty ? '—' : '${model.leases.length} active'),
              ('Status', model.executionStatus),
            ],
          ),
          const SizedBox(height: 10),
          _CostPanel(model: model),
          const SizedBox(height: 10),
          _ApprovalsPanel(model: model),
          const SizedBox(height: 10),
          _LatestLogs(model: model),
        ],
      );
}

class _SidePanel extends StatelessWidget {
  const _SidePanel({required this.title, required this.rows});

  final String title;
  final List<(String, String)> rows;

  @override
  Widget build(BuildContext context) => _Panel(
        title: title,
        child: Column(
          children: [
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 7),
                child: Row(
                  children: [
                    SizedBox(
                      width: 78,
                      child: Text(
                        row.$1,
                        style: const TextStyle(
                          color: IlaiosTheme.muted,
                          fontSize: 9,
                        ),
                      ),
                    ),
                    Expanded(
                      child: Text(
                        row.$2,
                        textAlign: TextAlign.right,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 9,
                          fontWeight: FontWeight.w600,
                          color: row.$1 == 'Status'
                              ? _stateColor(row.$2)
                              : IlaiosTheme.text,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      );
}

class _CostPanel extends StatelessWidget {
  const _CostPanel({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final usage = model.budgetUsage;
    return _Panel(
      title: 'COST & USAGE',
      child: Column(
        children: [
          _MetricRow(
            label: 'Total cost',
            value: model.totalCostUsd == null
                ? 'Unavailable'
                : '\$ ${model.totalCostUsd}',
          ),
          _MetricRow(
            label: 'Budget',
            value: model.budgetUsd == null ? 'Unavailable' : '\$ ${model.budgetUsd}',
          ),
          const SizedBox(height: 4),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: usage,
              minHeight: 6,
              backgroundColor: IlaiosTheme.surfaceRaised,
              color: usage == null ? IlaiosTheme.muted : IlaiosTheme.cyan,
            ),
          ),
          const SizedBox(height: 7),
          _MetricRow(
            label: 'Token usage',
            value: model.tokenUsage ?? 'Unavailable',
          ),
          _MetricRow(
            label: 'Cost minor',
            value: model.totalCostMinor ?? 'Unavailable',
          ),
          _MetricRow(
            label: 'Budget minor',
            value: model.budgetMinor ?? 'Unavailable',
          ),
        ],
      ),
    );
  }
}

class _MetricRow extends StatelessWidget {
  const _MetricRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Row(
          children: [
            Text(
              label,
              style: const TextStyle(color: IlaiosTheme.muted, fontSize: 9),
            ),
            const Spacer(),
            Flexible(
              child: Text(
                value,
                textAlign: TextAlign.right,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );
}

class _ApprovalsPanel extends StatelessWidget {
  const _ApprovalsPanel({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) => _Panel(
        title: 'APPROVALS',
        child: Column(
          children: [
            _MetricRow(
              label: 'Pending',
              value: model.pendingApprovals?.toString() ?? 'Unavailable',
            ),
            _MetricRow(
              label: 'Approved',
              value: model.approvedCount?.toString() ?? 'Unavailable',
            ),
            _MetricRow(
              label: 'Denied',
              value: model.deniedCount?.toString() ?? 'Unavailable',
            ),
            const SizedBox(height: 4),
            Container(
              width: double.infinity,
              height: 29,
              alignment: Alignment.center,
              decoration: BoxDecoration(
                color: IlaiosTheme.canvas,
                borderRadius: BorderRadius.circular(5),
                border: Border.all(color: IlaiosTheme.border),
              ),
              child: const Text(
                'View approvals',
                style: TextStyle(color: IlaiosTheme.muted, fontSize: 8.5),
              ),
            ),
          ],
        ),
      );
}

class _LatestLogs extends StatelessWidget {
  const _LatestLogs({required this.model});

  final _DashboardModel model;

  @override
  Widget build(BuildContext context) {
    final logs = model.latestLogs;
    return _Panel(
      title: 'LATEST LOGS',
      child: SizedBox(
        height: 174,
        child: logs.isEmpty
            ? const Center(
                child: Text(
                  'No authoritative log events available.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: IlaiosTheme.muted, fontSize: 9),
                ),
              )
            : Column(
                children: [
                  for (final event in logs)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 9),
                      child: _LogRow(event: event),
                    ),
                  const Spacer(),
                  const Align(
                    alignment: Alignment.centerRight,
                    child: Text(
                      'View all logs →',
                      style: TextStyle(color: IlaiosTheme.muted, fontSize: 8.5),
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}

class _LogRow extends StatelessWidget {
  const _LogRow({required this.event});

  final Map<String, Object?> event;

  @override
  Widget build(BuildContext context) {
    final time = _firstText(
          event,
          const ['timestamp', 'created_at', 'occurred_at'],
        ) ??
        '—';
    final message = _firstText(
          event,
          const ['message', 'log', 'detail', 'event_type', 'type'],
        ) ??
        'event';
    final state = _firstText(event, const ['state', 'status']) ?? '';

    return Row(
      children: [
        SizedBox(
          width: 56,
          child: Text(
            time,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8),
          ),
        ),
        const SizedBox(width: 5),
        Expanded(
          child: Text(
            message,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 8.5),
          ),
        ),
        const SizedBox(width: 5),
        Icon(Icons.circle, size: 6, color: _stateColor(state)),
      ],
    );
  }
}

class _Panel extends StatelessWidget {
  const _Panel({
    this.title,
    this.trailing,
    required this.child,
    this.padding = const EdgeInsets.all(11),
  });

  final String? title;
  final String? trailing;
  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: padding,
        decoration: BoxDecoration(
          color: IlaiosTheme.surface,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: IlaiosTheme.border),
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
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  if (trailing != null)
                    Text(
                      trailing!,
                      style: const TextStyle(
                        color: IlaiosTheme.muted,
                        fontSize: 8.5,
                      ),
                    ),
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
          borderRadius: BorderRadius.circular(4),
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

num? _firstNumberFromSources(
  List<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final source in sources) {
    final value = _firstNumber(source, keys);
    if (value != null) return value;
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

String _eventLine(Map<String, Object?> event) {
  final time = _firstText(
    event,
    const ['timestamp', 'created_at', 'occurred_at'],
  );
  final text = _firstText(
        event,
        const ['message', 'log', 'detail', 'event_type', 'type'],
      ) ??
      'event';
  final state = _firstText(event, const ['state', 'status']);
  final prefix = time == null ? '' : '$time  ';
  final suffix = state == null ? '' : '  [$state]';
  return '$prefix$text$suffix';
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
