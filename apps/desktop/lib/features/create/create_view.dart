import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../business_context/business_capability_context.dart';
import '../../control_plane/client.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'governed_lifecycle_projection.dart';
import 'reference_asset_picker.dart';

/// Reference-faithful Goals surface.
///
/// The supplied screenshots are layout/theme references only. Runtime values
/// come from the authoritative ControlPlaneProjection or from a PromptSubmission
/// returned by the control-plane callback. Missing goal detail is rendered as
/// unavailable instead of copying screenshot telemetry into production state.
class CreateView extends StatefulWidget {
  const CreateView({
    required this.projection,
    required this.status,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.onSignIn,
    this.onLogout,
    this.referenceAssets,
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
  final ReferenceAssetPickerController? referenceAssets;
  final Future<PromptSubmission> Function(String objective)? onSubmit;

  @override
  State<CreateView> createState() => _CreateViewState();
}

enum _FactoryPreset { web, video, software }

class _CreateViewState extends State<CreateView> {
  final TextEditingController _controller = TextEditingController();
  bool _submitting = false;
  PromptSubmission? _submission;
  String? _submittedObjective;
  String? _error;
  String _activeTab = 'all';
  _FactoryPreset? _selectedPreset;
  BusinessCapabilityFamily? _selectedBusinessCapability;

  @override
  void didUpdateWidget(covariant CreateView oldWidget) {
    super.didUpdateWidget(oldWidget);
    final sessionChanged =
        oldWidget.userSession?.sessionId != widget.userSession?.sessionId;
    if (sessionChanged ||
        (!widget.projection.connected && oldWidget.projection.connected)) {
      _submission = null;
      _submittedObjective = null;
      _error = null;
      _selectedBusinessCapability = null;
      BusinessCapabilitySubmissionBus.clear();
    }
  }

  @override
  void dispose() {
    BusinessCapabilitySubmissionBus.clear();
    _controller.dispose();
    super.dispose();
  }

  String _starterText(BuildContext context, _FactoryPreset preset) {
    final tr = _isTr(context);
    return switch (preset) {
      _FactoryPreset.web => tr
          ? 'Şirketim için premium, responsive bir web sitesi oluştur; test et ve bitmiş ürünü teslim et.'
          : 'Build a premium responsive website for my company, test it, and deliver the finished product.',
      _FactoryPreset.video => tr
          ? '20 saniyelik profesyonel bir ürün videosu oluştur, doğrula ve bitmiş videoyu teslim et.'
          : 'Create a professional 20-second product video, verify it, and deliver the finished video.',
      _FactoryPreset.software => tr
          ? 'İhtiyacımı karşılayan çalışan bir yazılım ürünü oluştur, test et ve doğrulanmış çıktıyı teslim et.'
          : 'Build a working software product for my requirement, test it, and deliver the verified output.',
    };
  }

  String _routePrefix(BuildContext context, _FactoryPreset preset) {
    final tr = _isTr(context);
    return switch (preset) {
      _FactoryPreset.web =>
        tr ? 'Web sitesi oluşturma görevi:' : 'Website build task:',
      _FactoryPreset.video =>
        tr ? 'Video oluşturma görevi:' : 'Video creation task:',
      _FactoryPreset.software =>
        tr ? 'Yazılım oluşturma görevi:' : 'Software build task:',
    };
  }

  String _presetLabel(BuildContext context, _FactoryPreset preset) =>
      switch (preset) {
        _FactoryPreset.web => 'Web Factory',
        _FactoryPreset.video => 'Video Factory',
        _FactoryPreset.software => 'Software Factory',
      };

  String _businessCapabilityLabel(
    BuildContext context,
    BusinessCapabilityFamily family,
  ) => switch (family) {
    BusinessCapabilityFamily.executiveEnterpriseIntelligence =>
      _copy(context, 'Executive', 'Yönetim'),
    BusinessCapabilityFamily.operations =>
      _copy(context, 'Operations', 'Operasyon'),
    BusinessCapabilityFamily.financeCostIntelligence =>
      _copy(context, 'Finance', 'Finans'),
    BusinessCapabilityFamily.growthMarketing =>
      _copy(context, 'Growth', 'Büyüme'),
    BusinessCapabilityFamily.commerceSales =>
      _copy(context, 'Commerce', 'Ticaret'),
    BusinessCapabilityFamily.researchData =>
      _copy(context, 'Research', 'Araştırma'),
  };

  void _selectPreset(_FactoryPreset preset) {
    final current = _controller.text.trim();
    final starterTexts = _FactoryPreset.values
        .map((item) => _starterText(context, item))
        .toSet();
    final shouldReplace = current.isEmpty || starterTexts.contains(current);
    setState(() {
      _selectedPreset = preset;
      _submission = null;
      _submittedObjective = null;
      _error = null;
      if (shouldReplace) {
        final text = _starterText(context, preset);
        _controller.text = text;
        _controller.selection = TextSelection.collapsed(offset: text.length);
      }
    });
  }

  void _selectBusinessCapability(BusinessCapabilityFamily? family) {
    setState(() {
      _selectedBusinessCapability = family;
      _submission = null;
      _submittedObjective = null;
      _error = null;
    });
    BusinessCapabilitySubmissionBus.clear();
  }

  Future<void> _submit() async {
    final callback = widget.onSubmit;
    if (callback == null || _submitting || !widget.projection.connected) return;
    final rawObjective = _controller.text.trim();
    if (rawObjective.isEmpty) {
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
    final preset = _selectedPreset;
    final objective = preset == null
        ? rawObjective
        : '${_routePrefix(context, preset)} $rawObjective';
    final family = _selectedBusinessCapability;
    BusinessCapabilitySubmissionBus.stage(
      family == null ? null : BusinessCapabilityContext(family),
    );
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
        _submittedObjective = rawObjective;
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      BusinessCapabilitySubmissionBus.clear();
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
    final governedSubmission = _submission is GovernedPromptSubmission
        ? _submission! as GovernedPromptSubmission
        : null;
    final lifecycle = governedSubmission == null
        ? GovernedLifecycleState.unavailable
        : resolveGovernedLifecycle(
            GovernedLifecycleProjectionStore.snapshot,
            governedSubmission.requestId,
            admittedStatus: governedSubmission.executionStatus,
          );

    return Container(
      key: const Key('reference-goals-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(18, 10, 18, 10),
      child: CustomScrollView(
        key: const Key('goals-content-scroll'),
        slivers: [
          SliverToBoxAdapter(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _GoalsHeader(
                  controller: _controller,
                  enabled: connected && widget.onSubmit != null,
                  submitting: _submitting,
                  selectedPreset: _selectedPreset,
                  selectedBusinessCapability: _selectedBusinessCapability,
                  referenceAssets: widget.referenceAssets,
                  presetLabel: (preset) => _presetLabel(context, preset),
                  businessCapabilityLabel: (family) =>
                      _businessCapabilityLabel(context, family),
                  onPresetChanged: _selectPreset,
                  onBusinessCapabilityChanged: _selectBusinessCapability,
                  onSubmit: _submit,
                ),
                if (goalCount != null && goalCount > 0) ...[
                  const SizedBox(height: 8),
                  _MetricStrip(
                    goalCount: goalCount,
                    lastEvent: widget.projection.lastEvent,
                  ),
                ],
                const SizedBox(height: 8),
                _GoalTabs(
                  activeTab: _activeTab,
                  onChanged: (value) => setState(() => _activeTab = value),
                ),
                const SizedBox(height: 6),
                if (_submission != null || _error != null) ...[
                  const SizedBox(height: 6),
                  _SubmissionStatus(
                    submission: _submission,
                    error: _error,
                    lifecycle: lifecycle,
                  ),
                ],
              ],
            ),
          ),
          SliverToBoxAdapter(
            child: SizedBox(
              height: (MediaQuery.sizeOf(context).height * 0.55)
                  .clamp(360.0, 640.0)
                  .toDouble(),
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
                            ],
                          ),
                        ),
                        if (showRightRail && _submission != null) ...[
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
                              ],
                            ),
                          ),
                        ],
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

class _GoalsHeader extends StatelessWidget {
  const _GoalsHeader({
    required this.controller,
    required this.enabled,
    required this.submitting,
    required this.selectedPreset,
    required this.selectedBusinessCapability,
    required this.referenceAssets,
    required this.presetLabel,
    required this.businessCapabilityLabel,
    required this.onPresetChanged,
    required this.onBusinessCapabilityChanged,
    required this.onSubmit,
  });

  final TextEditingController controller;
  final bool enabled;
  final bool submitting;
  final _FactoryPreset? selectedPreset;
  final BusinessCapabilityFamily? selectedBusinessCapability;
  final ReferenceAssetPickerController? referenceAssets;
  final String Function(_FactoryPreset preset) presetLabel;
  final String Function(BusinessCapabilityFamily family) businessCapabilityLabel;
  final ValueChanged<_FactoryPreset> onPresetChanged;
  final ValueChanged<BusinessCapabilityFamily?> onBusinessCapabilityChanged;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) => Container(
    key: const Key('goals-composer'),
    padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
    decoration: BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      borderRadius: BorderRadius.circular(8),
    ),
    child: Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          width: 205,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _copy(context, 'Goals', 'Hedefler'),
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                _copy(
                  context,
                  'Create and manage governed goals from one prompt.',
                  'Tek bir komutla yönetişimli hedef oluşturun ve yönetin.',
                ),
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                _copy(
                  context,
                  'What do you want ILAIOS to build?',
                  'ILAIOS’un ne oluşturmasını istiyorsun?',
                ),
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 6),
              TextField(
                key: const Key('one-prompt-input'),
                controller: controller,
                enabled: enabled,
                minLines: 3,
                maxLines: 5,
                textInputAction: TextInputAction.newline,
                decoration: InputDecoration(
                  hintText: _copy(
                    context,
                    'Describe the result, constraints and acceptance criteria…',
                    'İstediğin sonucu, kısıtları ve kabul kriterlerini yaz…',
                  ),
                  alignLabelWithHint: true,
                ),
              ),
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 6,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  _FactoryRouteStrip(
                    selected: selectedPreset,
                    presetLabel: presetLabel,
                    onChanged: onPresetChanged,
                  ),
                  _BusinessCapabilitySelector(
                    selected: selectedBusinessCapability,
                    labelFor: businessCapabilityLabel,
                    onChanged: onBusinessCapabilityChanged,
                  ),
                ],
              ),
              if (referenceAssets != null) ...[
                const SizedBox(height: 8),
                ReferenceAssetPicker(
                  controller: referenceAssets!,
                  enabled: enabled,
                  compact: true,
                ),
              ],
            ],
          ),
        ),
        const SizedBox(width: 12),
        SizedBox(
          width: 138,
          child: Align(
            alignment: Alignment.bottomCenter,
            child: SizedBox(
              width: double.infinity,
              height: 38,
              child: FilledButton.icon(
                key: const Key('one-prompt-submit'),
                onPressed: enabled && !submitting ? onSubmit : null,
                icon: submitting
                    ? const SizedBox(
                        width: 13,
                        height: 13,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.arrow_forward_rounded, size: 18),
                label: Text(
                  submitting
                      ? context.tr('goals.submitting')
                      : _copy(context, 'Start', 'Başlat'),
                ),
              ),
            ),
          ),
        ),
      ],
    ),
  );
}

