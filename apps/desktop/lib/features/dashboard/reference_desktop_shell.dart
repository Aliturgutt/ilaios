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
import 'home_dashboard_v2.dart';

class ReferenceDesktopShell extends StatefulWidget {
  const ReferenceDesktopShell({
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
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  @override
  State<ReferenceDesktopShell> createState() => _ReferenceDesktopShellState();
}

class _ReferenceDesktopShellState extends State<ReferenceDesktopShell> {
  DesktopSection _section = DesktopSection.home;

  void _selectSection(DesktopSection section) {
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
                      _ReferenceNavigationRail(
                        selected: _section,
                        snapshot: widget.operationalSnapshot,
                        userSession: widget.userSession,
                        onSelected: _selectSection,
                      ),
                      VerticalDivider(
                        width: 1,
                        thickness: 1,
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      Expanded(
                        child: Column(
                          children: [
                            _ReferenceTopBar(
                              projection: widget.projection,
                              snapshot: widget.operationalSnapshot,
                              userSession: widget.userSession,
                              themeMode: widget.themeMode,
                              onThemeModeChanged: widget.onThemeModeChanged,
                              onNavigate: _selectSection,
                            ),
                            Expanded(child: _buildSection()),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                _ReferenceBottomStatusBar(
                  projection: widget.projection,
                  snapshot: widget.operationalSnapshot,
                  onNavigate: _selectSection,
                ),
              ],
            ),
          );
        },
      );

  Widget _buildSection() => switch (_section) {
        DesktopSection.home => InteractiveHomeDashboardView(
            projection: widget.projection,
            snapshot: widget.operationalSnapshot,
            status: widget.operationalStatus,
            userSession: widget.userSession,
            onNavigate: _selectSection,
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

class _ReferenceNavigationRail extends StatelessWidget {
  const _ReferenceNavigationRail({
    required this.selected,
    required this.snapshot,
    required this.userSession,
    required this.onSelected,
  });

  final DesktopSection selected;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onSelected;

  static const _wordmark =
      '../../brand/assets/02-ilaios-primary-horizontal-dark.jpg';

  @override
  Widget build(BuildContext context) => Semantics(
        container: true,
        label: context.tr('shell.primaryNavigation'),
        child: Container(
          key: const Key('reference-desktop-sidebar'),
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
                  padding: const EdgeInsets.symmetric(horizontal: 6),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SizedBox(
                        width: 190,
                        height: 46,
                        child: Image.asset(
                          _wordmark,
                          fit: BoxFit.contain,
                          alignment: Alignment.centerLeft,
                          filterQuality: FilterQuality.high,
                          excludeFromSemantics: true,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        'Integrated Learning, Autonomous\nIntelligence & Orchestration Systems',
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 7.3,
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
                      _ReferenceNavItem(
                        section: section,
                        selected: section == selected,
                        onTap: () => onSelected(section),
                      ),
                  ],
                ),
              ),
              _ReferenceTenantSummary(
                snapshot: snapshot,
                userSession: userSession,
              ),
            ],
          ),
        ),
      );
}

class _ReferenceNavItem extends StatelessWidget {
  const _ReferenceNavItem({
    required this.section,
    required this.selected,
    required this.onTap,
  });

  final DesktopSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 5),
      child: Material(
        color: selected
            ? IlaiosTheme.enterpriseCyan.withValues(alpha: .12)
            : Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: BorderSide(
            color: selected
                ? IlaiosTheme.enterpriseCyan.withValues(alpha: .44)
                : Colors.transparent,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          key: ValueKey('nav-${section.name}'),
          onTap: onTap,
          child: SizedBox(
            height: 42,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  Icon(
                    section.icon,
                    size: 20,
                    color: selected
                        ? IlaiosTheme.enterpriseCyan
                        : scheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      section.localizedLabel(context),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 13.5,
                        color: selected
                            ? IlaiosTheme.enterpriseCyan
                            : scheme.onSurface,
                        fontWeight:
                            selected ? FontWeight.w700 : FontWeight.w500,
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

class _ReferenceTenantSummary extends StatelessWidget {
  const _ReferenceTenantSummary({
    required this.snapshot,
    required this.userSession,
  });

  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) {
    final tenant = userSession?.tenantId;
    final region = _runtimeValue(
      snapshot,
      const ['region', 'runtime_region', 'location'],
    );
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.tr('shell.tenant'),
            style: Theme.of(context).textTheme.labelSmall,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: Text(
                  tenant ?? context.tr('shell.unavailable'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 11.3,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Icon(
                Icons.circle,
                size: 7,
                color: tenant == null
                    ? Theme.of(context).colorScheme.outline
                    : IlaiosTheme.success,
              ),
            ],
          ),
          const SizedBox(height: 10),
          Divider(
            height: 1,
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          const SizedBox(height: 8),
          Text(
            _isTr(context) ? 'Bölge' : 'Region',
            style: Theme.of(context).textTheme.labelSmall,
          ),
          const SizedBox(height: 3),
          Text(
            region ?? context.tr('shell.unavailable'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.labelMedium,
          ),
        ],
      ),
    );
  }
}

class _ReferenceTopBar extends StatelessWidget {
  const _ReferenceTopBar({
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
        key: const Key('reference-desktop-topbar'),
        height: 82,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          border: Border(
            bottom: BorderSide(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
        ),
        child: Row(
          children: [
            _ReferenceProjectSelector(
              project: _projectLabel(snapshot),
              connected: projection.connected,
              onTap: () => onNavigate(DesktopSection.goals),
            ),
            const Spacer(),
            _ReferenceSearchButton(onNavigate: onNavigate),
            const SizedBox(width: 16),
            IconButton(
              tooltip: context.tr('shell.notifications'),
              onPressed: () => _showUnavailableNotice(context),
              style: IconButton.styleFrom(
                fixedSize: const Size.square(36),
                padding: EdgeInsets.zero,
              ),
              icon: const Icon(Icons.notifications_none_rounded, size: 20),
            ),
            const SizedBox(width: 8),
            const _ReferenceLanguageMenu(),
            const SizedBox(width: 8),
            _ReferenceThemeButton(
              themeMode: themeMode,
              onChanged: onThemeModeChanged,
            ),
            const SizedBox(width: 16),
            Container(
              width: 1,
              height: 42,
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
            const SizedBox(width: 16),
            _ReferenceProfileSummary(
              userSession: userSession,
              onTap: () => onNavigate(DesktopSection.settings),
            ),
          ],
        ),
      );
}

class _ReferenceProjectSelector extends StatelessWidget {
  const _ReferenceProjectSelector({
    required this.project,
    required this.connected,
    required this.onTap,
  });

  final String? project;
  final bool connected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 270,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('shell.project'),
              style: Theme.of(context).textTheme.labelSmall,
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Expanded(
                  child: Material(
                    color: Theme.of(context).colorScheme.surfaceContainerLowest,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(6),
                      side: BorderSide(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: onTap,
                      child: SizedBox(
                        height: 34,
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  project ?? context.tr('shell.unavailable'),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                              const Icon(Icons.expand_more_rounded, size: 16),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 8),
                Icon(
                  Icons.circle,
                  size: 7,
                  color: connected
                      ? IlaiosTheme.success
                      : Theme.of(context).colorScheme.outline,
                ),
                const SizedBox(width: 5),
                Text(
                  connected
                      ? (_isTr(context) ? 'Aktif' : 'Active')
                      : (_isTr(context) ? 'Çevrimdışı' : 'Offline'),
                  style: Theme.of(context).textTheme.labelSmall,
                ),
              ],
            ),
          ],
        ),
      );
}

class _ReferenceSearchButton extends StatelessWidget {
  const _ReferenceSearchButton({required this.onNavigate});

  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 218,
        height: 36,
        child: OutlinedButton(
          onPressed: () => _showCommandPalette(context, onNavigate),
          style: OutlinedButton.styleFrom(
            foregroundColor: Theme.of(context).colorScheme.onSurfaceVariant,
            side: BorderSide(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
            padding: const EdgeInsets.symmetric(horizontal: 10),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(6),
            ),
          ),
          child: Row(
            children: [
              const Icon(Icons.search_rounded, size: 17),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  context.tr('shell.search'),
                  textAlign: TextAlign.left,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10.5),
                ),
              ),
              Text('⌘K', style: Theme.of(context).textTheme.labelSmall),
            ],
          ),
        ),
      );
}

class _ReferenceLanguageMenu extends StatelessWidget {
  const _ReferenceLanguageMenu();

