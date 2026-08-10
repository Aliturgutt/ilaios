import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import '../operations/operational_views.dart';
import 'control_center_view.dart';

class DesktopShell extends StatefulWidget {
  const DesktopShell({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.approverId,
    this.onRefreshRequested,
    this.onGovernanceDecision,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final String? approverId;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

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
    if (_section != section) setState(() => _section = section);
  }

  Widget _buildSection() {
    return switch (_section) {
      DesktopSection.controlCenter => ControlCenterView(
          projection: widget.projection,
          operationalSnapshot: widget.operationalSnapshot,
          operationalStatus: widget.operationalStatus,
          onRefreshRequested: widget.onRefreshRequested,
        ),
      DesktopSection.liveExecution => LiveExecutionView(
          projection: widget.projection,
          snapshot: widget.operationalSnapshot,
          status: widget.operationalStatus,
        ),
      DesktopSection.evidence => EvidenceView(
          snapshot: widget.operationalSnapshot,
          status: widget.operationalStatus,
        ),
      DesktopSection.governance => GovernanceView(
          snapshot: widget.operationalSnapshot,
          status: widget.operationalStatus,
          approverId: widget.approverId,
          onDecision: widget.onGovernanceDecision,
        ),
    };
  }
}

class _NavigationRail extends StatelessWidget {
  const _NavigationRail({required this.selected, required this.onSelected});
  final DesktopSection selected;
  final ValueChanged<DesktopSection> onSelected;

  @override
  Widget build(BuildContext context) => Semantics(
        container: true,
        label: 'ILAIOS Desktop primary navigation',
        child: Material(
          color: IlaiosTheme.sidebar,
          child: SizedBox(
            width: 232,
            child: Padding(
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
            ),
          ),
        ),
      );
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
  Widget build(BuildContext context) => Container(
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
                    child: Row(children: [
                      Icon(item.icon, size: 18),
                      const SizedBox(width: 10),
                      Text(item.label),
                    ]),
                  ),
              ],
              child: Row(children: [
                const _BrandMark(),
                const SizedBox(width: 10),
                Text(
                  section.label,
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                const SizedBox(width: 6),
                const Icon(Icons.expand_more, size: 18),
              ]),
            ),
            const Spacer(),
            _ConnectionPill(projection: projection),
          ],
        ),
      );
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader();
  @override
  Widget build(BuildContext context) => const Row(children: [
        _BrandMark(),
        SizedBox(width: 12),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
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
        ]),
      ]);
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();
  @override
  Widget build(BuildContext context) => Semantics(
        label: 'ILAIOS',
        image: true,
        child: Container(
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
          child: const ExcludeSemantics(
            child: Text(
              'I',
              style: TextStyle(fontSize: 21, fontWeight: FontWeight.w800),
            ),
          ),
        ),
      );
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
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: selected,
        label: section.label,
        excludeSemantics: true,
        child: Padding(
          padding: const EdgeInsets.only(bottom: 7),
          child: Material(
            color: selected
                ? IlaiosTheme.primary.withValues(alpha: .13)
                : Colors.transparent,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(10),
              side: selected
                  ? BorderSide(
                      color: IlaiosTheme.primary.withValues(alpha: .25),
                    )
                  : BorderSide.none,
            ),
            clipBehavior: Clip.antiAlias,
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
          ),
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
        decoration: const BoxDecoration(
          color: IlaiosTheme.surface,
          border: Border(bottom: BorderSide(color: IlaiosTheme.border)),
        ),
        child: Row(children: [
          const Text(
            'Enterprise AI OS',
            style: TextStyle(fontWeight: FontWeight.w600),
          ),
          const Spacer(),
          _ConnectionPill(projection: projection),
        ]),
      );
}

class _ConnectionPill extends StatelessWidget {
  const _ConnectionPill({required this.projection});
  final ControlPlaneProjection projection;

  @override
  Widget build(BuildContext context) {
    final label = projection.connected
        ? 'Control plane connected'
        : 'Control plane offline';
    return Semantics(
      liveRegion: true,
      label: label,
      child: Container(
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
        child: Row(children: [
          Icon(
            Icons.circle,
            size: 8,
            color: projection.connected
                ? IlaiosTheme.success
                : IlaiosTheme.muted,
          ),
          const SizedBox(width: 8),
          ExcludeSemantics(
            child: Text(
              projection.connected
                  ? 'CONTROL PLANE CONNECTED'
                  : 'CONTROL PLANE OFFLINE',
              style: const TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ]),
      ),
    );
  }
}
