import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'agent_provisioning_scope.dart';

/// Agents is a truth-preserving projection of the canonical registry, runtime,
/// scheduler and live-event state. Desktop never invents an agent authority.
class ReferenceAgentsView extends StatefulWidget {
  const ReferenceAgentsView({
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
  State<ReferenceAgentsView> createState() => _ReferenceAgentsViewState();
}

class _ReferenceAgentsViewState extends State<ReferenceAgentsView> {
  static const int _pageSize = 6;
  static const String _all = '__all__';

  final TextEditingController _searchController = TextEditingController();
  int _tab = 0;
  int _selected = -1;
  int _page = 0;
  String _query = '';
  String _role = _all;
  String _state = _all;
  String _capability = _all;
  bool _provisioning = false;

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
      _role = _all;
      _state = _all;
      _capability = _all;
      _resetPosition();
    });
  }

  bool get _hasFilters =>
      _query.trim().isNotEmpty ||
      _role != _all ||
      _state != _all ||
      _capability != _all;

  List<_AgentRecord> _filtered(List<_AgentRecord> source) {
    Iterable<_AgentRecord> output = source;
    if (_tab == 1) output = output.where((item) => item.state == _AgentState.active);
    if (_tab == 2) output = output.where((item) => item.state == _AgentState.busy);
    if (_tab == 3) output = output.where((item) => item.state == _AgentState.idle);
    if (_tab == 4) output = output.where((item) => item.state == _AgentState.review);
    if (_tab == 5) output = output.where((item) => item.state == _AgentState.offline);
    if (_role != _all) output = output.where((item) => item.role == _role);
    if (_state != _all) {
      output = output.where((item) => item.state.name == _state);
    }
    if (_capability != _all) {
      output = output.where((item) => item.capabilities.contains(_capability));
    }
    final q = _query.trim().toLowerCase();
    if (q.isNotEmpty) {
      output = output.where(
        (item) =>
            '${item.name} ${item.id} ${item.role} ${item.team} '
                    '${item.currentTask} ${item.capabilities.join(' ')}'
                .toLowerCase()
                .contains(q),
      );
    }
    return output.toList(growable: false);
  }

  Future<void> _provisionCanonicalAgent() async {
    if (_provisioning) return;
    final provisioner = AgentProvisioningScope.maybeOf(context);
    if (provisioner == null) {
      _notice(
        _tr(
          context,
          'Ajan provision işlemi için doğrulanmış kullanıcı oturumu gerekiyor.',
          'A verified user session is required to provision an agent.',
        ),
      );
      return;
    }

    final candidates = _canonicalCandidates(widget.snapshot)
        .where((item) => !item.registered && item.authorityMatchesCanonical)
        .toList(growable: false);
    if (candidates.isEmpty) {
      _notice(
        _tr(
          context,
          'Provision edilebilecek kayıtlı olmayan canonical ajan yok.',
          'No unregistered canonical agent is available to provision.',
        ),
      );
      return;
    }

    final selected = await showDialog<_CanonicalAgentCandidate>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(_tr(context, 'Canonical Ajan Provision Et', 'Provision Canonical Agent')),
        content: SizedBox(
          width: 560,
          height: math.min(460.0, candidates.length * 72.0),
          child: ListView.separated(
            itemCount: candidates.length,
            separatorBuilder: (context, index) => const Divider(height: 1),
            itemBuilder: (_, index) {
              final candidate = candidates[index];
              return ListTile(
                key: ValueKey('canonical-agent-${candidate.id}'),
                leading: const Icon(Icons.smart_toy_outlined),
                title: Text(candidate.alias),
                subtitle: Text(
                  '${candidate.role} · ${candidate.team}\n${candidate.id}',
                ),
                isThreeLine: true,
                trailing: Text(candidate.readiness),
                onTap: () => Navigator.of(dialogContext).pop(candidate),
              );
            },
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(_tr(context, 'Vazgeç', 'Cancel')),
          ),
        ],
      ),
    );
    if (selected == null || !mounted) return;

    setState(() => _provisioning = true);
    try {
      await provisioner(selected.id);
      if (!mounted) return;
      _notice(
        _tr(
          context,
          '${selected.alias} canonical ajanı provision edildi.',
          '${selected.alias} canonical agent was provisioned.',
        ),
      );
      widget.onRefreshRequested?.call();
    } on Object catch (error) {
      if (!mounted) return;
      _notice(error.toString());
    } finally {
      if (mounted) setState(() => _provisioning = false);
    }
  }

  void _notice(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), duration: const Duration(seconds: 2)),
    );
  }

  @override
  Widget build(BuildContext context) {
    final allAgents = _agentRecords(widget.snapshot);
    final filtered = _filtered(allAgents);
    final pageCount = math.max(1, (filtered.length / _pageSize).ceil());
    final effectivePage = _page.clamp(0, pageCount - 1);
    final start = effectivePage * _pageSize;
    final end = math.min(start + _pageSize, filtered.length);
    final pageAgents = start >= filtered.length
        ? const <_AgentRecord>[]
        : filtered.sublist(start, end);
    final selected = pageAgents.isEmpty || _selected < 0
        ? null
        : pageAgents[_selected.clamp(0, pageAgents.length - 1)];
    final assignments = _pendingAssignments(widget.snapshot);
    final reviews = _pendingReviews(widget.snapshot, selected?.id);
    final roleOptions = _unique(allAgents.map((item) => item.role));
    final capabilityOptions = _unique(
      allAgents.expand((item) => item.capabilities),
    );

    return Container(
      key: const Key('reference-agents-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(14, 10, 12, 8),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final rightWidth = (constraints.maxWidth * .315).clamp(320.0, 410.0);
          return Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _Header(
                      connected: widget.projection.connected,
                      onRefresh: widget.onRefreshRequested,
                    ),
                    const SizedBox(height: 7),
                    _Metrics(snapshot: widget.snapshot, agents: allAgents),
                    const SizedBox(height: 8),
                    Expanded(
                      child: _TablePanel(
                        agents: pageAgents,
                        totalFiltered: filtered.length,
                        totalAgents: allAgents.length,
                        page: effectivePage,
                        pageCount: pageCount,
                        tab: _tab,
                        selected: selected,
                        searchController: _searchController,
                        role: _role,
                        state: _state,
                        capability: _capability,
                        roleOptions: roleOptions,
                        capabilityOptions: capabilityOptions,
                        hasFilters: _hasFilters,
                        provisioning: _provisioning,
                        canProvision:
                            AgentProvisioningScope.maybeOf(context) != null,
                        onTab: (value) => setState(() {
                          _tab = value;
                          _resetPosition();
                        }),
                        onQuery: (value) => setState(() {
                          _query = value;
                          _resetPosition();
                        }),
                        onRole: (value) => setState(() {
                          _role = value;
                          _resetPosition();
                        }),
                        onState: (value) => setState(() {
                          _state = value;
                          _resetPosition();
                        }),
                        onCapability: (value) => setState(() {
                          _capability = value;
                          _resetPosition();
                        }),
                        onClear: _clearFilters,
                        onSelect: (value) => setState(() => _selected = value),
                        onPrevious: effectivePage == 0
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
                        onProvision: _provisionCanonicalAgent,
                        onRefresh: widget.onRefreshRequested,
                      ),
                    ),
                    if (widget.snapshot.liveEvents.isNotEmpty ||
                        assignments.isNotEmpty) ...[
                      const SizedBox(height: 8),
                      SizedBox(
                        height: 145,
                        child: _BottomPanels(
                          snapshot: widget.snapshot,
                          agents: allAgents,
                          assignments: assignments,
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
                  child: _SelectedPanel(
                  agent: selected,
                  reviews: reviews,
                  connected: widget.projection.connected,
                  onRefresh: widget.onRefreshRequested,
                    onWorkspace: () =>
                        widget.onNavigate(DesktopSection.liveWorkspace),
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.connected, required this.onRefresh});
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
                    _tr(context, 'Ajanlar', 'Agents'),
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
                      'Canonical ajan durumunu, kapasiteyi ve gerçek runtime telemetrisini izleyin.',
                      'Monitor canonical agent state, capacity and real runtime telemetry.',
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
              key: const Key('agents-refresh'),
              onPressed: connected ? onRefresh : null,
              tooltip: _tr(context, 'Yenile', 'Refresh'),
              icon: const Icon(Icons.refresh_rounded, size: 18),
            ),
          ],
        ),
      );
}