class _BusinessCapabilitySelector extends StatelessWidget {
  const _BusinessCapabilitySelector({
    required this.selected,
    required this.labelFor,
    required this.onChanged,
  });

  final BusinessCapabilityFamily? selected;
  final String Function(BusinessCapabilityFamily family) labelFor;
  final ValueChanged<BusinessCapabilityFamily?> onChanged;

  @override
  Widget build(BuildContext context) => SizedBox(
    height: 34,
    child: PopupMenuButton<BusinessCapabilityFamily?>(
      key: const Key('business-capability-selector'),
      tooltip: _copy(
        context,
        'Optional business context; does not select execution authority',
        'İsteğe bağlı iş bağlamı; yürütme yetkisi seçmez',
      ),
      onSelected: onChanged,
      itemBuilder: (context) => <PopupMenuEntry<BusinessCapabilityFamily?>>[
        PopupMenuItem<BusinessCapabilityFamily?>(
          key: const Key('business-context-none'),
          value: null,
          child: Text(_copy(context, 'No business context', 'İş bağlamı yok')),
        ),
        for (final family in BusinessCapabilityFamily.values)
          PopupMenuItem<BusinessCapabilityFamily?>(
            key: ValueKey('business-context-${family.contextCode}'),
            value: family,
            child: Text('${family.contextCode} · ${labelFor(family)}'),
          ),
      ],
      child: Container(
        constraints: const BoxConstraints(minWidth: 76, maxWidth: 92),
        height: 34,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.business_center_outlined, size: 14),
            const SizedBox(width: 4),
            Flexible(
              child: Text(
                selected == null
                    ? _copy(context, 'Context', 'Bağlam')
                    : selected!.contextCode,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 8.4, fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(width: 2),
            const Icon(Icons.arrow_drop_down, size: 14),
          ],
        ),
      ),
    ),
  );
}

