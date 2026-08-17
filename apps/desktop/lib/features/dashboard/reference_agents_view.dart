import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';

/// Reference-faithful Agents surface.
///
/// The supplied Dark/Light screenshots define composition only. Runtime values
/// are derived from the authoritative operational snapshot. Missing values are
/// rendered as explicit empty values instead of copying screenshot telemetry.
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
  int _tab = 0;
  int _selected = 0;
  String _query = '';

  @override
  Widget build(BuildContext context) {
    final agents = _agentRecords(widget.snapshot);
    final visible = _filtered(agents);
    final selected = visible.isEmpty
        ? null
        : visible[_selected.clamp(0, visible.length - 1)];
    final pendingAssignments = _pendingAssignments(widget.snapshot);
    final reviews = _pendingReviews(widget.snapshot, selected?.id);

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
                    _PageHeader(
                      connected: widget.projection.connected,
                      onRefresh: widget.onRefreshRequested,
                    ),
                    const SizedBox(height: 7),
                    _MetricsRow(
                      snapshot: widget.snapshot,
                      agents: agents,
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: _AgentsTablePanel(
                        agents: visible,
                        allAgents: agents,
                        tab: _tab,
                        query: _query,
                        selected: selected,
                        onTab: (value) => setState(() {
                          _tab = value;
                          _selected = 0;
                        }),
                        onQuery: (value) => setState(() {
                          _query = value;
                          _selected = 0;
                        }),
                        onSelect: (value) => setState(() => _selected = value),
                        onCreate: () => _showUnavailableAction(
                          context,
                          _tr(
                            context,
                            'Yeni ajan oluşturma işlemi henüz Desktop API sözleşmesine bağlı değil.',
                            'New agent creation is not yet bound to a Desktop API contract.',
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    SizedBox(
                      height: 145,
                      child: _BottomPanels(
                        snapshot: widget.snapshot,
                        agents: agents,
                        pendingAssignments: pendingAssignments,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              SizedBox(
                width: rightWidth,
                child: _SelectedAgentPanel(
                  agent: selected,
                  reviews: reviews,
                  snapshot: widget.snapshot,
                  connected: widget.projection.connected,
                  onRefresh: widget.onRefreshRequested,
                  onNavigate: widget.onNavigate,
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  List<_AgentRecord> _filtered(List<_AgentRecord> source) {
    Iterable<_AgentRecord> output = source;
    if (_tab == 1) output = output.where((item) => item.state == _AgentState.active);
    if (_tab == 2) output = output.where((item) => item.state == _AgentState.busy);
    if (_tab == 3) output = output.where((item) => item.state == _AgentState.idle);
    if (_tab == 4) output = output.where((item) => item.state == _AgentState.review);
    if (_tab == 5) output = output.where((item) => item.state == _AgentState.offline);
    final q = _query.trim().toLowerCase();
    if (q.isNotEmpty) {
      output = output.where(
        (item) => '${item.name} ${item.id} ${item.role} ${item.currentTask}'
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
                      'Ajan filonuzu yönetin, kapasitelerini izleyin ve atamalarını düzenleyin.',
                      'Manage your agent fleet, monitor capacity and coordinate assignments.',
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
              tooltip: _tr(context, 'Yenile', 'Refresh'),
              onPressed: connected ? onRefresh : null,
              icon: const Icon(Icons.refresh_rounded, size: 18),
            ),
          ],
        ),
      );
}

class _MetricsRow extends StatelessWidget {
  const _MetricsRow({required this.snapshot, required this.agents});

  final OperationalSnapshot snapshot;
  final List<_AgentRecord> agents;

  @override
  Widget build(BuildContext context) {
    final total = agents.isNotEmpty
        ? agents.length
        : _authoritativeInt(snapshot.schedulerState, const [
            'agent_count',
            'total_agents',
            'worker_count',
          ]);
    final active = _stateCount(agents, _AgentState.active);
    final busy = _stateCount(agents, _AgentState.busy);
    final idle = _stateCount(agents, _AgentState.idle);
    final success = _average(
      agents.map((item) => item.successRate).whereType<double>(),
    );
    final latency = _average(
      agents.map((item) => item.responseSeconds).whereType<double>(),
    );

    return SizedBox(
      key: const Key('agents-metrics'),
      height: 76,
      child: Row(
        children: [
          _Metric(
            icon: Icons.groups_2_outlined,
            accent: IlaiosTheme.enterpriseCyan,
            title: _tr(context, 'Toplam Ajan', 'Total Agents'),
            value: total?.toString() ?? '—',
          ),
          const SizedBox(width: 7),
          _Metric(
            icon: Icons.circle,
            accent: IlaiosTheme.success,
            title: _tr(context, 'Aktif Ajan', 'Active Agents'),
            value: agents.isEmpty ? '—' : '$active',
          ),
          const SizedBox(width: 7),
          _Metric(
            icon: Icons.hexagon_outlined,
            accent: IlaiosTheme.warning,
            title: _tr(context, 'Meşgul', 'Busy'),
            value: agents.isEmpty ? '—' : '$busy',
          ),
          const SizedBox(width: 7),
          _Metric(
            icon: Icons.person_outline_rounded,
            accent: IlaiosTheme.coreBlue,
            title: _tr(context, 'Boşta', 'Idle'),
            value: agents.isEmpty ? '—' : '$idle',
          ),
          const SizedBox(width: 7),
          _Metric(
            icon: Icons.auto_awesome_outlined,
            accent: IlaiosTheme.violet,
            title: _tr(context, 'Ortalama Başarı', 'Average Success'),
            value: success == null ? '—' : '${(success * 100).toStringAsFixed(1)}%',
          ),
          const SizedBox(width: 7),
          _Metric(
            icon: Icons.schedule_rounded,
            accent: IlaiosTheme.enterpriseCyan,
            title: _tr(context, 'Ortalama Yanıt Süresi', 'Average Response Time'),
            value: latency == null ? '—' : '${latency.toStringAsFixed(2)} sn',
          ),
        ],
      ),
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({
    required this.icon,
    required this.accent,
    required this.title,
    required this.value,
  });

  final IconData icon;
  final Color accent;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Expanded(
        child: _Card(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
          child: Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: accent.withValues(alpha: .10),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Icon(icon, size: 21, color: accent),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 7.8,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                    const SizedBox(height: 3),
                    Text(
                      value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}

class _AgentsTablePanel extends StatelessWidget {
  const _AgentsTablePanel({
    required this.agents,
    required this.allAgents,
    required this.tab,
    required this.query,
    required this.selected,
    required this.onTab,
    required this.onQuery,
    required this.onSelect,
    required this.onCreate,
  });

  final List<_AgentRecord> agents;
  final List<_AgentRecord> allAgents;
  final int tab;
  final String query;
  final _AgentRecord? selected;
  final ValueChanged<int> onTab;
  final ValueChanged<String> onQuery;
  final ValueChanged<int> onSelect;
  final VoidCallback onCreate;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('agents-table-panel'),
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
                    ('Meşgul', 'Busy'),
                    ('Boşta', 'Idle'),
                    ('İncelemede', 'In Review'),
                    ('Devre Dışı', 'Offline'),
                  ].indexed)
                    _TabButton(
                      label: _tr(context, entry.$2.$1, entry.$2.$2),
                      selected: tab == entry.$1,
                      onTap: () => onTab(entry.$1),
                    ),
                  const Spacer(),
                  SizedBox(
                    height: 28,
                    child: FilledButton.icon(
                      key: const Key('new-agent-button'),
                      onPressed: onCreate,
                      icon: const Icon(Icons.add, size: 15),
                      label: Text(_tr(context, 'Yeni Ajan', 'New Agent')),
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(horizontal: 12),
                        textStyle: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  IconButton(
                    onPressed: () {},
                    icon: const Icon(Icons.more_vert, size: 16),
                    visualDensity: VisualDensity.compact,
                    tooltip: _tr(context, 'Diğer', 'More'),
                  ),
                  const SizedBox(width: 3),
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
                        onChanged: onQuery,
                        decoration: InputDecoration(
                          isDense: true,
                          hintText: _tr(context, 'Ajan ara...', 'Search agents...'),
                          prefixIcon: const Icon(Icons.search, size: 15),
                          contentPadding: const EdgeInsets.symmetric(vertical: 5),
                        ),
                        style: const TextStyle(fontSize: 9),
                      ),
                    ),
                    const SizedBox(width: 7),
                    for (final label in <(String, String)>[
                      ('Rol Türü', 'Role Type'),
                      ('Durum Türü', 'Status Type'),
                      ('Yetkinlik Türü', 'Capability Type'),
                    ]) ...[
                      Expanded(child: _FilterBox(label: _tr(context, label.$1, label.$2))),
                      const SizedBox(width: 7),
                    ],
                    OutlinedButton(
                      onPressed: query.isEmpty ? null : () => onQuery(''),
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size(102, 28),
                        padding: const EdgeInsets.symmetric(horizontal: 8),
                        textStyle: const TextStyle(fontSize: 8.2),
                      ),
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
                        for (var index = 0; index < agents.length && index < 6; index++)
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
              height: 27,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 9),
                child: Row(
                  children: [
                    Text(
                      agents.isEmpty
                          ? _tr(context, '0 ajan', '0 agents')
                          : '1-${agents.length.clamp(0, 6)} / ${allAgents.length} ${_tr(context, 'ajan', 'agents')}',
                      style: const TextStyle(fontSize: 8.1),
                    ),
                    const Spacer(),
                    Icon(Icons.chevron_left, size: 14, color: Theme.of(context).colorScheme.onSurfaceVariant),
                    Container(
                      width: 24,
                      height: 21,
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        border: Border.all(color: IlaiosTheme.enterpriseCyan.withValues(alpha: .7)),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: const Text('1', style: TextStyle(fontSize: 8)),
                    ),
                    const SizedBox(width: 4),
                    Text('2   3   4   5', style: TextStyle(fontSize: 8, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                    Icon(Icons.chevron_right, size: 14, color: Theme.of(context).colorScheme.onSurfaceVariant),
                    const SizedBox(width: 12),
                    _FilterBox(label: _tr(context, '10 / sayfa', '10 / page'), width: 82),
                  ],
                ),
              ),
            ),
          ],
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
              Expanded(flex: 22, child: Text(_tr(context, 'Ajan', 'Agent'), style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600))),
              Expanded(flex: 17, child: Text(_tr(context, 'Uzmanlık', 'Specialty'), style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600))),
              Expanded(flex: 12, child: Text(_tr(context, 'Durum', 'Status'), style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600))),
              Expanded(flex: 20, child: Text(_tr(context, 'Mevcut Görev', 'Current Task'), style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600))),
              Expanded(flex: 16, child: Text(_tr(context, 'Kapasite', 'Capacity'), style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600))),
              Expanded(flex: 14, child: Text(_tr(context, 'Başarı Oranı', 'Success Rate'), style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600))),
              Expanded(flex: 14, child: Text(_tr(context, 'Son Etkinlik', 'Last Activity'), style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600))),
              const SizedBox(width: 22),
            ],
          ),
        ),
      );
}