  @override
  Widget build(BuildContext context) {
    final scope = context.ilaiosLocale;
    return PopupMenuButton<IlaiosLocale>(
      tooltip: context.tr('shell.language'),
      onSelected: scope.onChanged,
      itemBuilder: (context) => [
        PopupMenuItem(
          value: IlaiosLocale.english,
          child: Text(context.tr('language.english')),
        ),
        PopupMenuItem(
          value: IlaiosLocale.turkish,
          child: Text(context.tr('language.turkish')),
        ),
      ],
      child: const SizedBox(
        width: 36,
        height: 36,
        child: Icon(Icons.language_rounded, size: 20),
      ),
    );
  }
}

class _ReferenceThemeButton extends StatelessWidget {
  const _ReferenceThemeButton({
    required this.themeMode,
    required this.onChanged,
  });

  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onChanged;

  @override
  Widget build(BuildContext context) {
    final systemLight = Theme.of(context).brightness == Brightness.light;
    final light = themeMode == ThemeMode.light ||
        (themeMode == ThemeMode.system && systemLight);
    return IconButton(
      key: const Key('theme-toggle'),
      tooltip: light
          ? (_isTr(context) ? 'Koyu temaya geç' : 'Switch to dark theme')
          : (_isTr(context) ? 'Açık temaya geç' : 'Switch to light theme'),
      onPressed: onChanged == null
          ? null
          : () => onChanged!(light ? ThemeMode.dark : ThemeMode.light),
      style: IconButton.styleFrom(
        fixedSize: const Size.square(36),
        padding: EdgeInsets.zero,
      ),
      icon: Icon(
        light ? Icons.dark_mode_outlined : Icons.light_mode_outlined,
        size: 20,
      ),
    );
  }
}

class _ReferenceProfileSummary extends StatelessWidget {
  const _ReferenceProfileSummary({
    required this.userSession,
    required this.onTap,
  });