class _FactoryRouteStrip extends StatelessWidget {
  const _FactoryRouteStrip({
    required this.selected,
    required this.presetLabel,
    required this.onChanged,
  });

  final _FactoryPreset? selected;
  final String Function(_FactoryPreset preset) presetLabel;
  final ValueChanged<_FactoryPreset> onChanged;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      for (final preset in _FactoryPreset.values) ...[
        if (preset.index > 0) const SizedBox(width: 4),
        _FactoryRouteChip(
          preset: preset,
          selected: selected == preset,
          label: presetLabel(preset),
          onTap: () => onChanged(preset),
        ),
      ],
    ],
  );
}

class _FactoryRouteChip extends StatelessWidget {
  const _FactoryRouteChip({
    required this.preset,
    required this.selected,
    required this.label,
    required this.onTap,
  });

  final _FactoryPreset preset;
  final bool selected;
  final String label;
  final VoidCallback onTap;

  String get _keyName => switch (preset) {
    _FactoryPreset.web => 'factory-preset-web',
    _FactoryPreset.video => 'factory-preset-video',
    _FactoryPreset.software => 'factory-preset-software',
  };

  IconData get _icon => switch (preset) {
    _FactoryPreset.web => Icons.language_outlined,
    _FactoryPreset.video => Icons.smart_display_outlined,
    _FactoryPreset.software => Icons.code_rounded,
  };

