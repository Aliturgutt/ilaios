import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../navigation/desktop_section.dart';

/// Reference Home implementation for the user-approved command-center design.
///
/// The surface is intentionally a fixed Desktop composition: the root never
/// scrolls vertically. Long runtime collections scroll only inside their own
/// panels. All telemetry is projected from authoritative Desktop inputs; the
/// reference screenshots are layout/theme references only and their demo values
/// are never copied into runtime state.
class ReferenceHomeDashboardV3 extends StatefulWidget {
  const ReferenceHomeDashboardV3({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.userSession,
    this.onPromptSubmit,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onNavigate;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final VoidCallback? onRefreshRequested;

  @override
  State<ReferenceHomeDashboardV3> createState() =>
      _ReferenceHomeDashboardV3State();
}

class _ReferenceHomeDashboardV3State extends State<ReferenceHomeDashboardV3> {
  final TextEditingController _promptController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  Future<void> _startWork() async {
    final objective = _promptController.text.trim();
    if (objective.isEmpty || widget.onPromptSubmit == null) {
      widget.onNavigate(DesktopSection.goals);
      return;
    }
    if (_submitting) return;
    setState(() => _submitting = true);
    try {
      final submission = await widget.onPromptSubmit!(objective);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _t(
              context,
              'Work accepted: ${submission.jobId} · ${submission.state}',
              'İş kabul edildi: ${submission.jobId} · ${submission.state}',
            ),
          ),
        ),
      );
      _promptController.clear();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _t(context, 'Work could not be started: $error',
                'İş başlatılamadı: $error'),
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = _CommandCenterModel(
      projection: widget.projection,
      snapshot: widget.snapshot,
      status: widget.status,
      userSession: widget.userSession,
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        final contentHeight =
            (constraints.maxHeight - 20).clamp(620.0, 1200.0).toDouble();
        final heroHeight = contentHeight * .27;
        final metricsHeight = contentHeight * .10;
        final middleHeight = contentHeight * .28;

        return Padding(
          padding: const EdgeInsets.fromLTRB(10, 10, 10, 14),
          child: Column(
            key: const Key('command-center-home'),
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              SizedBox(
                height: heroHeight,
                child: _CommandHero(
                  controller: _promptController,
                  submitting: _submitting,
                  model: model,
                  onStartWork: _startWork,
                  onNavigate: widget.onNavigate,
                ),
              ),
              if (model.runningWorkCount != null ||
                  model.pendingApprovalCount != null ||
                  model.totalCost != null) ...[
                const SizedBox(height: 8),
                SizedBox(
                  height: metricsHeight,
                  child: _MetricsRow(model: model),
                ),
              ],
              const SizedBox(height: 8),
              SizedBox(
                height: middleHeight,
                child: _MiddleRow(model: model, onNavigate: widget.onNavigate),
              ),
              const SizedBox(height: 8),
              Expanded(
                child: _BottomRow(
                  model: model,
                  onNavigate: widget.onNavigate,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _CommandCenterModel {
  const _CommandCenterModel({
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

  String? get projectLabel => _text(
        latestEvent,
        const ['project_name', 'project', 'workspace', 'goal', 'objective'],
      );

  int? get runningWorkCount {
    if (snapshot.governanceState.containsKey('work')) {
      return work.where((item) {
        final state = _normalize(_text(item, const ['status', 'state']) ?? '');
        return state.isNotEmpty &&
            !const {'completed', 'complete', 'succeeded', 'success', 'failed', 'denied', 'cancelled'}
                .contains(state);
      }).length;
    }
    if (projection.connected) return projection.jobCount;
    return null;
  }

  int? get activeAgentCount =>
      snapshot.schedulerState.containsKey('leases') ? leases.length : null;

  int? get pendingApprovalCount {
    if (!snapshot.governanceState.containsKey('work') &&
        !snapshot.governanceState.containsKey('admissions')) {
      return null;
    }
    final hasAdmissions = snapshot.governanceState.containsKey('admissions');
    final required = <String>{};
    for (final item in admissions) {
      if (item['human_approval_required'] != true) continue;
      final id = item['request_id'];
      if (id is String && id.isNotEmpty) required.add(id);
    }
    return work.where((item) {
      final id = item['request_id'];
      final state = _normalize(_text(item, const ['status', 'state']) ?? '');
      if (state != 'pending') return false;
      if (!hasAdmissions) return true;
      return id is String && required.contains(id);
    }).length;
  }

  int get deniedCount => work.where((item) {
        final state = _normalize(_text(item, const ['status', 'state']) ?? '');
        return state == 'denied' || state == 'failed';
      }).length;

  String? get totalCost => _firstValue(
        [snapshot.governanceState, snapshot.schedulerState],
        const [
          'today_cost_usd',
          'daily_cost_usd',
          'total_cost_usd',
          'cost_usd',
          'spent_minor',
        ],
      );

  double? get totalCostNumber => _firstNumber(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['today_cost_usd', 'daily_cost_usd', 'total_cost_usd', 'cost_usd'],
      );

  double? get budgetNumber => _firstNumber(
        [snapshot.governanceState, snapshot.schedulerState],
        const ['budget_usd', 'daily_budget_usd', 'hard_cap_usd'],
      );

  double? get healthPercent {
    final raw = _firstNumber(
      [
        latestEvent ?? const <String, Object?>{},
        snapshot.schedulerState,
        snapshot.governanceState,
      ],
      const ['system_health_percent', 'health_percent', 'health_score'],
    );
    if (raw == null) return null;
    final value = raw <= 1 ? raw * 100 : raw;
    if (value < 0 || value > 100) return null;
    return value;
  }

  List<Map<String, Object?>> get focusItems {
    if (work.isNotEmpty) return work.reversed.take(4).toList(growable: false);
    return snapshot.liveEvents.reversed.take(4).toList(growable: false);
  }

  List<_AttentionData> get attentionItems {
    final items = <_AttentionData>[];
    final pending = pendingApprovalCount;
    if (pending != null && pending > 0) {
      items.add(
        _AttentionData(
          severity: _AttentionSeverity.critical,
          title: '$pending approval${pending == 1 ? '' : 's'} waiting',
          subtitle: 'Human approval is required before governed execution can continue.',
          destination: DesktopSection.approvals,
        ),
      );
    }
    if (deniedCount > 0) {
      items.add(
        _AttentionData(
          severity: _AttentionSeverity.warning,
          title: '$deniedCount denied or failed work item${deniedCount == 1 ? '' : 's'}',
          subtitle: 'Review the latest governed execution records.',
          destination: DesktopSection.workflows,
        ),
      );
    }
    final cost = totalCostNumber;
    final budget = budgetNumber;
    if (cost != null && budget != null && budget > 0 && cost / budget >= .8) {
      items.add(
        _AttentionData(
          severity: _AttentionSeverity.warning,
          title: 'Budget threshold reached',
          subtitle: '${(cost / budget * 100).round()}% of the authoritative budget is consumed.',
          destination: DesktopSection.costs,
        ),
      );
    }
    for (final event in snapshot.liveEvents.reversed) {
      final state = _normalize(
        _text(event, const ['status', 'state', 'event_type', 'type']) ?? '',
      );
      if (!state.contains('error') &&
          !state.contains('failed') &&
          !state.contains('critical')) {
        continue;
      }
      items.add(
        _AttentionData(
          severity: _AttentionSeverity.critical,
          title: _text(event, const ['message', 'event_type', 'type']) ?? 'Runtime issue',
          subtitle: _text(event, const ['detail', 'reason']) ?? 'Authoritative runtime event requires review.',
          destination: DesktopSection.workflows,
        ),
      );
      break;
    }
    return items.take(4).toList(growable: false);
  }

  List<EvidenceRecord> get artifacts =>
      snapshot.evidenceRecords.reversed.take(3).toList(growable: false);

  List<EvidenceRecord> get recentCompletions =>
      snapshot.evidenceRecords.reversed.take(3).toList(growable: false);

  List<Map<String, Object?>> get recentActivities =>
      snapshot.liveEvents.reversed.take(5).toList(growable: false);

  String get sessionId =>
      userSession?.sessionId ??
      _text(latestEvent, const ['session_id', 'execution_id', 'job_id']) ??
      '—';

  String get elapsed =>
      _text(latestEvent, const ['elapsed', 'elapsed_time', 'duration']) ?? '—';

  String get owner =>
      userSession?.displayIdentity ?? userSession?.principalId ?? '—';

  String get role =>
      _text(latestEvent, const ['role', 'user_role', 'principal_role']) ?? '—';

  String get lastSaved =>
      _text(latestEvent, const ['updated_at', 'timestamp', 'saved_at']) ?? '—';
}

class _CommandHero extends StatelessWidget {
  const _CommandHero({
    required this.controller,
    required this.submitting,
    required this.model,
    required this.onStartWork,
    required this.onNavigate,
  });

  final TextEditingController controller;
  final bool submitting;
  final _CommandCenterModel model;
  final Future<void> Function() onStartWork;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('command-center-hero'),
        padding: const EdgeInsets.fromLTRB(18, 16, 18, 14),
        decoration: _panel(context, elevated: true),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _t(context, 'Start work', 'İş başlat'),
              style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                  ),
            ),
            const SizedBox(height: 4),
            Text(
              _t(
                context,
                'Describe the finished result. ILAIOS will route governed execution through the existing system.',
                'Bitmiş sonucu tarif et. ILAIOS mevcut yönetişimli yürütme zinciri üzerinden ilerlesin.',
              ),
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(height: 10),
            Expanded(
              child: TextField(
                key: const Key('home-command-prompt'),
                controller: controller,
                minLines: 3,
                maxLines: 6,
                textInputAction: TextInputAction.newline,
                decoration: InputDecoration(
                  hintText: _t(
                    context,
                    'Website, video, software or research — describe the result and constraints…',
                    'Web sitesi, video, yazılım veya araştırma — sonucu ve kısıtları yaz…',
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                TextButton.icon(
                  key: const Key('home-templates'),
                  onPressed: () => onNavigate(DesktopSection.workflows),
                  icon: const Icon(Icons.library_books_outlined, size: 16),
                  label: Text(_t(context, 'Templates', 'Şablonlar')),
                ),
                const SizedBox(width: 6),
                TextButton.icon(
                  key: const Key('home-last-session'),
                  onPressed: () => onNavigate(DesktopSection.workflows),
                  icon: const Icon(Icons.history_rounded, size: 16),
                  label: Text(_t(context, 'Recent work', 'Son işler')),
                ),
                const Spacer(),
                FilledButton.icon(
                  key: const Key('home-new-work'),
                  onPressed: submitting ? null : onStartWork,
                  icon: const Icon(Icons.arrow_forward_rounded, size: 17),
                  label: Text(_t(context, 'Start', 'Başlat')),
                ),
              ],
            ),
          ],
        ),
      );
}

class _MetricsRow extends StatelessWidget {
  const _MetricsRow({required this.model});

  final _CommandCenterModel model;

  @override
  Widget build(BuildContext context) {
    final items = <({IconData icon, String label, String value, Color color})>[];
    final running = model.runningWorkCount;
    if (running != null) {
      items.add((
        icon: Icons.play_circle_outline_rounded,
        label: _t(context, 'Ongoing', 'Devam eden'),
        value: '$running',
        color: Theme.of(context).colorScheme.onSurfaceVariant,
      ));
    }
    final approvals = model.pendingApprovalCount;
    if (approvals != null) {
      items.add((
        icon: Icons.shield_outlined,
        label: _t(context, 'Needs Attention', 'Müdahale gereken'),
        value: '$approvals',
        color: approvals > 0 ? IlaiosTheme.warning : Theme.of(context).colorScheme.onSurfaceVariant,
      ));
    }
    final cost = model.totalCost;
    if (cost != null) {
      items.add((
        icon: Icons.account_balance_wallet_outlined,
        label: _t(context, 'Current cost', 'Mevcut maliyet'),
        value: cost,
        color: Theme.of(context).colorScheme.onSurfaceVariant,
      ));
    }

    return Container(
      key: const Key('command-center-metrics'),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: _panel(context),
      child: Row(
        children: [
          for (var index = 0; index < items.length; index++) ...[
            if (index > 0)
              Container(
                width: 1,
                height: 28,
                margin: const EdgeInsets.symmetric(horizontal: 18),
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            Icon(items[index].icon, size: 16, color: items[index].color),
            const SizedBox(width: 7),
            Text(
              items[index].label,
              style: Theme.of(context).textTheme.bodySmall,
            ),
            const SizedBox(width: 7),
            Text(
              items[index].value,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
            ),
          ],
        ],
      ),
    );
  }
}

class _MiddleRow extends StatelessWidget {
  const _MiddleRow({required this.model, required this.onNavigate});

  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            flex: 45,
            child: _FocusWorkPanel(model: model, onNavigate: onNavigate),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 55,
            child: _AttentionPanel(model: model, onNavigate: onNavigate),
          ),
        ],
      );
}

class _FocusWorkPanel extends StatelessWidget {
  const _FocusWorkPanel({required this.model, required this.onNavigate});

  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final items = model.focusItems;
    return _SectionPanel(
      key: const Key('command-center-focus'),
      title: _t(context, 'FOCUS WORK', 'ODAK İŞLER'),
      actionLabel: _t(context, 'All', 'Tümü'),
      onAction: () => onNavigate(DesktopSection.workflows),
      child: items.isEmpty
          ? _EmptyState(
              icon: Icons.track_changes_rounded,
              label: _t(context, 'No authoritative focus work is available.',
                  'Doğrulanmış odak işi bulunmuyor.'),
            )
          : Column(
              children: [
                for (var index = 0; index < items.length; index++) ...[
                  Expanded(child: _FocusWorkRow(item: items[index])),
                  if (index < items.length - 1)
                    Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                ],
              ],
            ),
    );
  }
}

class _FocusWorkRow extends StatelessWidget {
  const _FocusWorkRow({required this.item});
  final Map<String, Object?> item;

  @override
  Widget build(BuildContext context) {
    final title = _text(
          item,
          const ['project_name', 'title', 'objective', 'goal', 'request_id', 'job_id'],
        ) ??
        '—';
    final subtitle = _text(item, const ['description', 'message', 'task']) ?? '—';
    final state = _text(item, const ['status', 'state', 'phase']) ?? '—';
    final phase = _text(item, const ['phase', 'stage']) ?? '—';
    final rawProgress = _number(item, const ['progress', 'progress_percent']);
    final progress = rawProgress == null
        ? null
        : ((rawProgress <= 1 ? rawProgress : rawProgress / 100).clamp(0.0, 1.0));

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      child: Row(
        children: [
          Container(
            width: 27,
            height: 27,
            decoration: BoxDecoration(
              color: IlaiosTheme.enterpriseCyan.withValues(alpha: .10),
              borderRadius: BorderRadius.circular(14),
            ),
            child: const Icon(Icons.language_rounded, size: 15, color: IlaiosTheme.enterpriseCyan),
          ),
          const SizedBox(width: 7),
          Expanded(
            flex: 5,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 9.7, fontWeight: FontWeight.w700)),
                Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 9.0)),
              ],
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            flex: 4,
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(state, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 8.8)),
                    ),
                    Text(phase, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.2)),
                  ],
                ),
                const SizedBox(height: 3),
                if (progress == null)
                  Container(
                    key: const Key('focus-progress-unavailable-track'),
                    height: 3,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      borderRadius: BorderRadius.circular(4),
                    ),
                  )
                else
                  ClipRRect(
                    borderRadius: BorderRadius.circular(4),
                    child: LinearProgressIndicator(
                      value: progress,
                      minHeight: 3,
                      backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

enum _AttentionSeverity { critical, warning, info }

class _AttentionData {
  const _AttentionData({
    required this.severity,
    required this.title,
    required this.subtitle,
    required this.destination,
  });

  final _AttentionSeverity severity;
  final String title;
  final String subtitle;
  final DesktopSection destination;
}

class _AttentionPanel extends StatelessWidget {
  const _AttentionPanel({required this.model, required this.onNavigate});

  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final items = model.attentionItems;
    return _SectionPanel(
      key: const Key('command-center-attention'),
      title: _t(context, 'NEEDS ATTENTION', 'DİKKAT GEREKTİRENLER'),
      actionLabel: _t(context, 'All', 'Tümü'),
      onAction: () => onNavigate(DesktopSection.approvals),
      child: items.isEmpty
          ? _EmptyState(
              icon: Icons.check_circle_outline_rounded,
              label: _t(context, 'No verified attention item is active.',
                  'Doğrulanmış aktif uyarı bulunmuyor.'),
            )
          : Column(
              children: [
                for (var index = 0; index < items.length; index++) ...[
                  Expanded(
                    child: _AttentionRow(
                      data: items[index],
                      onTap: () => onNavigate(items[index].destination),
                    ),
                  ),
                  if (index < items.length - 1)
                    Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                ],
              ],
            ),
    );
  }
}

class _AttentionRow extends StatelessWidget {
  const _AttentionRow({required this.data, required this.onTap});

  final _AttentionData data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = switch (data.severity) {
      _AttentionSeverity.critical => IlaiosTheme.danger,
      _AttentionSeverity.warning => IlaiosTheme.warning,
      _AttentionSeverity.info => IlaiosTheme.coreBlue,
    };
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          child: Row(
            children: [
              Container(
                width: 26,
                height: 26,
                decoration: BoxDecoration(
                  border: Border.all(color: color),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(Icons.priority_high_rounded, size: 14, color: color),
              ),
              const SizedBox(width: 7),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(data.title, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 9.7, fontWeight: FontWeight.w700)),
                    Text(data.subtitle, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 9.0)),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.chevron_right_rounded, size: 15),
            ],
          ),
        ),
      ),
    );
  }
}