class _Metrics extends StatelessWidget {
  const _Metrics({required this.snapshot, required this.agents});

  final OperationalSnapshot snapshot;
  final List<_AgentRecord> agents;

  @override
  Widget build(BuildContext context) {
    final total = _int(snapshot.agentState, const ['canonical_count']) ??
        (agents.isEmpty ? null : agents.length);
    final active = agents.where((item) => item.state == _AgentState.active).length;
    final busy = agents.where((item) => item.state == _AgentState.busy).length;
    final idle = agents.where((item) => item.state == _AgentState.idle).length;

    final summary = <(IconData, String, String, Color)>[
      (
        Icons.groups_2_outlined,
        _tr(context, 'Toplam', 'Total'),
        total?.toString() ?? '—',
        Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      (
        Icons.circle,
        _tr(context, 'Aktif', 'Active'),
        agents.isEmpty ? '—' : '$active',
        active > 0
            ? IlaiosTheme.success
            : Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      (
        Icons.hexagon_outlined,
        _tr(context, 'Meşgul', 'Busy'),
        agents.isEmpty ? '—' : '$busy',
        busy > 0
            ? IlaiosTheme.warning
            : Theme.of(context).colorScheme.onSurfaceVariant,
      ),
      (
        Icons.person_outline_rounded,
        _tr(context, 'Boşta', 'Idle'),
        agents.isEmpty ? '—' : '$idle',
        Theme.of(context).colorScheme.onSurfaceVariant,
      ),
    ];

    return SizedBox(
      key: const Key('agents-metrics'),
      height: 50,
      child: _Panel(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        child: Row(
          children: [
            for (var index = 0; index < summary.length; index++) ...[
              if (index > 0)
                Container(
                  width: 1,
                  height: 24,
                  margin: const EdgeInsets.symmetric(horizontal: 15),
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
              Icon(summary[index].$1, size: 14, color: summary[index].$4),
              const SizedBox(width: 5),
              Text(
                summary[index].$2,
                style: TextStyle(
                  fontSize: 8.2,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
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

enum _ToolbarAction { refresh }

class _TablePanel extends StatelessWidget {
  const _TablePanel({
    required this.agents,
    required this.totalFiltered,
    required this.totalAgents,
    required this.page,
    required this.pageCount,
    required this.tab,
    required this.selected,
    required this.searchController,
    required this.role,
    required this.state,
    required this.capability,
    required this.roleOptions,
    required this.capabilityOptions,
    required this.hasFilters,
    required this.provisioning,
    required this.canProvision,
    required this.onTab,
    required this.onQuery,
    required this.onRole,
    required this.onState,
    required this.onCapability,
    required this.onClear,
    required this.onSelect,
    required this.onPrevious,
    required this.onNext,
    required this.onProvision,
    required this.onRefresh,
  });

  final List<_AgentRecord> agents;
  final int totalFiltered;
  final int totalAgents;
  final int page;
  final int pageCount;
  final int tab;
  final _AgentRecord? selected;
  final TextEditingController searchController;
  final String role;
  final String state;
  final String capability;
  final List<String> roleOptions;
  final List<String> capabilityOptions;
  final bool hasFilters;
  final bool provisioning;
  final bool canProvision;
  final ValueChanged<int> onTab;
  final ValueChanged<String> onQuery;
  final ValueChanged<String> onRole;
  final ValueChanged<String> onState;
  final ValueChanged<String> onCapability;
  final VoidCallback onClear;
  final ValueChanged<int> onSelect;
  final VoidCallback? onPrevious;
  final VoidCallback? onNext;
  final VoidCallback onProvision;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) {
    final first = totalFiltered == 0 ? 0 : page * _ReferenceAgentsViewState._pageSize + 1;
    final last = math.min((page + 1) * _ReferenceAgentsViewState._pageSize, totalFiltered);
    return _Panel(
      key: const Key('agents-table-panel'),
      padding: EdgeInsets.zero,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            height: 38,
            child: Row(
              children: [
                for (final item in <(String, String)>[
                  ('Tümü', 'All'),
                  ('Aktif', 'Active'),
                  ('Meşgul', 'Busy'),
                  ('Boşta', 'Idle'),
                  ('İncelemede', 'In Review'),
                  ('Devre Dışı', 'Offline'),
                ].indexed)
                  _Tab(
                    label: _tr(context, item.$2.$1, item.$2.$2),
                    selected: tab == item.$1,
                    onTap: () => onTab(item.$1),
                  ),
                const Spacer(),
                SizedBox(
                  height: 28,
                  child: FilledButton.icon(
                    key: const Key('new-agent-button'),
                    onPressed: provisioning || !canProvision ? null : onProvision,
                    icon: provisioning
                        ? const SizedBox(width: 13, height: 13, child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.add, size: 15),
                    label: Text(_tr(context, 'Yeni Ajan', 'New Agent')),
                  ),
                ),
                PopupMenuButton<_ToolbarAction>(
                  key: const Key('agents-more-menu'),
                  tooltip: _tr(context, 'Diğer', 'More'),
                  onSelected: (action) {
                    switch (action) {
                      case _ToolbarAction.refresh:
                        onRefresh?.call();
                    }
                  },
                  itemBuilder: (_) => [
                    PopupMenuItem(
                      value: _ToolbarAction.refresh,
                      enabled: onRefresh != null,
                      child: Text(_tr(context, 'Yenile', 'Refresh')),
                    ),
                  ],
                  icon: const Icon(Icons.more_vert, size: 16),
                ),
              ],
            ),
          ),
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          SizedBox(
            height: 43,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
              child: Row(
                children: [
                  Expanded(
                    flex: 3,
                    child: TextField(
                      key: const Key('agent-search'),
                      controller: searchController,
                      onChanged: onQuery,
                      decoration: InputDecoration(
                        isDense: true,
                        hintText: _tr(context, 'Ajan ara...', 'Search agents...'),
                        prefixIcon: const Icon(Icons.search, size: 15),
                      ),
                      style: const TextStyle(fontSize: 9),
                    ),
                  ),
                  const SizedBox(width: 7),
                  Expanded(child: _Filter(id: 'role', label: _tr(context, 'Rol Türü', 'Role Type'), value: role, options: roleOptions, onChanged: onRole)),
                  const SizedBox(width: 7),
                  Expanded(child: _Filter(id: 'state', label: _tr(context, 'Durum Türü', 'Status Type'), value: state, options: _AgentState.values.map((e) => e.name).toList(growable: false), onChanged: onState)),
                  const SizedBox(width: 7),
                  Expanded(child: _Filter(id: 'capability', label: _tr(context, 'Yetkinlik Türü', 'Capability Type'), value: capability, options: capabilityOptions, onChanged: onCapability)),
                  const SizedBox(width: 7),
                  OutlinedButton(
                    key: const Key('agent-clear-filters'),
                    onPressed: hasFilters ? onClear : null,
                    child: Text(_tr(context, 'Filtreleri Temizle', 'Clear Filters')),
                  ),
                ],
              ),
            ),
          ),
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          const _AgentHeader(),
          Expanded(
            child: agents.isEmpty
                ? _EmptyAgents()
                : Column(
                    children: [
                      for (var index = 0; index < agents.length; index++)
                        Expanded(
                          child: _AgentRow(
                            record: agents[index],
                            selected: selected?.id == agents[index].id,
                            onTap: () => onSelect(index),
                          ),
                        ),
                    ],
                  ),
          ),
          SizedBox(
            height: 29,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Row(
                children: [
                  Text(
                    totalFiltered == 0
                        ? _tr(context, '0 ajan', '0 agents')
                        : '$first-$last / $totalFiltered ${_tr(context, 'ajan', 'agents')} · $totalAgents ${_tr(context, 'toplam', 'total')}',
                    style: const TextStyle(fontSize: 8),
                  ),
                  const Spacer(),
                  IconButton(key: const Key('agent-page-previous'), onPressed: onPrevious, icon: const Icon(Icons.chevron_left, size: 14)),
                  Container(
                    key: const Key('agent-page-indicator'),
                    height: 21,
                    constraints: const BoxConstraints(minWidth: 34),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(border: Border.all(color: IlaiosTheme.enterpriseCyan), borderRadius: BorderRadius.circular(4)),
                    child: Text('${page + 1}/$pageCount', style: const TextStyle(fontSize: 8)),
                  ),
                  IconButton(key: const Key('agent-page-next'), onPressed: onNext, icon: const Icon(Icons.chevron_right, size: 14)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Filter extends StatelessWidget {
  const _Filter({required this.id, required this.label, required this.value, required this.options, required this.onChanged});
  final String id;
  final String label;
  final String value;
  final List<String> options;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) => PopupMenuButton<String>(
        key: ValueKey('agent-filter-$id'),
        initialValue: value,
        onSelected: onChanged,
        itemBuilder: (_) => [
          PopupMenuItem(value: _ReferenceAgentsViewState._all, child: Text(_tr(context, 'Tümü', 'All'))),
          for (final option in options)
            PopupMenuItem(value: option, child: Text(_filterLabel(context, id, option))),
        ],
        child: Container(
          height: 28,
          padding: const EdgeInsets.symmetric(horizontal: 8),
          decoration: BoxDecoration(border: Border.all(color: Theme.of(context).colorScheme.outlineVariant), borderRadius: BorderRadius.circular(5)),
          child: Row(
            children: [
              Expanded(child: Text(value == _ReferenceAgentsViewState._all ? '$label: ${_tr(context, 'Tümü', 'All')}' : _filterLabel(context, id, value), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.7))),
              const Icon(Icons.keyboard_arrow_down, size: 14),
            ],
          ),
        ),
      );
}

class _AgentHeader extends StatelessWidget {
  const _AgentHeader();
  @override
  Widget build(BuildContext context) => SizedBox(
        height: 27,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Row(
            children: [
              Expanded(flex: 24, child: Text(_tr(context, 'Ajan', 'Agent'), style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600))),
              Expanded(flex: 17, child: Text(_tr(context, 'Uzmanlık', 'Specialty'), style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600))),
              Expanded(flex: 12, child: Text(_tr(context, 'Durum', 'Status'), style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600))),
              Expanded(flex: 20, child: Text(_tr(context, 'Mevcut Görev', 'Current Task'), style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600))),
              Expanded(flex: 14, child: Text(_tr(context, 'Kapasite', 'Capacity'), style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600))),
              Expanded(flex: 13, child: Text(_tr(context, 'Başarı Oranı', 'Success Rate'), style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600))),
              Expanded(flex: 13, child: Text(_tr(context, 'Son Etkinlik', 'Last Activity'), style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600))),
            ],
          ),
        ),
      );
}

class _AgentRow extends StatelessWidget {
  const _AgentRow({required this.record, required this.selected, required this.onTap});
  final _AgentRecord record;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = _stateColor(record.state);
    return InkWell(
      key: ValueKey('agent-row-${record.id}'),
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
        padding: const EdgeInsets.symmetric(horizontal: 6),
        decoration: BoxDecoration(
          color: selected ? IlaiosTheme.enterpriseCyan.withValues(alpha: .06) : null,
          border: selected ? Border.all(color: IlaiosTheme.enterpriseCyan.withValues(alpha: .75)) : null,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          children: [
            Expanded(
              flex: 24,
              child: Row(
                children: [
                  CircleAvatar(radius: 13, backgroundColor: _roleColor(record.role).withValues(alpha: .12), child: Icon(Icons.smart_toy_outlined, size: 14, color: _roleColor(record.role))),
                  const SizedBox(width: 7),
                  Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(record.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.3, fontWeight: FontWeight.w600)),
                  ])),
                ],
              ),
            ),
            Expanded(flex: 17, child: Text(record.role, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.7))),
            Expanded(flex: 12, child: Row(children: [Container(width: 6, height: 6, decoration: BoxDecoration(color: color, shape: BoxShape.circle)), const SizedBox(width: 5), Expanded(child: Text(_stateLabel(context, record.state), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 7.4, color: color)))])),
            Expanded(flex: 20, child: Text(record.currentTask.isEmpty ? _tr(context, 'Görev yok', 'No task') : record.currentTask, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.5))),
            Expanded(
              flex: 14,
              child: _Progress(
                key: ValueKey('agent-capacity-${record.id}'),
                value: record.capacity,
              ),
            ),
            Expanded(flex: 13, child: Text(record.successRate == null ? '—' : '${(record.successRate! * 100).toStringAsFixed(1)}%', style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w600))),
            Expanded(flex: 13, child: Text(record.lastActivity, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.2))),
          ],
        ),
      ),
    );
  }
}

