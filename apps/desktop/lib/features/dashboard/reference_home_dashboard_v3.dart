import 'dart:math' as math;

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
        final heroHeight = contentHeight * .225;
        final metricsHeight = contentHeight * .115;
        final middleHeight = contentHeight * .30;
        final railWidth = constraints.maxWidth >= 1500 ? 282.0 : 258.0;

        return Padding(
          padding: const EdgeInsets.all(10),
          child: Row(
            key: const Key('command-center-home'),
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Column(
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
                    const SizedBox(height: 7),
                    SizedBox(
                      height: metricsHeight,
                      child: _MetricsRow(model: model),
                    ),
                    const SizedBox(height: 7),
                    SizedBox(
                      height: middleHeight,
                      child: _MiddleRow(model: model, onNavigate: widget.onNavigate),
                    ),
                    const SizedBox(height: 7),
                    Expanded(
                      child: _BottomRow(
                        model: model,
                        onNavigate: widget.onNavigate,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(
                width: railWidth,
                child: _RightRail(
                  model: model,
                  onNavigate: widget.onNavigate,
                  onRefreshRequested: widget.onRefreshRequested,
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
      return required.isEmpty || (id is String && required.contains(id));
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
  Widget build(BuildContext context) {
    final tone = _Tone.of(context);
    return Container(
      key: const Key('command-center-hero'),
      padding: const EdgeInsets.fromLTRB(16, 13, 12, 12),
      decoration: _panel(context, elevated: true),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            flex: 58,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  _t(context, 'Main Control Center', 'Ana Kontrol Merkezi'),
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontSize: 24,
                        fontWeight: FontWeight.w700,
                      ),
                ),
                const SizedBox(height: 2),
                Text(
                  _t(
                    context,
                    'Manage all your work from one place and increase productivity.',
                    'Tüm iş akışlarınızı tek yerden yönetin, üretkenliğinizi artırın.',
                  ),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall,
                ),
                const SizedBox(height: 9),
                SizedBox(
                  height: 39,
                  child: TextField(
                    key: const Key('home-command-prompt'),
                    controller: controller,
                    onSubmitted: (_) => onStartWork(),
                    textInputAction: TextInputAction.go,
                    decoration: InputDecoration(
                      hintText: _t(
                        context,
                        'Start a website, video, software or research task with one prompt…',
                        'Tek komutla web sitesi, video, yazılım veya araştırma başlat…',
                      ),
                      suffixIcon: IconButton(
                        tooltip: _t(context, 'Start work', 'İşi başlat'),
                        onPressed: submitting ? null : onStartWork,
                        icon: submitting
                            ? const SizedBox(
                                width: 15,
                                height: 15,
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(
                                Icons.auto_awesome_rounded,
                                size: 18,
                                color: IlaiosTheme.enterpriseCyan,
                              ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Expanded(
                  child: Row(
                    children: [
                      _HeroButton(
                        key: const Key('home-new-work'),
                        icon: Icons.add_rounded,
                        label: _t(context, 'Start New Work', 'Yeni İş Başlat'),
                        primary: true,
                        onPressed: submitting ? null : onStartWork,
                      ),
                      const SizedBox(width: 7),
                      _HeroButton(
                        key: const Key('home-templates'),
                        icon: Icons.library_books_outlined,
                        label: _t(context, 'Templates', 'Şablonlar'),
                        onPressed: () => onNavigate(DesktopSection.workflows),
                      ),
                      const SizedBox(width: 7),
                      _HeroButton(
                        key: const Key('home-last-session'),
                        icon: Icons.history_rounded,
                        label: _t(context, 'Open Last Session', 'Son Oturumu Aç'),
                        onPressed: () => onNavigate(DesktopSection.workflows),
                      ),
                      const SizedBox(width: 7),
                      _HeroButton(
                        key: const Key('home-assign-agent'),
                        icon: Icons.person_add_alt_1_outlined,
                        label: _t(context, 'Assign Agent', 'Ajan Ata'),
                        onPressed: () => onNavigate(DesktopSection.agents),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            flex: 20,
            child: CustomPaint(
              key: const Key('command-center-orbit-visual'),
              painter: _OrbitCorePainter(
                line: tone.accent.withValues(alpha: tone.dark ? .62 : .42),
                faint: tone.accent.withValues(alpha: tone.dark ? .17 : .13),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            flex: 26,
            child: Column(
              children: [
                Expanded(
                  child: _FactoryAction(
                    key: const Key('home-factory-web'),
                    icon: Icons.language_rounded,
                    title: _t(context, 'Create Website', 'Website Oluştur'),
                    subtitle: _t(context, 'Create a web project from zero',
                        'Sıfırdan site veya içerik oluştur'),
                    onTap: () => onNavigate(DesktopSection.goals),
                  ),
                ),
                const SizedBox(height: 5),
                Expanded(
                  child: _FactoryAction(
                    key: const Key('home-factory-video'),
                    icon: Icons.smart_display_outlined,
                    title: _t(context, 'Create Video', 'Video Üret'),
                    subtitle: _t(context, 'Scenario, shooting, editing',
                        'Senaryo, çekim, kurgu'),
                    onTap: () => onNavigate(DesktopSection.goals),
                  ),
                ),
                const SizedBox(height: 5),
                Expanded(
                  child: _FactoryAction(
                    key: const Key('home-factory-software'),
                    icon: Icons.code_rounded,
                    title: _t(context, 'Develop Software', 'Yazılım Geliştir'),
                    subtitle: _t(context, 'Application or tool', 'Uygulama veya araç'),
                    onTap: () => onNavigate(DesktopSection.goals),
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

class _HeroButton extends StatelessWidget {
  const _HeroButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.primary = false,
    super.key,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool primary;

  @override
  Widget build(BuildContext context) {
    if (primary) {
      return Expanded(
        child: FilledButton.icon(
          onPressed: onPressed,
          icon: Icon(icon, size: 15),
          label: Text(
            label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700),
          ),
          style: FilledButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 9),
          ),
        ),
      );
    }
    return Expanded(
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 14),
        label: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 9),
        ),
        style: OutlinedButton.styleFrom(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          foregroundColor: Theme.of(context).colorScheme.onSurfaceVariant,
          side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
      ),
    );
  }
}

class _FactoryAction extends StatelessWidget {
  const _FactoryAction({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
    super.key,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(7),
          side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Row(
              children: [
                Container(
                  width: 29,
                  height: 29,
                  decoration: BoxDecoration(
                    color: IlaiosTheme.enterpriseCyan.withValues(alpha: .10),
                    borderRadius: BorderRadius.circular(15),
                  ),
                  child: Icon(icon, size: 16, color: IlaiosTheme.enterpriseCyan),
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
                        style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700),
                      ),
                      Text(
                        subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.3),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right_rounded, size: 15),
              ],
            ),
          ),
        ),
      );
}

class _MetricsRow extends StatelessWidget {
  const _MetricsRow({required this.model});

  final _CommandCenterModel model;

  @override
  Widget build(BuildContext context) {
    final health = model.healthPercent;
    final metrics = <_MetricData>[
      _MetricData(
        title: _t(context, 'Ongoing Work', 'Devam Eden İşler'),
        value: model.runningWorkCount?.toString() ?? '—',
        footnote: _t(context, 'Authoritative active work', 'Doğrulanmış aktif işler'),
        icon: Icons.folder_open_rounded,
        accent: IlaiosTheme.enterpriseCyan,
      ),
      _MetricData(
        title: _t(context, 'Needs Attention', 'Müdahale Gerektiren'),
        value: model.pendingApprovalCount?.toString() ?? '—',
        footnote: _t(context, 'Governed approvals', 'Yönetişim onayları'),
        icon: Icons.shield_outlined,
        accent: IlaiosTheme.danger,
      ),
      _MetricData(
        title: _t(context, 'Active Agents', 'Aktif Ajanlar'),
        value: model.activeAgentCount?.toString() ?? '—',
        footnote: _t(context, 'Scheduler leases', 'Zamanlayıcı kiralamaları'),
        icon: Icons.groups_2_outlined,
        accent: IlaiosTheme.enterpriseCyan,
      ),
      _MetricData(
        title: _t(context, "Today's Cost", 'Bugünkü Harcama'),
        value: model.totalCost ?? '—',
        footnote: _t(context, 'Authoritative cost', 'Doğrulanmış maliyet'),
        icon: Icons.account_balance_wallet_outlined,
        accent: IlaiosTheme.coreBlue,
      ),
      _MetricData(
        title: _t(context, 'System Health', 'Sistem Sağlığı'),
        value: health == null
            ? (model.projection.connected
                ? _t(context, 'Connected', 'Bağlı')
                : _t(context, 'Offline', 'Çevrimdışı'))
            : '${health.round()}%',
        footnote: model.status,
        icon: Icons.verified_user_outlined,
        accent: IlaiosTheme.success,
        progress: health == null ? null : health / 100,
      ),
    ];

    return Row(
      key: const Key('command-center-metrics'),
      children: [
        for (var index = 0; index < metrics.length; index++) ...[
          Expanded(child: _MetricCard(data: metrics[index])),
          if (index < metrics.length - 1) const SizedBox(width: 6),
        ],
      ],
    );
  }
}

class _MetricData {
  const _MetricData({
    required this.title,
    required this.value,
    required this.footnote,
    required this.icon,
    required this.accent,
    this.progress,
  });

  final String title;
  final String value;
  final String footnote;
  final IconData icon;
  final Color accent;
  final double? progress;
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.data});
  final _MetricData data;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.fromLTRB(10, 8, 9, 7),
        decoration: _panel(context),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Row(
                    children: [
                      Icon(data.icon, size: 16, color: data.accent),
                      const SizedBox(width: 6),
                      Expanded(
                        child: Text(
                          data.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w600),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 4),
                  Text(
                    data.value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 17, height: 1, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    data.footnote,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.0),
                  ),
                ],
              ),
            ),
            if (data.progress != null) ...[
              const SizedBox(width: 7),
              SizedBox(
                width: 35,
                height: 35,
                child: CircularProgressIndicator(
                  value: data.progress,
                  strokeWidth: 4,
                  color: data.accent,
                ),
              ),
            ],
          ],
        ),
      );
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
                    style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w700)),
                Text(subtitle, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.0)),
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
                          style: const TextStyle(fontSize: 7.8)),
                    ),
                    Text(phase, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 7.0)),
                  ],
                ),
                const SizedBox(height: 3),
                ClipRRect(
                  borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(
                    value: progress ?? 0,
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
                        style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w700)),
                    Text(data.subtitle, maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.0)),
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
            flex: 40,
            child: _ArtifactsPanel(model: model, onNavigate: onNavigate),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 30,
            child: _CompletedPanel(model: model, onNavigate: onNavigate),
          ),
          const SizedBox(width: 8),
          Expanded(
            flex: 30,
            child: _QuickActionsPanel(onNavigate: onNavigate),
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
                      style: const TextStyle(fontSize: 8.1, fontWeight: FontWeight.w700)),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(record.executionId, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 7)),
            Text(_short(record.artifactDigest), maxLines: 1, overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 7)),
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
                      style: const TextStyle(fontSize: 8.4, fontWeight: FontWeight.w700)),
                  Text(record.executionId, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 7.1)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _QuickActionsPanel extends StatelessWidget {
  const _QuickActionsPanel({required this.onNavigate});
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final actions = <(IconData, String, DesktopSection)>[
      (Icons.account_tree_outlined, _t(context, 'Create New Workflow', 'Yeni İş Akışı Oluştur'), DesktopSection.workflows),
      (Icons.group_add_outlined, _t(context, 'Add or Manage Agent', 'Ajan Ekle veya Yönet'), DesktopSection.agents),
      (Icons.library_books_outlined, _t(context, 'Start From Templates', 'Şablonlardan Başlat'), DesktopSection.goals),
      (Icons.analytics_outlined, _t(context, 'Create Report & Analysis', 'Rapor & Analiz Oluştur'), DesktopSection.evidence),
      (Icons.account_balance_wallet_outlined, _t(context, 'Budget & Usage Details', 'Bütçe ve Kullanım Detayları'), DesktopSection.costs),
    ];
    return _SectionPanel(
      key: const Key('command-center-quick-actions'),
      title: _t(context, 'QUICK ACTIONS', 'HIZLI İŞLEMLER'),
      child: Column(
        children: [
          for (var index = 0; index < actions.length; index++)
            Expanded(
              child: Material(
                color: Colors.transparent,
                child: InkWell(
                  key: ValueKey('home-quick-${actions[index].$3.name}-$index'),
                  onTap: () => onNavigate(actions[index].$3),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8),
                    child: Row(
                      children: [
                        Icon(actions[index].$1, size: 14),
                        const SizedBox(width: 7),
                        Expanded(
                          child: Text(actions[index].$2, maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 8.2)),
                        ),
                        const Icon(Icons.chevron_right_rounded, size: 14),
                      ],
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _RightRail extends StatelessWidget {
  const _RightRail({
    required this.model,
    required this.onNavigate,
    required this.onRefreshRequested,
  });

  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Expanded(
            flex: 10,
            child: _SessionCard(
              model: model,
              onManage: () => onNavigate(DesktopSection.settings),
            ),
          ),
          const SizedBox(height: 7),
          Expanded(
            flex: 13,
            child: _ActivitiesCard(
              model: model,
              onRefreshRequested: onRefreshRequested,
              onOpen: () => onNavigate(DesktopSection.workflows),
            ),
          ),
          const SizedBox(height: 7),
          Expanded(
            flex: 8,
            child: _AlertsCard(
              model: model,
              onNavigate: onNavigate,
            ),
          ),
        ],
      );
}

class _SessionCard extends StatelessWidget {
  const _SessionCard({required this.model, required this.onManage});
  final _CommandCenterModel model;
  final VoidCallback onManage;

  @override
  Widget build(BuildContext context) {
    final active = model.userSession != null;
    final badge = active
        ? _t(context, 'ACTIVE', 'AKTİF')
        : (model.projection.connected
            ? _t(context, 'CONNECTED', 'BAĞLI')
            : _t(context, 'OFFLINE', 'ÇEVRİMDIŞI'));
    return Container(
      key: const Key('command-center-session'),
      padding: const EdgeInsets.fromLTRB(11, 9, 11, 8),
      decoration: _panel(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(_t(context, 'SESSION STATUS', 'OTURUM DURUMU'),
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800)),
              ),
              _StatusPill(label: badge, positive: model.projection.connected),
            ],
          ),
          const SizedBox(height: 5),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _InfoRow(label: _t(context, 'Session ID', 'Oturum ID'), value: model.sessionId),
                _InfoRow(label: _t(context, 'Elapsed', 'Süre'), value: model.elapsed),
                _InfoRow(label: _t(context, 'Owner', 'Sahip'), value: model.owner),
                _InfoRow(label: _t(context, 'Role', 'Rol'), value: model.role),
                _InfoRow(
                  label: _t(context, 'Connected Agents', 'Bağlı Ajanlar'),
                  value: model.activeAgentCount?.toString() ?? '—',
                ),
                _InfoRow(label: _t(context, 'Last Save', 'Son Kaydetme'), value: model.lastSaved),
              ],
            ),
          ),
          TextButton.icon(
            onPressed: onManage,
            icon: const Icon(Icons.settings_outlined, size: 13),
            label: Text(_t(context, 'Manage Session', 'Oturumu Yönet'),
                style: const TextStyle(fontSize: 8.4)),
            style: TextButton.styleFrom(alignment: Alignment.centerLeft, padding: EdgeInsets.zero),
          ),
        ],
      ),
    );
  }
}