class _BottomRow extends StatelessWidget {
  const _BottomRow({required this.model, required this.onNavigate});

  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            flex: 55,
            child: _ArtifactsPanel(model: model, onNavigate: onNavigate),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 45,
            child: _CompletedPanel(model: model, onNavigate: onNavigate),
          ),
        ],
      );
}

class _ArtifactsPanel extends StatelessWidget {
  const _ArtifactsPanel({required this.model, required this.onNavigate});

  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final records = model.artifacts;
    return _SectionPanel(
      key: const Key('command-center-artifacts'),
      title: _t(context, 'LATEST OUTPUTS', 'SON ÇIKTILAR'),
      actionLabel: _t(context, 'All', 'Tümü'),
      onAction: () => onNavigate(DesktopSection.artifacts),
      child: records.isEmpty
          ? _EmptyState(
              icon: Icons.inventory_2_outlined,
              label: _t(context, 'No verified output is available.',
                  'Doğrulanmış çıktı bulunmuyor.'),
            )
          : Row(
              children: [
                for (var index = 0; index < records.length; index++) ...[
                  Expanded(child: _ArtifactTile(record: records[index])),
                  if (index < records.length - 1) const SizedBox(width: 5),
                ],
              ],
            ),
    );
  }
}

class _ArtifactTile extends StatelessWidget {
  const _ArtifactTile({required this.record});
  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.fromLTRB(5, 3, 0, 5),
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
            Row(
              children: [
                const Icon(Icons.description_outlined, size: 16, color: IlaiosTheme.enterpriseCyan),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(record.action, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w700)),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(record.executionId, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.4)),
            Text(_short(record.artifactDigest), maxLines: 1, overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.4)),
          ],
        ),
      );
}

