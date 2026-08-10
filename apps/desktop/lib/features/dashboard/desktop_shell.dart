import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/projection.dart';

class DesktopShell extends StatelessWidget {
  const DesktopShell({
    required this.projection,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;

  String _count(int? value) => value?.toString() ?? '—';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          const _NavigationRail(),
          Expanded(
            child: Column(
              children: [
                _TopBar(projection: projection),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(28),
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 1500),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text('Control Center', style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700)),
                          const SizedBox(height: 6),
                          const Text('Authoritative execution visibility for ILAIOS operations.'),
                          const SizedBox(height: 24),
                          Wrap(
                            spacing: 14,
                            runSpacing: 14,
                            children: [
                              _MetricCard(label: 'Goals', value: _count(projection.goalCount), icon: Icons.flag_outlined),
                              _MetricCard(label: 'Jobs', value: _count(projection.jobCount), icon: Icons.work_outline),
                              _MetricCard(label: 'Last event', value: projection.lastEvent ?? '—', icon: Icons.bolt_outlined),
                              _MetricCard(label: 'Schema', value: projection.schemaVersion ?? '—', icon: Icons.schema_outlined),
                            ],
                          ),
                          const SizedBox(height: 20),
                          LayoutBuilder(
                            builder: (context, constraints) {
                              final wide = constraints.maxWidth >= 900;
                              final execution = _ExecutionPanel(projection: projection, onRefreshRequested: onRefreshRequested);
                              const governance = _GovernancePanel();
                              if (!wide) {
                                return Column(children: [execution, const SizedBox(height: 16), governance]);
                              }
                              return Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [Expanded(flex: 2, child: execution), const SizedBox(width: 16), const Expanded(child: governance)],
                              );
                            },
                          ),
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

class _NavigationRail extends StatelessWidget {
  const _NavigationRail();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 232,
      color: IlaiosTheme.sidebar,
      padding: const EdgeInsets.fromLTRB(18, 24, 18, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(children: [
            _BrandMark(),
            SizedBox(width: 12),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('ILAIOS', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, letterSpacing: 1.8)),
              Text('DESKTOP', style: TextStyle(fontSize: 10, color: IlaiosTheme.muted, letterSpacing: 2)),
            ]),
          ]),
          const SizedBox(height: 34),
          const _NavItem(icon: Icons.dashboard_outlined, label: 'Control Center', selected: true),
          const _NavItem(icon: Icons.play_circle_outline, label: 'Live Execution'),
          const _NavItem(icon: Icons.account_tree_outlined, label: 'Workflows'),
          const _NavItem(icon: Icons.smart_toy_outlined, label: 'Agents'),
          const _NavItem(icon: Icons.fact_check_outlined, label: 'Evidence'),
          const _NavItem(icon: Icons.admin_panel_settings_outlined, label: 'Approvals'),
          const Spacer(),
          const Divider(),
          const SizedBox(height: 10),
          const Text('Client projection', style: TextStyle(color: IlaiosTheme.muted, fontSize: 11)),
          const SizedBox(height: 4),
          const Text('Backend authority enforced', style: TextStyle(fontSize: 12)),
        ],
      ),
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();
  @override
  Widget build(BuildContext context) => Container(
    width: 38,
    height: 38,
    decoration: BoxDecoration(
      borderRadius: BorderRadius.circular(10),
      border: Border.all(color: IlaiosTheme.primary.withValues(alpha: .65)),
      gradient: const LinearGradient(colors: [Color(0xFF173A72), Color(0xFF10273E)]),
    ),
    alignment: Alignment.center,
    child: const Text('I', style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800)),
  );
}

