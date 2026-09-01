import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
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
import 'desktop_shell.dart';
import 'reference_home_dashboard.dart';

class ReferenceDesktopShellV2 extends StatefulWidget {
  const ReferenceDesktopShellV2({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.themeMode = ThemeMode.dark,
    this.onThemeModeChanged,
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
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String requestId, GovernanceDecision decision)? onGovernanceDecision;

  @override
  State<ReferenceDesktopShellV2> createState() => _ReferenceDesktopShellV2State();
}

class _ReferenceDesktopShellV2State extends State<ReferenceDesktopShellV2> {
  DesktopSection _section = DesktopSection.home;

  void _select(DesktopSection section) {
    if (_section != section) setState(() => _section = section);
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          if (constraints.maxWidth < 1180) {
            return DesktopShell(
              projection: widget.projection,
              operationalSnapshot: widget.operationalSnapshot,
              operationalStatus: widget.operationalStatus,
              approverId: widget.approverId,
              identityProviders: widget.identityProviders,
              userSession: widget.userSession,
              identityStatus: widget.identityStatus,
              themeMode: widget.themeMode,
              onThemeModeChanged: widget.onThemeModeChanged,
              onSignIn: widget.onSignIn,
              onLogout: widget.onLogout,
              onPromptSubmit: widget.onPromptSubmit,
              onSaveArtifact: widget.onSaveArtifact,
              onRefreshRequested: widget.onRefreshRequested,
              onGovernanceDecision: widget.onGovernanceDecision,
            );
          }
          return Scaffold(
            body: Column(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      _Sidebar(
                        selected: _section,
                        projection: widget.projection,
                        snapshot: widget.operationalSnapshot,
                        userSession: widget.userSession,
                        onSelected: _select,
                      ),
                      VerticalDivider(
                        width: 1,
                        thickness: 1,
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      Expanded(
                        child: Column(
                          children: [
                            _TopBar(
                              projection: widget.projection,
                              snapshot: widget.operationalSnapshot,
                              userSession: widget.userSession,
                              themeMode: widget.themeMode,
                              onThemeModeChanged: widget.onThemeModeChanged,
                              onNavigate: _select,
                            ),
                            Expanded(child: _buildSection()),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                _BottomStatusBar(
                  projection: widget.projection,
                  snapshot: widget.operationalSnapshot,
                ),
              ],
            ),
          );
        },
      );

  Widget _buildSection() => switch (_section) {
        DesktopSection.home => ReferenceHomeDashboard(
            projection: widget.projection,
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
            onNavigate: _select,
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

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.selected,
    required this.projection,
    required this.snapshot,
    required this.userSession,
    required this.onSelected,
  });

  final DesktopSection selected;
  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onSelected;

  static const _wordmark = '../../brand/assets/02-ilaios-primary-horizontal-dark.jpg';

  @override
  Widget build(BuildContext context) => Semantics(
        container: true,
        label: context.tr('shell.primaryNavigation'),
        child: Container(
          key: const Key('reference-desktop-sidebar-v2'),
          width: 262,
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          padding: const EdgeInsets.fromLTRB(13, 16, 13, 14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Semantics(
                label: 'ILAIOS',
                image: true,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 5),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 205,
                        height: 48,
                        child: Image.asset(
                          _wordmark,
                          fit: BoxFit.contain,
                          alignment: Alignment.centerLeft,
                          filterQuality: FilterQuality.high,
                          excludeFromSemantics: true,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        'Integrated Learning, Autonomous\nIntelligence & Orchestration Systems',
                        style: TextStyle(
                          fontSize: 7.4,
                          height: 1.25,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 15),
              Expanded(
                child: ListView(
                  padding: EdgeInsets.zero,
                  children: [
                    for (final section in DesktopSection.values)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 5),
                        child: _NavItem(
                          section: section,
                          selected: selected == section,
                          onTap: () => onSelected(section),
                        ),
                      ),
                  ],
                ),
              ),
              _TenantSummary(
                projection: projection,
                snapshot: snapshot,
                userSession: userSession,
              ),
            ],
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
  Widget build(BuildContext context) => Material(
        color: selected ? IlaiosTheme.enterpriseCyan.withValues(alpha: .12) : Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: BorderSide(
            color: selected
                ? IlaiosTheme.enterpriseCyan.withValues(alpha: .46)
                : Colors.transparent,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          key: ValueKey('nav-${section.name}'),
          onTap: onTap,
          child: SizedBox(
            height: 43,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  Icon(
                    section.icon,
                    size: 20,
                    color: selected
                        ? IlaiosTheme.enterpriseCyan
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      section.localizedLabel(context),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13.2,
                        fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                        color: selected
                            ? IlaiosTheme.enterpriseCyan
                            : Theme.of(context).colorScheme.onSurface,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      );
}

class _TenantSummary extends StatelessWidget {
  const _TenantSummary({required this.projection, required this.snapshot, required this.userSession});
  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) {
    final region = _runtimeText(snapshot, const ['region', 'runtime_region', 'location']);
    return Container(
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(context.tr('shell.tenant'), style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: Text(
                  userSession?.tenantId ?? context.tr('shell.unavailable'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
                ),
              ),
              Icon(
                Icons.circle,
                size: 7,
                color: userSession == null ? Theme.of(context).colorScheme.outline : IlaiosTheme.success,
              ),
            ],
          ),
          const SizedBox(height: 8),
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          const SizedBox(height: 8),
          Text(_isTr(context) ? 'Bölge' : 'Region', style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 3),
          Text(
            region ?? context.tr('shell.unavailable'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelMedium,
          ),
          const SizedBox(height: 8),
          Text(
            projection.schemaVersion == null ? '—' : 'v${projection.schemaVersion}',
            style: Theme.of(context).textTheme.labelSmall,
          ),
        ],
      ),
    );
  }
}

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.projection,
    required this.snapshot,
    required this.userSession,
    required this.themeMode,
    required this.onThemeModeChanged,
    required this.onNavigate,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-desktop-topbar-v2'),
        height: 82,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 300,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(context.tr('shell.project'), style: Theme.of(context).textTheme.labelSmall),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Expanded(
                        child: Material(
                          color: Theme.of(context).colorScheme.surfaceContainerLowest,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6),
                            side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
                          ),
                          clipBehavior: Clip.antiAlias,
                          child: InkWell(
                            onTap: () => onNavigate(DesktopSection.goals),
                            child: SizedBox(
                              height: 35,
                              child: Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 10),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        _projectLabel(snapshot) ?? context.tr('shell.unavailable'),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: Theme.of(context).textTheme.labelLarge,
                                      ),
                                    ),
                                    const Icon(Icons.keyboard_arrow_down_rounded, size: 18),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Icon(
                        Icons.circle,
                        size: 7,
                        color: projection.connected ? IlaiosTheme.success : Theme.of(context).colorScheme.outline,
                      ),
                      const SizedBox(width: 5),
                      Text(
                        projection.connected ? context.tr('shell.connected') : context.tr('shell.offline'),
                        style: Theme.of(context).textTheme.labelSmall,
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const Spacer(),
            SizedBox(
              width: 250,
              height: 35,
              child: OutlinedButton.icon(
                onPressed: () => onNavigate(DesktopSection.goals),
                icon: const Icon(Icons.search_rounded, size: 18),
                label: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(context.tr('shell.search'), style: Theme.of(context).textTheme.bodySmall),
                ),
              ),
            ),
            const SizedBox(width: 14),
            IconButton(
              tooltip: context.tr('shell.notifications'),
              onPressed: () => _showNotice(context),
              icon: const Icon(Icons.notifications_none_rounded, size: 20),
            ),
            const SizedBox(width: 5),
            const _LanguageMenu(),
            const SizedBox(width: 5),
            IconButton(
              key: const Key('theme-toggle'),
              tooltip: context.tr('shell.darkTheme'),
              onPressed: onThemeModeChanged == null
                  ? null
                  : () => onThemeModeChanged!(
                        themeMode == ThemeMode.light ? ThemeMode.dark : ThemeMode.light,
                      ),
              icon: Icon(
                themeMode == ThemeMode.light ? Icons.dark_mode_outlined : Icons.light_mode_outlined,
                size: 20,
              ),
            ),
            const SizedBox(width: 12),
            Container(width: 1, height: 42, color: Theme.of(context).colorScheme.outlineVariant),
            const SizedBox(width: 14),
            InkWell(
              onTap: () => onNavigate(DesktopSection.settings),
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                child: Row(
                  children: [
                    CircleAvatar(
                      radius: 17,
                      backgroundColor: IlaiosTheme.enterpriseCyan.withValues(alpha: .13),
                      child: const Icon(Icons.person_outline_rounded, size: 19, color: IlaiosTheme.enterpriseCyan),
                    ),
                    const SizedBox(width: 9),
                    SizedBox(
                      width: 130,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            userSession?.displayIdentity ?? userSession?.principalId ?? context.tr('shell.identityUnavailable'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.labelLarge,
                          ),
                          const SizedBox(height: 2),
                          Text(
                            userSession == null ? context.tr('shell.signedOut') : context.tr('shell.authenticated'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.labelSmall,
                          ),
                        ],
                      ),
                    ),
                    const Icon(Icons.keyboard_arrow_down_rounded, size: 18),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
}

class _LanguageMenu extends StatelessWidget {
  const _LanguageMenu();

  @override
  Widget build(BuildContext context) => PopupMenuButton<IlaiosLocale>(
        tooltip: context.tr('shell.language'),
        icon: const Icon(Icons.language_rounded, size: 20),
        onSelected: (value) => context.ilaiosLocale.onChanged(value),
        itemBuilder: (context) => [
          PopupMenuItem(value: IlaiosLocale.english, child: Text(context.tr('language.english'))),
          PopupMenuItem(value: IlaiosLocale.turkish, child: Text(context.tr('language.turkish'))),
        ],
      );
}

class _BottomStatusBar extends StatelessWidget {
  const _BottomStatusBar({required this.projection, required this.snapshot});
  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final workers = _mapList(snapshot.schedulerState['leases']);
    final queues = _mapList(snapshot.schedulerState['queues']);
    return Container(
      key: const Key('reference-bottom-status-v2'),
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: 18),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        border: Border(top: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
      ),
      child: Row(
        children: [
          _StatusSegment(
            label: context.tr('shell.systemHealth'),
            value: projection.connected ? context.tr('shell.connected') : context.tr('shell.offline'),
            active: projection.connected,
          ),
          const SizedBox(width: 14),
          _StatusSegment(label: context.tr('shell.workers'), value: '${workers.length}'),
          const SizedBox(width: 14),
          _StatusSegment(
            label: context.tr('shell.queues'),
            value: queues.isEmpty ? '—' : '${queues.length}',
          ),
          const SizedBox(width: 14),
          _StatusSegment(label: context.tr('shell.eventsPerMinute'), value: '${snapshot.liveEventCount}'),
          const Spacer(),
          Text('© 2026 ILAIOS', style: Theme.of(context).textTheme.labelSmall),
          const Spacer(),
          _StatusSegment(
            label: context.tr('shell.realTime'),
            value: projection.connected ? context.tr('shell.connected') : context.tr('shell.offline'),
            active: projection.connected,
          ),
        ],
      ),
    );
  }
}

class _StatusSegment extends StatelessWidget {
  const _StatusSegment({required this.label, required this.value, this.active = false});
  final String label;
  final String value;
  final bool active;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label, style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(width: 7),
            if (active) ...[
              const Icon(Icons.circle, size: 7, color: IlaiosTheme.success),
              const SizedBox(width: 5),
            ],
            Text(value, style: Theme.of(context).textTheme.labelMedium),
          ],
        ),
      );
}