class _SelectedPanel extends StatelessWidget {
  const _SelectedPanel({required this.agent, required this.reviews, required this.connected, required this.onRefresh, required this.onWorkspace});
  final _AgentRecord? agent;
  final List<Map<String, Object?>> reviews;
  final bool connected;
  final VoidCallback? onRefresh;
  final VoidCallback onWorkspace;

  @override
  Widget build(BuildContext context) => _Panel(
        key: const Key('selected-agent-panel'),
        padding: const EdgeInsets.all(10),
        child: agent == null
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(_tr(context, 'Seçili Ajan', 'Selected Agent'), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700)),
                  Expanded(child: Center(child: Text(_tr(context, 'Doğrulanmış ajan kaydı yok', 'No verified agent record')))),
                  OutlinedButton.icon(onPressed: connected ? onRefresh : null, icon: const Icon(Icons.refresh, size: 14), label: Text(_tr(context, 'Yenile', 'Refresh'))),
                ],
              )
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(_tr(context, 'Seçili Ajan', 'Selected Agent'), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 10),
                  Row(children: [
                    CircleAvatar(radius: 20, backgroundColor: _roleColor(agent!.role).withValues(alpha: .12), child: Icon(Icons.smart_toy_outlined, color: _roleColor(agent!.role))),
                    const SizedBox(width: 9),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(agent!.name, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w600)), Text(agent!.id, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 7.5, color: Theme.of(context).colorScheme.onSurfaceVariant))])),
                    _Chip(text: _stateLabel(context, agent!.state), color: _stateColor(agent!.state)),
                  ]),
                  const SizedBox(height: 12),
                  _Info(label: _tr(context, 'Rol', 'Role'), value: agent!.role),
                  _Info(label: _tr(context, 'Takım', 'Team'), value: agent!.team),
                  _Info(label: _tr(context, 'Readiness', 'Readiness'), value: agent!.readiness),
                  _Info(label: _tr(context, 'Provision', 'Provisioned'), value: agent!.registered ? _tr(context, 'Evet', 'Yes') : _tr(context, 'Hayır', 'No')),
                  _Info(label: _tr(context, 'Mevcut Görev', 'Current Task'), value: agent!.currentTask.isEmpty ? _tr(context, 'Görev yok', 'No task') : agent!.currentTask),
                  _Info(label: _tr(context, 'Sistem Sağlığı', 'System Health'), value: agent!.health),
                  const SizedBox(height: 9),
                  Text(_tr(context, 'Yetkinlikler', 'Capabilities'), style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 5),
                  Wrap(spacing: 4, runSpacing: 4, children: [for (final capability in agent!.capabilities.take(8)) _Chip(text: capability, color: IlaiosTheme.enterpriseCyan)]),
                  const SizedBox(height: 10),
                  Text('${_tr(context, 'Bekleyen İncelemeler', 'Pending Reviews')} (${reviews.length})', style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 5),
                  Expanded(
                    child: reviews.isEmpty
                        ? Center(child: Text(_tr(context, 'Bekleyen inceleme yok', 'No pending review'), style: const TextStyle(fontSize: 7.5)))
                        : ListView.builder(
                            itemCount: math.min(3, reviews.length),
                            itemBuilder: (_, index) => ListTile(
                              dense: true,
                              contentPadding: EdgeInsets.zero,
                              leading: const Icon(Icons.warning_amber_rounded, size: 15),
                              title: Text(_text(reviews[index], const ['title', 'summary', 'request_id', 'id']) ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis),
                              subtitle: Text(_text(reviews[index], const ['severity', 'priority', 'risk', 'status']) ?? '—'),
                            ),
                          ),
                  ),
                  Row(children: [
                    Expanded(child: FilledButton(onPressed: () => _showAgentDetail(context, agent!), child: Text(_tr(context, 'Detayı Aç', 'Open Detail')))),
                    const SizedBox(width: 8),
                    Expanded(child: Tooltip(message: _tr(context, 'Governed assignment API henüz mevcut değil.', 'Governed assignment API is not available yet.'), child: OutlinedButton.icon(onPressed: null, icon: const Icon(Icons.person_add_alt_1_outlined, size: 14), label: Text(_tr(context, 'Göreve Ata', 'Assign Task'))))),
                  ]),
                  const SizedBox(height: 7),
                  OutlinedButton.icon(key: const Key('agent-live-workspace'), onPressed: onWorkspace, icon: const Icon(Icons.hub_outlined, size: 14), label: Text(_tr(context, 'Canlı Çalışma Alanına Git', 'Go to Live Workspace'))),
                ],
              ),
      );
}