class _NavItem extends StatelessWidget {
  const _NavItem({required this.icon, required this.label, this.selected = false});
  final IconData icon;
  final String label;
  final bool selected;
  @override
  Widget build(BuildContext context) => Container(
    margin: const EdgeInsets.only(bottom: 7),
    decoration: BoxDecoration(
      color: selected ? IlaiosTheme.primary.withValues(alpha: .13) : Colors.transparent,
      borderRadius: BorderRadius.circular(10),
      border: selected ? Border.all(color: IlaiosTheme.primary.withValues(alpha: .25)) : null,
    ),
    child: ListTile(
      dense: true,
      leading: Icon(icon, size: 20, color: selected ? IlaiosTheme.cyan : IlaiosTheme.muted),
      title: Text(label, style: TextStyle(color: selected ? IlaiosTheme.text : IlaiosTheme.muted, fontSize: 13)),
    ),
  );
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.projection});
  final ControlPlaneProjection projection;
  @override
  Widget build(BuildContext context) => Container(
    height: 70,
    padding: const EdgeInsets.symmetric(horizontal: 28),
    decoration: const BoxDecoration(color: IlaiosTheme.surface, border: Border(bottom: BorderSide(color: IlaiosTheme.border))),
    child: Row(children: [
      const Text('Enterprise AI OS', style: TextStyle(fontWeight: FontWeight.w600)),
      const Spacer(),
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(color: projection.connected ? IlaiosTheme.success.withValues(alpha: .10) : IlaiosTheme.surfaceRaised, borderRadius: BorderRadius.circular(20), border: Border.all(color: projection.connected ? IlaiosTheme.success.withValues(alpha: .4) : IlaiosTheme.border)),
        child: Row(children: [
          Icon(Icons.circle, size: 8, color: projection.connected ? IlaiosTheme.success : IlaiosTheme.muted),
          const SizedBox(width: 8),
          Text(projection.connected ? 'CONTROL PLANE CONNECTED' : 'CONTROL PLANE OFFLINE', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
        ]),
      ),
    ]),
  );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.label, required this.value, required this.icon});
  final String label;
  final String value;
  final IconData icon;
  @override
  Widget build(BuildContext context) => Card(
    child: SizedBox(
      width: 220,
      height: 116,
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Row(children: [
          Container(width: 42, height: 42, decoration: BoxDecoration(color: IlaiosTheme.primary.withValues(alpha: .12), borderRadius: BorderRadius.circular(10)), child: Icon(icon, color: IlaiosTheme.cyan)),
          const SizedBox(width: 14),
          Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [Text(label, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12)), const SizedBox(height: 7), Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w700))])),
        ]),
      ),
    ),
  );
}

class _ExecutionPanel extends StatelessWidget {
  const _ExecutionPanel({required this.projection, this.onRefreshRequested});
  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;
  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(22),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        const Row(children: [Icon(Icons.monitor_heart_outlined, color: IlaiosTheme.cyan), SizedBox(width: 10), Text('Live Execution', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700))]),
        const SizedBox(height: 18),
        Semantics(label: 'Control plane connection status', child: Text(projection.status, key: const Key('connection-status'))),
        const SizedBox(height: 18),
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(color: IlaiosTheme.canvas, borderRadius: BorderRadius.circular(10), border: Border.all(color: IlaiosTheme.border)),
          child: Text(projection.connected ? 'Authoritative state is available. Execution details will appear only when supplied by the control plane.' : 'No authoritative execution state available. ILAIOS Desktop will not fabricate jobs, agents, logs, or progress.', style: const TextStyle(color: IlaiosTheme.muted, height: 1.5)),
        ),
        const SizedBox(height: 16),
        FilledButton.icon(key: const Key('refresh-command'), onPressed: projection.connected ? onRefreshRequested : null, icon: const Icon(Icons.refresh), label: const Text('Refresh authoritative state')),
      ]),
    ),
  );
}

class _GovernancePanel extends StatelessWidget {
  const _GovernancePanel();
  @override
  Widget build(BuildContext context) => const Card(
    child: Padding(
      padding: EdgeInsets.all(22),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [Icon(Icons.shield_outlined, color: IlaiosTheme.cyan), SizedBox(width: 10), Text('Governance', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700))]),
        SizedBox(height: 18),
        _GovernanceRow(label: 'Authority', value: 'Backend / control plane'),
        _GovernanceRow(label: 'Client mode', value: 'Projection only'),
        _GovernanceRow(label: 'Unverified capabilities', value: 'Hidden'),
        _GovernanceRow(label: 'Critical decisions', value: 'Server enforced'),
      ]),
    ),
  );
}

class _GovernanceRow extends StatelessWidget {
  const _GovernanceRow({required this.label, required this.value});
  final String label;
  final String value;
  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 9),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [Expanded(child: Text(label, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12))), const SizedBox(width: 12), Flexible(child: Text(value, textAlign: TextAlign.right, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600)))]),
  );
}