Future<void> _showNotice(BuildContext context) => showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.tr('shell.notifications')),
        content: Text(
          _isTr(context)
              ? 'Yetkili bildirim kaydı sunulmadığı için sentetik bildirim gösterilmiyor.'
              : 'No synthetic notifications are shown when authoritative notification records are unavailable.',
        ),
        actions: [
          TextButton(onPressed: () => Navigator.of(context).pop(), child: const Text('OK')),
        ],
      ),
    );

String? _projectLabel(OperationalSnapshot snapshot) {
  if (snapshot.liveEvents.isEmpty) return null;
  final event = snapshot.liveEvents.last;
  for (final key in const ['project', 'project_name', 'goal_title', 'goal']) {
    final value = event[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
  }
  return null;
}

String? _runtimeText(OperationalSnapshot snapshot, List<String> keys) {
  final sources = <Map<String, Object?>>[
    if (snapshot.liveEvents.isNotEmpty) snapshot.liveEvents.last,
    snapshot.schedulerState,
    snapshot.grantsState,
    snapshot.governanceState,
  ];
  for (final source in sources) {
    for (final key in keys) {
      final value = source[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
      if (value is num || value is bool) return '$value';
    }
  }
  return null;
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return value.whereType<Map<String, Object?>>().toList(growable: false);
}

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;