  final DesktopUserSession? userSession;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final identity =
        userSession?.displayIdentity ?? context.tr('shell.signedOut');
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(7),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: IlaiosTheme.enterpriseCyan.withValues(alpha: .10),
                shape: BoxShape.circle,
                border: Border.all(
                  color: IlaiosTheme.enterpriseCyan.withValues(alpha: .24),
                ),
              ),
              child: const Icon(
                Icons.person_outline_rounded,
                size: 19,
                color: IlaiosTheme.enterpriseCyan,
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 96,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    identity,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 11.2,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    userSession == null
                        ? context.tr('shell.signedOut')
                        : context.tr('shell.authenticated'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall,
                  ),
                ],
              ),
            ),
            const Icon(Icons.expand_more_rounded, size: 15),
          ],
        ),
      ),
    );
  }
}

class _ReferenceBottomStatusBar extends StatelessWidget {
  const _ReferenceBottomStatusBar({
    required this.projection,
    required this.snapshot,
    required this.onNavigate,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final ValueChanged<DesktopSection> onNavigate;

  int _listLength(Map<String, Object?> source, String key) {
    final value = source[key];
    return value is List<Object?> ? value.length : 0;
  }

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-desktop-statusbar'),
        height: 48,
        padding: const EdgeInsets.symmetric(horizontal: 20),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          border: Border(
            top: BorderSide(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
        ),
        child: Row(
          children: [
            _ReferenceStatusChip(
              label: context.tr('shell.systemHealth'),
              value: projection.connected
                  ? context.tr('shell.healthy')
                  : context.tr('shell.offline'),
              accent: projection.connected
                  ? IlaiosTheme.success
                  : Theme.of(context).colorScheme.outline,
              onTap: () => onNavigate(DesktopSection.workflows),
            ),
            const SizedBox(width: 11),
            _ReferenceStatusChip(
              label: context.tr('shell.workers'),
              value: '${_listLength(snapshot.schedulerState, 'leases')}',
              accent: IlaiosTheme.enterpriseCyan,
              onTap: () => onNavigate(DesktopSection.agents),
            ),
            const SizedBox(width: 11),
            _ReferenceStatusChip(
              label: _isTr(context) ? 'Kuyruklar' : 'Queues',
              value: '${_listLength(snapshot.schedulerState, 'queues')}',
              accent: IlaiosTheme.coreBlue,
              onTap: () => onNavigate(DesktopSection.workflows),
            ),
            const SizedBox(width: 11),
            _ReferenceStatusChip(
              label: _isTr(context) ? 'Olaylar' : 'Events',
              value: '${snapshot.liveEventCount}',
              accent: IlaiosTheme.enterpriseCyan,
              onTap: () => onNavigate(DesktopSection.liveWorkspace),
            ),
            const Spacer(),
            Text(
              '© 2026 ILAIOS',
              style: Theme.of(context).textTheme.labelSmall,
            ),
            const Spacer(),
            Icon(
              Icons.circle,
              size: 7,
              color: projection.connected
                  ? IlaiosTheme.success
                  : Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(width: 6),
            Text(
              context.tr('shell.realTime'),
              style: Theme.of(context).textTheme.labelSmall,
            ),
            const SizedBox(width: 6),
            Text(
              projection.connected
                  ? context.tr('shell.connected')
                  : context.tr('shell.offline'),
              style: const TextStyle(fontSize: 10.5),
            ),
          ],
        ),
      );
}

class _ReferenceStatusChip extends StatelessWidget {
  const _ReferenceStatusChip({
    required this.label,
    required this.value,
    required this.accent,
    required this.onTap,
  });

  final String label;
  final String value;
  final Color accent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(5),
        child: Container(
          height: 30,
          padding: const EdgeInsets.symmetric(horizontal: 9),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(5),
            border: Border.all(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label, style: Theme.of(context).textTheme.labelSmall),
              const SizedBox(width: 6),
              Text(
                value,
                style: TextStyle(
                  color: accent,
                  fontSize: 10.3,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ],
          ),
        ),
      );
}

String? _projectLabel(OperationalSnapshot snapshot) {
  for (final event in snapshot.liveEvents.reversed) {
    for (final key in const [
      'project',
      'project_name',
      'workspace',
      'goal_title',
    ]) {
      final value = event[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
  }
  return null;
}

String? _runtimeValue(OperationalSnapshot snapshot, List<String> keys) {
  for (final event in snapshot.liveEvents.reversed) {
    for (final key in keys) {
      final value = event[key];
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
  }
  return null;
}

Future<void> _showCommandPalette(
  BuildContext context,
  ValueChanged<DesktopSection> onNavigate,
) async {
  final controller = TextEditingController();
  DesktopSection? selected;
  await showDialog<void>(
    context: context,
    builder: (dialogContext) => StatefulBuilder(
      builder: (context, setState) {
        final query = controller.text.trim().toLowerCase();
        final items = DesktopSection.values.where((section) {
          final label = section.localizedLabel(context).toLowerCase();
          return query.isEmpty ||
              label.contains(query) ||
              section.name.toLowerCase().contains(query);
        }).toList();
        return AlertDialog(
          title: Text(_isTr(context) ? 'ILAIOS içinde ara' : 'Search ILAIOS'),
          content: SizedBox(
            width: 440,
            height: 400,
            child: Column(
              children: [
                TextField(
                  autofocus: true,
                  controller: controller,
                  onChanged: (value) => setState(() {}),
                  decoration: InputDecoration(
                    prefixIcon: const Icon(Icons.search_rounded),
                    hintText: _isTr(context)
                        ? 'Sayfa veya özellik ara'
                        : 'Search pages or features',
                  ),
                ),
                const SizedBox(height: 10),
                Expanded(
                  child: ListView(
                    children: [
                      for (final section in items)
                        ListTile(
                          leading: Icon(section.icon, size: 19),
                          title: Text(section.localizedLabel(context)),
                          onTap: () {
                            selected = section;
                            Navigator.of(dialogContext).pop();
                          },
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    ),
  );
  controller.dispose();
  if (selected != null) onNavigate(selected!);
}

Future<void> _showUnavailableNotice(BuildContext context) => showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: const Icon(Icons.notifications_none_rounded),
        title: Text(_isTr(context) ? 'Bildirimler' : 'Notifications'),
        content: Text(
          _isTr(context)
              ? 'Yetkili çalışma zamanı bildirim verisi sunmadı. Sentetik bildirim üretilmez.'
              : 'The authoritative runtime exposes no notification data. Synthetic notifications are not fabricated.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_isTr(context) ? 'Kapat' : 'Close'),
          ),
        ],
      ),
    );

bool _isTr(BuildContext context) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish;