class _BottomPanels extends StatelessWidget {
  const _BottomPanels({required this.snapshot, required this.agents, required this.assignments});
  final OperationalSnapshot snapshot;
  final List<_AgentRecord> agents;
  final List<Map<String, Object?>> assignments;

  @override
  Widget build(BuildContext context) {
    final updates = snapshot.liveEvents.reversed.take(4).toList(growable: false);
    final roles = <String, int>{};
    for (final agent in agents) {
      roles.update(agent.role, (value) => value + 1, ifAbsent: () => 1);
    }
    return Row(
      key: const Key('agents-bottom-panels'),
      children: [
        Expanded(child: _Mini(title: _tr(context, 'Son Güncellemeler', 'Recent Updates'), lines: updates.map((item) => '${_text(item, const ['agent_id', 'worker_id', 'actor']) ?? '—'} · ${_text(item, const ['event_type', 'event', 'action', 'type']) ?? '—'}').toList(growable: false))),
        const SizedBox(width: 8),
        Expanded(child: _Mini(title: _tr(context, 'Bekleyen Atamalar', 'Pending Assignments'), lines: assignments.map((item) => '${_text(item, const ['title', 'task', 'job_id', 'id']) ?? '—'} · ${_text(item, const ['status', 'priority']) ?? '—'}').toList(growable: false))),
        const SizedBox(width: 8),
        Expanded(child: _Mini(title: _tr(context, 'Performans Özeti (7 Gün)', 'Performance Summary (7 Days)'), lines: <String>[
          '${_tr(context, 'Toplam Ajan', 'Total Agents')}: ${agents.isEmpty ? '—' : agents.length}',
          '${_tr(context, 'Aktif', 'Active')}: ${agents.where((e) => e.state == _AgentState.active).length}',
          '${_tr(context, 'Meşgul', 'Busy')}: ${agents.where((e) => e.state == _AgentState.busy).length}',
        ])),
        const SizedBox(width: 8),
        Expanded(child: _Mini(title: _tr(context, 'Ajan Rolleri', 'Agent Roles'), lines: roles.entries.take(5).map((e) => '${e.key}: ${e.value}').toList(growable: false))),
      ],
    );
  }
}

