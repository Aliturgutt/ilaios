import 'package:flutter/material.dart';

import '../../app/ilaios_home_catalog.dart';
import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';

class ReferenceHomeDashboardV2 extends StatefulWidget {
  const ReferenceHomeDashboardV2({
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
  State<ReferenceHomeDashboardV2> createState() =>
      _ReferenceHomeDashboardV2State();
}

class _ReferenceHomeDashboardV2State extends State<ReferenceHomeDashboardV2> {
  String _workspaceTab = 'Live Code';

  @override
  Widget build(BuildContext context) {
    final model = _HomeModel(
      projection: widget.projection,
      snapshot: widget.snapshot,
      status: widget.status,
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final contentHeight = (constraints.maxHeight - 20).clamp(620.0, 1200.0);
        final workflowHeight = contentHeight * .215;
        final executionHeight = contentHeight * .19;
        final bottomHeight = contentHeight * .145;
        final railWidth = constraints.maxWidth >= 1380 ? 284.0 : 254.0;

        return Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    SizedBox(
                      height: workflowHeight,
                      child: _WorkflowSection(
                        model: model,
                        onNavigate: widget.onNavigate,
                        onRefreshRequested: widget.onRefreshRequested,
                      ),
                    ),
                    const SizedBox(height: 6),
                    SizedBox(
                      height: executionHeight,
                      child: _ExecutionSection(model: model),
                    ),
                    const SizedBox(height: 6),
                    Expanded(
                      child: _WorkspaceSection(
                        model: model,
                        selectedTab: _workspaceTab,
                        onTabSelected: (tab) {
                          if (_workspaceTab != tab) {
                            setState(() => _workspaceTab = tab);
                          }
                        },
                      ),
                    ),
                    const SizedBox(height: 6),
                    SizedBox(
                      height: bottomHeight,
                      child: _BottomContentRow(model: model),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(width: railWidth, child: _RightRail(model: model)),
            ],
          ),
        );
      },
    );
  }
}

class _HomeModel {
  const _HomeModel({
    required this.projection,
    required this.snapshot,
    required this.status,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;

  Map<String, Object?>? get latestEvent =>
      snapshot.liveEvents.isEmpty ? null : snapshot.liveEvents.last;

  List<Map<String, Object?>> get leases => _mapList(snapshot.schedulerState['leases']);
  List<Map<String, Object?>> get work => _mapList(snapshot.governanceState['work']);
  List<Map<String, Object?>> get admissions =>
      _mapList(snapshot.governanceState['admissions']);

  String get badge {
    if (!projection.connected) return 'OFFLINE';
    if (latestEvent == null) return 'NO ACTIVE DATA';
    final state = executionStatus;
    return state == 'Unavailable' ? 'STATE UNAVAILABLE' : state.toUpperCase();
  }

  String get jobId => _text(latestEvent, const ['job_id', 'execution_id']) ?? '—';
  String get started => _text(latestEvent, const ['started_at', 'start_time']) ?? '—';
  String get elapsed => _text(latestEvent, const ['elapsed', 'elapsed_time']) ?? '—';
  String get estimatedFinish =>
      _text(latestEvent, const ['estimated_finish', 'eta', 'finish_at']) ?? '—';
  String get phase =>
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
    final current = _text(latestEvent, const ['phase', 'stage', 'workflow_phase']);
    if (current == null) return 'Unavailable';
    if (_normalize(current) != _normalize(stage)) return '—';
    return executionStatus;
  }

  Map<String, Object?>? leaseFor(String role) {
    final target = _roleKey(role);
    for (final lease in leases) {
      final candidate = _text(lease, const ['role', 'worker_type', 'worker_id']);
      if (candidate == null) continue;
      final key = _roleKey(candidate);
      if (key.contains(target) || target.contains(key)) return lease;
    }
    return null;
  }

  String? get totalCost => _firstValue(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['total_cost_usd', 'cost_usd', 'total_cost_minor', 'spent_minor'],
      );
  String? get budget => _firstValue(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['budget_usd', 'budget_minor', 'hard_cap_minor'],
      );
  String? get tokenUsage => _firstValue(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['token_usage', 'tokens_used', 'total_tokens'],
      );
  String? get gpuTime => _firstValue(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['gpu_time', 'gpu_runtime', 'gpu_duration'],
      );

  int get pendingApprovals {
    final required = <String>{};
    for (final item in admissions) {
      if (item['human_approval_required'] != true) continue;
      final id = item['request_id'];
      if (id is String && id.isNotEmpty) required.add(id);
    }
    return work.where((item) {
      final id = item['request_id'];
      return item['status'] == 'pending' && id is String && required.contains(id);
    }).length;
  }

  int get approvedCount => work.where((item) => item['status'] == 'approved').length;
  int get deniedCount => work.where((item) => item['status'] == 'denied').length;

  String? get sourceProjection => _text(latestEvent, const ['source', 'source_code', 'code']);
  String? get terminalProjection =>
      _text(latestEvent, const ['terminal', 'stdout', 'log', 'message']);
  String? get browserProjection =>
      _text(latestEvent, const ['browser_url', 'preview_url', 'url']);

  String verificationValue(List<String> keys) =>
      _firstValue([snapshot.governanceState, snapshot.schedulerState], keys) ?? '—';
}

class _WorkflowSection extends StatelessWidget {
  const _WorkflowSection({
    required this.model,
    required this.onNavigate,
    required this.onRefreshRequested,
  });

