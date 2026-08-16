import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../create/create_view.dart';
import '../deliveries/deliveries_view.dart';
import '../navigation/desktop_section.dart';
import '../operations/live_workspace_view.dart';
import '../operations/operational_views.dart';
import '../operations/support_views.dart';
import 'control_center_view.dart';
import 'home_dashboard_view.dart';

class DesktopShell extends StatefulWidget {
  const DesktopShell({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.onSignIn,
    this.onLogout,
    this.onPromptSubmit,
    this.onSaveArtifact,
    this.onRefreshRequested,
    this.onGovernanceDecision,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final String? approverId;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  @override
  State<DesktopShell> createState() => _DesktopShellState();
}

class _DesktopShellState extends State<DesktopShell> {
  DesktopSection _section = DesktopSection.home;

  @override
  Widget build(BuildContext context) => Scaffold(
        body: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 900;
            final body = Column(
              children: [
                if (compact)
                  _CompactTopBar(
                    projection: widget.projection,
                    section: _section,
                    onSectionSelected: _selectSection,
                  )
                else
                  _TopBar(
                    projection: widget.projection,
                    snapshot: widget.operationalSnapshot,
                    userSession: widget.userSession,
                  ),
                Expanded(child: _buildSection()),
                _BottomStatusBar(
                  projection: widget.projection,
                  snapshot: widget.operationalSnapshot,
                ),
              ],
            );
            if (compact) return body;
            return Row(
              children: [
                _NavigationRail(
                  selected: _section,
                  userSession: widget.userSession,
                  onSelected: _selectSection,
                ),
                const VerticalDivider(width: 1, thickness: 1, color: IlaiosTheme.border),
                Expanded(child: body),
              ],
            );
          },
        ),
      );

  void _selectSection(DesktopSection section) {
    if (_section != section) setState(() => _section = section);
  }

  Widget _buildSection() => switch (_section) {
        DesktopSection.home => HomeDashboardView(
            projection: widget.projection,
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
            userSession: widget.userSession,
            onRefreshRequested: widget.onRefreshRequested,
          ),
        DesktopSection.goals => CreateView(
            projection: widget.projection,
            status: widget.operationalStatus,
            identityProviders: widget.identityProviders,
            userSession: widget.userSession,
            identityStatus: widget.identityStatus,
            onSignIn: widget.onSignIn,
            onLogout: widget.onLogout,
            onSubmit: widget.onPromptSubmit,
          ),
        DesktopSection.workflows => ControlCenterView(
            projection: widget.projection,
            operationalSnapshot: widget.operationalSnapshot,
            operationalStatus: widget.operationalStatus,
            onRefreshRequested: widget.onRefreshRequested,
          ),
        DesktopSection.agents => LiveExecutionView(
            projection: widget.projection,
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
          ),
        DesktopSection.liveWorkspace => LiveWorkspaceView(
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
          ),
        DesktopSection.artifacts => DeliveriesView(
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
            onSaveArtifact: widget.onSaveArtifact,
          ),
        DesktopSection.approvals => GovernanceView(
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
            approverId: widget.approverId,
            onDecision: widget.onGovernanceDecision,
          ),
        DesktopSection.evidence => EvidenceView(
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
          ),
        DesktopSection.costs => CostsView(
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
          ),
        DesktopSection.settings => SettingsView(
            projection: widget.projection,
            identityStatus: widget.identityStatus,
            userSession: widget.userSession,
            providers: widget.identityProviders,
          ),
      };
}

class _NavigationRail extends StatelessWidget {
  const _NavigationRail({
    required this.selected,
    required this.userSession,
    required this.onSelected,
  });

  final DesktopSection selected;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onSelected;

  @override
  Widget build(BuildContext context) => Semantics(
        container: true,
        label: 'ILAIOS Desktop primary navigation',
        child: Material(
          color: IlaiosTheme.sidebar,
          child: SizedBox(
            width: 242,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 18, 14, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _BrandHeader(),
                  const SizedBox(height: 20),
                  Expanded(
                    child: ListView(
                      padding: EdgeInsets.zero,
                      children: [
                        for (final section in DesktopSection.values)
                          _NavItem(
                            section: section,
                            selected: selected == section,
                            onTap: () => onSelected(section),
                          ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 10),
                  _TenantSummary(userSession: userSession),
                ],
              ),
            ),
          ),
        ),
      );
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader();

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const _BrandMark(size: 42),
          const SizedBox(width: 11),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(top: 1),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: const [
                  Text(
                    'ILAIOS',
                    style: TextStyle(
                      fontSize: 23,
                      height: 1,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 1.8,
                      color: IlaiosTheme.text,
                    ),
                  ),
                  SizedBox(height: 6),
                  Text(
                    'Integrated Learning, Autonomous\nIntelligence & Orchestration Systems',
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 7.4,
                      height: 1.35,
                      color: IlaiosTheme.muted,
                      letterSpacing: .15,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      );
}

class _BrandMark extends StatelessWidget {
  const _BrandMark({this.size = 36});
  final double size;
  static const _asset = '../../brand/assets/03-ilaios-symbol-dark.jpg';

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'ILAIOS',
        image: true,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(7),
          child: Image.asset(
            _asset,
            width: size,
            height: size,
            fit: BoxFit.contain,
            filterQuality: FilterQuality.high,
            excludeFromSemantics: true,
          ),
        ),
      );
}

