import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';

class DesktopShell extends StatefulWidget {
  const DesktopShell({
    required this.projection,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;

  @override
  State<DesktopShell> createState() => _DesktopShellState();
}

class _DesktopShellState extends State<DesktopShell> {
  DesktopSection _section = DesktopSection.controlCenter;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 980;
          if (compact) {
            return Column(
              children: [
                _CompactTopBar(
                  projection: widget.projection,
                  section: _section,
                  onSectionSelected: _selectSection,
                ),
                Expanded(child: _buildSection()),
              ],
            );
          }
          return Row(
            children: [
              _NavigationRail(
                selected: _section,
                onSelected: _selectSection,
              ),
              Expanded(
                child: Column(
                  children: [
                    _TopBar(projection: widget.projection),
                    Expanded(child: _buildSection()),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  void _selectSection(DesktopSection section) {
    if (_section == section) {
      return;
    }
    setState(() => _section = section);
  }

  Widget _buildSection() {
    return switch (_section) {
      DesktopSection.controlCenter => _ControlCenterView(
          projection: widget.projection,
          onRefreshRequested: widget.onRefreshRequested,
        ),
      DesktopSection.liveExecution => _CapabilityBoundaryView(
          title: 'Live Execution',
          icon: Icons.play_circle_outline,
          projection: widget.projection,
          description:
              'This surface will render runtime routes, scheduler state and live events only from authenticated control-plane APIs.',
        ),
      DesktopSection.evidence => _CapabilityBoundaryView(
          title: 'Evidence',
          icon: Icons.fact_check_outlined,
          projection: widget.projection,
          description:
              'Evidence records remain server-owned. Desktop will display verification results only after the evidence API contract is connected.',
        ),
      DesktopSection.governance => _CapabilityBoundaryView(
          title: 'Governance',
          icon: Icons.admin_panel_settings_outlined,
          projection: widget.projection,
          description:
              'Authorization, policy and approvals remain authoritative in the backend. No client-side decision state is created here.',
        ),
    };
  }
}

class _ControlCenterView extends StatelessWidget {
  const _ControlCenterView({
    required this.projection,
    this.onRefreshRequested,
  });

  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;

  String _count(int? value) => value?.toString() ?? '—';

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1500),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Control Center',
                style: TextStyle(fontSize: 30, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 6),
              const Text(
                'Authoritative execution visibility for ILAIOS operations.',
              ),
              const SizedBox(height: 24),
              Wrap(
                spacing: 14,
                runSpacing: 14,
                children: [
                  _MetricCard(
                    label: 'Goals',
                    value: _count(projection.goalCount),
                    icon: Icons.flag_outlined,
                  ),
                  _MetricCard(
                    label: 'Jobs',
                    value: _count(projection.jobCount),
                    icon: Icons.work_outline,
                  ),
                  _MetricCard(
                    label: 'Last event',
                    value: projection.lastEvent ?? '—',
                    icon: Icons.bolt_outlined,
                  ),
                  _MetricCard(
                    label: 'Schema',
                    value: projection.schemaVersion ?? '—',
                    icon: Icons.schema_outlined,
                  ),
                ],
              ),
              const SizedBox(height: 20),
              LayoutBuilder(
                builder: (context, constraints) {
                  final wide = constraints.maxWidth >= 900;
                  final execution = _ExecutionPanel(
                    projection: projection,
                    onRefreshRequested: onRefreshRequested,
                  );
                  const governance = _GovernancePanel();
                  if (!wide) {
                    return Column(
                      children: [
                        execution,
                        const SizedBox(height: 16),
                        governance,
                      ],
                    );
                  }
                  return Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(flex: 2, child: execution),
                      const SizedBox(width: 16),
                      const Expanded(child: governance),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CapabilityBoundaryView extends StatelessWidget {
  const _CapabilityBoundaryView({
    required this.title,
    required this.icon,
    required this.projection,
    required this.description,
  });

  final String title;
  final IconData icon;
  final ControlPlaneProjection projection;
  final String description;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1000),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(26),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: IlaiosTheme.cyan),
                      const SizedBox(width: 10),
                      Text(
                        title,
                        style: const TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 18),
                  Text(description),
                  const SizedBox(height: 20),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: IlaiosTheme.canvas,
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: IlaiosTheme.border),
                    ),
                    child: Text(
                      projection.connected
                          ? 'Control plane connection is available. This surface remains locked until its typed API contract is verified.'
                          : 'Control plane unavailable. No operational data is fabricated or cached as authoritative state.',
                      style: const TextStyle(
                        color: IlaiosTheme.muted,
                        height: 1.5,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _NavigationRail extends StatelessWidget {
  const _NavigationRail({required this.selected, required this.onSelected});

  final DesktopSection selected;
  final ValueChanged<DesktopSection> onSelected;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 232,
      color: IlaiosTheme.sidebar,
      padding: const EdgeInsets.fromLTRB(18, 24, 18, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BrandHeader(),
          const SizedBox(height: 34),
          for (final section in DesktopSection.values)
            _NavItem(
              section: section,
              selected: selected == section,
              onTap: () => onSelected(section),
            ),
          const Spacer(),
          const Divider(),
          const SizedBox(height: 10),
          const Text(
            'Client projection',
            style: TextStyle(color: IlaiosTheme.muted, fontSize: 11),
          ),
          const SizedBox(height: 4),
          const Text(
            'Backend authority enforced',
            style: TextStyle(fontSize: 12),
          ),
        ],
      ),
    );
  }
}

class _CompactTopBar extends StatelessWidget {
  const _CompactTopBar({
    required this.projection,
    required this.section,
    required this.onSectionSelected,
  });

  final ControlPlaneProjection projection;
  final DesktopSection section;
  final ValueChanged<DesktopSection> onSectionSelected;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 68,
      padding: const EdgeInsets.symmetric(horizontal: 18),
      decoration: const BoxDecoration(
        color: IlaiosTheme.surface,
        border: Border(bottom: BorderSide(color: IlaiosTheme.border)),
      ),
      child: Row(
        children: [
          PopupMenuButton<DesktopSection>(
            tooltip: 'Navigate ILAIOS Desktop',
            onSelected: onSectionSelected,
            itemBuilder: (context) => [
              for (final item in DesktopSection.values)
                PopupMenuItem(
                  value: item,
                  child: Row(
                    children: [
                      Icon(item.icon, size: 18),
                      const SizedBox(width: 10),
                      Text(item.label),
                    ],
                  ),
                ),
            ],
            child: Row(
              children: [
                const _BrandMark(),
                const SizedBox(width: 10),
                Text(
                  section.label,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(width: 6),
                const Icon(Icons.expand_more, size: 18),
              ],
            ),
          ),
          const Spacer(),
          _ConnectionPill(projection: projection),
        ],
      ),
    );
  }
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader();

  @override
  Widget build(BuildContext context) {
    return const Row(
      children: [
        _BrandMark(),
        SizedBox(width: 12),
        Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'ILAIOS',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.8,
              ),
            ),
            Text(
              'DESKTOP',
              style: TextStyle(
                fontSize: 10,
                color: IlaiosTheme.muted,
                letterSpacing: 2,
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 38,
      height: 38,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(
          color: IlaiosTheme.primary.withValues(alpha: .65),
        ),
        gradient: const LinearGradient(
          colors: [Color(0xFF173A72), Color(0xFF10273E)],
        ),
      ),
      alignment: Alignment.center,
      child: const Text(
        'I',
        style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
      ),
    );
  }
}

class _NavItem extends StatelessWidget {
  const _NavItem({
    required this.section,
    required this.selected,
    required this.onTap,
  });

  final DesktopSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      decoration: BoxDecoration(
        color: selected
            ? IlaiosTheme.primary.withValues(alpha: .13)
            : Colors.transparent,
        borderRadius: BorderRadius.circular(10),
        border: selected
            ? Border.all(
                color: IlaiosTheme.primary.withValues(alpha: .25),
              )
            : null,
      ),
      child: ListTile(
        key: ValueKey('nav-${section.name}'),
        dense: true,
        onTap: onTap,
        leading: Icon(
          section.icon,
          size: 20,
          color: selected ? IlaiosTheme.cyan : IlaiosTheme.muted,
        ),
        title: Text(
          section.label,
          style: TextStyle(
            color: selected ? IlaiosTheme.text : IlaiosTheme.muted,
            fontSize: 13,
          ),
        ),
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({required this.projection});

  final ControlPlaneProjection projection;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: 70,
      padding: const EdgeInsets.symmetric(horizontal: 28),
      decoration: const BoxDecoration(
        color: IlaiosTheme.surface,
        border: Border(bottom: BorderSide(color: IlaiosTheme.border)),
      ),
      child: Row(
        children: [
          const Text(
            'Enterprise AI OS',
            style: TextStyle(fontWeight: FontWeight.w600),
          ),
          const Spacer(),
          _ConnectionPill(projection: projection),
        ],
      ),
    );
  }
}

class _ConnectionPill extends StatelessWidget {
  const _ConnectionPill({required this.projection});

  final ControlPlaneProjection projection;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
      decoration: BoxDecoration(
        color: projection.connected
            ? IlaiosTheme.success.withValues(alpha: .10)
            : IlaiosTheme.surfaceRaised,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: projection.connected
              ? IlaiosTheme.success.withValues(alpha: .4)
              : IlaiosTheme.border,
        ),
      ),
      child: Row(
        children: [
          Icon(
            Icons.circle,
            size: 8,
            color: projection.connected
                ? IlaiosTheme.success
                : IlaiosTheme.muted,
          ),
          const SizedBox(width: 8),
          Text(
            projection.connected
                ? 'CONTROL PLANE CONNECTED'
                : 'CONTROL PLANE OFFLINE',
            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
          ),
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.label,
    required this.value,
    required this.icon,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: SizedBox(
        width: 220,
        height: 116,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: IlaiosTheme.primary.withValues(alpha: .12),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Icon(icon, color: IlaiosTheme.cyan),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: const TextStyle(
                        color: IlaiosTheme.muted,
                        fontSize: 12,
                      ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 21,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ExecutionPanel extends StatelessWidget {
  const _ExecutionPanel({
    required this.projection,
    this.onRefreshRequested,
  });

  final ControlPlaneProjection projection;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Icon(Icons.monitor_heart_outlined, color: IlaiosTheme.cyan),
                SizedBox(width: 10),
                Text(
                  'Live Execution',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            const SizedBox(height: 18),
            Semantics(
              label: 'Control plane connection status',
              child: Text(
                projection.status,
                key: const Key('connection-status'),
              ),
            ),
            const SizedBox(height: 18),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: IlaiosTheme.canvas,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: IlaiosTheme.border),
              ),
              child: Text(
                projection.connected
                    ? 'Authoritative state is available. Execution details appear only after their typed backend contracts are connected.'
                    : 'No authoritative execution state available. ILAIOS Desktop will not fabricate jobs, agents, logs, or progress.',
                style: const TextStyle(
                  color: IlaiosTheme.muted,
                  height: 1.5,
                ),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton.icon(
              key: const Key('refresh-command'),
              onPressed: projection.connected ? onRefreshRequested : null,
              icon: const Icon(Icons.refresh),
              label: const Text('Refresh authoritative state'),
            ),
          ],
        ),
      ),
    );
  }
}

class _GovernancePanel extends StatelessWidget {
  const _GovernancePanel();

  @override
  Widget build(BuildContext context) {
    return const Card(
      child: Padding(
        padding: EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.shield_outlined, color: IlaiosTheme.cyan),
                SizedBox(width: 10),
                Text(
                  'Governance',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ],
            ),
            SizedBox(height: 18),
            _GovernanceRow(
              label: 'Authority',
              value: 'Backend / control plane',
            ),
            _GovernanceRow(label: 'Client mode', value: 'Projection only'),
            _GovernanceRow(
              label: 'Unverified capabilities',
              value: 'Hidden',
            ),
            _GovernanceRow(
              label: 'Critical decisions',
              value: 'Server enforced',
            ),
          ],
        ),
      ),
    );
  }
}

class _GovernanceRow extends StatelessWidget {
  const _GovernanceRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: IlaiosTheme.muted,
                fontSize: 12,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Flexible(
            child: Text(
              value,
              textAlign: TextAlign.right,
              style: const TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