  final _HomeModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  static const _stages = <_StageSpec>[
    _StageSpec('Goal Intake', 'Intent accepted', Icons.track_changes_outlined, DesktopSection.goals),
    _StageSpec('Planning', 'Workflow prepared', Icons.account_tree_outlined, DesktopSection.workflows),
    _StageSpec('Execution', 'Agents executing', Icons.play_circle_outline, DesktopSection.agents),
    _StageSpec('Verification', 'Tests & evidence', Icons.verified_user_outlined, DesktopSection.evidence),
    _StageSpec('Delivery', 'Finished product', Icons.inventory_2_outlined, DesktopSection.artifacts),
  ];

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 34,
            child: Row(
              children: [
                Text(
                  _home(context, 'Active Workflow'),
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                        fontSize: 18,
                      ),
                ),
                const SizedBox(width: 10),
                _Badge(label: _home(context, model.badge)),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    model.started == '—'
                        ? model.status
                        : '${_home(context, 'Started')}: ${model.started}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ),
                IconButton(
                  tooltip: _home(context, 'Refresh authoritative state'),
                  onPressed: onRefreshRequested,
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.refresh_rounded, size: 19, color: IlaiosTheme.enterpriseCyan),
                ),
                IconButton(
                  tooltip: _isTr(context) ? 'Canlı çalışma alanını aç' : 'Open live workspace',
                  onPressed: () => onNavigate(DesktopSection.liveWorkspace),
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.open_in_full_rounded, size: 17),
                ),
              ],
            ),
          ),
          const SizedBox(height: 5),
          Expanded(
            child: Container(
              key: const Key('reference-workflow-strip'),
              padding: const EdgeInsets.fromLTRB(9, 8, 9, 7),
              decoration: _box(context),
              child: Column(
                children: [
                  Expanded(
                    child: Row(
                      children: [
                        for (var i = 0; i < _stages.length; i++) ...[
                          Expanded(
                            child: _StageCard(
                              spec: _stages[i],
                              state: model.stageState(_stages[i].title),
                              onTap: () => onNavigate(_stages[i].destination),
                            ),
                          ),
                          if (i < _stages.length - 1)
                            const SizedBox(
                              width: 22,
                              child: Icon(Icons.arrow_forward_rounded, size: 17),
                            ),
                        ],
                      ],
                    ),
                  ),
                  const SizedBox(height: 6),
                  SizedBox(
                    height: 20,
                    child: Row(
                      children: [
                        Text(_home(context, 'Overall Progress'), style: Theme.of(context).textTheme.labelSmall),
                        const SizedBox(width: 10),
                        Expanded(
                          child: ClipRRect(
                            borderRadius: BorderRadius.circular(10),
                            child: LinearProgressIndicator(
                              value: model.progressValue ?? 0,
                              minHeight: 4,
                              backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        SizedBox(
                          width: 38,
                          child: Text(
                            model.progressLabel,
                            textAlign: TextAlign.right,
                            style: const TextStyle(
                              color: IlaiosTheme.enterpriseCyan,
                              fontWeight: FontWeight.w800,
                              fontSize: 11,
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

class _StageSpec {
  const _StageSpec(this.title, this.subtitle, this.icon, this.destination);
  final String title;
  final String subtitle;
  final IconData icon;
  final DesktopSection destination;
}

class _StageCard extends StatelessWidget {
  const _StageCard({required this.spec, required this.state, required this.onTap});
  final _StageSpec spec;
  final String state;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final active = state != '—' && state != 'Unavailable';
    return Material(
      color: active
          ? IlaiosTheme.coreBlue.withValues(alpha: .12)
          : Theme.of(context).colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(7),
        side: BorderSide(
          color: active
              ? IlaiosTheme.coreBlue.withValues(alpha: .78)
              : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: ValueKey('home-stage-${spec.destination.name}'),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Container(
                    width: 27,
                    height: 27,
                    decoration: BoxDecoration(
                      color: IlaiosTheme.coreBlue.withValues(alpha: .14),
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Icon(spec.icon, size: 16, color: IlaiosTheme.enterpriseCyan),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          _home(context, spec.title),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 10.1, fontWeight: FontWeight.w800),
                        ),
                        Text(
                          _home(context, spec.subtitle),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 8.3),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const Spacer(),
              Row(
                children: [
                  Icon(
                    active ? Icons.radio_button_checked : Icons.circle_outlined,
                    size: 10,
                    color: active ? IlaiosTheme.success : Theme.of(context).colorScheme.outline,
                  ),
                  const SizedBox(width: 4),
                  Expanded(
                    child: Text(
                      state == 'Unavailable' ? _home(context, 'Unavailable') : state,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 8.4),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExecutionSection extends StatelessWidget {
  const _ExecutionSection({required this.model});
  final _HomeModel model;

  static const _roles = <(String, IconData)>[
    ('Architect Agent', Icons.account_tree_rounded),
    ('Frontend Dev', Icons.web_rounded),
    ('Backend Dev', Icons.dns_rounded),
    ('Test Engineer', Icons.bug_report_rounded),
    ('Security Agent', Icons.security_rounded),
    ('Browser Agent', Icons.travel_explore_rounded),
    ('Deploy Agent', Icons.rocket_launch_rounded),
  ];

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 28,
            child: Row(
              children: [
                Text(_home(context, 'LIVE EXECUTION'), style: Theme.of(context).textTheme.titleMedium),
                if (model.leases.isEmpty) ...[
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      _home(context, 'No active worker leases are exposed by the scheduler.'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 5),
          Expanded(
            child: Row(
              key: const Key('reference-agent-row'),
              children: [
                for (var i = 0; i < _roles.length; i++) ...[
                  Expanded(
                    child: _AgentCard(
                      role: _roles[i].$1,
                      icon: _roles[i].$2,
                      lease: model.leaseFor(_roles[i].$1),
                      accent: i == _roles.length - 1 ? IlaiosTheme.coreBlue : IlaiosTheme.enterpriseCyan,
                    ),
                  ),
                  if (i < _roles.length - 1) const SizedBox(width: 6),
                ],
              ],
            ),
          ),
        ],
      );
}

class _AgentCard extends StatelessWidget {
  const _AgentCard({
    required this.role,
    required this.icon,
    required this.lease,
    required this.accent,
  });

  final String role;
  final IconData icon;
  final Map<String, Object?>? lease;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final active = lease != null;
    final activity = _text(lease, const ['task', 'task_id', 'request_id', 'activity']) ?? _home(context, 'Unavailable');
    final state = _text(lease, const ['state', 'status', 'health']) ?? _home(context, 'Unavailable');

    return Container(
      padding: const EdgeInsets.fromLTRB(7, 7, 7, 6),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(
          color: active ? accent.withValues(alpha: .72) : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.circle, size: 6, color: active ? IlaiosTheme.success : Theme.of(context).colorScheme.outline),
              const SizedBox(width: 4),
              Expanded(
                child: Text(role, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w800)),
              ),
            ],
          ),
          const SizedBox(height: 2),
          Text(state, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.1)),
          Text(activity, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.1)),
          const Spacer(),
          Center(
            child: Container(
              width: 48,
              height: 43,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: .08),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: accent.withValues(alpha: .16)),
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Icon(icon, size: 24, color: active ? accent : Theme.of(context).colorScheme.outline),
                  Positioned(
                    right: 4,
                    bottom: 3,
                    child: Icon(Icons.laptop_windows_rounded, size: 13, color: accent),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _WorkspaceSection extends StatelessWidget {
  const _WorkspaceSection({
    required this.model,
    required this.selectedTab,
    required this.onTabSelected,
  });

  final _HomeModel model;
  final String selectedTab;
  final ValueChanged<String> onTabSelected;

  static const _tabs = ['Live Code', 'Terminal', 'Browser', 'Files', 'Logs', 'Events'];

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-workspace'),
        decoration: _box(context),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 36,
              child: Row(
                children: [
                  const SizedBox(width: 4),
                  for (final tab in _tabs)
                    Expanded(
                      child: Material(
                        color: Colors.transparent,
                        child: InkWell(
                          key: ValueKey('workspace-tab-${_normalize(tab).replaceAll(' ', '-')}'),
                          onTap: () => onTabSelected(tab),
                          child: Container(
                            decoration: BoxDecoration(
                              border: Border(
                                bottom: BorderSide(
                                  color: selectedTab == tab ? IlaiosTheme.enterpriseCyan : Colors.transparent,
                                  width: 2,
                                ),
                              ),
                            ),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                Icon(
                                  _tabIcon(tab),
                                  size: 13,
                                  color: selectedTab == tab ? IlaiosTheme.enterpriseCyan : Theme.of(context).colorScheme.onSurfaceVariant,
                                ),
                                const SizedBox(width: 4),
                                Flexible(
                                  child: Text(
                                    _home(context, tab),
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 9.7,
                                      color: selectedTab == tab ? IlaiosTheme.enterpriseCyan : Theme.of(context).colorScheme.onSurfaceVariant,
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  const SizedBox(width: 4),
                ],
              ),
            ),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            Expanded(child: _workspaceBody(context)),
          ],
        ),
      );

  Widget _workspaceBody(BuildContext context) {
    if (selectedTab == 'Live Code') {
      return Row(
        children: [
          Expanded(
            flex: 34,
            child: _WorkspacePane(
              title: _home(context, 'Live Code'),
              icon: Icons.code_rounded,
              primary: model.sourceProjection,
              emptyTitle: _home(context, 'Code projection unavailable'),
              emptyBody: _home(context, 'No source buffer is exposed by the current Desktop API.'),
            ),
          ),
          VerticalDivider(width: 1, color: Theme.of(context).colorScheme.outlineVariant),
          Expanded(
            flex: 31,
            child: _WorkspacePane(
              title: _home(context, 'Terminal'),
              icon: Icons.terminal_rounded,
              primary: model.terminalProjection,
              emptyTitle: _home(context, 'Terminal'),
              emptyBody: _home(context, 'No authoritative live events are available.'),
            ),
          ),
          VerticalDivider(width: 1, color: Theme.of(context).colorScheme.outlineVariant),
          Expanded(
            flex: 35,
            child: _WorkspacePane(
              title: _home(context, 'Browser'),
              icon: Icons.public_rounded,
              primary: model.browserProjection,
              emptyTitle: _home(context, 'Preview unavailable'),
              emptyBody: _home(context, 'No browser preview projection is exposed.'),
            ),
          ),
        ],
      );
    }

    if (selectedTab == 'Terminal') {
      return _WorkspacePane(
        title: _home(context, 'Terminal'),
        icon: Icons.terminal_rounded,
        primary: model.terminalProjection,
        emptyTitle: _home(context, 'Terminal'),
        emptyBody: _home(context, 'No authoritative live events are available.'),
      );
    }
    if (selectedTab == 'Browser') {
      return _WorkspacePane(
        title: _home(context, 'Browser'),
        icon: Icons.public_rounded,
        primary: model.browserProjection,
        emptyTitle: _home(context, 'Preview unavailable'),
        emptyBody: _home(context, 'No browser preview projection is exposed.'),
      );
    }
    if (selectedTab == 'Files') {
      return _EvidenceList(
        icon: Icons.folder_open_outlined,
        title: _home(context, 'Files'),
        records: model.snapshot.evidenceRecords,
      );
    }
    return _EventList(
      title: _home(context, selectedTab),
      icon: selectedTab == 'Logs' ? Icons.list_alt_rounded : Icons.bolt_rounded,
      events: model.snapshot.liveEvents,
    );
  }

  IconData _tabIcon(String tab) => switch (tab) {
        'Live Code' => Icons.code_rounded,
        'Terminal' => Icons.terminal_rounded,
        'Browser' => Icons.public_rounded,
        'Files' => Icons.folder_open_outlined,
        'Logs' => Icons.list_alt_rounded,
        _ => Icons.bolt_rounded,
      };
}

class _WorkspacePane extends StatelessWidget {
  const _WorkspacePane({
    required this.title,
    required this.icon,
    required this.primary,
    required this.emptyTitle,
    required this.emptyBody,
  });

  final String title;
  final IconData icon;
  final String? primary;
  final String emptyTitle;
  final String emptyBody;

  @override
  Widget build(BuildContext context) => ColoredBox(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              height: 31,
              padding: const EdgeInsets.symmetric(horizontal: 9),
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              child: Row(
                children: [
                  Icon(icon, size: 13),
                  const SizedBox(width: 5),
                  Expanded(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9.4, fontWeight: FontWeight.w600))),
                ],
              ),
            ),
            Expanded(
              child: primary == null
                  ? Center(
                      child: Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 14),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(icon, size: 27, color: IlaiosTheme.coreBlue.withValues(alpha: .8)),
                            const SizedBox(height: 6),
                            Text(emptyTitle, textAlign: TextAlign.center, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700)),
                            const SizedBox(height: 3),
                            Text(emptyBody, textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.8)),
                          ],
                        ),
                      ),
                    )
                  : Scrollbar(
                      child: SingleChildScrollView(
                        padding: const EdgeInsets.all(10),
                        child: SelectableText(
                          primary!,
                          style: const TextStyle(fontFamily: 'Consolas', fontSize: 9.7, height: 1.38),
                        ),
                      ),
                    ),
            ),
          ],
        ),
      );
}

class _EvidenceList extends StatelessWidget {
  const _EvidenceList({required this.icon, required this.title, required this.records});
  final IconData icon;
  final String title;
  final List<EvidenceRecord> records;

  @override
  Widget build(BuildContext context) => _InnerListShell(
        title: title,
        icon: icon,
        child: records.isEmpty
            ? Center(child: Text(_isTr(context) ? 'Dosya/çıktı projeksiyonu kullanılamıyor.' : 'No file/artifact projection is available.'))
            : ListView.separated(
                padding: const EdgeInsets.all(10),
                itemCount: records.length,
                separatorBuilder: (_, __) => const SizedBox(height: 6),
                itemBuilder: (context, index) {
                  final record = records[index];
                  return Text('${record.action}  ·  ${record.executionId}', maxLines: 1, overflow: TextOverflow.ellipsis);
                },
              ),
      );
}

class _EventList extends StatelessWidget {
  const _EventList({required this.title, required this.icon, required this.events});
  final String title;
  final IconData icon;
  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) => _InnerListShell(
        title: title,
        icon: icon,
        child: events.isEmpty
            ? Center(child: Text(_home(context, 'No live event records available.')))
            : ListView.separated(
                padding: const EdgeInsets.all(10),
                itemCount: events.length,
                separatorBuilder: (_, __) => const SizedBox(height: 5),
                itemBuilder: (context, index) {
                  final event = events.reversed.elementAt(index);
                  final label = _text(event, const ['event_type', 'type', 'status', 'message']) ?? _home(context, 'Unavailable');
                  return Text(label, maxLines: 1, overflow: TextOverflow.ellipsis);
                },
              ),
      );
}

class _InnerListShell extends StatelessWidget {
  const _InnerListShell({required this.title, required this.icon, required this.child});
  final String title;
  final IconData icon;
  final Widget child;

  @override
  Widget build(BuildContext context) => ColoredBox(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        child: Column(
          children: [
            Container(
              height: 31,
              padding: const EdgeInsets.symmetric(horizontal: 9),
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              child: Row(children: [Icon(icon, size: 13), const SizedBox(width: 5), Text(title, style: const TextStyle(fontSize: 9.4, fontWeight: FontWeight.w600))]),
            ),
            Expanded(child: child),
          ],
        ),
      );
}

class _BottomContentRow extends StatelessWidget {
  const _BottomContentRow({required this.model});
  final _HomeModel model;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(child: _ArtifactsPanel(records: model.snapshot.evidenceRecords)),
          const SizedBox(width: 8),
          Expanded(child: _VerificationPanel(model: model)),
        ],
      );
}

class _ArtifactsPanel extends StatelessWidget {
  const _ArtifactsPanel({required this.records});
  final List<EvidenceRecord> records;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-artifacts-panel'),
        padding: const EdgeInsets.all(9),
        decoration: _box(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_home(context, 'LATEST ARTIFACTS'), style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 6),
            Expanded(
              child: records.isEmpty
                  ? Center(child: Text(_home(context, 'No verified artifact evidence is available.'), textAlign: TextAlign.center, style: const TextStyle(fontSize: 9)))
                  : Row(
                      children: [
                        for (var i = 0; i < records.take(3).length; i++) ...[
                          Expanded(child: _ArtifactCard(record: records[i])),
                          if (i < records.take(3).length - 1) const SizedBox(width: 5),
                        ],
                      ],
                    ),
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
        padding: const EdgeInsets.all(7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Row(children: [const Icon(Icons.inventory_2_outlined, size: 14, color: IlaiosTheme.enterpriseCyan), const SizedBox(width: 5), Expanded(child: Text(record.action, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w700)))]),
            const SizedBox(height: 3),
            Text(record.executionId, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8)),
            Text(_short(record.artifactDigest), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8)),
          ],
        ),
      );
}

class _VerificationPanel extends StatelessWidget {
  const _VerificationPanel({required this.model});
  final _HomeModel model;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-evidence-panel'),
        padding: const EdgeInsets.all(9),
        decoration: _box(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_home(context, 'EVIDENCE & VERIFICATION'), style: Theme.of(context).textTheme.titleSmall),
            const SizedBox(height: 6),
            Expanded(
              child: Row(
                children: [
                  Expanded(child: _VerificationCard(title: 'QA Report', value: model.verificationValue(const ['qa_status', 'qa_result', 'test_status']))),
                  const SizedBox(width: 5),
                  Expanded(child: _VerificationCard(title: 'Security Scan', value: model.verificationValue(const ['security_status', 'security_result', 'scan_status']))),
                  const SizedBox(width: 5),
                  Expanded(child: _VerificationCard(title: 'Policy Check', value: model.verificationValue(const ['policy_status', 'policy_result', 'compliance_status']))),
                ],
              ),
            ),
          ],
        ),
      );
}

