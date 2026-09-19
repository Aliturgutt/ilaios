import 'package:flutter/material.dart';

import '../../app/ilaios_home_catalog.dart';
import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';

class ReferenceHomeDashboard extends StatelessWidget {
  const ReferenceHomeDashboard({
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
    final model = _ReferenceHomeModel(
      projection: projection,
      snapshot: snapshot,
      status: status,
    );
    return LayoutBuilder(
      builder: (context, constraints) {
        final railWidth = constraints.maxWidth >= 1120 ? 286.0 : 252.0;
        return SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _WorkflowSection(
                      model: model,
                      onNavigate: onNavigate,
                      onRefreshRequested: onRefreshRequested,
                    ),
                    const SizedBox(height: 12),
                    _ExecutionSection(model: model),
                    const SizedBox(height: 12),
                    _WorkspaceSection(model: model),
                    const SizedBox(height: 12),
                    _BottomContentRow(model: model),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              SizedBox(width: railWidth, child: _RightRail(model: model)),
            ],
          ),
        );
      },
    );
  }
}

class _ReferenceHomeModel {
  const _ReferenceHomeModel({
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

  String get badge {
    if (!projection.connected) return 'OFFLINE';
    if (!hasRuntimeEvent) return 'NO ACTIVE DATA';
    final state = executionStatus;
    return state == 'Unavailable'
        ? 'STATE UNAVAILABLE'
        : state.toUpperCase();
  }

  String get jobId =>
      _text(latestEvent, const ['job_id', 'execution_id']) ?? '—';
  String get started =>
      _text(latestEvent, const ['started_at', 'start_time']) ?? '—';
  String get elapsed =>
      _text(latestEvent, const ['elapsed', 'elapsed_time']) ?? '—';
  String get estimatedFinish =>
      _text(latestEvent, const ['estimated_finish', 'eta', 'finish_at']) ?? '—';
  String get phase =>
      _text(latestEvent, const ['phase', 'stage', 'workflow_phase']) ??
      'Unavailable';
  String get executionStatus =>
      _text(latestEvent, const ['state', 'status', 'execution_status']) ??
      'Unavailable';

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
    final current =
        _text(latestEvent, const ['phase', 'stage', 'workflow_phase']);
    if (current == null) return 'Unavailable';
    if (_normalize(current) != _normalize(stage)) return '—';
    return executionStatus;
  }

  Map<String, Object?>? leaseFor(String role) {
    final normalizedRole = _normalize(role)
        .replaceAll('agent', '')
        .replaceAll('dev', '')
        .replaceAll('engineer', '')
        .trim();
    for (final lease in leases) {
      final candidate =
          _text(lease, const ['role', 'worker_type', 'worker_id']);
      if (candidate == null) continue;
      final normalizedCandidate = _normalize(candidate)
          .replaceAll('agent', '')
          .replaceAll('dev', '')
          .replaceAll('engineer', '')
          .trim();
      if (normalizedCandidate.contains(normalizedRole) ||
          normalizedRole.contains(normalizedCandidate)) {
        return lease;
      }
    }
    return null;
  }

  String? get totalCost => _firstValue(
        <Map<String, Object?>>[
          snapshot.governanceState,
          snapshot.schedulerState,
          ..._mapList(snapshot.governanceState['costs']),
        ],
        const [
          'total_cost_usd',
          'cost_usd',
          'total_cost_minor',
          'spent_minor',
        ],
      );

  String? get budget => _firstValue(
        <Map<String, Object?>>[
          snapshot.governanceState,
          snapshot.schedulerState,
          ..._mapList(snapshot.governanceState['costs']),
        ],
        const ['budget_usd', 'budget_minor', 'hard_cap_minor'],
      );

  String? get tokenUsage => _firstValue(
        <Map<String, Object?>>[
          snapshot.governanceState,
          snapshot.schedulerState,
        ],
        const ['token_usage', 'tokens_used', 'total_tokens'],
      );

  String? get gpuTime => _firstValue(
        <Map<String, Object?>>[
          snapshot.governanceState,
          snapshot.schedulerState,
        ],
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
      if (item['status'] != 'pending') return false;
      final id = item['request_id'];
      return id is String && required.contains(id);
    }).length;
  }

  int get approvedCount =>
      work.where((item) => item['status'] == 'approved').length;
  int get deniedCount =>
      work.where((item) => item['status'] == 'denied').length;

  String? get sourceProjection =>
      _text(latestEvent, const ['source', 'source_code', 'code']);
  String? get terminalProjection =>
      _text(latestEvent, const ['terminal', 'stdout', 'log', 'message']);
  String? get browserProjection =>
      _text(latestEvent, const ['browser_url', 'preview_url', 'url']);

  String verificationValue(List<String> keys) =>
      _firstValue(
        <Map<String, Object?>>[
          snapshot.governanceState,
          snapshot.schedulerState,
        ],
        keys,
      ) ??
      '—';
}