class _NavItem extends StatelessWidget {
  const _NavItem({required this.section, required this.selected, required this.onTap});

  final DesktopSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 5),
        child: Material(
          color: selected
              ? IlaiosTheme.cyan.withValues(alpha: .115)
              : Colors.transparent,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(7),
            side: selected
                ? BorderSide(color: IlaiosTheme.cyan.withValues(alpha: .38))
                : BorderSide.none,
          ),
          clipBehavior: Clip.antiAlias,
          child: ListTile(
            key: ValueKey('nav-${section.name}'),
            minTileHeight: 43,
            contentPadding: const EdgeInsets.symmetric(horizontal: 12),
            dense: true,
            onTap: onTap,
            leading: Icon(
              section.icon,
              size: 19,
              color: selected ? IlaiosTheme.cyan : IlaiosTheme.muted,
            ),
            title: Text(
              section.label,
              style: TextStyle(
                color: selected ? IlaiosTheme.text : IlaiosTheme.mutedStrong,
                fontSize: 12.5,
                fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
              ),
            ),
          ),
        ),
      );
}

class _TenantSummary extends StatelessWidget {
  const _TenantSummary({required this.userSession});
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) {
    final tenant = userSession?.tenantId;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: IlaiosTheme.canvas.withValues(alpha: .58),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: IlaiosTheme.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Tenant', style: TextStyle(color: IlaiosTheme.muted, fontSize: 9)),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: Text(
                  tenant ?? 'Unavailable',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600),
                ),
              ),
              if (tenant != null) ...[
                const SizedBox(width: 6),
                const Icon(Icons.circle, size: 6, color: IlaiosTheme.success),
              ],
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'Region —    Plan —',
            style: TextStyle(color: IlaiosTheme.muted, fontSize: 9),
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
  Widget build(BuildContext context) => Container(
        height: 64,
        padding: const EdgeInsets.symmetric(horizontal: 14),
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
                  const _BrandMark(size: 34),
                  const SizedBox(width: 9),
                  Text(section.label, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(width: 4),
                  const Icon(Icons.expand_more, size: 17),
                ],
              ),
            ),
            const Spacer(),
            _ConnectionPill(projection: projection, compact: true),
          ],
        ),
      );
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.projection,
    required this.snapshot,
    required this.userSession,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final project = _projectLabel(snapshot);
          return Container(
            height: 78,
            padding: const EdgeInsets.symmetric(horizontal: 18),
            decoration: BoxDecoration(
              color: IlaiosTheme.surface.withValues(alpha: .97),
              border: const Border(bottom: BorderSide(color: IlaiosTheme.border)),
            ),
            child: Row(
              children: [
                _ProjectSelector(project: project),
                const Spacer(),
                if (constraints.maxWidth >= 760) ...[
                  const _SearchField(),
                  const SizedBox(width: 18),
                ],
                const _TopIcon(icon: Icons.notifications_none, tooltip: 'Notifications'),
                const SizedBox(width: 14),
                const _TopIcon(icon: Icons.language, tooltip: 'System locale'),
                const SizedBox(width: 14),
                const _TopIcon(icon: Icons.light_mode_outlined, tooltip: 'Dark theme'),
                const SizedBox(width: 17),
                if (constraints.maxWidth >= 620) ...[
                  _ProfileSummary(userSession: userSession),
                  const SizedBox(width: 14),
                ],
                _ConnectionPill(projection: projection),
              ],
            ),
          );
        },
      );
}

class _ProjectSelector extends StatelessWidget {
  const _ProjectSelector({required this.project});
  final String? project;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 210,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Project', style: TextStyle(color: IlaiosTheme.muted, fontSize: 9)),
            const SizedBox(height: 4),
            Container(
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 11),
              decoration: BoxDecoration(
                color: IlaiosTheme.canvas,
                borderRadius: BorderRadius.circular(7),
                border: Border.all(color: IlaiosTheme.border),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      project ?? 'Unavailable',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 10.5,
                        fontWeight: FontWeight.w600,
                        color: project == null ? IlaiosTheme.muted : IlaiosTheme.text,
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Icon(Icons.expand_more, size: 15, color: IlaiosTheme.muted),
                ],
              ),
            ),
          ],
        ),
      );
}

class _SearchField extends StatelessWidget {
  const _SearchField();

  @override
  Widget build(BuildContext context) => Container(
        width: 220,
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 11),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(7),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: const Row(
          children: [
            Icon(Icons.search, size: 16, color: IlaiosTheme.muted),
            SizedBox(width: 8),
            Expanded(
              child: Text(
                'Search',
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(color: IlaiosTheme.muted, fontSize: 10),
              ),
            ),
            Text('⌘K', style: TextStyle(color: IlaiosTheme.muted, fontSize: 9)),
          ],
        ),
      );
}

