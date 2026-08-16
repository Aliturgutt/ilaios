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
  Widget build(BuildContext context) {
    return Scaffold(
      body: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 900;
          if (compact) {
            return Column(
              children: [
                _CompactTopBar(
                  projection: widget.projection,
                  section: _section,
                  onSectionSelected: _selectSection,
                ),
                Expanded(child: _buildSection()),
                _BottomStatusBar(
                  projection: widget.projection,
                  snapshot: widget.operationalSnapshot,
                ),
              ],
            );
          }
          return Row(
            children: [
              _NavigationRail(
                selected: _section,
                userSession: widget.userSession,
                onSelected: _selectSection,
              ),
              Expanded(
                child: Column(
                  children: [
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
            width: 226,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(14, 20, 14, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const _BrandHeader(),
                  const SizedBox(height: 22),
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

class _TenantSummary extends StatelessWidget {
  const _TenantSummary({required this.userSession});
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) => Container(
        width: double.infinity,
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas.withValues(alpha: .55),
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Tenant', style: TextStyle(color: IlaiosTheme.muted, fontSize: 10)),
            const SizedBox(height: 4),
            Text(
              userSession?.tenantId ?? 'Unavailable',
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            const Row(
              children: [
                Expanded(
                  child: Text('Region  —', style: TextStyle(color: IlaiosTheme.muted, fontSize: 10)),
                ),
                Text('Plan  —', style: TextStyle(color: IlaiosTheme.muted, fontSize: 10)),
              ],
            ),
          ],
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
                  const _BrandMark(),
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

class _BrandHeader extends StatelessWidget {
  const _BrandHeader();

  @override
  Widget build(BuildContext context) => const Row(
        children: [
          _BrandMark(),
          SizedBox(width: 11),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'ILAIOS',
                  style: TextStyle(
                    fontSize: 20,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 1.7,
                  ),
                ),
                SizedBox(height: 1),
                Text(
                  'AUTONOMOUS OS',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 8,
                    color: IlaiosTheme.muted,
                    letterSpacing: 1.4,
                  ),
                ),
              ],
            ),
          ),
        ],
      );
}

class _BrandMark extends StatelessWidget {
  const _BrandMark();

  static const _asset = '../../brand/assets/05-ilaios-app-icon.jpg';

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'ILAIOS',
        image: true,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: Image.asset(
            _asset,
            width: 36,
            height: 36,
            fit: BoxFit.contain,
            filterQuality: FilterQuality.high,
            excludeFromSemantics: true,
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
          padding: const EdgeInsets.only(bottom: 5),
          child: Material(
            color: selected
                ? IlaiosTheme.cyan.withValues(alpha: .10)
                : Colors.transparent,
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(8),
              side: selected
                  ? BorderSide(color: IlaiosTheme.cyan.withValues(alpha: .32))
                  : BorderSide.none,
            ),
            clipBehavior: Clip.antiAlias,
            child: ListTile(
              key: ValueKey('nav-${section.name}'),
              minTileHeight: 40,
              contentPadding: const EdgeInsets.symmetric(horizontal: 11),
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
                  color: selected ? IlaiosTheme.text : IlaiosTheme.muted,
                  fontSize: 12,
                  fontWeight: selected ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ),
          ),
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
        builder: (context, constraints) => Container(
          height: 68,
          padding: const EdgeInsets.symmetric(horizontal: 18),
          decoration: const BoxDecoration(
            color: IlaiosTheme.surface,
            border: Border(bottom: BorderSide(color: IlaiosTheme.border)),
          ),
          child: Row(
            children: [
              ConstrainedBox(
                constraints: const BoxConstraints(maxWidth: 215),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text('Project', style: TextStyle(color: IlaiosTheme.muted, fontSize: 9)),
                    const SizedBox(height: 3),
                    Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Flexible(
                          child: Text(
                            _projectLabel(snapshot),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w600),
                          ),
                        ),
                        const SizedBox(width: 7),
                        Icon(
                          Icons.circle,
                          size: 7,
                          color: projection.connected ? IlaiosTheme.success : IlaiosTheme.muted,
                        ),
                      ],
                    ),
                  ],
                ),
              ),
              const Spacer(),
              if (constraints.maxWidth >= 880) ...[
                Container(
                  width: 210,
                  height: 34,
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: BoxDecoration(
                    color: IlaiosTheme.canvas,
                    borderRadius: BorderRadius.circular(7),
                    border: Border.all(color: IlaiosTheme.border),
                  ),
                  child: const Row(
                    children: [
                      Icon(Icons.search, size: 16, color: IlaiosTheme.muted),
                      SizedBox(width: 7),
                      Expanded(
                        child: Text(
                          'Global search unavailable',
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(color: IlaiosTheme.muted, fontSize: 10),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 10),
              ],
              const Tooltip(
                message: 'Notifications are not exposed by the current Desktop API',
                child: Icon(Icons.notifications_none, size: 20, color: IlaiosTheme.muted),
              ),
              const SizedBox(width: 14),
              const Tooltip(
                message: 'Locale follows system settings',
                child: Icon(Icons.language, size: 19, color: IlaiosTheme.muted),
              ),
              const SizedBox(width: 14),
              const Tooltip(
                message: 'Dark theme',
                child: Icon(Icons.dark_mode_outlined, size: 19, color: IlaiosTheme.muted),
              ),
              const SizedBox(width: 16),
              if (constraints.maxWidth >= 700) ...[
                _ProfileSummary(userSession: userSession),
                const SizedBox(width: 14),
              ],
              _ConnectionPill(projection: projection),
            ],
          ),
        ),
      );
}

class _ProfileSummary extends StatelessWidget {
  const _ProfileSummary({required this.userSession});
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) {
    final identity = userSession?.displayIdentity ?? userSession?.providerId ?? 'Signed out';
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 155),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: IlaiosTheme.surfaceRaised,
            child: Icon(
              userSession == null ? Icons.person_outline : Icons.person,
              size: 16,
              color: IlaiosTheme.cyan,
            ),
          ),
          const SizedBox(width: 8),
          Flexible(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  identity,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600),
                ),
                Text(
                  userSession == null ? 'Identity unavailable' : 'Authenticated',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: IlaiosTheme.muted, fontSize: 9),
                ),
              ],
            ),
          ),
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
    return Semantics(
      label: 'Control plane connection status: $label',
      liveRegion: true,
      child: ExcludeSemantics(
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: compact ? 8 : 10, vertical: 6),
          decoration: BoxDecoration(
            color: connected
                ? IlaiosTheme.success.withValues(alpha: .09)
                : IlaiosTheme.surfaceRaised,
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: connected
                  ? IlaiosTheme.success.withValues(alpha: .35)
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
        ),
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
    return Container(
      height: 34,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: const BoxDecoration(
        color: IlaiosTheme.surface,
        border: Border(top: BorderSide(color: IlaiosTheme.border)),
      ),
      child: Row(
        children: [
          _StatusItem(
            label: 'System',
            value: projection.connected ? 'Healthy' : 'Offline',
            active: projection.connected,
          ),
          const SizedBox(width: 18),
          _StatusItem(label: 'Workers', value: '$leases'),
          const SizedBox(width: 18),
          _StatusItem(label: 'Queues', value: queues?.toString() ?? '—'),
          const SizedBox(width: 18),
          const _StatusItem(label: 'Events/min', value: '—'),
          const Spacer(),
          _StatusItem(
            label: 'Control plane',
            value: projection.connected ? 'Connected' : 'Disconnected',
            active: projection.connected,
          ),
        ],
      ),
    );
  }
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
          Text('$label  ', style: const TextStyle(color: IlaiosTheme.muted, fontSize: 9)),
          Text(value, style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600)),
        ],
      );
}

String _projectLabel(OperationalSnapshot snapshot) {
  if (snapshot.liveEvents.isEmpty) return 'Current workspace';
  final latest = snapshot.liveEvents.last;
  for (final key in const <String>['project_name', 'project_id']) {
    final value = latest[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
  }
  return 'Current workspace';
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