class _VerificationCard extends StatelessWidget {
  const _VerificationCard({required this.title, required this.value});
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Icon(Icons.verified_user_outlined, size: 20, color: value == '—' ? Theme.of(context).colorScheme.outline : IlaiosTheme.success),
            const SizedBox(width: 5),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 2),
                  Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.1)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _RightRail extends StatelessWidget {
  const _RightRail({required this.model});
  final _HomeModel model;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Expanded(
            flex: 9,
            child: _RailCard(
              key: const Key('reference-status-card'),
              title: _home(context, 'STATUS'),
              accent: IlaiosTheme.coreBlue,
              rows: [
                (_home(context, 'Job ID'), model.jobId),
                (_home(context, 'Started'), model.started),
                (_home(context, 'Elapsed'), model.elapsed),
                (_home(context, 'Est. finish'), model.estimatedFinish),
                (_home(context, 'Phase'), model.phase == 'Unavailable' ? _home(context, 'Unavailable') : model.phase),
                (_home(context, 'Active workers'), model.leases.isEmpty ? '0' : '${model.leases.length}'),
                (_home(context, 'Status'), model.executionStatus == 'Unavailable' ? _home(context, 'Unavailable') : model.executionStatus),
              ],
            ),
          ),
          const SizedBox(height: 7),
          Expanded(
            flex: 6,
            child: _RailCard(
              title: _home(context, 'COST & USAGE'),
              accent: IlaiosTheme.violet,
              rows: [
                (_home(context, 'Total cost'), model.totalCost ?? _home(context, 'Unavailable')),
                (_home(context, 'Budget'), model.budget ?? _home(context, 'Unavailable')),
                (_home(context, 'Token usage'), model.tokenUsage ?? _home(context, 'Unavailable')),
                (_home(context, 'GPU time'), model.gpuTime ?? _home(context, 'Unavailable')),
              ],
            ),
          ),
          const SizedBox(height: 7),
          Expanded(
            flex: 5,
            child: _RailCard(
              title: _home(context, 'APPROVALS'),
              accent: IlaiosTheme.enterpriseCyan,
              rows: [
                (_home(context, 'Pending'), '${model.pendingApprovals}'),
                (_home(context, 'Approved'), '${model.approvedCount}'),
                (_home(context, 'Denied'), '${model.deniedCount}'),
              ],
            ),
          ),
          const SizedBox(height: 7),
          Expanded(flex: 7, child: _LatestLogs(model: model)),
        ],
      );
}

