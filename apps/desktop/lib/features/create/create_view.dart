import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';

/// Reference-faithful Goals surface.
///
/// The supplied screenshots are used only as layout/theme references. Values
/// rendered here come from the authoritative ControlPlaneProjection or from a
/// PromptSubmission returned by the configured control-plane callback. Missing
/// goal detail is shown as unavailable instead of being fabricated from the
/// reference images.
class CreateView extends StatefulWidget {
  const CreateView({
    required this.projection,
    required this.status,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.onSignIn,
    this.onLogout,
    this.onSubmit,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String status;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onSubmit;

  @override
  State<CreateView> createState() => _CreateViewState();
}

class _CreateViewState extends State<CreateView> {
  final TextEditingController _controller = TextEditingController();
  bool _submitting = false;
  PromptSubmission? _submission;
  String? _submittedObjective;
  String? _error;
  String _activeTab = 'all';

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final callback = widget.onSubmit;
    if (callback == null || _submitting || !widget.projection.connected) return;
    final objective = _controller.text.trim();
    if (objective.isEmpty) {
      setState(() {
        _submission = null;
        _error = _copy(
          context,
          'Describe what should be built before starting.',
          'Başlatmadan önce oluşturulacak hedefi yazın.',
        );
      });
      return;
    }
    setState(() {
      _submitting = true;
      _submission = null;
      _submittedObjective = null;
      _error = null;
    });
    try {
      final result = await callback(objective);
      if (!mounted) return;
      setState(() {
        _submission = result;
        _submittedObjective = objective;
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final connected = widget.projection.connected;
    final goalCount = widget.projection.goalCount;
    final owner = widget.userSession?.displayIdentity ??
        widget.userSession?.principalId ??
        _copy(context, 'Current user', 'Mevcut kullanıcı');

    return Container(
      key: const Key('reference-goals-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(18, 10, 18, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _GoalsHeader(
            controller: _controller,
            enabled: connected && widget.onSubmit != null,
            submitting: _submitting,
            onSubmit: _submit,
          ),
          const SizedBox(height: 8),
          _MetricStrip(
            goalCount: goalCount,
            lastEvent: widget.projection.lastEvent,
          ),
          const SizedBox(height: 8),
          _GoalTabs(
            activeTab: _activeTab,
            onChanged: (value) => setState(() => _activeTab = value),
          ),
          const SizedBox(height: 6),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final showRightRail = constraints.maxWidth >= 1080;
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(
                            child: _GoalsTable(
                              submission: _submission,
                              objective: _submittedObjective,
                              owner: owner,
                              activeTab: _activeTab,
                            ),
                          ),
                          const SizedBox(height: 8),
                          SizedBox(
                            height: 152,
                            child: Row(
                              children: [
                                Expanded(
                                  child: _InfoCard(
                                    title: _copy(context, 'Recent Updates', 'Son Güncellemeler'),
                                    trailing: _copy(context, 'All ›', 'Tümü ›'),
                                    child: _RecentUpdates(
                                      lastEvent: widget.projection.lastEvent,
                                      submission: _submission,
                                      objective: _submittedObjective,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: _InfoCard(
                                    title: _copy(context, 'Critical Blockers', 'Kritik Engeller'),
                                    trailing: _copy(context, 'All ›', 'Tümü ›'),
                                    child: const _UnavailablePanel(
                                      icon: Icons.warning_amber_rounded,
                                    ),
                                  ),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: _InfoCard(
                                    key: const Key('goals-distribution'),
                                    title: _copy(context, 'Goal Distribution', 'Hedef Dağılımı'),
                                    trailing: _copy(context, 'All ›', 'Tümü ›'),
                                    child: _Distribution(goalCount: goalCount),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                    if (showRightRail) ...[
                      const SizedBox(width: 12),
                      SizedBox(
                        width: 390,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(
                              child: _SelectedGoal(
                                submission: _submission,
                                objective: _submittedObjective,
                                owner: owner,
                              ),
                            ),
                            const SizedBox(height: 8),
                            SizedBox(
                              height: 164,
                              child: _InfoCard(
                                title: _copy(context, 'Upcoming Deliveries', 'Yaklaşan Teslimler'),
                                trailing: _copy(context, 'All ›', 'Tümü ›'),
                                child: const _UnavailablePanel(
                                  icon: Icons.calendar_month_outlined,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                );
              },
            ),
          ),
          if (_submission != null || _error != null) ...[
            const SizedBox(height: 6),
            _SubmissionStatus(
              submission: _submission,
              error: _error,
            ),
          ],
        ],
      ),
    );
  }
}

class _GoalsHeader extends StatelessWidget {
  const _GoalsHeader({
    required this.controller,
    required this.enabled,
    required this.submitting,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool enabled;
  final bool submitting;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 58,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _copy(context, 'Goals', 'Hedefler'),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _copy(
                      context,
                      'Track strategic goals, OKRs and progress.',
                      'Stratejik hedefleri, OKR’leri ve ilerleme durumlarını izleyin.',
                    ),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 10.2),
                  ),
                ],
              ),
            ),
            SizedBox(
              width: 300,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _copy(
                      context,
                      'What do you want ILAIOS to build?',
                      'ILAIOS’un ne oluşturmasını istiyorsunuz?',
                    ),
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.2),
                  ),
                  const SizedBox(height: 3),
                  SizedBox(
                    height: 32,
                    child: TextField(
                      key: const Key('one-prompt-input'),
                      controller: controller,
                      enabled: enabled,
                      onSubmitted: enabled && !submitting ? (_) => onSubmit() : null,
                      decoration: InputDecoration(
                        isDense: true,
                        hintText: _copy(context, 'Describe a new goal…', 'Yeni hedefi tanımlayın…'),
                        prefixIcon: const Icon(Icons.track_changes_outlined, size: 16),
                        contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
                      ),
                      style: const TextStyle(fontSize: 10.5),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            _HeaderButton(
              icon: Icons.filter_alt_outlined,
              label: _copy(context, 'Filter', 'Filtrele'),
              onPressed: () {},
            ),
            const SizedBox(width: 8),
            _HeaderButton(
              icon: Icons.download_outlined,
              label: _copy(context, 'Export', 'Dışa Aktar'),
              onPressed: () {},
            ),
            const SizedBox(width: 8),
            SizedBox(
              height: 34,
              child: FilledButton.icon(
                key: const Key('one-prompt-submit'),
                onPressed: enabled && !submitting ? onSubmit : null,
                icon: submitting
                    ? const SizedBox(
                        width: 13,
                        height: 13,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.add_rounded, size: 18),
                label: Text(
                  submitting
                      ? _copy(context, 'Submitting…', 'Gönderiliyor…')
                      : _copy(context, 'New Goal', 'Yeni Hedef'),
                ),
                style: FilledButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 15),
                  textStyle: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600),
                ),
              ),
            ),
          ],
        ),
      );
}

class _HeaderButton extends StatelessWidget {
  const _HeaderButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 34,
        child: OutlinedButton.icon(
          onPressed: onPressed,
          icon: Icon(icon, size: 16),
          label: Text(label),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 13),
            textStyle: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w600),
          ),
        ),
      );
}