class _CompletedPanel extends StatelessWidget {
  const _CompletedPanel({required this.model, required this.onNavigate});

  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final records = model.recentCompletions;
    return _SectionPanel(
      key: const Key('command-center-completed'),
      title: _t(context, 'RECENTLY COMPLETED', 'SON TAMAMLANANLAR'),
      actionLabel: _t(context, 'All', 'Tümü'),
      onAction: () => onNavigate(DesktopSection.evidence),
      child: records.isEmpty
          ? _EmptyState(
              icon: Icons.task_alt_rounded,
              label: _t(context, 'No verified completion is available.',
                  'Doğrulanmış tamamlanma kaydı bulunmuyor.'),
            )
          : Column(
              children: [
                for (var index = 0; index < records.length; index++) ...[
                  Expanded(child: _CompletionRow(record: records[index])),
                  if (index < records.length - 1)
                    Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                ],
              ],
            ),
    );
  }
}

class _CompletionRow extends StatelessWidget {
  const _CompletionRow({required this.record});
  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        child: Row(
          children: [
            const Icon(Icons.check_circle_outline_rounded, size: 17, color: IlaiosTheme.success),
            const SizedBox(width: 6),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(record.action, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 9.4, fontWeight: FontWeight.w700)),
                  Text(record.executionId, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.4)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _SectionPanel extends StatelessWidget {
  const _SectionPanel({
    required this.title,
    required this.child,
    this.actionLabel,
    this.onAction,
    super.key,
  });

  final String title;
  final Widget child;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _panel(context),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 30,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800)),
                    ),
                    if (actionLabel != null)
                      TextButton(
                        onPressed: onAction,
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 5),
                          visualDensity: VisualDensity.compact,
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(actionLabel!, style: const TextStyle(fontSize: 9.1)),
                            const Icon(Icons.chevron_right_rounded, size: 12),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
            ),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            Expanded(child: child),
          ],
        ),
      );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.label});
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 20, color: Theme.of(context).colorScheme.outline),
              const SizedBox(height: 5),
              Text(label,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 9.5)),
            ],
          ),
        ),
      );
}

BoxDecoration _panel(BuildContext context, {bool elevated = false}) {
  final dark = Theme.of(context).brightness == Brightness.dark;
  return BoxDecoration(
    color: Theme.of(context).colorScheme.surfaceContainerLow,
    borderRadius: BorderRadius.circular(9),
    border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    boxShadow: dark || !elevated
        ? const []
        : const [
            BoxShadow(
              color: Color(0x0A0B0F14),
              blurRadius: 10,
              offset: Offset(0, 3),
            ),
          ],
  );
}

String _t(BuildContext context, String english, String turkish) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish ? turkish : english;

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

double? _firstNumber(
  List<Map<String, Object?>> sources,
  List<String> keys,
) {
  for (final source in sources) {
    final value = _number(source, keys);
    if (value != null) return value;
  }
  return null;
}

String _short(String value) =>
    value.length <= 20 ? value : '${value.substring(0, 20)}…';