class _RailCard extends StatelessWidget {
  const _RailCard({required this.title, required this.accent, required this.rows, super.key});
  final String title;
  final Color accent;
  final List<(String, String)> rows;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.fromLTRB(10, 9, 10, 7),
        decoration: _box(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(width: 4, height: 18, decoration: BoxDecoration(color: accent, borderRadius: BorderRadius.circular(3))),
                const SizedBox(width: 7),
                Expanded(child: Text(title, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800))),
              ],
            ),
            const SizedBox(height: 6),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.spaceEvenly,
                children: [
                  for (final row in rows)
                    Row(
                      children: [
                        Expanded(child: Text(row.$1, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9.2))),
                        const SizedBox(width: 7),
                        Flexible(child: Text(row.$2, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right, style: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w600))),
                      ],
                    ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _LatestLogs extends StatelessWidget {
  const _LatestLogs({required this.model});
  final _HomeModel model;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-latest-logs'),
        padding: const EdgeInsets.all(10),
        decoration: _box(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_home(context, 'LATEST LOGS'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            Expanded(
              child: model.snapshot.liveEvents.isEmpty
                  ? Align(alignment: Alignment.topLeft, child: Text(_home(context, 'No live event records available.'), style: const TextStyle(fontSize: 9.2)))
                  : ListView.builder(
                      padding: EdgeInsets.zero,
                      itemCount: model.snapshot.liveEvents.length.clamp(0, 5),
                      itemBuilder: (context, index) {
                        final event = model.snapshot.liveEvents.reversed.elementAt(index);
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 5),
                          child: Row(
                            children: [
                              Expanded(child: Text(_text(event, const ['event_type', 'type', 'status']) ?? _home(context, 'Unavailable'), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9))),
                              const SizedBox(width: 5),
                              const Icon(Icons.circle, size: 5, color: IlaiosTheme.success),
                            ],
                          ),
                        );
                      },
                    ),
            ),
          ],
        ),
      );
}