class _MetricStrip extends StatelessWidget {
  const _MetricStrip({required this.goalCount, required this.lastEvent});

  final int? goalCount;
  final String? lastEvent;

  @override
  Widget build(BuildContext context) {
    final metrics = <({IconData icon, Color color, String label, String value, String note})>[
      (
        icon: Icons.track_changes_outlined,
        color: IlaiosTheme.coreBlue,
        label: _copy(context, 'Total Goals', 'Toplam Hedef'),
        value: goalCount?.toString() ?? '—',
        note: _copy(context, 'Authoritative projection', 'Yetkili projeksiyon'),
      ),
      (
        icon: Icons.trending_up_rounded,
        color: IlaiosTheme.success,
        label: _copy(context, 'On Track', 'Yolda'),
        value: '—',
        note: _copy(context, 'Detail unavailable', 'Ayrıntı kullanılamıyor'),
      ),
      (
        icon: Icons.warning_amber_rounded,
        color: IlaiosTheme.warning,
        label: _copy(context, 'At Risk', 'Riskte'),
        value: '—',
        note: _copy(context, 'Detail unavailable', 'Ayrıntı kullanılamıyor'),
      ),
      (
        icon: Icons.check_circle_outline_rounded,
        color: IlaiosTheme.success,
        label: _copy(context, 'Completed', 'Tamamlanan'),
        value: '—',
        note: _copy(context, 'Detail unavailable', 'Ayrıntı kullanılamıyor'),
      ),
      (
        icon: Icons.insights_outlined,
        color: const Color(0xFF9C5CFF),
        label: _copy(context, 'Average Progress', 'Ortalama İlerleme'),
        value: '—',
        note: _copy(context, 'Detail unavailable', 'Ayrıntı kullanılamıyor'),
      ),
      (
        icon: Icons.calendar_month_outlined,
        color: IlaiosTheme.coreBlue,
        label: _copy(context, 'Last Update', 'Son Güncelleme'),
        value: lastEvent?.trim().isNotEmpty == true ? lastEvent!.trim() : '—',
        note: _copy(context, 'Authoritative event', 'Yetkili olay'),
      ),
    ];

    return SizedBox(
      key: const Key('goals-kpis'),
      height: 82,
      child: Row(
        children: [
          for (var index = 0; index < metrics.length; index++) ...[
            if (index > 0) const SizedBox(width: 8),
            Expanded(child: _MetricCard(metric: metrics[index])),
          ],
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.metric});

  final ({IconData icon, Color color, String label, String value, String note}) metric;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
        decoration: _cardDecoration(context, radius: 7),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: metric.color.withValues(alpha: .11),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Icon(metric.icon, color: metric.color, size: 22),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(metric.label, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.3)),
                  const SizedBox(height: 2),
                  Text(metric.value, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 17.5, fontWeight: FontWeight.w700, height: 1)),
                  const SizedBox(height: 4),
                  Text(metric.note, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 7.5, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
          ],
        ),
      );
}