class _ActivitiesCard extends StatelessWidget {
  const _ActivitiesCard({
    required this.model,
    required this.onRefreshRequested,
    required this.onOpen,
  });

  final _CommandCenterModel model;
  final VoidCallback? onRefreshRequested;
  final VoidCallback onOpen;

  @override
  Widget build(BuildContext context) {
    final events = model.recentActivities;
    return Container(
      key: const Key('command-center-activities'),
      padding: const EdgeInsets.fromLTRB(11, 9, 11, 8),
      decoration: _panel(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(_t(context, 'RECENT ACTIVITY', 'SON ETKİNLİKLER'),
                    style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800)),
              ),
              IconButton(
                tooltip: _t(context, 'Refresh', 'Yenile'),
                onPressed: onRefreshRequested,
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.refresh_rounded, size: 15),
              ),
            ],
          ),
          Expanded(
            child: events.isEmpty
                ? _EmptyState(
                    icon: Icons.history_rounded,
                    label: _t(context, 'No live activity is available.',
                        'Canlı etkinlik kaydı bulunmuyor.'),
                  )
                : ListView.builder(
                    padding: EdgeInsets.zero,
                    physics: const ClampingScrollPhysics(),
                    itemCount: events.length,
                    itemBuilder: (context, index) => _ActivityRow(event: events[index]),
                  ),
          ),
          TextButton(
            onPressed: onOpen,
            child: Text(_t(context, 'View all activity', 'Tüm aktiviteleri görüntüle'),
                style: const TextStyle(fontSize: 8.2)),
          ),
        ],
      ),
    );
  }
}