class _Mini extends StatelessWidget {
  const _Mini({required this.title, required this.lines});
  final String title;
  final List<String> lines;
  @override
  Widget build(BuildContext context) => _Panel(
        padding: const EdgeInsets.all(8),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(title, style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600)),
          const Divider(),
          Expanded(child: lines.isEmpty ? Center(child: Text(_tr(context, 'Veri yok', 'No data'), style: const TextStyle(fontSize: 7))) : Column(children: [for (final line in lines.take(4)) Expanded(child: Align(alignment: Alignment.centerLeft, child: Text(line, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.1))))])),
        ]),
      );
}

class _Tab extends StatelessWidget {
  const _Tab({required this.label, required this.selected, required this.onTap});
  final String label;
  final bool selected;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        child: Container(
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 11),
          decoration: BoxDecoration(border: selected ? const Border(bottom: BorderSide(color: IlaiosTheme.enterpriseCyan, width: 2)) : null),
          child: Text(label, style: TextStyle(fontSize: 8.4, fontWeight: selected ? FontWeight.w600 : FontWeight.w400)),
        ),
      );
}

class _Progress extends StatelessWidget {
  const _Progress({required this.value, super.key});
  final double? value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: value == null
                ? Container(
                    key: const Key('agent-capacity-unavailable-track'),
                    height: 4,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.outlineVariant,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  )
                : LinearProgressIndicator(
                    key: const Key('agent-capacity-progress'),
                    value: value,
                    minHeight: 4,
                  ),
          ),
          const SizedBox(width: 5),
          SizedBox(
            width: 28,
            child: Text(
              value == null ? '—' : '${(value! * 100).round()}%',
              style: const TextStyle(fontSize: 7),
            ),
          ),
        ],
      );
}