class _AgentRow extends StatelessWidget {
  const _AgentRow({
    required this.record,
    required this.selected,
    required this.onTap,
  });

  final _AgentRecord record;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final statusColor = _stateColor(record.state);
    return InkWell(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 1.5),
        padding: const EdgeInsets.symmetric(horizontal: 6),
        decoration: BoxDecoration(
          color: selected ? IlaiosTheme.coreBlue.withValues(alpha: .08) : null,
          border: selected
              ? Border.all(color: IlaiosTheme.enterpriseCyan.withValues(alpha: .78))
              : null,
          borderRadius: BorderRadius.circular(6),
        ),
        child: Row(
          children: [
            Expanded(
              flex: 22,
              child: Row(
                children: [
                  _RoundIcon(icon: _agentIcon(record.role), accent: _roleColor(record.role), size: 28),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(record.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8.3, fontWeight: FontWeight.w600)),
                        const SizedBox(height: 2),
                        Text(record.id, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 7, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              flex: 17,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(record.role, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.8)),
                  if (record.skills.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Wrap(
                        spacing: 3,
                        children: [
                          for (final skill in record.skills.take(2)) _MiniTag(text: skill),
                        ],
                      ),
                    ),
                ],
              ),
            ),
            Expanded(
              flex: 12,
              child: Row(
                children: [
                  Container(width: 6, height: 6, decoration: BoxDecoration(color: statusColor, shape: BoxShape.circle)),
                  const SizedBox(width: 5),
                  Expanded(child: Text(_stateLabel(context, record.state), maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 7.8, color: statusColor, fontWeight: FontWeight.w600))),
                ],
              ),
            ),
            Expanded(
              flex: 20,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(record.currentTask, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.7)),
                  if (record.currentTaskDetail != '—')
                    Text(record.currentTaskDetail, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
            Expanded(
              flex: 16,
              child: _ProgressCell(value: record.capacity),
            ),
            Expanded(
              flex: 14,
              child: record.successRate == null
                  ? const Text('—', style: TextStyle(fontSize: 8.2))
                  : Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${(record.successRate! * 100).toStringAsFixed(1)}%', style: const TextStyle(fontSize: 8.3, fontWeight: FontWeight.w600)),
                        if (record.successDelta != null)
                          Text(
                            '${record.successDelta! >= 0 ? '↑' : '↓'} ${(record.successDelta!.abs() * 100).toStringAsFixed(1)}%',
                            style: TextStyle(fontSize: 6.8, color: record.successDelta! >= 0 ? IlaiosTheme.success : IlaiosTheme.danger),
                          ),
                      ],
                    ),
            ),
            Expanded(
              flex: 14,
              child: Text(record.lastActivity, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.5)),
            ),
            SizedBox(
              width: 22,
              child: IconButton(
                onPressed: () => _showAgentDetail(context, record),
                padding: EdgeInsets.zero,
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.more_vert, size: 15),
                tooltip: _tr(context, 'Detay', 'Detail'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SelectedAgentPanel extends StatelessWidget {
  const _SelectedAgentPanel({
    required this.agent,
    required this.reviews,
    required this.snapshot,
    required this.connected,
    required this.onRefresh,
    required this.onNavigate,
  });

  final _AgentRecord? agent;
  final List<Map<String, Object?>> reviews;
  final OperationalSnapshot snapshot;
  final bool connected;
  final VoidCallback? onRefresh;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('selected-agent-panel'),
        padding: EdgeInsets.zero,
        child: agent == null
            ? _EmptySelectedAgent(connected: connected, onRefresh: onRefresh)
            : Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  _PanelTitle(title: _tr(context, 'Seçili Ajan', 'Selected Agent')),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(10, 8, 10, 7),
                    child: _SelectedAgentSummary(agent: agent!),
                  ),
                  Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                  Expanded(
                    child: Padding(
                      padding: const EdgeInsets.all(8),
                      child: Column(
                        children: [
                          Expanded(
                            flex: 34,
                            child: Row(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                Expanded(
                                  flex: 65,
                                  child: _PerformancePanel(agent: agent!),
                                ),
                                const SizedBox(width: 8),
                                Expanded(
                                  flex: 35,
                                  child: _AgentFlowPanel(
                                    agent: agent!,
                                    snapshot: snapshot,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            flex: 18,
                            child: _SkillsPanel(agent: agent!),
                          ),
                          const SizedBox(height: 8),
                          Expanded(
                            flex: 24,
                            child: _ReviewsPanel(reviews: reviews),
                          ),
                          const SizedBox(height: 8),
                          SizedBox(
                            height: 74,
                            child: Column(
                              children: [
                                Expanded(
                                  child: Row(
                                    children: [
                                      Expanded(
                                        child: FilledButton(
                                          onPressed: () => _showAgentDetail(context, agent!),
                                          child: Text(_tr(context, 'Detayı Aç', 'Open Detail')),
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                        child: OutlinedButton.icon(
                                          onPressed: () => _showUnavailableAction(
                                            context,
                                            _tr(
                                              context,
                                              'Göreve atama API sözleşmesi henüz bağlı değil.',
                                              'Assignment API contract is not yet bound.',
                                            ),
                                          ),
                                          icon: const Icon(Icons.person_add_alt_1_outlined, size: 14),
                                          label: Text(_tr(context, 'Göreve Ata', 'Assign Task')),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                                const SizedBox(height: 7),
                                SizedBox(
                                  width: double.infinity,
                                  height: 31,
                                  child: OutlinedButton.icon(
                                    key: const Key('agent-live-workspace'),
                                    onPressed: () => onNavigate(DesktopSection.liveWorkspace),
                                    icon: const Icon(Icons.hub_outlined, size: 14),
                                    label: Text(_tr(context, 'Canlı Çalışma Alanına Git', 'Go to Live Workspace')),
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
              ),
      );
}

class _SelectedAgentSummary extends StatelessWidget {
  const _SelectedAgentSummary({required this.agent});

  final _AgentRecord agent;

  @override
  Widget build(BuildContext context) {
    final stateColor = _stateColor(agent.state);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            _RoundIcon(icon: _agentIcon(agent.role), accent: _roleColor(agent.role), size: 40),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(agent.name, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text(agent.id, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 8.2, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
            _Tag(text: _stateLabel(context, agent.state), color: stateColor),
          ],
        ),
        const SizedBox(height: 10),
        Row(
          children: [
            Expanded(child: _InfoBlock(label: _tr(context, 'Rol', 'Role'), value: agent.role)),
            Expanded(child: _InfoBlock(label: _tr(context, 'Sahip', 'Owner'), value: agent.owner)),
            Expanded(child: _InfoBlock(label: _tr(context, 'Oluşturulma Süresi', 'Created'), value: agent.created)),
          ],
        ),
        const SizedBox(height: 7),
        Row(
          children: [
            Expanded(child: _InfoBlock(label: _tr(context, 'Aktif Görevler', 'Active Tasks'), value: agent.activeTasks?.toString() ?? '—')),
            Expanded(child: _InfoBlock(label: _tr(context, 'Token Kullanımı', 'Token Usage'), value: agent.tokenUsage)),
            const Spacer(),
          ],
        ),
        const SizedBox(height: 9),
        Row(
          children: [
            Text(_tr(context, 'Kapasite', 'Capacity'), style: TextStyle(fontSize: 7.4, color: Theme.of(context).colorScheme.onSurfaceVariant)),
            const SizedBox(width: 10),
            Expanded(child: _ProgressCell(value: agent.capacity, compact: true)),
            const SizedBox(width: 12),
            Text(_tr(context, 'Sistem Sağlığı', 'System Health'), style: TextStyle(fontSize: 7.4, color: Theme.of(context).colorScheme.onSurfaceVariant)),
            const SizedBox(width: 8),
            Text(agent.health, style: TextStyle(fontSize: 8.2, color: agent.health == '—' ? null : IlaiosTheme.success, fontWeight: FontWeight.w600)),
          ],
        ),
      ],
    );
  }
}

class _PerformancePanel extends StatelessWidget {
  const _PerformancePanel({required this.agent});

  final _AgentRecord agent;

  @override
  Widget build(BuildContext context) => _MiniPanel(
        title: _tr(context, 'Son Performans (7 Gün)', 'Recent Performance (7 Days)'),
        trailing: _tr(context, 'Detaylar', 'Details'),
        child: agent.performance.isEmpty
            ? _InlineEmpty(label: _tr(context, 'Doğrulanmış performans verisi yok', 'No verified performance data'))
            : Padding(
                padding: const EdgeInsets.fromLTRB(6, 4, 6, 6),
                child: CustomPaint(
                  painter: _LineChartPainter(
                    values: agent.performance,
                    lineColor: IlaiosTheme.enterpriseCyan,
                    gridColor: Theme.of(context).colorScheme.outlineVariant,
                  ),
                  child: const SizedBox.expand(),
                ),
              ),
      );
}

class _AgentFlowPanel extends StatelessWidget {
  const _AgentFlowPanel({required this.agent, required this.snapshot});

  final _AgentRecord agent;
  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final events = _agentEvents(snapshot, agent.id).take(6).toList();
    return _MiniPanel(
      title: _tr(context, 'Ajan Akışı', 'Agent Flow'),
      child: events.isEmpty
          ? _InlineEmpty(label: _tr(context, 'Canlı ajan olayı yok', 'No live agent event'))
          : Padding(
              padding: const EdgeInsets.fromLTRB(8, 5, 7, 5),
              child: Column(
                children: [
                  for (final event in events)
                    Expanded(
                      child: Row(
                        children: [
                          Container(width: 6, height: 6, decoration: const BoxDecoration(color: IlaiosTheme.success, shape: BoxShape.circle)),
                          const SizedBox(width: 6),
                          Expanded(child: Text(_text(event, const ['event_type', 'event', 'action', 'type']) ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.2))),
                          const SizedBox(width: 4),
                          Text(_text(event, const ['timestamp', 'created_at', 'time']) ?? '—', maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 6.4, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                        ],
                      ),
                    ),
                ],
              ),
            ),
    );
  }
}

class _SkillsPanel extends StatelessWidget {
  const _SkillsPanel({required this.agent});

  final _AgentRecord agent;

  @override
  Widget build(BuildContext context) => _MiniPanel(
        title: _tr(context, 'Yetkinlikler', 'Capabilities'),
        trailing: _tr(context, 'Detaylar', 'Details'),
        child: agent.skills.isEmpty
            ? _InlineEmpty(label: _tr(context, 'Yetkinlik verisi yok', 'No capability data'))
            : Padding(
                padding: const EdgeInsets.all(8),
                child: Align(
                  alignment: Alignment.topLeft,
                  child: Wrap(
                    spacing: 5,
                    runSpacing: 5,
                    children: [
                      for (var index = 0; index < agent.skills.length && index < 8; index++)
                        _Tag(
                          text: agent.skills[index],
                          color: _skillColor(index),
                        ),
                    ],
                  ),
                ),
              ),
      );
}

class _ReviewsPanel extends StatelessWidget {
  const _ReviewsPanel({required this.reviews});

  final List<Map<String, Object?>> reviews;

  @override
  Widget build(BuildContext context) => _MiniPanel(
        title: '${_tr(context, 'Bekleyen İncelemeler', 'Pending Reviews')} (${reviews.length})',
        child: reviews.isEmpty
            ? _InlineEmpty(label: _tr(context, 'Bekleyen doğrulanmış inceleme yok', 'No verified pending review'))
            : Padding(
                padding: const EdgeInsets.fromLTRB(7, 3, 7, 3),
                child: Column(
                  children: [
                    for (final review in reviews.take(3))
                      Expanded(
                        child: Row(
                          children: [
                            Icon(Icons.warning_amber_rounded, size: 14, color: _severityColor(_text(review, const ['severity', 'priority', 'risk']) ?? '')),
                            const SizedBox(width: 6),
                            Expanded(
                              child: Text(
                                _text(review, const ['title', 'summary', 'description', 'request_id', 'id']) ?? '—',
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 7.4),
                              ),
                            ),
                            const SizedBox(width: 4),
                            Text(
                              _text(review, const ['severity', 'priority', 'risk', 'status']) ?? '—',
                              style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              ),
      );
}

class _EmptySelectedAgent extends StatelessWidget {
  const _EmptySelectedAgent({required this.connected, required this.onRefresh});

  final bool connected;
  final VoidCallback? onRefresh;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _PanelTitle(title: _tr(context, 'Seçili Ajan', 'Selected Agent')),
          Expanded(
            child: Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.groups_2_outlined, size: 35, color: Theme.of(context).colorScheme.outline),
                  const SizedBox(height: 9),
                  Text(_tr(context, 'Doğrulanmış ajan kaydı yok', 'No verified agent record'), style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 5),
                  Text(_tr(context, 'Runtime ajan bilgisi sağladığında burada görünecek.', 'Runtime agent data will appear here when available.'), textAlign: TextAlign.center, style: TextStyle(fontSize: 8, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                  const SizedBox(height: 11),
                  OutlinedButton.icon(
                    key: const Key('agents-empty-refresh'),
                    onPressed: connected ? onRefresh : null,
                    icon: const Icon(Icons.refresh, size: 14),
                    label: Text(_tr(context, 'Yenile', 'Refresh')),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
}

class _BottomPanels extends StatelessWidget {
  const _BottomPanels({
    required this.snapshot,
    required this.agents,
    required this.pendingAssignments,
  });

  final OperationalSnapshot snapshot;
  final List<_AgentRecord> agents;
  final List<Map<String, Object?>> pendingAssignments;

  @override
  Widget build(BuildContext context) {
    final updates = snapshot.liveEvents.reversed.take(4).toList(growable: false);
    final success = _average(agents.map((item) => item.successRate).whereType<double>());
    final roles = <String, int>{};
    for (final agent in agents) {
      roles.update(agent.role, (value) => value + 1, ifAbsent: () => 1);
    }
    final sortedRoles = roles.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));

    return Row(
      key: const Key('agents-bottom-panels'),
      children: [
        Expanded(
          child: _BottomPanel(
            title: _tr(context, 'Son Güncellemeler', 'Recent Updates'),
            child: updates.isEmpty
                ? _InlineEmpty(label: _tr(context, 'Canlı güncelleme yok', 'No live update'))
                : _SimpleList(
                    rows: [
                      for (final item in updates)
                        (
                          _text(item, const ['agent_name', 'agent_id', 'worker', 'actor']) ?? '—',
                          _text(item, const ['event_type', 'event', 'action', 'type']) ?? '—',
                          _text(item, const ['timestamp', 'created_at', 'time']) ?? '—',
                        ),
                    ],
                  ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _BottomPanel(
            title: _tr(context, 'Bekleyen Atamalar', 'Pending Assignments'),
            child: pendingAssignments.isEmpty
                ? _InlineEmpty(label: _tr(context, 'Bekleyen atama yok', 'No pending assignment'))
                : _SimpleList(
                    rows: [
                      for (final item in pendingAssignments.take(4))
                        (
                          _text(item, const ['title', 'task', 'workflow_name', 'job_id', 'id']) ?? '—',
                          _text(item, const ['role', 'capability', 'type']) ?? '—',
                          _text(item, const ['priority', 'severity', 'status']) ?? '—',
                        ),
                    ],
                  ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _BottomPanel(
            title: _tr(context, 'Performans Özeti (7 Gün)', 'Performance Summary (7 Days)'),
            child: Row(
              children: [
                SizedBox(
                  width: 92,
                  child: Center(
                    child: _Donut(
                      value: success,
                      centerText: success == null ? '—' : '%${(success * 100).toStringAsFixed(1)}',
                    ),
                  ),
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _SummaryLine(label: _tr(context, 'Toplam Ajan', 'Total Agents'), value: agents.isEmpty ? '—' : '${agents.length}'),
                      _SummaryLine(label: _tr(context, 'Aktif', 'Active'), value: agents.isEmpty ? '—' : '${_stateCount(agents, _AgentState.active)}'),
                      _SummaryLine(label: _tr(context, 'Meşgul', 'Busy'), value: agents.isEmpty ? '—' : '${_stateCount(agents, _AgentState.busy)}'),
                      _SummaryLine(label: _tr(context, 'Boşta', 'Idle'), value: agents.isEmpty ? '—' : '${_stateCount(agents, _AgentState.idle)}'),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _BottomPanel(
            title: _tr(context, 'Ajan Rolleri', 'Agent Roles'),
            child: sortedRoles.isEmpty
                ? _InlineEmpty(label: _tr(context, 'Rol verisi yok', 'No role data'))
                : Padding(
                    padding: const EdgeInsets.fromLTRB(9, 4, 9, 4),
                    child: Column(
                      children: [
                        for (final entry in sortedRoles.take(6))
                          Expanded(
                            child: Row(
                              children: [
                                _RoundIcon(icon: _agentIcon(entry.key), accent: _roleColor(entry.key), size: 18),
                                const SizedBox(width: 6),
                                Expanded(child: Text(entry.key, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.4))),
                                Text('${entry.value} ${_tr(context, 'ajan', 'agents')}', style: TextStyle(fontSize: 7, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                              ],
                            ),
                          ),
                      ],
                    ),
                  ),
          ),
        ),
      ],
    );
  }
}

class _BottomPanel extends StatelessWidget {
  const _BottomPanel({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => _Card(
        padding: EdgeInsets.zero,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 29,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 9),
                child: Row(
                  children: [
                    Expanded(child: Text(title, style: const TextStyle(fontSize: 8.6, fontWeight: FontWeight.w600))),
                    Text(_tr(context, 'Tümü', 'All'), style: TextStyle(fontSize: 7, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                    const SizedBox(width: 2),
                    const Icon(Icons.chevron_right, size: 13),
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

class _SimpleList extends StatelessWidget {
  const _SimpleList({required this.rows});

  final List<(String, String, String)> rows;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(8, 4, 8, 4),
        child: Column(
          children: [
            for (final row in rows)
              Expanded(
                child: Row(
                  children: [
                    Container(width: 6, height: 6, decoration: const BoxDecoration(color: IlaiosTheme.enterpriseCyan, shape: BoxShape.circle)),
                    const SizedBox(width: 6),
                    Expanded(child: Text(row.$1, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.3, fontWeight: FontWeight.w600))),
                    const SizedBox(width: 4),
                    Expanded(child: Text(row.$2, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant))),
                    const SizedBox(width: 4),
                    Text(row.$3, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 6.5, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                  ],
                ),
              ),
          ],
        ),
      );
}

class _SummaryLine extends StatelessWidget {
  const _SummaryLine({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Expanded(
        child: Row(
          children: [
            Expanded(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 7, color: Theme.of(context).colorScheme.onSurfaceVariant))),
            Text(value, style: const TextStyle(fontSize: 7.3, fontWeight: FontWeight.w600)),
          ],
        ),
      );
}

class _MiniPanel extends StatelessWidget {
  const _MiniPanel({required this.title, required this.child, this.trailing});

  final String title;
  final String? trailing;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(6),
          color: Theme.of(context).colorScheme.surfaceContainerLowest.withValues(alpha: .28),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              height: 27,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8),
                child: Row(
                  children: [
                    Expanded(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w600))),
                    if (trailing != null)
                      Text(trailing!, style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant)),
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

class _PanelTitle extends StatelessWidget {
  const _PanelTitle({required this.title});

  final String title;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 33,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Row(
            children: [
              Expanded(child: Text(title, style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600))),
              const Icon(Icons.more_horiz, size: 14),
              const SizedBox(width: 8),
              const Icon(Icons.close, size: 13),
            ],
          ),
        ),
      );
}

class _FilterBox extends StatelessWidget {
  const _FilterBox({required this.label, this.width});

  final String label;
  final double? width;

  @override
  Widget build(BuildContext context) => Container(
        width: width,
        height: 28,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(5),
        ),
        child: Row(
          children: [
            Expanded(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.7))),
            const Icon(Icons.keyboard_arrow_down, size: 14),
          ],
        ),
      );
}

class _TabButton extends StatelessWidget {
  const _TabButton({required this.label, required this.selected, required this.onTap});

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
                ? const Border(bottom: BorderSide(color: IlaiosTheme.enterpriseCyan, width: 2))
                : null,
          ),
          child: Text(
            label,
            maxLines: 1,
            style: TextStyle(
              fontSize: 8.5,
              fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              color: selected ? null : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      );
}

class _Card extends StatelessWidget {
  const _Card({required this.child, this.padding = const EdgeInsets.all(10), this.key});

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

class _RoundIcon extends StatelessWidget {
  const _RoundIcon({required this.icon, required this.accent, this.size = 26});

  final IconData icon;
  final Color accent;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: accent.withValues(alpha: .11), shape: BoxShape.circle),
        child: Icon(icon, size: size * .54, color: accent),
      );
}

class _InfoBlock extends StatelessWidget {
  const _InfoBlock({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant)),
          const SizedBox(height: 2),
          Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.7, fontWeight: FontWeight.w600)),
        ],
      );
}

class _Tag extends StatelessWidget {
  const _Tag({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 100),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2.5),
        decoration: BoxDecoration(color: color.withValues(alpha: .10), borderRadius: BorderRadius.circular(4)),
        child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 7, color: color)),
      );
}

class _MiniTag extends StatelessWidget {
  const _MiniTag({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 54),
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
        decoration: BoxDecoration(
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
          borderRadius: BorderRadius.circular(3),
        ),
        child: Text(text, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 5.9)),
      );
}

class _ProgressCell extends StatelessWidget {
  const _ProgressCell({required this.value, this.compact = false});

  final double? value;
  final bool compact;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Expanded(
            child: ClipRRect(
              borderRadius: BorderRadius.circular(3),
              child: LinearProgressIndicator(
                minHeight: compact ? 3 : 4,
                value: value,
                backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
                color: IlaiosTheme.coreBlue,
              ),
            ),
          ),
          const SizedBox(width: 6),
          SizedBox(
            width: 30,
            child: Text(value == null ? '—' : '${(value! * 100).round()}%', style: TextStyle(fontSize: compact ? 7 : 7.5)),
          ),
        ],
      );
}

class _InlineEmpty extends StatelessWidget {
  const _InlineEmpty({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Center(
        child: Text(
          label,
          textAlign: TextAlign.center,
          style: TextStyle(fontSize: 7.2, color: Theme.of(context).colorScheme.onSurfaceVariant),
        ),
      );
}

class _EmptyAgents extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(Icons.groups_2_outlined, size: 30, color: Theme.of(context).colorScheme.outline),
            const SizedBox(height: 7),
            Text(_tr(context, 'Doğrulanmış ajan kaydı yok', 'No verified agent record'), style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600)),
            const SizedBox(height: 3),
            Text(_tr(context, 'Runtime ajan verisi sağladığında liste burada görünür.', 'The list appears when runtime agent data is available.'), style: TextStyle(fontSize: 7.2, color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ],
        ),
      );
}

class _Donut extends StatelessWidget {
  const _Donut({required this.value, required this.centerText});

  final double? value;
  final String centerText;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 76,
        height: 76,
        child: CustomPaint(
          painter: _DonutPainter(
            value: value,
            active: IlaiosTheme.coreBlue,
            track: Theme.of(context).colorScheme.surfaceContainerHighest,
          ),
          child: Center(
            child: Text(
              centerText,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
        ),
      );
}

class _DonutPainter extends CustomPainter {
  const _DonutPainter({required this.value, required this.active, required this.track});

  final double? value;
  final Color active;
  final Color track;

  @override
  void paint(Canvas canvas, Size size) {
    final center = size.center(Offset.zero);
    final radius = math.min(size.width, size.height) / 2 - 5;
    final rect = Rect.fromCircle(center: center, radius: radius);
    final trackPaint = Paint()
      ..color = track
      ..style = PaintingStyle.stroke
      ..strokeWidth = 7;
    canvas.drawArc(rect, -math.pi / 2, math.pi * 2, false, trackPaint);
    if (value == null) return;
    final activePaint = Paint()
      ..color = active
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 7;
    canvas.drawArc(rect, -math.pi / 2, math.pi * 2 * value!.clamp(0.0, 1.0), false, activePaint);
  }

  @override
  bool shouldRepaint(covariant _DonutPainter oldDelegate) =>
      oldDelegate.value != value || oldDelegate.active != active || oldDelegate.track != track;
}

class _LineChartPainter extends CustomPainter {
  const _LineChartPainter({
    required this.values,
    required this.lineColor,
    required this.gridColor,
  });

  final List<double> values;
  final Color lineColor;
  final Color gridColor;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final gridPaint = Paint()
      ..color = gridColor.withValues(alpha: .5)
      ..strokeWidth = .6;
    for (var index = 1; index < 4; index++) {
      final y = size.height * index / 4;
      canvas.drawLine(Offset.zero.translate(0, y), Offset(size.width, y), gridPaint);
    }
    if (values.length < 2) return;
    final normalized = values.map((value) => value.clamp(0.0, 1.0)).toList(growable: false);
    final path = Path();
    for (var index = 0; index < normalized.length; index++) {
      final x = size.width * index / (normalized.length - 1);
      final y = size.height * (1 - normalized[index]);
      if (index == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }
    final linePaint = Paint()
      ..color = lineColor
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.6;
    canvas.drawPath(path, linePaint);
    final pointPaint = Paint()..color = lineColor;
    for (var index = 0; index < normalized.length; index++) {
      final x = size.width * index / (normalized.length - 1);
      final y = size.height * (1 - normalized[index]);
      canvas.drawCircle(Offset(x, y), 2.1, pointPaint);
    }
  }

  @override
  bool shouldRepaint(covariant _LineChartPainter oldDelegate) =>
      oldDelegate.values != values ||
      oldDelegate.lineColor != lineColor ||
      oldDelegate.gridColor != gridColor;
}

enum _AgentState { active, busy, idle, review, offline }

class _AgentRecord {
  const _AgentRecord({
    required this.id,
    required this.name,
    required this.role,
    required this.state,
    required this.currentTask,
    required this.currentTaskDetail,
    required this.capacity,
    required this.successRate,
    required this.successDelta,
    required this.responseSeconds,
    required this.lastActivity,
    required this.owner,
    required this.created,
    required this.activeTasks,
    required this.tokenUsage,
    required this.health,
    required this.skills,
    required this.performance,
  });

  final String id;
  final String name;
  final String role;
  final _AgentState state;
  final String currentTask;
  final String currentTaskDetail;
  final double? capacity;
  final double? successRate;
  final double? successDelta;
  final double? responseSeconds;
  final String lastActivity;
  final String owner;
  final String created;
  final int? activeTasks;
  final String tokenUsage;
  final String health;
  final List<String> skills;
  final List<double> performance;
}

List<_AgentRecord> _agentRecords(OperationalSnapshot snapshot) {
  final sources = <Map<String, Object?>>[];
  for (final key in const ['agents', 'workers', 'executors', 'leases']) {
    sources.addAll(_mapList(snapshot.schedulerState[key]));
  }
  for (final route in snapshot.runtimeRoutes) {
    if (_text(route, const ['agent_id', 'worker_id', 'executor_id', 'agent', 'worker']) != null) {
      sources.add(route);
    }
  }
  for (final event in snapshot.liveEvents) {
    if (_text(event, const ['agent_id', 'worker_id', 'executor_id', 'agent', 'worker']) != null) {
      sources.add(event);
    }
  }

  final merged = <String, Map<String, Object?>>{};
  for (final source in sources) {
    final id = _text(source, const ['agent_id', 'worker_id', 'executor_id', 'agent', 'worker', 'id']);
    if (id == null) continue;
    merged[id] = <String, Object?>{...?merged[id], ...source};
  }

  return merged.entries.map((entry) {
    final item = entry.value;
    final role = _text(item, const ['role', 'agent_role', 'worker_role', 'capability', 'specialty', 'type']) ?? '—';
    final stateRaw = _text(item, const ['agent_status', 'worker_status', 'status', 'state', 'lease_state']) ?? '';
    final activeTasks = _authoritativeInt(item, const ['active_tasks', 'task_count', 'active_jobs']);
    final tokenCurrent = _text(item, const ['token_usage', 'tokens_used', 'input_tokens', 'tokens']);
    final tokenLimit = _text(item, const ['token_limit', 'token_budget', 'max_tokens']);
    final skills = _stringList(item, const ['skills', 'capabilities', 'tools', 'competencies']);
    final performance = _numberList(item, const ['performance_7d', 'performance_history', 'success_history', 'performance']);
    return _AgentRecord(
      id: entry.key,
      name: _text(item, const ['agent_name', 'worker_name', 'display_name', 'name', 'title']) ?? entry.key,
      role: role,
      state: _agentState(stateRaw),
      currentTask: _text(item, const ['current_task', 'task', 'workflow_name', 'job_name', 'job_id', 'execution_id']) ?? '—',
      currentTaskDetail: _text(item, const ['task_detail', 'task_stage', 'stage', 'phase', 'action']) ?? '—',
      capacity: _ratio(item, const ['capacity', 'utilization', 'load', 'capacity_used', 'usage_percent']),
      successRate: _ratio(item, const ['success_rate', 'success_ratio', 'success_percent', 'quality_score']),
      successDelta: _signedRatio(item, const ['success_delta', 'success_change', 'quality_delta']),
      responseSeconds: _responseSeconds(item),
      lastActivity: _text(item, const ['last_activity', 'last_seen', 'updated_at', 'timestamp']) ?? '—',
      owner: _text(item, const ['owner', 'owner_name', 'assignee', 'principal']) ?? '—',
      created: _text(item, const ['created_at', 'created', 'started_at']) ?? '—',
      activeTasks: activeTasks,
      tokenUsage: tokenCurrent == null ? '—' : tokenLimit == null ? tokenCurrent : '$tokenCurrent / $tokenLimit',
      health: _text(item, const ['health', 'health_status', 'system_health']) ?? '—',
      skills: skills.isEmpty && role != '—' ? <String>[role] : skills,
      performance: performance,
    );
  }).toList(growable: false);
}

List<Map<String, Object?>> _pendingAssignments(OperationalSnapshot snapshot) {
  for (final key in const ['pending_assignments', 'assignments', 'queue', 'pending_tasks']) {
    final items = _mapList(snapshot.schedulerState[key]);
    if (items.isNotEmpty) return items;
  }
  return const <Map<String, Object?>>[];
}

List<Map<String, Object?>> _pendingReviews(OperationalSnapshot snapshot, String? agentId) {
  final candidates = <Map<String, Object?>>[];
  for (final key in const ['pending_reviews', 'pending_approvals', 'reviews', 'approvals', 'work']) {
    candidates.addAll(_mapList(snapshot.governanceState[key]));
  }
  if (agentId == null) return candidates;
  final matching = candidates.where((item) {
    final owner = _text(item, const ['agent_id', 'worker_id', 'assignee', 'subject_id']);
    return owner == null || owner == agentId;
  }).toList(growable: false);
  return matching;
}

Iterable<Map<String, Object?>> _agentEvents(OperationalSnapshot snapshot, String agentId) sync* {
  for (final event in snapshot.liveEvents.reversed) {
    final id = _text(event, const ['agent_id', 'worker_id', 'executor_id', 'agent', 'worker']);
    if (id == agentId) yield event;
  }
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
    if (value is String) {
      final parsed = int.tryParse(value.trim());
      if (parsed != null) return parsed;
    }
  }
  return null;
}

double? _ratio(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final parsed = _number(source[key]);
    if (parsed == null) continue;
    final ratio = parsed.abs() > 1 ? parsed / 100 : parsed;
    return ratio.clamp(0.0, 1.0);
  }
  return null;
}

double? _signedRatio(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final parsed = _number(source[key]);
    if (parsed == null) continue;
    return parsed.abs() > 1 ? parsed / 100 : parsed;
  }
  return null;
}

double? _responseSeconds(Map<String, Object?> source) {
  final seconds = _number(source['response_seconds']) ?? _number(source['latency_seconds']);
  if (seconds != null) return seconds;
  final milliseconds = _number(source['response_ms']) ?? _number(source['latency_ms']);
  return milliseconds == null ? null : milliseconds / 1000;
}

List<String> _stringList(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is List<Object?>) {
      return value
          .where((item) => item is String && item.trim().isNotEmpty)
          .cast<String>()
          .map((item) => item.trim())
          .toList(growable: false);
    }
    if (value is String && value.trim().isNotEmpty) {
      return value
          .split(RegExp(r'[,;|]'))
          .map((item) => item.trim())
          .where((item) => item.isNotEmpty)
          .toList(growable: false);
    }
  }
  return const <String>[];
}

List<double> _numberList(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is! List<Object?>) continue;
    final output = <double>[];
    for (final item in value) {
      final parsed = _number(item);
      if (parsed == null) continue;
      output.add((parsed.abs() > 1 ? parsed / 100 : parsed).clamp(0.0, 1.0));
    }
    if (output.isNotEmpty) return output;
  }
  return const <double>[];
}

double? _number(Object? value) {
  if (value is num) return value.toDouble();
  if (value is String) return double.tryParse(value.replaceAll('%', '').trim());
  return null;
}

int _stateCount(List<_AgentRecord> agents, _AgentState state) =>
    agents.where((item) => item.state == state).length;

double? _average(Iterable<double> values) {
  final list = values.toList(growable: false);
  if (list.isEmpty) return null;
  return list.reduce((a, b) => a + b) / list.length;
}

_AgentState _agentState(String raw) {
  final value = _normalize(raw);
  if (value.contains('offline') || value.contains('disabled') || value.contains('stopped') || value.contains('dead')) return _AgentState.offline;
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
  if (value.contains('test') || value.contains('qa')) return IlaiosTheme.success;
  if (value.contains('security')) return IlaiosTheme.danger;
  if (value.contains('backend')) return IlaiosTheme.warning;
  if (value.contains('deploy') || value.contains('devops')) return IlaiosTheme.violet;
  if (value.contains('automation') || value.contains('browser')) return IlaiosTheme.coreBlue;
  return IlaiosTheme.enterpriseCyan;
}

IconData _agentIcon(String role) {
  final value = _normalize(role);
  if (value.contains('test') || value.contains('qa')) return Icons.science_outlined;
  if (value.contains('security')) return Icons.shield_outlined;
  if (value.contains('backend')) return Icons.settings_suggest_outlined;
  if (value.contains('deploy') || value.contains('devops')) return Icons.rocket_launch_outlined;
  if (value.contains('automation') || value.contains('browser')) return Icons.smart_toy_outlined;
  if (value.contains('frontend')) return Icons.auto_awesome_outlined;
  return Icons.person_outline_rounded;
}

Color _skillColor(int index) {
  const colors = <Color>[
    IlaiosTheme.enterpriseCyan,
    IlaiosTheme.coreBlue,
    IlaiosTheme.violet,
    IlaiosTheme.warning,
    IlaiosTheme.success,
    IlaiosTheme.danger,
  ];
  return colors[index % colors.length];
}

Color _severityColor(String severity) {
  final value = _normalize(severity);
  if (value.contains('critical') || value.contains('high') || value.contains('yuksek')) return IlaiosTheme.danger;
  if (value.contains('medium') || value.contains('warning') || value.contains('orta')) return IlaiosTheme.warning;
  return IlaiosTheme.coreBlue;
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
            Text('${_tr(context, 'Durum', 'Status')}: ${_stateLabel(context, agent.state)}'),
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

void _showUnavailableAction(BuildContext context, String message) {
  ScaffoldMessenger.of(context).showSnackBar(
    SnackBar(content: Text(message), duration: const Duration(seconds: 2)),
  );
}