class _GoalTabs extends StatelessWidget {
  const _GoalTabs({required this.activeTab, required this.onChanged});

  final String activeTab;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final tabs = <({String id, String label})>[
      (id: 'all', label: _copy(context, 'All', 'Tümü')),
      (id: 'strategic', label: _copy(context, 'Strategic', 'Stratejik')),
      (id: 'operational', label: _copy(context, 'Operational', 'Operasyonel')),
      (id: 'product', label: _copy(context, 'Product', 'Ürün')),
      (id: 'marketing', label: _copy(context, 'Marketing', 'Pazarlama')),
      (id: 'archive', label: _copy(context, 'Archive', 'Arşiv')),
    ];
    return SizedBox(
      key: const Key('goals-tabs'),
      height: 36,
      child: Row(
        children: [
          for (final tab in tabs)
            InkWell(
              onTap: () => onChanged(tab.id),
              child: Container(
                margin: const EdgeInsets.only(right: 5),
                padding: const EdgeInsets.symmetric(horizontal: 13),
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(
                      color: activeTab == tab.id ? IlaiosTheme.coreBlue : Colors.transparent,
                      width: 2,
                    ),
                  ),
                ),
                child: Text(
                  tab.label,
                  style: TextStyle(
                    fontSize: 10,
                    fontWeight: activeTab == tab.id ? FontWeight.w700 : FontWeight.w500,
                    color: activeTab == tab.id
                        ? IlaiosTheme.coreBlue
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _GoalsTable extends StatelessWidget {
  const _GoalsTable({
    required this.submission,
    required this.objective,
    required this.owner,
    required this.activeTab,
  });

  final PromptSubmission? submission;
  final String? objective;
  final String owner;
  final String activeTab;

  @override
  Widget build(BuildContext context) {
    final showSubmission = submission != null && activeTab != 'archive';
    return Container(
      key: const Key('goals-table'),
      decoration: _cardDecoration(context, radius: 7),
      clipBehavior: Clip.antiAlias,
      child: Column(
        children: [
          Container(
            height: 34,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            color: Theme.of(context).colorScheme.surfaceContainerLow,
            child: const Row(
              children: [
                Expanded(flex: 31, child: _TableHeader('Goal')),
                Expanded(flex: 17, child: _TableHeader('Owner')),
                Expanded(flex: 22, child: _TableHeader('Progress')),
                Expanded(flex: 12, child: _TableHeader('Status')),
                Expanded(flex: 12, child: _TableHeader('Target')),
                Expanded(flex: 10, child: _TableHeader('Priority')),
                SizedBox(width: 22),
              ],
            ),
          ),
          if (showSubmission)
            _GoalRow(
              submission: submission!,
              objective: objective ?? submission!.goalId,
              owner: owner,
            )
          else
            Expanded(
              child: Center(
                child: Padding(
                  padding: const EdgeInsets.all(22),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(Icons.track_changes_outlined,
                          size: 34, color: Theme.of(context).colorScheme.outline),
                      const SizedBox(height: 8),
                      Text(
                        _copy(
                          context,
                          'Detailed goal records are not exposed by the current authoritative projection.',
                          'Ayrıntılı hedef kayıtları mevcut yetkili projeksiyon tarafından sunulmuyor.',
                        ),
                        textAlign: TextAlign.center,
                        style: TextStyle(
                          fontSize: 10,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          Container(
            height: 38,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              border: Border(top: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    showSubmission
                        ? _copy(context, 'Showing 1 authoritative goal.', '1 yetkili hedef gösteriliyor.')
                        : _copy(context, 'No detailed goal rows available.', 'Ayrıntılı hedef satırı bulunmuyor.'),
                    style: TextStyle(fontSize: 8.7, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
                ),
                _PageBox(label: '1', selected: true),
                const SizedBox(width: 7),
                _PageBox(label: _copy(context, '10 / page', '10 / sayfa')),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _TableHeader extends StatelessWidget {
  const _TableHeader(this.label);
  final String label;

  @override
  Widget build(BuildContext context) => Text(
        label,
        style: TextStyle(
          fontSize: 8.5,
          fontWeight: FontWeight.w600,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
      );
}

class _GoalRow extends StatelessWidget {
  const _GoalRow({required this.submission, required this.objective, required this.owner});

  final PromptSubmission submission;
  final String objective;
  final String owner;

  @override
  Widget build(BuildContext context) {
    final state = submission.state.toUpperCase();
    final completed = state == 'COMPLETED' || state == 'SUCCEEDED' || state == 'FINISHED';
    final active = state == 'RUNNING' || state == 'PENDING' || state == 'QUEUED';
    final progress = completed ? 1.0 : (active ? 0.0 : 0.0);
    final statusColor = completed
        ? IlaiosTheme.success
        : active
            ? IlaiosTheme.coreBlue
            : Theme.of(context).colorScheme.outline;

    return Container(
      height: 56,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        color: IlaiosTheme.coreBlue.withValues(alpha: .045),
        border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
      ),
      child: Row(
        children: [
          Expanded(
            flex: 31,
            child: Row(
              children: [
                Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: IlaiosTheme.coreBlue.withValues(alpha: .10),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: const Icon(Icons.track_changes_outlined, size: 17, color: IlaiosTheme.coreBlue),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(objective, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w600)),
                      const SizedBox(height: 2),
                      Text(submission.goalId, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 8.2, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(flex: 17, child: Text(owner, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 9.4))),
          Expanded(
            flex: 22,
            child: Row(
              children: [
                Expanded(
                  child: LinearProgressIndicator(
                    value: progress,
                    minHeight: 4,
                    borderRadius: BorderRadius.circular(4),
                    backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                  ),
                ),
                const SizedBox(width: 8),
                Text(completed ? '100%' : '0%', style: const TextStyle(fontSize: 9)),
              ],
            ),
          ),
          Expanded(
            flex: 12,
            child: Align(
              alignment: Alignment.centerLeft,
              child: _Pill(label: submission.state, color: statusColor),
            ),
          ),
          const Expanded(flex: 12, child: Text('—', style: TextStyle(fontSize: 9.2))),
          const Expanded(flex: 10, child: Text('—', style: TextStyle(fontSize: 9.2))),
          const SizedBox(width: 22, child: Icon(Icons.more_vert, size: 16)),
        ],
      ),
    );
  }
}

class _SelectedGoal extends StatelessWidget {
  const _SelectedGoal({required this.submission, required this.objective, required this.owner});

  final PromptSubmission? submission;
  final String? objective;
  final String owner;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('goals-selected'),
        decoration: _cardDecoration(context, radius: 7),
        padding: const EdgeInsets.fromLTRB(13, 12, 13, 12),
        child: submission == null
            ? const _UnavailablePanel(icon: Icons.track_changes_outlined)
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(_copy(context, 'Selected Goal', 'Seçili Hedef'),
                      style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: IlaiosTheme.coreBlue.withValues(alpha: .10),
                          borderRadius: BorderRadius.circular(22),
                        ),
                        child: const Icon(Icons.track_changes_outlined,
                            color: IlaiosTheme.coreBlue, size: 23),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(objective ?? submission!.goalId,
                                maxLines: 2, overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
                            const SizedBox(height: 3),
                            Text('ID: ${submission!.goalId}',
                                maxLines: 1, overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontSize: 8.5,
                                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
                          ],
                        ),
                      ),
                      _Pill(label: submission!.state, color: IlaiosTheme.success),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                  const SizedBox(height: 10),
                  _DetailRow(label: _copy(context, 'Owner', 'Sahip'), value: owner),
                  const SizedBox(height: 7),
                  _DetailRow(label: _copy(context, 'Job', 'İş'), value: submission!.jobId),
                  const SizedBox(height: 7),
                  _DetailRow(label: _copy(context, 'Progress', 'İlerleme'), value: '—'),
                  const SizedBox(height: 10),
                  Text(_copy(context, 'OKR Summary', 'OKR Özeti'),
                      style: const TextStyle(fontSize: 9.4, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 5),
                  Text(
                    _copy(
                      context,
                      'Detailed OKR results are not exposed by the current authoritative projection.',
                      'Ayrıntılı OKR sonuçları mevcut yetkili projeksiyon tarafından sunulmuyor.',
                    ),
                    style: TextStyle(fontSize: 8.8,
                        color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
                  const Spacer(),
                  Container(
                    height: 36,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surfaceContainerLow,
                      borderRadius: BorderRadius.circular(5),
                      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                    ),
                    child: Text(
                      _copy(context, 'Authoritative details only', 'Yalnızca yetkili ayrıntılar'),
                      style: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
      );
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          SizedBox(
            width: 78,
            child: Text(label,
                style: TextStyle(fontSize: 8.6,
                    color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ),
          Expanded(
            child: Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 9.1, fontWeight: FontWeight.w600)),
          ),
        ],
      );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({
    required this.title,
    required this.trailing,
    required this.child,
    super.key,
  });

  final String title;
  final String trailing;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _cardDecoration(context, radius: 7),
        padding: const EdgeInsets.fromLTRB(11, 9, 11, 9),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(child: Text(title,
                    style: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w700))),
                Text(trailing,
                    style: const TextStyle(fontSize: 8.3, color: IlaiosTheme.coreBlue,
                        fontWeight: FontWeight.w600)),
              ],
            ),
            const SizedBox(height: 7),
            Expanded(child: child),
          ],
        ),
      );
}

class _RecentUpdates extends StatelessWidget {
  const _RecentUpdates({required this.lastEvent, required this.submission, required this.objective});

  final String? lastEvent;
  final PromptSubmission? submission;
  final String? objective;

  @override
  Widget build(BuildContext context) {
    final rows = <({IconData icon, String title, String detail})>[];
    if (submission != null) {
      rows.add((
        icon: Icons.track_changes_outlined,
        title: objective ?? submission!.goalId,
        detail: '${submission!.goalId} · ${submission!.state}',
      ));
    }
    if (lastEvent?.trim().isNotEmpty == true) {
      rows.add((
        icon: Icons.bolt_outlined,
        title: lastEvent!.trim(),
        detail: _copy(context, 'Authoritative event projection', 'Yetkili olay projeksiyonu'),
      ));
    }
    if (rows.isEmpty) return const _UnavailablePanel(icon: Icons.update_outlined);
    return Column(
      children: [
        for (final row in rows.take(3))
          Expanded(
            child: Row(
              children: [
                Icon(row.icon, size: 15, color: IlaiosTheme.coreBlue),
                const SizedBox(width: 7),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(row.title, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 8.9, fontWeight: FontWeight.w600)),
                      Text(row.detail, maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 7.6,
                              color: Theme.of(context).colorScheme.onSurfaceVariant)),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Distribution extends StatelessWidget {
  const _Distribution({required this.goalCount});
  final int? goalCount;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          SizedBox(
            width: 86,
            height: 86,
            child: Stack(
              alignment: Alignment.center,
              children: [
                SizedBox(
                  width: 78,
                  height: 78,
                  child: CircularProgressIndicator(
                    value: goalCount == null ? 0 : 1,
                    strokeWidth: 10,
                    backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                    color: goalCount == null ? Theme.of(context).colorScheme.outline : IlaiosTheme.coreBlue,
                  ),
                ),
                Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Text(goalCount?.toString() ?? '—',
                        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                    Text(_copy(context, 'Total', 'Toplam'), style: const TextStyle(fontSize: 7.5)),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 9),
          Expanded(
            child: Text(
              _copy(
                context,
                'Category distribution is not exposed by the authoritative projection.',
                'Kategori dağılımı yetkili projeksiyon tarafından sunulmuyor.',
              ),
              style: TextStyle(fontSize: 8.2,
                  color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
          ),
        ],
      );
}

class _UnavailablePanel extends StatelessWidget {
  const _UnavailablePanel({required this.icon});
  final IconData icon;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 22, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 5),
            Text(
              _copy(context, 'Authoritative detail unavailable', 'Yetkili ayrıntı kullanılamıyor'),
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 8.1,
                  color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      );
}

class _SubmissionStatus extends StatelessWidget {
  const _SubmissionStatus({required this.submission, required this.error});
  final PromptSubmission? submission;
  final String? error;

  @override
  Widget build(BuildContext context) {
    if (error != null) {
      return Container(
        key: const Key('goal-submit-error'),
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.errorContainer,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Text(error!, style: const TextStyle(fontSize: 9)),
      );
    }
    final value = submission;
    if (value == null) return const SizedBox.shrink();
    return Container(
      key: const Key('one-prompt-accepted'),
      padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
      decoration: BoxDecoration(
        color: IlaiosTheme.success.withValues(alpha: .08),
        border: Border.all(color: IlaiosTheme.success.withValues(alpha: .24)),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        children: [
          const Icon(Icons.check_circle_outline, size: 16, color: IlaiosTheme.success),
          const SizedBox(width: 8),
          Text('Goal: ${value.goalId}', style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w600)),
          const SizedBox(width: 14),
          Text('Job: ${value.jobId}', style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w600)),
          const SizedBox(width: 14),
          Text('Authoritative state: ${value.state}', style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w600)),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              _copy(
                context,
                'Desktop does not treat submission as completion; runtime evidence remains authoritative.',
                'Desktop gönderimi tamamlanmış saymaz; çalışma zamanı kanıtı yetkili olmaya devam eder.',
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 8.1,
                  color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
          ),
        ],
      ),
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(5),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 7.8, fontWeight: FontWeight.w700, color: color),
        ),
      );
}

class _PageBox extends StatelessWidget {
  const _PageBox({required this.label, this.selected = false});
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(minWidth: 27),
        height: 26,
        alignment: Alignment.center,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          color: selected ? IlaiosTheme.coreBlue.withValues(alpha: .10) : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: selected ? IlaiosTheme.coreBlue : Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: Text(label, style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600)),
      );
}

BoxDecoration _cardDecoration(BuildContext context, {double radius = 8}) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

String _copy(BuildContext context, String en, String tr) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish ? tr : en;