class _Info extends StatelessWidget {
  const _Info({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [SizedBox(width: 95, child: Text(label, style: TextStyle(fontSize: 7.2, color: Theme.of(context).colorScheme.onSurfaceVariant))), Expanded(child: Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.8, fontWeight: FontWeight.w600)))]),
      );
}

class _Chip extends StatelessWidget {
  const _Chip({required this.text, required this.color});
  final String text;
  final Color color;
  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 140),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(color: color.withValues(alpha: .10), borderRadius: BorderRadius.circular(4)),
        child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 7, color: color)),
      );
}

class _Panel extends StatelessWidget {
  const _Panel({required this.child, this.padding = const EdgeInsets.all(10), this.key});
  final Widget child;
  final EdgeInsetsGeometry padding;
  final Key? key;
  @override
  Widget build(BuildContext context) => Container(
        key: key,
        padding: padding,
        decoration: BoxDecoration(color: Theme.of(context).colorScheme.surfaceContainerLow, borderRadius: BorderRadius.circular(7), border: Border.all(color: Theme.of(context).colorScheme.outlineVariant)),
        child: child,
      );
}

class _EmptyAgents extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.groups_2_outlined, size: 30, color: Theme.of(context).colorScheme.outline),
          const SizedBox(height: 7),
          Text(_tr(context, 'Doğrulanmış ajan kaydı yok', 'No verified agent record'), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600)),
        ]),
      );
}

enum _AgentState { active, busy, idle, review, offline }

class _AgentRecord {
  const _AgentRecord({
    required this.id,
    required this.name,
    required this.role,
    required this.team,
    required this.state,
    required this.currentTask,
    required this.capacity,
    required this.successRate,
    required this.responseSeconds,
    required this.lastActivity,
    required this.health,
    required this.capabilities,
    required this.readiness,
    required this.registered,
  });
  final String id;
  final String name;
  final String role;
  final String team;
  final _AgentState state;
  final String currentTask;
  final double? capacity;
  final double? successRate;
  final double? responseSeconds;
  final String lastActivity;
  final String health;
  final List<String> capabilities;
  final String readiness;
  final bool registered;
}