  @override
  Widget build(BuildContext context) => Material(
    key: ValueKey(_keyName),
    color: selected
        ? IlaiosTheme.coreBlue.withValues(alpha: .10)
        : Theme.of(context).colorScheme.surfaceContainerLowest,
    shape: RoundedRectangleBorder(
      borderRadius: BorderRadius.circular(5),
      side: BorderSide(
        color: selected
            ? IlaiosTheme.coreBlue.withValues(alpha: .65)
            : Theme.of(context).colorScheme.outlineVariant,
      ),
    ),
    clipBehavior: Clip.antiAlias,
    child: InkWell(
      onTap: onTap,
      child: Container(
        key: selected ? const Key('selected-factory-route') : null,
        height: 32,
        constraints: const BoxConstraints(minWidth: 43, maxWidth: 52),
        padding: const EdgeInsets.symmetric(horizontal: 5),
        child: Tooltip(
          message: label,
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                _icon,
                size: 14,
                color: selected
                    ? IlaiosTheme.coreBlue
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(height: 1),
              Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 6.5,
                  fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                  color: selected
                      ? IlaiosTheme.coreBlue
                      : Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
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
        value: _displayEvent(context, lastEvent) ?? '—',
        note: _copy(context, 'Authoritative event', 'Yetkili olay'),
      ),
    ];

    return SizedBox(
      key: const Key('goals-kpis'),
      height: 78,
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
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
    decoration: _cardDecoration(context, radius: 7),
    child: Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            color: metric.color.withValues(alpha: .11),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Icon(metric.icon, color: metric.color, size: 21),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                metric.label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 8.1),
              ),
              const SizedBox(height: 1),
              Text(
                metric.value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700, height: 1),
              ),
              const SizedBox(height: 3),
              Text(
                metric.note,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 7.2,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
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
      height: 34,
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
                    fontSize: 9.8,
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
    final header = Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      child: Row(
        children: [
          Expanded(flex: 31, child: _TableHeader(_copy(context, 'Goal', 'Hedef'))),
          Expanded(flex: 17, child: _TableHeader(_copy(context, 'Owner', 'Sahip'))),
          Expanded(
            flex: 22,
            child: _TableHeader(_copy(context, 'Progress', 'İlerleme')),
          ),
          Expanded(flex: 12, child: _TableHeader(_copy(context, 'Status', 'Durum'))),
          Expanded(
            flex: 12,
            child: _TableHeader(_copy(context, 'Target', 'Hedef Tarihi')),
          ),
          Expanded(
            flex: 10,
            child: _TableHeader(_copy(context, 'Priority', 'Öncelik')),
          ),
          const SizedBox(width: 22),
        ],
      ),
    );
    final body = showSubmission
        ? _GoalRow(
            submission: submission!,
            objective: objective ?? submission!.goalId,
            owner: owner,
          )
        : Padding(
            padding: const EdgeInsets.all(22),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.track_changes_outlined,
                  size: 34,
                  color: Theme.of(context).colorScheme.outline,
                ),
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
          );
    final footer = Container(
      height: 38,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      decoration: BoxDecoration(
        border: Border(
          top: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Text(
              showSubmission
                  ? _copy(
                      context,
                      'Showing 1 authoritative goal.',
                      '1 yetkili hedef gösteriliyor.',
                    )
                  : _copy(
                      context,
                      'No detailed goal rows available.',
                      'Ayrıntılı hedef satırı bulunmuyor.',
                    ),
              style: TextStyle(
                fontSize: 8.7,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          const _PageBox(label: '1', selected: true),
          const SizedBox(width: 7),
          _PageBox(label: _copy(context, '10 / page', '10 / sayfa')),
        ],
      ),
    );

    return Container(
      key: const Key('goals-table'),
      decoration: _cardDecoration(context, radius: 7),
      clipBehavior: Clip.antiAlias,
      child: LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxHeight < 72) {
            return SingleChildScrollView(
              primary: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [header, body, footer],
              ),
            );
          }
          return Column(
            children: [
              header,
              Expanded(
                child: SingleChildScrollView(
                  primary: false,
                  child: body,
                ),
              ),
              footer,
            ],
          );
        },
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
  const _GoalRow({
    required this.submission,
    required this.objective,
    required this.owner,
  });

  final PromptSubmission submission;
  final String objective;
  final String owner;

  @override
  Widget build(BuildContext context) {
    final state = submission.state.toUpperCase();
    final completed = state == 'COMPLETED' || state == 'SUCCEEDED' || state == 'FINISHED';
    final active = state == 'RUNNING' ||
        state == 'PENDING' ||
        state == 'QUEUED' ||
        state == 'ADMITTED';
    final double? progress = completed ? 1.0 : null;
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
        border: Border(
          bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
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
                  child: const Icon(
                    Icons.track_changes_outlined,
                    size: 17,
                    color: IlaiosTheme.coreBlue,
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        objective,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w600),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        submission.goalId,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 8.2,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            flex: 17,
            child: Text(
              owner,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 9.4),
            ),
          ),
          Expanded(
            flex: 22,
            child: progress == null
                ? Text(
                    _copy(context, 'Hesaplanmadı', 'Not calculated'),
                    style: TextStyle(
                      fontSize: 8.5,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  )
                : Row(
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
                      const Text('100%', style: TextStyle(fontSize: 9)),
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
        ],
      ),
    );
  }
}