class _ActivityRow extends StatelessWidget {
  const _ActivityRow({required this.event});
  final Map<String, Object?> event;

  @override
  Widget build(BuildContext context) {
    final title = _text(event, const ['message', 'event_type', 'type', 'status']) ?? '—';
    final time = _text(event, const ['timestamp', 'updated_at', 'time']) ?? '—';
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 3),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 48,
            child: Text(time, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 7)),
          ),
          const SizedBox(width: 5),
          Expanded(
            child: Text(title, maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 8.0, height: 1.2)),
          ),
          const SizedBox(width: 4),
          const Padding(
            padding: EdgeInsets.only(top: 3),
            child: Icon(Icons.circle, size: 5, color: IlaiosTheme.success),
          ),
        ],
      ),
    );
  }
}

class _AlertsCard extends StatelessWidget {
  const _AlertsCard({required this.model, required this.onNavigate});
  final _CommandCenterModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final alerts = model.attentionItems.take(3).toList(growable: false);
    return Container(
      key: const Key('command-center-alerts'),
      padding: const EdgeInsets.fromLTRB(11, 9, 11, 8),
      decoration: _panel(context),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(_t(context, 'ALERTS', 'UYARILAR'),
              style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800)),
          const SizedBox(height: 5),
          Expanded(
            child: alerts.isEmpty
                ? _EmptyState(
                    icon: Icons.notifications_none_rounded,
                    label: _t(context, 'No verified alert is active.',
                        'Doğrulanmış aktif uyarı bulunmuyor.'),
                  )
                : Column(
                    children: [
                      for (final alert in alerts)
                        Expanded(
                          child: Material(
                            color: Colors.transparent,
                            child: InkWell(
                              onTap: () => onNavigate(alert.destination),
                              child: Row(
                                children: [
                                  Icon(
                                    Icons.circle,
                                    size: 8,
                                    color: alert.severity == _AttentionSeverity.critical
                                        ? IlaiosTheme.danger
                                        : IlaiosTheme.warning,
                                  ),
                                  const SizedBox(width: 7),
                                  Expanded(
                                    child: Text(alert.title, maxLines: 1, overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(fontSize: 8.1)),
                                  ),
                                  const Icon(Icons.chevron_right_rounded, size: 13),
                                ],
                              ),
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
                          style: const TextStyle(fontSize: 9.6, fontWeight: FontWeight.w800)),
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
                            Text(actionLabel!, style: const TextStyle(fontSize: 8.1)),
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
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.4)),
            ],
          ),
        ),
      );
}