class _TopIcon extends StatelessWidget {
  const _TopIcon({required this.icon, required this.tooltip});
  final IconData icon;
  final String tooltip;

  @override
  Widget build(BuildContext context) => Tooltip(
        message: tooltip,
        child: Icon(icon, size: 19, color: IlaiosTheme.mutedStrong),
      );
}

class _ProfileSummary extends StatelessWidget {
  const _ProfileSummary({required this.userSession});
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) {
    final identity = userSession?.displayIdentity ?? userSession?.providerId;
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 175),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(
            radius: 16,
            backgroundColor: IlaiosTheme.surfaceRaised,
            child: Icon(
              userSession == null ? Icons.person_outline : Icons.person,
              size: 17,
              color: userSession == null ? IlaiosTheme.muted : IlaiosTheme.cyan,
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  identity ?? 'Identity unavailable',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w600),
                ),
                Text(
                  userSession == null ? 'Signed out' : 'Authenticated',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: IlaiosTheme.muted, fontSize: 9),
                ),
              ],
            ),
          ),
          const SizedBox(width: 4),
          const Icon(Icons.expand_more, size: 14, color: IlaiosTheme.muted),
        ],
      ),
    );
  }
}

class _ConnectionPill extends StatelessWidget {
  const _ConnectionPill({required this.projection, this.compact = false});
  final ControlPlaneProjection projection;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final connected = projection.connected;
    final label = connected ? 'Connected' : 'Offline';
    return Container(
      padding: EdgeInsets.symmetric(horizontal: compact ? 8 : 11, vertical: 7),
      decoration: BoxDecoration(
        color: connected
            ? IlaiosTheme.success.withValues(alpha: .08)
            : IlaiosTheme.surfaceRaised,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: connected
              ? IlaiosTheme.success.withValues(alpha: .38)
              : IlaiosTheme.border,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.circle,
            size: 7,
            color: connected ? IlaiosTheme.success : IlaiosTheme.muted,
          ),
          const SizedBox(width: 6),
          Text(label, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }
}

class _BottomStatusBar extends StatelessWidget {
  const _BottomStatusBar({required this.projection, required this.snapshot});
  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final leases = _mapList(snapshot.schedulerState['leases']).length;
    final queues = _queueCount(snapshot.schedulerState);
    final wide = MediaQuery.sizeOf(context).width >= 980;
    return Container(
      height: 38,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: const BoxDecoration(
        color: IlaiosTheme.surface,
        border: Border(top: BorderSide(color: IlaiosTheme.border)),
      ),
      child: Row(
        children: [
          _StatusCapsule(
            label: 'System Health',
            value: projection.connected ? 'Healthy' : 'Offline',
            active: projection.connected,
          ),
          const SizedBox(width: 10),
          _StatusCapsule(label: 'Workers', value: '$leases'),
          const SizedBox(width: 10),
          _StatusCapsule(label: 'Queues', value: queues?.toString() ?? '—'),
          if (wide) ...[
            const SizedBox(width: 10),
            const _StatusCapsule(label: 'Events / min', value: '—'),
          ],
          const Spacer(),
          if (wide)
            const Text(
              '© ILAIOS',
              style: TextStyle(color: IlaiosTheme.muted, fontSize: 9),
            ),
          const Spacer(),
          _StatusItem(
            label: 'Real-time',
            value: projection.connected ? 'Connected' : 'Offline',
            active: projection.connected,
          ),
        ],
      ),
    );
  }
}

class _StatusCapsule extends StatelessWidget {
  const _StatusCapsule({required this.label, required this.value, this.active = false});
  final String label;
  final String value;
  final bool active;

  @override
  Widget build(BuildContext context) => Container(
        height: 25,
        padding: const EdgeInsets.symmetric(horizontal: 9),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas.withValues(alpha: .7),
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Center(child: _StatusItem(label: label, value: value, active: active)),
      );
}

class _StatusItem extends StatelessWidget {
  const _StatusItem({required this.label, required this.value, this.active = false});
  final String label;
  final String value;
  final bool active;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (active) ...[
            const Icon(Icons.circle, size: 6, color: IlaiosTheme.success),
            const SizedBox(width: 5),
          ],
          Text('$label  ', style: const TextStyle(color: IlaiosTheme.muted, fontSize: 8.5)),
          Text(value, style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600)),
        ],
      );
}

String? _projectLabel(OperationalSnapshot snapshot) {
  if (snapshot.liveEvents.isEmpty) return null;
  final latest = snapshot.liveEvents.last;
  for (final key in const <String>['project_name', 'project_id']) {
    final value = latest[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
  }
  return null;
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return <Map<String, Object?>>[
    for (final item in value)
      if (item is Map<String, dynamic>) Map<String, Object?>.from(item),
  ];
}

int? _queueCount(Map<String, Object?> scheduler) {
  for (final key in const <String>['queue', 'queued', 'pending', 'tasks']) {
    final value = scheduler[key];
    if (value is List<Object?>) return value.length;
    if (value is int && value >= 0) return value;
  }
  return null;
}