class _SelectedGoal extends StatelessWidget {
  const _SelectedGoal({
    required this.submission,
    required this.objective,
    required this.owner,
  });

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
        : SingleChildScrollView(
            primary: false,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  _copy(context, 'Selected Goal', 'Seçili Hedef'),
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
                ),
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
                      child: const Icon(
                        Icons.track_changes_outlined,
                        color: IlaiosTheme.coreBlue,
                        size: 23,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            objective ?? submission!.goalId,
                            maxLines: 2,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            'ID: ${submission!.goalId}',
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 8.5,
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                          ),
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
                const SizedBox(height: 10),
                Text(
                  _copy(
                    context,
                    'Ek ayrıntılar mevcut olduğunda burada görünür.',
                    'Additional details appear here when available.',
                  ),
                  style: TextStyle(
                    fontSize: 8.8,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
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
        child: Text(
          label,
          style: TextStyle(
            fontSize: 8.6,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ),
      Expanded(
        child: Text(
          value,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 9.1, fontWeight: FontWeight.w600),
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
          _copy(
            context,
            'Authoritative detail unavailable',
            'Yetkili ayrıntı kullanılamıyor',
          ),
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 8.1,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    ),
  );
}

class _SubmissionStatus extends StatelessWidget {
  const _SubmissionStatus({
    required this.submission,
    required this.error,
    required this.lifecycle,
  });

  final PromptSubmission? submission;
  final String? error;
  final GovernedLifecycleState lifecycle;

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
    final lifecycleLabel = _lifecycleLabel(context, lifecycle);
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
          const Icon(Icons.verified_user_outlined, size: 16, color: IlaiosTheme.success),
          const SizedBox(width: 8),
          Text(
            'Goal: ${value.goalId}',
            style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 14),
          Text(
            'Job: ${value.jobId}',
            style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 14),
          Text(
            lifecycleLabel,
            key: const Key('authoritative-lifecycle-state'),
            style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w600),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Text(
              _copy(
                context,
                'Lifecycle is projected from fresh control-plane state; missing evidence stays unavailable.',
                'Yaşam döngüsü güncel kontrol düzlemi durumundan yansıtılır; eksik kanıt kullanılamaz kalır.',
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 8.1,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

String _lifecycleLabel(BuildContext context, GovernedLifecycleState state) => switch (state) {
  GovernedLifecycleState.pendingApproval => _copy(
    context,
    'Lifecycle: Pending approval',
    'Yaşam döngüsü: Onay bekliyor',
  ),
  GovernedLifecycleState.admitted => _copy(
    context,
    'Lifecycle: Admitted',
    'Yaşam döngüsü: Kabul edildi',
  ),
  GovernedLifecycleState.executing => _copy(
    context,
    'Lifecycle: Executing',
    'Yaşam döngüsü: Yürütülüyor',
  ),
  GovernedLifecycleState.accepted => _copy(
    context,
    'Lifecycle: Accepted',
    'Yaşam döngüsü: Doğrulandı',
  ),
  GovernedLifecycleState.blocked => _copy(
    context,
    'Lifecycle: Blocked',
    'Yaşam döngüsü: Engellendi',
  ),
  GovernedLifecycleState.denied => _copy(
    context,
    'Lifecycle: Denied',
    'Yaşam döngüsü: Reddedildi',
  ),
  GovernedLifecycleState.failed => _copy(
    context,
    'Lifecycle: Failed',
    'Yaşam döngüsü: Başarısız',
  ),
  GovernedLifecycleState.unavailable => _copy(
    context,
    'Lifecycle: Unavailable',
    'Yaşam döngüsü: Kullanılamıyor',
  ),
};

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
    child: Text(
      label,
      style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),
    ),
  );
}

BoxDecoration _cardDecoration(BuildContext context, {double radius = 8}) => BoxDecoration(
  color: Theme.of(context).colorScheme.surfaceContainerLowest,
  borderRadius: BorderRadius.circular(radius),
  border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
);

String? _displayEvent(BuildContext context, String? raw) {
  final value = raw?.trim();
  if (value == null || value.isEmpty) return null;
  if (value != 'job.updated') return value;
  return _copy(context, 'Job update', 'İş güncellemesi');
}

bool _isTr(BuildContext context) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;

String _copy(BuildContext context, String en, String tr) => _isTr(context) ? tr : en;