class _InfoRow extends StatelessWidget {
  const _InfoRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.3)),
          ),
          const SizedBox(width: 6),
          Flexible(
            child: Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 8.4, fontWeight: FontWeight.w600)),
          ),
        ],
      );
}

class _StatusPill extends StatelessWidget {
  const _StatusPill({required this.label, required this.positive});
  final String label;
  final bool positive;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: (positive ? IlaiosTheme.success : Theme.of(context).colorScheme.outline)
              .withValues(alpha: .12),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Text(
          label,
          style: TextStyle(
            fontSize: 7.2,
            fontWeight: FontWeight.w800,
            color: positive ? IlaiosTheme.success : Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );
}

class _OrbitCorePainter extends CustomPainter {
  const _OrbitCorePainter({required this.line, required this.faint});

  final Color line;
  final Color faint;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height * .57);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.2
      ..color = faint;
    for (final scale in <double>[.34, .52, .72, .92]) {
      canvas.drawOval(
        Rect.fromCenter(
          center: center,
          width: size.width * scale,
          height: size.height * scale * .38,
        ),
        paint,
      );
    }
    paint.color = line;
    paint.strokeWidth = 1.4;
    canvas.drawLine(Offset(center.dx, size.height * .10), Offset(center.dx, size.height * .79), paint);
    canvas.drawCircle(center, 4, Paint()..color = line.withValues(alpha: .65));

