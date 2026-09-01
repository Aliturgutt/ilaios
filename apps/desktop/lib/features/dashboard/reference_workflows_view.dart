import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';

/// Reference-faithful Workflows surface backed only by authoritative Desktop
/// projections. Screenshot values are never copied into runtime state.
class ReferenceWorkflowsView extends StatefulWidget {
  const ReferenceWorkflowsView({
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
  State<ReferenceWorkflowsView> createState() => _ReferenceWorkflowsViewState();
}

class _ReferenceWorkflowsViewState extends State<ReferenceWorkflowsView> {
  static const int _pageSize = 5;

  final TextEditingController _searchController = TextEditingController();
  int _tab = 0;
  int _selected = -1;
  int _page = 0;
  String _query = '';
  String _type = _allFilter;
  String _priority = _allFilter;
  String _owner = _allFilter;
  String _stage = _allFilter;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  void _resetPosition() {
    _page = 0;
    _selected = -1;
  }

  void _clearFilters() {
    _searchController.clear();
    setState(() {
      _query = '';
      _type = _allFilter;
      _priority = _allFilter;
      _owner = _allFilter;
      _stage = _allFilter;
      _resetPosition();
    });
  }

  bool get _hasFilters =>
      _query.trim().isNotEmpty ||
      _type != _allFilter ||
      _priority != _allFilter ||
      _owner != _allFilter ||
      _stage != _allFilter;

  @override
  Widget build(BuildContext context) {
    final workflows = _workflowRecords(widget.snapshot);
    final filtered = _filtered(workflows);
    final pageCount = math.max(1, (filtered.length / _pageSize).ceil());
    final effectivePage = _page.clamp(0, pageCount - 1);
    final start = effectivePage * _pageSize;
    final end = math.min(start + _pageSize, filtered.length);
    final pageRows = start >= filtered.length
        ? const <_WorkflowRecord>[]
        : filtered.sublist(start, end);
    final selected = pageRows.isEmpty || _selected < 0
        ? null
        : pageRows[_selected.clamp(0, pageRows.length - 1)];
    final approvals = _approvalItems(widget.snapshot);
    final templates = _templateItems(widget.snapshot);

    return Container(
      key: const Key('reference-workflows-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(14, 10, 12, 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final rightWidth = (constraints.maxWidth * .31).clamp(330.0, 405.0);
          return Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _PageHeader(
                      connected: widget.projection.connected,
                      onRefresh: widget.onRefreshRequested,
                    ),
                    const SizedBox(height: 7),
                    _MetricsRow(
                      projection: widget.projection,
                      snapshot: widget.snapshot,
                      workflows: workflows,
                      approvals: approvals,
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: _WorkflowTablePanel(
                        workflows: pageRows,
                        allWorkflows: workflows,
                        filteredCount: filtered.length,
                        approvals: approvals,
                        tab: _tab,
                        queryController: _searchController,
                        type: _type,
                        priority: _priority,
                        owner: _owner,
                        stage: _stage,
                        page: effectivePage,
                        pageCount: pageCount,
                        pageSize: _pageSize,
                        selected: selected,
                        hasFilters: _hasFilters,
                        connected: widget.projection.connected,
                        onTab: (value) => setState(() {
                          _tab = value;
                          _resetPosition();
                        }),
                        onQuery: (value) => setState(() {
                          _query = value;
                          _resetPosition();
                        }),
                        onType: (value) => setState(() {
                          _type = value;
                          _resetPosition();
                        }),
                        onPriority: (value) => setState(() {
                          _priority = value;
                          _resetPosition();
                        }),
                        onOwner: (value) => setState(() {
                          _owner = value;
                          _resetPosition();
                        }),
                        onStage: (value) => setState(() {
                          _stage = value;
                          _resetPosition();
                        }),
                        onSelect: (value) => setState(() => _selected = value),
                        onPrevious: effectivePage <= 0
                            ? null
                            : () => setState(() {
                                  _page = effectivePage - 1;
                                  _selected = -1;
                                }),
                        onNext: effectivePage >= pageCount - 1
                            ? null
                            : () => setState(() {
                                  _page = effectivePage + 1;
                                  _selected = -1;
                                }),
                        onClear: _clearFilters,
                        onRefresh: widget.onRefreshRequested,
                        onApprovals: () =>
                            widget.onNavigate(DesktopSection.approvals),
                        onWorkspace: () =>
                            widget.onNavigate(DesktopSection.liveWorkspace),
                      ),
                    ),
                    if (widget.snapshot.liveEvents.isNotEmpty ||
                        widget.snapshot.evidenceRecords.isNotEmpty ||
                        approvals.isNotEmpty ||
                        templates.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 145,
                        child: _BottomPanels(
                          snapshot: widget.snapshot,
                          approvals: approvals,
                          templates: templates,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              if (selected != null) ...[
                const SizedBox(width: 10),
                SizedBox(
                  width: rightWidth,
                  child: _SelectedWorkflowPanel(
                  workflow: selected,
                  approvals: approvals,
                  connected: widget.projection.connected,
                  onRefresh: widget.onRefreshRequested,
                    onNavigate: widget.onNavigate,
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }

  List<_WorkflowRecord> _filtered(List<_WorkflowRecord> source) {
    Iterable<_WorkflowRecord> output = source;
    if (_tab == 1) output = output.where((item) => item.active);
    if (_tab == 2) output = output.where((item) => item.awaitingApproval);
    if (_tab == 3) output = output.where((item) => item.completed);
    if (_tab == 4) output = output.where((item) => item.archived);
    if (_type != _allFilter) {
      output = output.where((item) => item.kind == _type);
    }
    if (_priority != _allFilter) {
      output = output.where((item) => item.priority == _priority);
    }
    if (_owner != _allFilter) {
      output = output.where((item) => item.owner == _owner);
    }
    if (_stage != _allFilter) {
      output = output.where((item) => item.phase == _stage);
    }
    final q = _query.trim().toLowerCase();
    if (q.isNotEmpty) {
      output = output.where(
        (item) =>
            '${item.name} ${item.subtitle} ${item.id} ${item.kind} ${item.phase} ${item.owner} ${item.priority}'
                .toLowerCase()
                .contains(q),
      );
    }
    return output.toList(growable: false);
  }
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.connected, this.onRefresh});

  final bool connected;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 43,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _tr(context, 'İş Akışları', 'Workflows'),
                    style: const TextStyle(
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    _tr(
                      context,
                      'İş akışlarını orkestre edin ve teslimat süreçlerini takip edin.',
                      'Orchestrate workflows and track delivery processes.',
                    ),
                    style: TextStyle(
                      fontSize: 9.2,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            IconButton(
              key: const Key('workflows-refresh'),
              tooltip: _tr(context, 'Yenile', 'Refresh'),
              onPressed: connected ? onRefresh : null,
              icon: const Icon(Icons.refresh_rounded, size: 18),
            ),
          ],
        ),
      );
}

class _MetricsRow extends StatelessWidget {
  const _MetricsRow({
    required this.projection,
    required this.snapshot,
    required this.workflows,
    required this.approvals,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final List<_WorkflowRecord> workflows;
  final List<Map<String, Object?>> approvals;

  @override
  Widget build(BuildContext context) {
    final activeCount = _authoritativeInt(snapshot.schedulerState, const [
          'active_count',
          'active_jobs',
          'running_count',
        ]) ??
        (workflows.isEmpty ? null : workflows.where((item) => item.active).length);
    final completedCount = _authoritativeInt(snapshot.schedulerState, const [
          'completed_count',
          'completed_jobs',
          'done_count',
        ]) ??
        (workflows.isEmpty
            ? null
            : workflows.where((item) => item.completed).length);
    final overdue = _authoritativeInt(snapshot.schedulerState, const [
      'overdue_count',
      'late_count',
    ]);

    final summary = <(IconData, String, String, Color)>[
      (
        Icons.account_tree_outlined,
        _tr(context, 'Toplam', 'Total'),
        projection.jobCount?.toString() ?? '—',
        Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      (
        Icons.play_arrow_rounded,
        _tr(context, 'Aktif', 'Active'),
        activeCount?.toString() ?? '—',
        Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      (
        Icons.hourglass_bottom_rounded,
        _tr(context, 'Onay Bekleyen', 'Awaiting Approval'),
        approvals.length.toString(),
        approvals.isEmpty
            ? Theme.of(context).colorScheme.onSurfaceVariant
            : IlaiosTheme.warning,
      ),
      (
        Icons.schedule_rounded,
        _tr(context, 'Geciken', 'Overdue'),
        overdue?.toString() ?? '—',
        overdue != null && overdue > 0
            ? IlaiosTheme.danger
            : Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      (
        Icons.check_circle_outline_rounded,
        _tr(context, 'Tamamlanan', 'Completed'),
        completedCount?.toString() ?? '—',
        completedCount != null && completedCount > 0
            ? IlaiosTheme.success
            : Theme.of(context).colorScheme.onSurfaceVariant,
      ),
    ];

    return SizedBox(
      key: const Key('workflows-metrics'),
      height: 50,
      child: _Card(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        child: Row(
          children: [
            for (var index = 0; index < summary.length; index++) ...[
              if (index > 0)
                Container(
                  width: 1,
                  height: 24,
                  margin: const EdgeInsets.symmetric(horizontal: 12),
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
              Icon(summary[index].$1, size: 14, color: summary[index].$4),
              const SizedBox(width: 5),
              Flexible(
                child: Text(
                  summary[index].$2,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 8.2,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
              const SizedBox(width: 5),
              Text(
                summary[index].$3,
                style: const TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

enum _WorkflowMenuAction { refresh }
enum _WorkflowRowAction { approvals, workspace }

class _WorkflowTablePanel extends StatelessWidget {
  const _WorkflowTablePanel({
    required this.workflows,
    required this.allWorkflows,
    required this.filteredCount,
    required this.approvals,
    required this.tab,
    required this.queryController,
    required this.type,
    required this.priority,
    required this.owner,
    required this.stage,
    required this.page,
    required this.pageCount,
    required this.pageSize,
    required this.selected,
    required this.hasFilters,
    required this.connected,
    required this.onTab,
    required this.onQuery,
    required this.onType,
    required this.onPriority,
    required this.onOwner,
    required this.onStage,
    required this.onSelect,
    required this.onPrevious,
    required this.onNext,
    required this.onClear,
    required this.onRefresh,
    required this.onApprovals,
    required this.onWorkspace,
  });

  final List<_WorkflowRecord> workflows;
  final List<_WorkflowRecord> allWorkflows;
  final int filteredCount;
  final List<Map<String, Object?>> approvals;
  final int tab;
  final TextEditingController queryController;
  final String type;
  final String priority;
  final String owner;
  final String stage;
  final int page;
  final int pageCount;
  final int pageSize;
  final _WorkflowRecord? selected;
  final bool hasFilters;
  final bool connected;
  final ValueChanged<int> onTab;
  final ValueChanged<String> onQuery;
  final ValueChanged<String> onType;
  final ValueChanged<String> onPriority;
  final ValueChanged<String> onOwner;
  final ValueChanged<String> onStage;
  final ValueChanged<int> onSelect;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;
  final VoidCallback onClear;
  final VoidCallback? onRefresh;
  final VoidCallback onApprovals;
  final VoidCallback onWorkspace;

  @override
  Widget build(BuildContext context) {
    final typeOptions = _filterValues(allWorkflows.map((item) => item.kind));
    final priorityOptions =
        _filterValues(allWorkflows.map((item) => item.priority));
    final ownerOptions = _filterValues(allWorkflows.map((item) => item.owner));
    final stageOptions = _filterValues(allWorkflows.map((item) => item.phase));
    final first = filteredCount == 0 ? 0 : page * pageSize + 1;
    final last = math.min((page + 1) * pageSize, filteredCount);

    return _Card(
      key: const Key('workflows-table-panel'),
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 38,
            child: Row(
              children: [
                for (final entry in <(String, String)>[
                  ('Tümü', 'All'),
                  ('Aktif', 'Active'),
                  ('Onay Bekleyen', 'Awaiting Approval'),
                  ('Tamamlanan', 'Completed'),
                  ('Arşiv', 'Archive'),
                ].indexed)
                  _TabButton(
                    label: _tr(context, entry.$2.$1, entry.$2.$2),
                    selected: tab == entry.$1,
                    onTap: () => onTab(entry.$1),
                  ),
                const Spacer(),

                PopupMenuButton<_WorkflowMenuAction>(
                  key: const Key('workflows-more-menu'),
                  tooltip: _tr(context, 'Diğer', 'More'),
                  onSelected: (action) {
                    switch (action) {
                      case _WorkflowMenuAction.refresh:
                        onRefresh?.call();
                    }
                  },
                  itemBuilder: (context) => [
                    PopupMenuItem(
                      value: _WorkflowMenuAction.refresh,
                      enabled: connected && onRefresh != null,
                      child: Text(_tr(context, 'Yenile', 'Refresh')),
                    ),

                  ],
                  icon: const Icon(Icons.more_vert, size: 16),
                ),
                const SizedBox(width: 4),
              ],
            ),
          ),
          if (allWorkflows.isNotEmpty) ...[
            Divider(
              height: 1,
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
            SizedBox(
              height: 56,
              child: _StageDistribution(workflows: allWorkflows),
            ),
          ],
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          SizedBox(
            height: 39,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
              child: Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: TextField(
                      key: const Key('workflow-search'),
                      controller: queryController,
                      onChanged: onQuery,
                      decoration: InputDecoration(
                        isDense: true,
                        hintText: _tr(
                          context,
                          'İş akışı ara...',
                          'Search workflows...',
                        ),
                        prefixIcon: const Icon(Icons.search, size: 15),
                        contentPadding: const EdgeInsets.symmetric(vertical: 5),
                      ),
                      style: const TextStyle(fontSize: 9.2),
                    ),
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: _FilterBox(
                      id: 'type',
                      label: _tr(context, 'Tür', 'Type'),
                      value: type,
                      options: typeOptions,
                      onChanged: onType,
                    ),
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: _FilterBox(
                      id: 'priority',
                      label: _tr(context, 'Öncelik', 'Priority'),
                      value: priority,
                      options: priorityOptions,
                      onChanged: onPriority,
                    ),
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: _FilterBox(
                      id: 'owner',
                      label: _tr(context, 'Sahip', 'Owner'),
                      value: owner,
                      options: ownerOptions,
                      onChanged: onOwner,
                    ),
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: _FilterBox(
                      id: 'stage',
                      label: _tr(context, 'Aşama', 'Stage'),
                      value: stage,
                      options: stageOptions,
                      onChanged: onStage,
                    ),
                  ),
                  const SizedBox(width: 7),
                  OutlinedButton(
                    key: const Key('workflow-clear-filters'),
                    onPressed: hasFilters ? onClear : null,
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size(105, 28),
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      textStyle: const TextStyle(fontSize: 8.3),
                    ),
                    child: Text(_tr(context, 'Filtreleri Temizle', 'Clear Filters')),
                  ),
                ],
              ),
            ),
          ),
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          const _WorkflowHeader(),
          Expanded(
            child: workflows.isEmpty
                ? _EmptyWorkflows()
                : Column(
                    children: [
                      for (var index = 0; index < workflows.length; index++)
                        Expanded(
                          child: _WorkflowRow(
                            record: workflows[index],
                            selected: selected?.id == workflows[index].id,
                            onTap: () => onSelect(index),
                            onApprovals: onApprovals,
                            onWorkspace: onWorkspace,
                          ),
                        ),
                    ],
                  ),
          ),
          SizedBox(
            height: 29,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 7),
              child: Row(
                children: [
                  Text(
                    filteredCount == 0
                        ? _tr(context, '0 sonuç', '0 results')
                        : '$first-$last / $filteredCount ${_tr(context, 'sonuç', 'results')}',
                    style: const TextStyle(fontSize: 8.2),
                  ),
                  const Spacer(),
                  IconButton(
                    key: const Key('workflow-page-previous'),
                    onPressed: onPrevious,
                    visualDensity: VisualDensity.compact,
                    iconSize: 14,
                    tooltip: _tr(context, 'Önceki sayfa', 'Previous page'),
                    icon: const Icon(Icons.chevron_left),
                  ),
                  Container(
                    key: const Key('workflow-page-indicator'),
                    constraints: const BoxConstraints(minWidth: 26),
                    height: 21,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      border: Border.all(
                        color: IlaiosTheme.enterpriseCyan.withValues(alpha: .7),
                      ),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      '${page + 1}/$pageCount',
                      style: const TextStyle(fontSize: 8),
                    ),
                  ),
                  IconButton(
                    key: const Key('workflow-page-next'),
                    onPressed: onNext,
                    visualDensity: VisualDensity.compact,
                    iconSize: 14,
                    tooltip: _tr(context, 'Sonraki sayfa', 'Next page'),
                    icon: const Icon(Icons.chevron_right),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    _tr(context, 'Sayfa başına $pageSize', '$pageSize per page'),
                    style: const TextStyle(fontSize: 8.2),
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

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        child: Container(
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            border: selected
                ? const Border(
                    bottom: BorderSide(
                      color: IlaiosTheme.enterpriseCyan,
                      width: 2,
                    ),
                  )
                : null,
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 9.2,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected
                  ? Theme.of(context).colorScheme.onSurface
                  : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      );
}

class _StageDistribution extends StatelessWidget {
  const _StageDistribution({required this.workflows});

  final List<_WorkflowRecord> workflows;

  @override
  Widget build(BuildContext context) {
    final stages = <_StageCount>[
      _StageCount(
        'Planlama',
        'Planning',
        IlaiosTheme.enterpriseCyan,
        _stageCount(workflows, 'plan'),
      ),
      _StageCount(
        'Yürütme',
        'Execution',
        IlaiosTheme.coreBlue,
        _stageCount(workflows, 'exec'),
      ),
      _StageCount(
        'Doğrulama',
        'Verification',
        IlaiosTheme.violet,
        _stageCount(workflows, 'verif'),
      ),
      _StageCount(
        'Teslimat',
        'Delivery',
        IlaiosTheme.warning,
        _stageCount(workflows, 'deliver'),
      ),
      _StageCount(
        'Tamamlandı',
        'Completed',
        IlaiosTheme.success,
        workflows.where((item) => item.completed).length,
      ),
    ];
    final total = stages.fold<int>(0, (sum, item) => sum + item.count);
    return Padding(
      padding: const EdgeInsets.fromLTRB(10, 7, 10, 5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _tr(
              context,
              'Aşama Dağılımı (Tüm İş Akışları)',
              'Stage Distribution (All Workflows)',
            ),
            style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 7),
          Row(
            children: [
              for (var index = 0; index < stages.length; index++) ...[
                Expanded(
                  flex: total == 0 ? 1 : stages[index].count.clamp(1, 99),
                  child: Container(
                    height: 4,
                    color: total == 0
                        ? Theme.of(context).colorScheme.outlineVariant
                        : stages[index].color,
                  ),
                ),
                if (index < stages.length - 1) const SizedBox(width: 2),
              ],
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              for (final stage in stages)
                Expanded(
                  child: Text(
                    total == 0
                        ? '${_tr(context, stage.tr, stage.en)} —'
                        : '${_tr(context, stage.tr, stage.en)} ${stage.count} (${(stage.count * 100 / total).round()}%)',
                    textAlign: TextAlign.center,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 7.2,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StageCount {
  const _StageCount(this.tr, this.en, this.color, this.count);

  final String tr;
  final String en;
  final Color color;
  final int count;
}

class _FilterBox extends StatelessWidget {
  const _FilterBox({
    required this.id,
    required this.label,
    required this.value,
    required this.options,
    required this.onChanged,
  });

  final String id;
  final String label;
  final String value;
  final List<String> options;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => PopupMenuButton<String>(
        key: ValueKey('workflow-filter-$id'),
        initialValue: value,
        tooltip: label,
        onSelected: onChanged,
        itemBuilder: (context) => [
          PopupMenuItem(
            value: _allFilter,
            child: Text(_tr(context, 'Tümü', 'All')),
          ),
          for (final option in options)
            PopupMenuItem(value: option, child: Text(option)),
        ],
        child: Container(
          height: 28,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
            borderRadius: BorderRadius.circular(5),
            color: Theme.of(context).colorScheme.surfaceContainerLowest,
          ),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  value == _allFilter
                      ? '$label: ${_tr(context, 'Tümü', 'All')}'
                      : value,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 8.2),
                ),
              ),
              const Icon(Icons.keyboard_arrow_down, size: 13),
            ],
          ),
        ),
      );
}

class _WorkflowHeader extends StatelessWidget {
  const _WorkflowHeader();

  @override
  Widget build(BuildContext context) => Container(
        height: 26,
        padding: const EdgeInsets.symmetric(horizontal: 9),
        color: Theme.of(context)
            .colorScheme
            .surfaceContainerLowest
            .withValues(alpha: .35),
        child: Row(
          children: [
            _HeaderCell(_tr(context, 'İş Akışı', 'Workflow'), flex: 31),
            _HeaderCell(_tr(context, 'Tür', 'Type'), flex: 9),
            _HeaderCell(_tr(context, 'Aşama', 'Stage'), flex: 13),
            _HeaderCell(_tr(context, 'İlerleme', 'Progress'), flex: 13),
            _HeaderCell(_tr(context, 'Sahip', 'Owner'), flex: 13),
            _HeaderCell(_tr(context, 'Öncelik', 'Priority'), flex: 10),
            _HeaderCell(_tr(context, 'ETA / Son Tarih', 'ETA / Due'), flex: 14),
            const SizedBox(width: 22),
          ],
        ),
      );
}

class _HeaderCell extends StatelessWidget {
  const _HeaderCell(this.text, {required this.flex});

  final String text;
  final int flex;

  @override
  Widget build(BuildContext context) => Expanded(
        flex: flex,
        child: Text(
          text,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 7.8,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );
}

class _WorkflowRow extends StatelessWidget {
  const _WorkflowRow({
    required this.record,
    required this.selected,
    required this.onTap,
    required this.onApprovals,
    required this.onWorkspace,
  });

  final _WorkflowRecord record;
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback onApprovals;
  final VoidCallback onWorkspace;

  @override
  Widget build(BuildContext context) => InkWell(
        key: ValueKey('workflow-row-${record.id}'),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(
            color: selected
                ? IlaiosTheme.enterpriseCyan.withValues(alpha: .06)
                : null,
            border: Border(
              bottom: BorderSide(
                color: Theme.of(context)
                    .colorScheme
                    .outlineVariant
                    .withValues(alpha: .65),
              ),
              left: BorderSide(
                color: selected
                    ? IlaiosTheme.enterpriseCyan
                    : Colors.transparent,
              ),
              right: BorderSide(
                color: selected
                    ? IlaiosTheme.enterpriseCyan
                    : Colors.transparent,
              ),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                flex: 31,
                child: Row(
                  children: [
                    _RoundIcon(
                      icon: _workflowIcon(record.kind),
                      accent: _phaseColor(record.phase),
                    ),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            record.name,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(
                              fontSize: 8.4,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          Text(
                            record.subtitle,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 6.9,
                              color: Theme.of(context)
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
              Expanded(
                flex: 9,
                child: _Tag(
                  text: record.kind,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              Expanded(
                flex: 13,
                child: _Tag(
                  text: record.phase,
                  color: _phaseColor(record.phase),
                ),
              ),
              Expanded(
                flex: 13,
                child: record.progress == null
                    ? const Text('—', style: TextStyle(fontSize: 8.2))
                    : Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            '${(record.progress! * 100).round()}%',
                            style: const TextStyle(
                              fontSize: 8.3,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 2),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(2),
                            child: LinearProgressIndicator(
                              value: record.progress,
                              minHeight: 3,
                            ),
                          ),
                        ],
                      ),
              ),
              Expanded(
                flex: 13,
                child: Text(
                  record.owner,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 8.1),
                ),
              ),
              Expanded(
                flex: 10,
                child: _Tag(
                  text: record.priority,
                  color: _priorityColor(record.priority),
                ),
              ),
              Expanded(
                flex: 14,
                child: Text(
                  record.eta,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 7.7),
                ),
              ),
              SizedBox(
                width: 22,
                child: PopupMenuButton<_WorkflowRowAction>(
                  key: ValueKey('workflow-row-menu-${record.id}'),
                  padding: EdgeInsets.zero,
                  tooltip: _tr(context, 'İş akışı eylemleri', 'Workflow actions'),
                  onSelected: (action) {
                    switch (action) {
                      case _WorkflowRowAction.approvals:
                        onApprovals();
                      case _WorkflowRowAction.workspace:
                        onWorkspace();
                    }
                  },
                  itemBuilder: (context) => [
                    PopupMenuItem(
                      value: _WorkflowRowAction.approvals,
                      child: Text(_tr(context, 'Onayları Gör', 'View Approvals')),
                    ),
                    PopupMenuItem(
                      value: _WorkflowRowAction.workspace,
                      child: Text(
                        _tr(
                          context,
                          'Canlı Çalışma Alanı',
                          'Live Workspace',
                        ),
                      ),
                    ),
                  ],
                  icon: const Icon(Icons.more_vert, size: 13),
                ),
              ),
            ],
          ),
        ),
      );
}

class _EmptyWorkflows extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.account_tree_outlined,
              size: 26,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 5),
            Text(
              _tr(
                context,
                'Yetkili iş akışı kaydı yok.',
                'No authoritative workflow records are available.',
              ),
              style: TextStyle(
                fontSize: 8.5,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
}

class _BottomPanels extends StatelessWidget {
  const _BottomPanels({
    required this.snapshot,
    required this.approvals,
    required this.templates,
  });

  final OperationalSnapshot snapshot;
  final List<Map<String, Object?>> approvals;
  final List<Map<String, Object?>> templates;

  @override
  Widget build(BuildContext context) {
    final updates = snapshot.liveEvents.reversed.take(3).toList(growable: false);
    final evidence = snapshot.evidenceRecords.reversed.take(3).toList(growable: false);
    return Row(
      key: const Key('workflows-bottom-panels'),
      children: [
        Expanded(
          child: _MiniPanel(
            title: _tr(context, 'SON GÜNCELLEMELER', 'RECENT UPDATES'),
            child: _EventList(items: updates),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MiniPanel(
            title: _tr(
              context,
              'ONAY BEKLEYEN ADIMLAR',
              'PENDING APPROVAL STEPS',
            ),
            child: _ApprovalList(
              items: approvals.take(3).toList(growable: false),
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MiniPanel(
            title: _tr(context, 'SON TESLİMATLAR', 'RECENT DELIVERIES'),
            child: _EvidenceList(items: evidence),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MiniPanel(
            title: _tr(
              context,
              'İŞ AKIŞI ŞABLONLARI',
              'WORKFLOW TEMPLATES',
            ),
            child: _TemplateList(
              items: templates.take(3).toList(growable: false),
            ),
          ),
        ),
      ],
    );
  }
}

class _MiniPanel extends StatelessWidget {
  const _MiniPanel({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => _Card(
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 30,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 9),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(
                          fontSize: 8.2,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    Text(
                      _tr(context, 'Tümü', 'All'),
                      style: TextStyle(
                        fontSize: 7.3,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const Icon(Icons.chevron_right, size: 12),
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

class _EventList extends StatelessWidget {
  const _EventList({required this.items});
  final List<Map<String, Object?>> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return _SmallEmpty(text: _tr(context, 'Güncelleme yok', 'No updates'));
    }
    return Column(
      children: [
        for (final item in items)
          Expanded(
            child: _SmallRow(
              icon: Icons.person_outline,
              color: IlaiosTheme.enterpriseCyan,
              title: _text(item, const ['event', 'action', 'type', 'status']) ?? '—',
              subtitle: _text(
                    item,
                    const [
                      'project_name',
                      'workflow_name',
                      'job_id',
                      'execution_id',
                    ],
                  ) ??
                  '—',
              trailing: _text(
                    item,
                    const ['timestamp', 'time', 'created_at', 'updated_at'],
                  ) ??
                  '—',
            ),
          ),
      ],
    );
  }
}

class _ApprovalList extends StatelessWidget {
  const _ApprovalList({required this.items});
  final List<Map<String, Object?>> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return _SmallEmpty(
        text: _tr(context, 'Bekleyen onay yok', 'No pending approvals'),
      );
    }
    return Column(
      children: [
        for (final item in items)
          Expanded(
            child: _SmallRow(
              icon: Icons.error_outline,
              color: IlaiosTheme.warning,
              title: _text(
                    item,
                    const ['title', 'action', 'reason', 'request_type'],
                  ) ??
                  '—',
              subtitle: _text(
                    item,
                    const ['workflow_name', 'job_id', 'execution_id', 'request_id'],
                  ) ??
                  '—',
              trailing: _text(
                    item,
                    const ['priority', 'risk', 'severity'],
                  ) ??
                  '—',
            ),
          ),
      ],
    );
  }
}

class _EvidenceList extends StatelessWidget {
  const _EvidenceList({required this.items});
  final List<dynamic> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return _SmallEmpty(text: _tr(context, 'Teslimat yok', 'No deliveries'));
    }
    return Column(
      children: [
        for (final item in items)
          Expanded(
            child: _SmallRow(
              icon: Icons.description_outlined,
              color: IlaiosTheme.coreBlue,
              title: item.action,
              subtitle: item.executionId,
              trailing: '#${item.sequence}',
            ),
          ),
      ],
    );
  }
}

class _TemplateList extends StatelessWidget {
  const _TemplateList({required this.items});
  final List<Map<String, Object?>> items;

  @override
  Widget build(BuildContext context) {
    if (items.isEmpty) {
      return _SmallEmpty(
        text: _tr(
          context,
          'Yetkili şablon kaydı yok',
          'No authoritative templates',
        ),
      );
    }
    return Column(
      children: [
        for (final item in items)
          Expanded(
            child: _SmallRow(
              icon: Icons.content_copy_outlined,
              color: IlaiosTheme.violet,
              title: _text(item, const ['name', 'title', 'template_name']) ?? '—',
              subtitle: _text(item, const ['description', 'type', 'category']) ?? '—',
              trailing: '',
            ),
          ),
      ],
    );
  }
}

class _SmallRow extends StatelessWidget {
  const _SmallRow({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.trailing,
  });

  final IconData icon;
  final Color color;
  final String title;
  final String subtitle;
  final String trailing;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        child: Row(
          children: [
            CircleAvatar(
              radius: 10,
              backgroundColor: color.withValues(alpha: .11),
              child: Icon(icon, size: 11, color: color),
            ),
            const SizedBox(width: 6),
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
                      fontSize: 7.5,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    subtitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 6.5,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 4),
            Text(
              trailing,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 6.4,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
}

class _SmallEmpty extends StatelessWidget {
  const _SmallEmpty({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Center(
        child: Text(
          text,
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 7.4,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );
}

class _SelectedWorkflowPanel extends StatelessWidget {
  const _SelectedWorkflowPanel({
    required this.workflow,
    required this.approvals,
    required this.connected,
    required this.onRefresh,
    required this.onNavigate,
  });

  final _WorkflowRecord? workflow;
  final List<Map<String, Object?>> approvals;
  final bool connected;
  final VoidCallback? onRefresh;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('selected-workflow-panel'),
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 9),
        child: workflow == null
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _RightHeader(
                    title: _tr(context, 'Seçili İş Akışı', 'Selected Workflow'),
                  ),
                  Expanded(
                    child: _SmallEmpty(
                      text: _tr(
                        context,
                        'Seçilebilir iş akışı yok.',
                        'No workflow is available to select.',
                      ),
                    ),
                  ),
                  OutlinedButton.icon(
                    onPressed: connected ? onRefresh : null,
                    icon: const Icon(Icons.refresh, size: 14),
                    label: Text(_tr(context, 'Yenile', 'Refresh')),
                  ),
                ],
              )
            : _SelectedContent(
                workflow: workflow!,
                approvals: approvals,
                onNavigate: onNavigate,
              ),
      );
}

class _SelectedContent extends StatelessWidget {
  const _SelectedContent({
    required this.workflow,
    required this.approvals,
    required this.onNavigate,
  });

  final _WorkflowRecord workflow;
  final List<Map<String, Object?>> approvals;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final matchingApprovals = approvals.where((item) {
      final id = _text(
        item,
        const ['job_id', 'workflow_id', 'execution_id'],
      );
      return id != null && id == workflow.id;
    }).take(2).toList(growable: false);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        _RightHeader(
          title: _tr(context, 'Seçili İş Akışı', 'Selected Workflow'),
        ),
        Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
        SizedBox(
          height: 62,
          child: Row(
            children: [
              _RoundIcon(
                icon: _workflowIcon(workflow.kind),
                accent: IlaiosTheme.enterpriseCyan,
                size: 34,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      workflow.name,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 10.8,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      workflow.subtitle,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 7.2,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                  color: (workflow.completed
                          ? IlaiosTheme.success
                          : IlaiosTheme.enterpriseCyan)
                      .withValues(alpha: .10),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  workflow.completed
                      ? _tr(context, 'Tamamlandı', 'Completed')
                      : _tr(context, 'Aktif', 'Active'),
                  style: TextStyle(
                    fontSize: 7,
                    color: workflow.completed
                        ? IlaiosTheme.success
                        : IlaiosTheme.enterpriseCyan,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
        ),
        Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
        SizedBox(
          height: 104,
          child: Padding(
            padding: const EdgeInsets.symmetric(vertical: 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _InfoLine(
                        label: _tr(context, 'Mevcut Aşama', 'Current Stage'),
                        value: workflow.phase,
                        accent: _phaseColor(workflow.phase),
                      ),
                      _InfoLine(
                        label: _tr(context, 'İlerleme', 'Progress'),
                        value: workflow.progress == null
                            ? '—'
                            : '${(workflow.progress! * 100).round()}%',
                      ),
                      if (workflow.progress != null)
                        ClipRRect(
                          borderRadius: BorderRadius.circular(2),
                          child: LinearProgressIndicator(
                            value: workflow.progress,
                            minHeight: 4,
                          ),
                        ),
                    ],
                  ),
                ),
                VerticalDivider(
                  width: 16,
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _InfoLine(
                        label: _tr(context, 'Sahip', 'Owner'),
                        value: workflow.owner,
                      ),
                      _InfoLine(
                        label: _tr(context, 'Oluşturulma Tarihi', 'Created'),
                        value: workflow.created,
                      ),
                      _InfoLine(
                        label: _tr(context, 'ETA / Son Tarih', 'ETA / Due'),
                        value: workflow.eta,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        _RightSection(
          title: _tr(
            context,
            'Blokajlar & Bekleyen Onaylar',
            'Blockers & Pending Approvals',
          ),
          badge: matchingApprovals.length,
          height: 106,
          child: matchingApprovals.isEmpty
              ? _SmallEmpty(
                  text: _tr(
                    context,
                    'Doğrulanmış bekleyen onay yok.',
                    'No verified pending approvals.',
                  ),
                )
              : Column(
                  children: [
                    for (final item in matchingApprovals)
                      Expanded(
                        child: _SmallRow(
                          icon: Icons.schedule,
                          color: IlaiosTheme.warning,
                          title: _text(
                                item,
                                const ['title', 'reason', 'action', 'request_type'],
                              ) ??
                              '—',
                          subtitle: _text(
                                item,
                                const ['approver', 'owner', 'requested_by'],
                              ) ??
                              '—',
                          trailing: _text(
                                item,
                                const ['priority', 'risk', 'severity'],
                              ) ??
                              '—',
                        ),
                      ),
                  ],
                ),
        ),
        const SizedBox(height: 8),
        _RightSection(
          title: _tr(context, 'Aşama Akışı', 'Stage Flow'),
          height: 92,
          child: _StageFlow(phase: workflow.phase),
        ),
        const Spacer(),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                onPressed: () => _showWorkflowDetail(context, workflow),
                icon: const Icon(Icons.open_in_new, size: 13),
                label: Text(_tr(context, 'Detayı Aç', 'Open Details')),
                style: FilledButton.styleFrom(
                  textStyle: const TextStyle(fontSize: 8.3),
                  minimumSize: const Size.fromHeight(34),
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: () => onNavigate(DesktopSection.approvals),
                icon: const Icon(Icons.task_alt_outlined, size: 13),
                label: Text(_tr(context, 'Onayları Gör', 'View Approvals')),
                style: OutlinedButton.styleFrom(
                  textStyle: const TextStyle(fontSize: 8.3),
                  minimumSize: const Size.fromHeight(34),
                ),
              ),
            ),
          ],
        ),
        const SizedBox(height: 8),
        OutlinedButton.icon(
          key: const Key('go-live-workspace'),
          onPressed: () => onNavigate(DesktopSection.liveWorkspace),
          icon: const Icon(Icons.hub_outlined, size: 13),
          label: Text(
            _tr(context, 'Canlı Çalışma Alanına Git', 'Go to Live Workspace'),
          ),
          style: OutlinedButton.styleFrom(
            textStyle: const TextStyle(fontSize: 8.6),
            minimumSize: const Size.fromHeight(34),
          ),
        ),
      ],
    );
  }
}

class _RightHeader extends StatelessWidget {
  const _RightHeader({required this.title});
  final String title;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 34,
        child: Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: const TextStyle(
                  fontSize: 10.4,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ),
      );
}

class _RightSection extends StatelessWidget {
  const _RightSection({
    required this.title,
    required this.height,
    required this.child,
    this.badge,
  });

  final String title;
  final double height;
  final Widget child;
  final int? badge;

  @override
  Widget build(BuildContext context) => Container(
        height: height,
        decoration: BoxDecoration(
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(7),
          color: Theme.of(context)
              .colorScheme
              .surfaceContainerLowest
              .withValues(alpha: .35),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 31,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        title,
                        style: const TextStyle(
                          fontSize: 8.6,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    if (badge != null && badge! > 0)
                      CircleAvatar(
                        radius: 8,
                        backgroundColor: IlaiosTheme.danger,
                        child: Text(
                          '$badge',
                          style: const TextStyle(fontSize: 7, color: Colors.white),
                        ),
                      ),
                  ],
                ),
              ),
            ),
            Expanded(child: child),
          ],
        ),
      );
}

class _StageFlow extends StatelessWidget {
  const _StageFlow({required this.phase});
  final String phase;

  @override
  Widget build(BuildContext context) {
    const stages = <(String, String, String)>[
      ('plan', 'Planlama', 'Planning'),
      ('exec', 'Yürütme', 'Execution'),
      ('verif', 'Doğrulama', 'Verification'),
      ('deliver', 'Teslimat', 'Delivery'),
      ('complete', 'Tamamlandı', 'Completed'),
    ];
    final normalized = _normalize(phase);
    var current = stages.indexWhere((stage) => normalized.contains(stage.$1));
    if (normalized.contains('run')) current = 1;
    if (normalized.contains('accept') || normalized.contains('done')) current = 4;
    if (current < 0) current = 0;

    return Padding(
      padding: const EdgeInsets.fromLTRB(8, 4, 8, 5),
      child: Row(
        children: [
          for (var index = 0; index < stages.length; index++) ...[
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  CircleAvatar(
                    radius: 11,
                    backgroundColor: index < current
                        ? IlaiosTheme.success.withValues(alpha: .12)
                        : index == current
                            ? IlaiosTheme.coreBlue.withValues(alpha: .14)
                            : Theme.of(context)
                                .colorScheme
                                .surfaceContainerHighest,
                    child: index < current
                        ? const Icon(
                            Icons.check,
                            size: 12,
                            color: IlaiosTheme.success,
                          )
                        : Text(
                            '${index + 1}',
                            style: TextStyle(
                              fontSize: 7.5,
                              color: index == current
                                  ? IlaiosTheme.coreBlue
                                  : Theme.of(context)
                                      .colorScheme
                                      .onSurfaceVariant,
                            ),
                          ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _tr(context, stages[index].$2, stages[index].$3),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      fontSize: 6.5,
                      color: index == current
                          ? IlaiosTheme.coreBlue
                          : Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            if (index < stages.length - 1)
              Container(
                width: 18,
                height: 1.5,
                color: index < current
                    ? IlaiosTheme.enterpriseCyan
                    : Theme.of(context).colorScheme.outlineVariant,
              ),
          ],
        ],
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({required this.label, required this.value, this.accent});
  final String label;
  final String value;
  final Color? accent;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          SizedBox(
            width: 86,
            child: Text(
              label,
              style: TextStyle(
                fontSize: 7.3,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Expanded(
            child: Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 7.8,
                fontWeight: FontWeight.w600,
                color: accent,
              ),
            ),
          ),
        ],
      );
}

class _RoundIcon extends StatelessWidget {
  const _RoundIcon({required this.icon, required this.accent, this.size = 26});
  final IconData icon;
  final Color accent;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          color: accent.withValues(alpha: .11),
          shape: BoxShape.circle,
        ),
        child: Icon(icon, size: size * .54, color: accent),
      );
}

class _Tag extends StatelessWidget {
  const _Tag({required this.text, required this.color});
  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Align(
        alignment: Alignment.centerLeft,
        child: Container(
          constraints: const BoxConstraints(maxWidth: 76),
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2.5),
          decoration: BoxDecoration(
            color: color.withValues(alpha: .10),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            text,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 7.1, color: color),
          ),
        ),
      );
}

class _Card extends StatelessWidget {
  const _Card({
    required this.child,
    this.padding = const EdgeInsets.all(10),
    this.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;
  final Key? key;

  @override
  Widget build(BuildContext context) => Container(
        key: key,
        padding: padding,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: child,
      );
}

class _WorkflowRecord {
  const _WorkflowRecord({
    required this.id,
    required this.name,
    required this.subtitle,
    required this.kind,
    required this.phase,
    required this.progress,
    required this.owner,
    required this.priority,
    required this.eta,
    required this.created,
    required this.active,
    required this.awaitingApproval,
    required this.completed,
    required this.archived,
  });

  final String id;
  final String name;
  final String subtitle;
  final String kind;
  final String phase;
  final double? progress;
  final String owner;
  final String priority;
  final String eta;
  final String created;
  final bool active;
  final bool awaitingApproval;
  final bool completed;
  final bool archived;
}

const String _allFilter = '__all__';

List<_WorkflowRecord> _workflowRecords(OperationalSnapshot snapshot) {
  final latestById = <String, Map<String, Object?>>{};
  for (final event in snapshot.liveEvents.reversed) {
    final id = _text(
      event,
      const ['workflow_id', 'job_id', 'execution_id', 'request_id', 'id'],
    );
    if (id == null || latestById.containsKey(id)) continue;
    latestById[id] = event;
  }
  return latestById.entries.map((entry) {
    final item = entry.value;
    final phase =
        _text(item, const ['phase', 'stage', 'workflow_phase', 'status']) ?? '—';
    final normalized = _normalize(phase);
    final eventName = _text(item, const ['event', 'action', 'type']) ?? '';
    final state = '$normalized ${_normalize(eventName)}';
    final completed = state.contains('complete') ||
        state.contains('done') ||
        state.contains('deliver') ||
        state.contains('accept');
    final archived = state.contains('archiv');
    final awaitingApproval =
        state.contains('approval') || state.contains('pending');
    return _WorkflowRecord(
      id: entry.key,
      name: _text(
            item,
            const ['workflow_name', 'project_name', 'title', 'objective', 'name'],
          ) ??
          entry.key,
      subtitle: _text(
            item,
            const ['description', 'summary', 'goal', 'objective', 'event', 'action'],
          ) ??
          '—',
      kind: _text(
            item,
            const ['workflow_type', 'factory', 'kind', 'type', 'category'],
          ) ??
          '—',
      phase: phase,
      progress: _progress(item),
      owner: _text(
            item,
            const ['owner', 'assignee', 'worker', 'agent_name', 'agent'],
          ) ??
          '—',
      priority: _text(item, const ['priority', 'risk', 'severity']) ?? '—',
      eta: _text(
            item,
            const ['eta', 'due_at', 'deadline', 'end_date', 'target_date'],
          ) ??
          '—',
      created: _text(
            item,
            const ['created_at', 'created', 'timestamp', 'started_at'],
          ) ??
          '—',
      active: !completed && !archived,
      awaitingApproval: awaitingApproval,
      completed: completed,
      archived: archived,
    );
  }).toList(growable: false);
}

List<String> _filterValues(Iterable<String> values) {
  final unique = values
      .where((value) => value.trim().isNotEmpty && value != '—')
      .toSet()
      .toList(growable: false)
    ..sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
  return unique;
}

List<Map<String, Object?>> _approvalItems(OperationalSnapshot snapshot) {
  for (final key in const ['pending_approvals', 'approvals', 'requests', 'items']) {
    final result = _mapList(snapshot.governanceState[key]);
    if (result.isNotEmpty) return result;
  }
  return const <Map<String, Object?>>[];
}

List<Map<String, Object?>> _templateItems(OperationalSnapshot snapshot) {
  for (final source in <Map<String, Object?>>[
    snapshot.schedulerState,
    snapshot.governanceState,
  ]) {
    for (final key in const ['workflow_templates', 'templates']) {
      final result = _mapList(source[key]);
      if (result.isNotEmpty) return result;
    }
  }
  return const <Map<String, Object?>>[];
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return value.whereType<Map<String, Object?>>().toList(growable: false);
}

String? _text(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return '$value';
  }
  return null;
}

int? _authoritativeInt(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is int) return value;
    if (value is num) return value.round();
    if (value is List<Object?>) return value.length;
  }
  return null;
}

double? _progress(Map<String, Object?> source) {
  for (final key in const ['progress', 'progress_percent', 'percentage', 'percent']) {
    final value = source[key];
    if (value is num) {
      final raw = value.toDouble();
      return (raw > 1 ? raw / 100 : raw).clamp(0.0, 1.0);
    }
    if (value is String) {
      final parsed = double.tryParse(value.replaceAll('%', '').trim());
      if (parsed != null) {
        return (parsed > 1 ? parsed / 100 : parsed).clamp(0.0, 1.0);
      }
    }
  }
  return null;
}

int _stageCount(List<_WorkflowRecord> workflows, String token) => workflows
    .where((item) => _normalize(item.phase).contains(token))
    .length;

String _normalize(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');

Color _phaseColor(String phase) {
  final value = _normalize(phase);
  if (value.contains('verif') || value.contains('test')) {
    return IlaiosTheme.violet;
  }
  if (value.contains('deliver')) return IlaiosTheme.warning;
  if (value.contains('complete') ||
      value.contains('done') ||
      value.contains('accept')) {
    return IlaiosTheme.success;
  }
  if (value.contains('plan')) return IlaiosTheme.enterpriseCyan;
  return IlaiosTheme.coreBlue;
}

Color _priorityColor(String priority) {
  final value = _normalize(priority);
  if (value.contains('high') ||
      value.contains('critical') ||
      value.contains('yuksek')) {
    return IlaiosTheme.danger;
  }
  if (value.contains('medium') || value.contains('orta')) {
    return IlaiosTheme.warning;
  }
  if (value.contains('low') || value.contains('dusuk')) {
    return IlaiosTheme.coreBlue;
  }
  return IlaiosTheme.enterpriseCyan;
}

IconData _workflowIcon(String kind) {
  final value = _normalize(kind);
  if (value.contains('video')) return Icons.smart_display_outlined;
  if (value.contains('web')) return Icons.language_outlined;
  if (value.contains('software') ||
      value.contains('app') ||
      value.contains('code')) {
    return Icons.code_outlined;
  }
  if (value.contains('security')) return Icons.shield_outlined;
  if (value.contains('research')) return Icons.query_stats_outlined;
  return Icons.account_tree_outlined;
}

String _tr(BuildContext context, String tr, String en) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish ? tr : en;

void _showWorkflowDetail(BuildContext context, _WorkflowRecord workflow) {
  showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(workflow.name),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(workflow.subtitle),
            const SizedBox(height: 12),
            Text('${_tr(context, 'Kimlik', 'ID')}: ${workflow.id}'),
            Text('${_tr(context, 'Aşama', 'Stage')}: ${workflow.phase}'),
            Text('${_tr(context, 'Sahip', 'Owner')}: ${workflow.owner}'),
            Text(
              '${_tr(context, 'İlerleme', 'Progress')}: '
              '${workflow.progress == null ? '—' : '${(workflow.progress! * 100).round()}%'}',
            ),
            Text('${_tr(context, 'ETA / Son Tarih', 'ETA / Due')}: ${workflow.eta}'),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(_tr(context, 'Kapat', 'Close')),
        ),
      ],
    ),
  );
}