class _CanonicalAgentCandidate {
  const _CanonicalAgentCandidate({required this.id, required this.alias, required this.role, required this.team, required this.readiness, required this.registered, required this.authorityMatchesCanonical});
  final String id;
  final String alias;
  final String role;
  final String team;
  final String readiness;
  final bool registered;
  final bool authorityMatchesCanonical;
}

const _agentTelemetryKeys = <String>[
  'agent_status',
  'worker_status',
  'status',
  'state',
  'lease_state',
  'current_task',
  'task',
  'workflow_name',
  'job_id',
  'execution_id',
  'capacity',
  'utilization',
  'load',
  'capacity_used',
  'usage_percent',
  'success_rate',
  'success_ratio',
  'success_percent',
  'quality_score',
  'response_seconds',
  'latency_seconds',
  'response_ms',
  'latency_ms',
  'last_activity',
  'last_seen',
  'updated_at',
  'timestamp',
  'readiness_updated_at',
  'health',
  'health_status',
  'system_health',
];

List<_AgentRecord> _agentRecords(OperationalSnapshot snapshot) {
  final merged = <String, Map<String, Object?>>{};

  // The server-projected canonical registry is the only identity/governance
  // authority for this surface. Runtime data can enrich these identities, but
  // it can never create a new Desktop agent or widen registry-owned authority.
  for (final item in _maps(snapshot.agentState['agents'])) {
    final id = _text(item, const ['agent_id']);
    if (id == null || !id.startsWith('ilaios.agent.')) continue;
    merged[id] = Map<String, Object?>.of(item);
  }

  void mergeTelemetry(Map<String, Object?> item) {
    String? canonicalId;
    for (final key in const [
      'agent_id',
      'worker_id',
      'executor_id',
      'agent',
      'worker',
      'id',
    ]) {
      final candidate = _text(item, [key]);
      if (candidate != null && merged.containsKey(candidate)) {
        canonicalId = candidate;
        break;
      }
    }
    if (canonicalId == null) return;

    final telemetry = <String, Object?>{};
    for (final key in _agentTelemetryKeys) {
      if (item.containsKey(key)) telemetry[key] = item[key];
    }
    if (telemetry.isEmpty) return;
    merged[canonicalId] = <String, Object?>{
      ...merged[canonicalId]!,
      ...telemetry,
    };
  }

  for (final key in const ['agents', 'workers', 'executors', 'leases']) {
    for (final item in _maps(snapshot.schedulerState[key])) {
      mergeTelemetry(item);
    }
  }
  for (final item in snapshot.runtimeRoutes) {
    mergeTelemetry(item);
  }
  for (final item in snapshot.liveEvents) {
    mergeTelemetry(item);
  }

  return merged.entries.map((entry) {
    final item = entry.value;
    final registered = item['registered'] is bool ? item['registered'] as bool : true;
    final rawState = _text(item, const ['agent_status', 'worker_status', 'status', 'state', 'lease_state']) ?? (registered ? 'active' : 'offline');
    final capabilities = _strings(item, const ['capabilities', 'skills', 'tools', 'competencies']);
    return _AgentRecord(
      id: entry.key,
      name: _text(item, const ['alias', 'agent_name', 'worker_name', 'display_name', 'name', 'title']) ?? entry.key,
      role: _text(item, const ['role', 'agent_role', 'worker_role', 'specialty', 'type']) ?? '—',
      team: _text(item, const ['team']) ?? '—',
      state: _agentState(rawState),
      currentTask: _text(item, const ['current_task', 'task', 'workflow_name']) ?? '',
      capacity: _ratio(item, const ['capacity', 'utilization', 'load', 'capacity_used', 'usage_percent']),
      successRate: _ratio(item, const ['success_rate', 'success_ratio', 'success_percent', 'quality_score']),
      responseSeconds: _responseSeconds(item),
      lastActivity: _text(item, const ['last_activity', 'last_seen', 'updated_at', 'timestamp', 'readiness_updated_at']) ?? '—',
      health: _text(item, const ['health', 'health_status', 'system_health']) ?? '—',
      capabilities: capabilities,
      readiness: _text(item, const ['readiness']) ?? '—',
      registered: registered,
    );
  }).toList(growable: false);
}

List<_CanonicalAgentCandidate> _canonicalCandidates(OperationalSnapshot snapshot) =>
    _maps(snapshot.agentState['agents']).map((item) {
      return _CanonicalAgentCandidate(
        id: _text(item, const ['agent_id']) ?? '',
        alias: _text(item, const ['alias']) ?? _text(item, const ['agent_id']) ?? '—',
        role: _text(item, const ['role']) ?? '—',
        team: _text(item, const ['team']) ?? '—',
        readiness: _text(item, const ['readiness']) ?? '—',
        registered: item['registered'] == true,
        authorityMatchesCanonical: item['authority_matches_canonical'] != false,
      );
    }).where((item) => item.id.startsWith('ilaios.agent.')).toList(growable: false);

List<Map<String, Object?>> _pendingAssignments(OperationalSnapshot snapshot) {
  for (final key in const ['pending_assignments', 'assignments', 'queue', 'pending_tasks']) {
    final values = _maps(snapshot.schedulerState[key]);
    if (values.isNotEmpty) return values;
  }
  return const [];
}