    final cubeCenter = Offset(center.dx, size.height * .31);
    final r = math.min(size.width, size.height) * .105;
    final top = Offset(cubeCenter.dx, cubeCenter.dy - r);
    final left = Offset(cubeCenter.dx - r * .86, cubeCenter.dy - r * .5);
    final right = Offset(cubeCenter.dx + r * .86, cubeCenter.dy - r * .5);
    final bottom = Offset(cubeCenter.dx, cubeCenter.dy + r);
    final mid = Offset(cubeCenter.dx, cubeCenter.dy);
    final cubePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6
      ..color = line;
    canvas.drawLine(top, left, cubePaint);
    canvas.drawLine(top, right, cubePaint);
    canvas.drawLine(left, mid, cubePaint);
    canvas.drawLine(right, mid, cubePaint);
    canvas.drawLine(mid, bottom, cubePaint);
    canvas.drawLine(left, Offset(left.dx, bottom.dy - r * .5), cubePaint);
    canvas.drawLine(right, Offset(right.dx, bottom.dy - r * .5), cubePaint);
    canvas.drawLine(Offset(left.dx, bottom.dy - r * .5), bottom, cubePaint);
    canvas.drawLine(Offset(right.dx, bottom.dy - r * .5), bottom, cubePaint);
  }

  @override
  bool shouldRepaint(covariant _OrbitCorePainter oldDelegate) =>
      oldDelegate.line != line || oldDelegate.faint != faint;
}

class _Tone {
  const _Tone({required this.dark, required this.accent});
  final bool dark;
  final Color accent;

  static _Tone of(BuildContext context) => _Tone(
        dark: Theme.of(context).brightness == Brightness.dark,
        accent: IlaiosTheme.enterpriseCyan,
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