class _WorkflowSection extends StatelessWidget {
  const _WorkflowSection({
    required this.model,
    required this.onNavigate,
    required this.onRefreshRequested,
  });

  final _ReferenceHomeModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  static const _stages = <_StageSpec>[
    _StageSpec(
      'Goal Intake',
      'Intent accepted',
      Icons.track_changes_outlined,
      DesktopSection.goals,
    ),
    _StageSpec(
      'Planning',
      'Workflow prepared',
      Icons.account_tree_outlined,
      DesktopSection.workflows,
    ),
    _StageSpec(
      'Execution',
      'Agents executing',
      Icons.play_circle_outline,
      DesktopSection.agents,
    ),
    _StageSpec(
      'Verification',
      'Tests & evidence',
      Icons.verified_user_outlined,
      DesktopSection.evidence,
    ),
    _StageSpec(
      'Delivery',
      'Finished product',
      Icons.inventory_2_outlined,
      DesktopSection.artifacts,
    ),
  ];

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(
                _home(context, 'Active Workflow'),
                style: Theme.of(context)
                    .textTheme
                    .titleLarge
                    ?.copyWith(fontWeight: FontWeight.w800),
              ),
              const SizedBox(width: 10),
              _Badge(label: _home(context, model.badge)),
              const SizedBox(width: 14),
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
                icon: const Icon(
                  Icons.refresh_rounded,
                  size: 20,
                  color: IlaiosTheme.enterpriseCyan,
                ),
              ),
              IconButton(
                tooltip: _isTr(context) ? 'Tam ekran' : 'Fullscreen',
                onPressed: () {},
                icon: const Icon(Icons.open_in_full_rounded, size: 18),
              ),
              IconButton(
                tooltip: _isTr(context) ? 'Daha fazla' : 'More',
                onPressed: () {},
                icon: const Icon(Icons.more_vert_rounded, size: 18),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            key: const Key('reference-workflow-strip'),
            padding: const EdgeInsets.all(10),
            decoration: _box(context),
            child: Column(
              children: [
                Row(
                  children: [
                    for (var index = 0;
                        index < _stages.length;
                        index++) ...[
                      Expanded(
                        child: _StageCard(
                          spec: _stages[index],
                          state: model.stageState(_stages[index].title),
                          onTap: () =>
                              onNavigate(_stages[index].destination),
                        ),
                      ),
                      if (index < _stages.length - 1)
                        const SizedBox(
                          width: 24,
                          child: Icon(Icons.arrow_forward_rounded, size: 18),
                        ),
                    ],
                  ],
                ),
                const SizedBox(height: 12),
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
                          minHeight: 5,
                          backgroundColor: Theme.of(context)
                              .colorScheme
                              .surfaceContainerHighest,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    SizedBox(
                      width: 44,
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
  const _StageCard({
    required this.spec,
    required this.state,
    required this.onTap,
  });
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
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(
          color: active
              ? IlaiosTheme.coreBlue.withValues(alpha: .82)
              : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: ValueKey('home-stage-${spec.destination.name}'),
        onTap: onTap,
        child: SizedBox(
          height: 84,
          child: Padding(
            padding: const EdgeInsets.all(9),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: 30,
                      height: 30,
                      decoration: BoxDecoration(
                        color: IlaiosTheme.coreBlue.withValues(alpha: .14),
                        borderRadius: BorderRadius.circular(15),
                      ),
                      child: Icon(
                        spec.icon,
                        size: 18,
                        color: IlaiosTheme.enterpriseCyan,
                      ),
                    ),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _home(context, spec.title),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 10.5,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          Text(
                            _home(context, spec.subtitle),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.bodySmall,
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
                      active
                          ? Icons.radio_button_checked
                          : Icons.circle_outlined,
                      size: 11,
                      color: active
                          ? IlaiosTheme.success
                          : Theme.of(context).colorScheme.outline,
                    ),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        state == 'Unavailable'
                            ? _home(context, 'Unavailable')
                            : state,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ExecutionSection extends StatelessWidget {
  const _ExecutionSection({required this.model});
  final _ReferenceHomeModel model;

  static const _roles = <String>[
    'Architect Agent',
    'Frontend Dev',
    'Backend Dev',
    'Test Engineer',
    'Security Agent',
    'Browser Agent',
    'Deploy Agent',
  ];

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _home(context, 'LIVE EXECUTION'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          if (model.leases.isEmpty) ...[
            const SizedBox(height: 4),
            Text(
              _home(
                context,
                'No active worker leases are exposed by the scheduler.',
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
          const SizedBox(height: 8),
          Row(
            key: const Key('reference-agent-row'),
            children: [
              for (var index = 0; index < _roles.length; index++) ...[
                Expanded(
                  child: _AgentCard(
                    role: _roles[index],
                    lease: model.leaseFor(_roles[index]),
                    accent: index == _roles.length - 1
                        ? IlaiosTheme.coreBlue
                        : IlaiosTheme.enterpriseCyan,
                  ),
                ),
                if (index < _roles.length - 1) const SizedBox(width: 7),
              ],
            ],
          ),
        ],
      );
}

class _AgentCard extends StatelessWidget {
  const _AgentCard({
    required this.role,
    required this.lease,
    required this.accent,
  });
  final String role;
  final Map<String, Object?>? lease;
  final Color accent;

  @override
  Widget build(BuildContext context) {
    final activity =
        _text(lease, const ['task', 'task_id', 'request_id', 'activity']) ??
        _home(context, 'Unavailable');
    final state = _text(lease, const ['state', 'status', 'health']) ??
        _home(context, 'Unavailable');
    final active = lease != null;
    return Container(
      height: 132,
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 7),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: active
              ? accent.withValues(alpha: .72)
              : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                Icons.circle,
                size: 7,
                color: active
                    ? IlaiosTheme.success
                    : Theme.of(context).colorScheme.outline,
              ),
              const SizedBox(width: 5),
              Expanded(
                child: Text(
                  role,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 9.2,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          Text(
            state,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelSmall,
          ),
          const SizedBox(height: 2),
          Text(
            activity,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelSmall,
          ),
          const Spacer(),
          Center(
            child: Container(
              width: 52,
              height: 52,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: .08),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Stack(
                alignment: Alignment.center,
                children: [
                  Icon(
                    Icons.person_rounded,
                    size: 30,
                    color: active
                        ? accent
                        : Theme.of(context).colorScheme.outline,
                  ),
                  Positioned(
                    right: 3,
                    bottom: 6,
                    child: Icon(
                      Icons.laptop_windows_rounded,
                      size: 18,
                      color: accent,
                    ),
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
  const _WorkspaceSection({required this.model});
  final _ReferenceHomeModel model;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _home(context, 'LIVE WORKSPACE'),
            style: Theme.of(context).textTheme.titleMedium,
          ),
          const SizedBox(height: 7),
          Container(
            key: const Key('reference-workspace'),
            decoration: _box(context),
            child: Column(
              children: [
                SizedBox(
                  height: 38,
                  child: SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: [
                        for (final tab in const [
                          'Live Code',
                          'Terminal',
                          'Browser',
                          'Files',
                          'Logs',
                          'Events',
                        ])
                          Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 10),
                            child: Row(
                              children: [
                                Icon(
                                  _tabIcon(tab),
                                  size: 14,
                                  color: tab == 'Live Code'
                                      ? IlaiosTheme.enterpriseCyan
                                      : Theme.of(context)
                                          .colorScheme
                                          .onSurfaceVariant,
                                ),
                                const SizedBox(width: 5),
                                Text(
                                  _home(context, tab),
                                  style: TextStyle(
                                    fontSize: 10.5,
                                    color: tab == 'Live Code'
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
                Divider(
                  height: 1,
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
                SizedBox(
                  height: 276,
                  child: Row(
                    children: [
                      Expanded(
                        flex: 34,
                        child: _WorkspacePane(
                          title: _home(context, 'Live Code'),
                          icon: Icons.code_rounded,
                          primary: model.sourceProjection,
                          emptyTitle:
                              _home(context, 'Code projection unavailable'),
                          emptyBody: _home(
                            context,
                            'No source buffer is exposed by the current Desktop API.',
                          ),
                        ),
                      ),
                      VerticalDivider(
                        width: 1,
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      Expanded(
                        flex: 31,
                        child: _WorkspacePane(
                          title: _home(context, 'Terminal'),
                          icon: Icons.terminal_rounded,
                          primary: model.terminalProjection,
                          emptyTitle: _home(context, 'Terminal'),
                          emptyBody: _home(
                            context,
                            'No authoritative live events are available.',
                          ),
                        ),
                      ),
                      VerticalDivider(
                        width: 1,
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      Expanded(
                        flex: 35,
                        child: _WorkspacePane(
                          title: _home(context, 'Browser'),
                          icon: Icons.public_rounded,
                          primary: model.browserProjection,
                          emptyTitle: _home(context, 'Preview unavailable'),
                          emptyBody: _home(
                            context,
                            'No browser preview projection is exposed.',
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      );

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
  Widget build(BuildContext context) => Container(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              height: 34,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              child: Row(
                children: [
                  Icon(icon, size: 14),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelMedium,
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(11),
                child: primary == null
                    ? Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          Icon(
                            icon,
                            size: 30,
                            color:
                                IlaiosTheme.coreBlue.withValues(alpha: .75),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            emptyTitle,
                            textAlign: TextAlign.center,
                            style: const TextStyle(fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 5),
                          Text(
                            emptyBody,
                            textAlign: TextAlign.center,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      )
                    : SelectableText(
                        primary!,
                        style: const TextStyle(
                          fontFamily: 'Consolas',
                          fontSize: 10.5,
                          height: 1.45,
                        ),
                      ),
              ),
            ),
          ],
        ),
      );
}

class _BottomContentRow extends StatelessWidget {
  const _BottomContentRow({required this.model});
  final _ReferenceHomeModel model;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: _ArtifactsPanel(records: model.snapshot.evidenceRecords),
          ),
          const SizedBox(width: 10),
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
        height: 126,
        padding: const EdgeInsets.all(10),
        decoration: _box(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    _home(context, 'LATEST ARTIFACTS'),
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
                Text(
                  _home(context, 'View all →'),
                  style: Theme.of(context).textTheme.labelSmall,
                ),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: records.isEmpty
                  ? Center(
                      child: Text(
                        _home(
                          context,
                          'No verified artifact evidence is available.',
                        ),
                        textAlign: TextAlign.center,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    )
                  : Row(
                      children: [
                        for (var index = 0;
                            index < records.take(3).length;
                            index++) ...[
                          Expanded(
                            child: _ArtifactCard(record: records[index]),
                          ),
                          if (index < records.take(3).length - 1)
                            const SizedBox(width: 7),
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
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(
                  Icons.inventory_2_outlined,
                  size: 17,
                  color: IlaiosTheme.enterpriseCyan,
                ),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    record.action,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 9.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 5),
            Text(
              record.executionId,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall,
            ),
            Text(
              _short(record.artifactDigest),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.labelSmall,
            ),
          ],
        ),
      );
}

class _VerificationPanel extends StatelessWidget {
  const _VerificationPanel({required this.model});
  final _ReferenceHomeModel model;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-evidence-panel'),
        height: 126,
        padding: const EdgeInsets.all(10),
        decoration: _box(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _home(context, 'EVIDENCE & VERIFICATION'),
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 8),
            Expanded(
              child: Row(
                children: [
                  Expanded(
                    child: _VerificationCard(
                      title: 'QA Report',
                      value: model.verificationValue(
                        const ['qa_status', 'qa_result', 'test_status'],
                      ),
                    ),
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: _VerificationCard(
                      title: 'Security Scan',
                      value: model.verificationValue(
                        const [
                          'security_status',
                          'security_result',
                          'scan_status',
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: _VerificationCard(
                      title: 'Policy Check',
                      value: model.verificationValue(
                        const [
                          'policy_status',
                          'policy_result',
                          'compliance_status',
                        ],
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

class _VerificationCard extends StatelessWidget {
  const _VerificationCard({required this.title, required this.value});
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: Row(
          children: [
            Icon(
              Icons.verified_user_outlined,
              size: 24,
              color: value == '—'
                  ? Theme.of(context).colorScheme.outline
                  : IlaiosTheme.success,
            ),
            const SizedBox(width: 7),
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
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _RightRail extends StatelessWidget {
  const _RightRail({required this.model});
  final _ReferenceHomeModel model;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          _RailCard(
            key: const Key('reference-status-card'),
            title: _home(context, 'STATUS'),
            accent: IlaiosTheme.coreBlue,
            rows: [
              (_home(context, 'Job ID'), model.jobId),
              (_home(context, 'Started'), model.started),
              (_home(context, 'Elapsed'), model.elapsed),
              (_home(context, 'Est. finish'), model.estimatedFinish),
              (
                _home(context, 'Phase'),
                model.phase == 'Unavailable'
                    ? _home(context, 'Unavailable')
                    : model.phase,
              ),
              (
                _home(context, 'Active workers'),
                model.leases.isEmpty ? '0' : '${model.leases.length}',
              ),
              (
                _home(context, 'Status'),
                model.executionStatus == 'Unavailable'
                    ? _home(context, 'Unavailable')
                    : model.executionStatus,
              ),
            ],
          ),
          const SizedBox(height: 10),
          _RailCard(
            title: _home(context, 'COST & USAGE'),
            accent: IlaiosTheme.violet,
            rows: [
              (
                _home(context, 'Total cost'),
                model.totalCost ?? _home(context, 'Unavailable'),
              ),
              (
                _home(context, 'Budget'),
                model.budget ?? _home(context, 'Unavailable'),
              ),
              (
                _home(context, 'Token usage'),
                model.tokenUsage ?? _home(context, 'Unavailable'),
              ),
              (
                _home(context, 'GPU time'),
                model.gpuTime ?? _home(context, 'Unavailable'),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _RailCard(
            title: _home(context, 'APPROVALS'),
            accent: IlaiosTheme.enterpriseCyan,
            rows: [
              (_home(context, 'Pending'), '${model.pendingApprovals}'),
              (_home(context, 'Approved'), '${model.approvedCount}'),
              (_home(context, 'Denied'), '${model.deniedCount}'),
            ],
          ),
          const SizedBox(height: 10),
          Container(
            key: const Key('reference-latest-logs'),
            padding: const EdgeInsets.all(12),
            decoration: _box(context),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  _home(context, 'LATEST LOGS'),
                  style: Theme.of(context).textTheme.titleSmall,
                ),
                const SizedBox(height: 8),
                if (model.snapshot.liveEvents.isEmpty)
                  Text(
                    _home(context, 'No live event records available.'),
                    style: Theme.of(context).textTheme.bodySmall,
                  )
                else
                  for (final event in model.snapshot.liveEvents.reversed.take(5))
                    Padding(
                      padding: const EdgeInsets.only(bottom: 7),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              _text(
                                    event,
                                    const ['event_type', 'type', 'status'],
                                  ) ??
                                  _home(context, 'Unavailable'),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: Theme.of(context).textTheme.bodySmall,
                            ),
                          ),
                          const SizedBox(width: 6),
                          const Icon(
                            Icons.circle,
                            size: 6,
                            color: IlaiosTheme.success,
                          ),
                        ],
                      ),
                    ),
              ],
            ),
          ),
        ],
      );
}

class _RailCard extends StatelessWidget {
  const _RailCard({
    required this.title,
    required this.accent,
    required this.rows,
    super.key,
  });
  final String title;
  final Color accent;
  final List<(String, String)> rows;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(12),
        decoration: _box(context),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Container(
                  width: 4,
                  height: 20,
                  decoration: BoxDecoration(
                    color: accent,
                    borderRadius: BorderRadius.circular(3),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.titleSmall,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 9),
            for (final row in rows)
              Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        row.$1,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        row.$2,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        textAlign: TextAlign.right,
                        style: const TextStyle(
                          fontSize: 10.5,
                          fontWeight: FontWeight.w600,
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

class _Badge extends StatelessWidget {
  const _Badge({required this.label});
  final String label;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(
          color: IlaiosTheme.enterpriseCyan.withValues(alpha: .10),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: IlaiosTheme.enterpriseCyan.withValues(alpha: .45),
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: IlaiosTheme.enterpriseCyan,
            fontSize: 9,
            fontWeight: FontWeight.w800,
          ),
        ),
      );
}

BoxDecoration _box(BuildContext context) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      borderRadius: BorderRadius.circular(9),
      border: Border.all(
        color: Theme.of(context).colorScheme.outlineVariant,
      ),
    );

String _home(BuildContext context, String english) =>
    IlaiosHomeCatalog.text(context.ilaiosLocale.locale.code, english);

bool _isTr(BuildContext context) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _normalize(String value) => value
    .toLowerCase()
    .replaceAll(RegExp(r'[^a-z0-9]+'), ' ')
    .trim();

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

String? _firstValue(
  List<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final source in sources) {
    final value = _text(source, keys);
    if (value != null) return value;
  }
  return null;
}

String _short(String value) =>
    value.length <= 18 ? value : '${value.substring(0, 18)}…';