class _Badge extends StatelessWidget {
  const _Badge({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
          color: IlaiosTheme.enterpriseCyan.withValues(alpha: .10),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: IlaiosTheme.enterpriseCyan.withValues(alpha: .45)),
        ),
        child: Text(label, style: const TextStyle(color: IlaiosTheme.enterpriseCyan, fontSize: 8.7, fontWeight: FontWeight.w800)),
      );
}

BoxDecoration _box(BuildContext context) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

String _home(BuildContext context, String english) =>
    IlaiosHomeCatalog.text(context.ilaiosLocale.locale.code, english);

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _normalize(String value) => value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();
String _roleKey(String value) => _normalize(value).replaceAll('agent', '').replaceAll('dev', '').replaceAll('engineer', '').trim();

String? _text(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return '$value';
  }
  return null;
}

double? _number(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is num) return value.toDouble();
    if (value is String) {
      final parsed = double.tryParse(value.trim());
      if (parsed != null) return parsed;
    }
  }
  return null;
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return value.whereType<Map<String, Object?>>().toList(growable: false);
}

String? _firstValue(List<Map<String, Object?>> sources, List<String> keys) {
  for (final source in sources) {
    final value = _text(source, keys);
    if (value != null) return value;
  }
  return null;
}

String _short(String value) => value.length <= 18 ? value : '${value.substring(0, 18)}…';