List<Map<String, Object?>> _pendingReviews(OperationalSnapshot snapshot, String? id) {
  final values = <Map<String, Object?>>[];
  for (final key in const ['pending_reviews', 'pending_approvals', 'reviews', 'approvals', 'work']) {
    values.addAll(_maps(snapshot.governanceState[key]));
  }
  if (id == null) return values;
  return values.where((item) {
    final owner = _text(item, const ['agent_id', 'worker_id', 'assignee', 'subject_id']);
    return owner != null && owner == id;
  }).toList(growable: false);
}

List<Map<String, Object?>> _maps(Object? raw) {
  if (raw is! List<Object?>) return const [];
  return raw.whereType<Map<String, Object?>>().toList(growable: false);
}

List<String> _strings(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final raw = source[key];
    if (raw is List<Object?>) {
      return raw.whereType<String>().where((e) => e.trim().isNotEmpty).map((e) => e.trim()).toList(growable: false);
    }
    if (raw is String && raw.trim().isNotEmpty) {
      return raw.split(RegExp(r'[,;|]')).map((e) => e.trim()).where((e) => e.isNotEmpty).toList(growable: false);
    }
  }
  return const [];
}

List<String> _unique(Iterable<String> values) {
  final result = values.where((e) => e.isNotEmpty && e != '—').toSet().toList(growable: false)..sort();
  return result;
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

int? _int(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is int) return value;
    if (value is num) return value.round();
  }
  return null;
}

double? _number(Object? value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value.replaceAll('%', '').trim());
  return null;
}

double? _ratio(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = _number(source[key]);
    if (value == null) continue;
    return (value.abs() > 1 ? value / 100 : value).clamp(0.0, 1.0);
  }
  return null;
}

double? _responseSeconds(Map<String, Object?> source) {
  final seconds = _number(source['response_seconds']) ?? _number(source['latency_seconds']);
  if (seconds != null) return seconds;
  final ms = _number(source['response_ms']) ?? _number(source['latency_ms']);
  return ms == null ? null : ms / 1000;
}

_AgentState _agentState(String raw) {
  final value = _normalize(raw);
  if (value.contains('offline') || value.contains('disabled') || value.contains('stopped') || value.contains('dead') || value.contains('unregistered')) return _AgentState.offline;
  if (value.contains('review') || value.contains('approval')) return _AgentState.review;
  if (value.contains('busy') || value.contains('running') || value.contains('executing') || value.contains('working')) return _AgentState.busy;
  if (value.contains('idle') || value.contains('available') || value.contains('free')) return _AgentState.idle;
  return _AgentState.active;
}

String _stateLabel(BuildContext context, _AgentState state) => switch (state) {
      _AgentState.active => _tr(context, 'Aktif', 'Active'),
      _AgentState.busy => _tr(context, 'Meşgul', 'Busy'),
      _AgentState.idle => _tr(context, 'Boşta', 'Idle'),
      _AgentState.review => _tr(context, 'İncelemede', 'In Review'),
      _AgentState.offline => _tr(context, 'Devre Dışı', 'Offline'),
    };

Color _stateColor(_AgentState state) => switch (state) {
      _AgentState.active => IlaiosTheme.success,
      _AgentState.busy => IlaiosTheme.warning,
      _AgentState.idle => IlaiosTheme.coreBlue,
      _AgentState.review => IlaiosTheme.violet,
      _AgentState.offline => IlaiosTheme.danger,
    };

Color _roleColor(String role) {
  final value = _normalize(role);
  if (value.contains('security')) return IlaiosTheme.danger;
  if (value.contains('test') || value.contains('qa')) return IlaiosTheme.success;
  if (value.contains('backend')) return IlaiosTheme.warning;
  if (value.contains('release') || value.contains('deploy')) return IlaiosTheme.violet;
  return IlaiosTheme.enterpriseCyan;
}

String _filterLabel(BuildContext context, String id, String value) {
  if (id != 'state') return value;
  final state = _AgentState.values.where((e) => e.name == value).firstOrNull;
  return state == null ? value : _stateLabel(context, state);
}

String _normalize(String value) => value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');

String _tr(BuildContext context, String tr, String en) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish ? tr : en;

void _showAgentDetail(BuildContext context, _AgentRecord agent) {
  showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(agent.name),
      content: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 520),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${_tr(context, 'Kimlik', 'ID')}: ${agent.id}'),
            Text('${_tr(context, 'Rol', 'Role')}: ${agent.role}'),
            Text('${_tr(context, 'Takım', 'Team')}: ${agent.team}'),
            Text('${_tr(context, 'Durum', 'Status')}: ${_stateLabel(context, agent.state)}'),
            Text('${_tr(context, 'Readiness', 'Readiness')}: ${agent.readiness}'),
            Text('${_tr(context, 'Provision', 'Provisioned')}: ${agent.registered}'),
            Text('${_tr(context, 'Mevcut Görev', 'Current Task')}: ${agent.currentTask}'),
            Text('${_tr(context, 'Kapasite', 'Capacity')}: ${agent.capacity == null ? '—' : '${(agent.capacity! * 100).round()}%'}'),
            Text('${_tr(context, 'Başarı', 'Success')}: ${agent.successRate == null ? '—' : '${(agent.successRate! * 100).toStringAsFixed(1)}%'}'),
            Text('${_tr(context, 'Son Etkinlik', 'Last Activity')}: ${agent.lastActivity}'),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(_tr(context, 'Kapat', 'Close'))),
      ],
    ),
  );
}
