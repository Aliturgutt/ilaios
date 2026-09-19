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
import 'reference_home_dashboard_v2.dart';

/// Final reference shell for the approved ILAIOS Desktop dashboard.
///
/// Normal desktop windows use a fixed single-viewport composition. Compact or
/// accessibility-constrained windows deliberately fall back to the verified
/// responsive shell rather than introducing a web-page-like global scroll.
class ReferenceDesktopShellV5 extends StatefulWidget {
  const ReferenceDesktopShellV5({
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
  State<ReferenceDesktopShellV5> createState() =>
      _ReferenceDesktopShellV5State();
}

class _ReferenceDesktopShellV5State extends State<ReferenceDesktopShellV5> {
  DesktopSection _section = DesktopSection.home;

  void _select(DesktopSection section) {
    if (_section != section) setState(() => _section = section);
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final textScale = MediaQuery.textScalerOf(context).scale(1);
          final compact = constraints.maxWidth < 1180 ||
              constraints.maxHeight < 800 ||
              (textScale >= 1.45 && constraints.maxWidth < 1800);

          if (compact) {
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
        DesktopSection.home => ReferenceHomeDashboardV2(
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

  static const _symbol = '../../brand/assets/05-ilaios-app-icon.jpg';

  @override
  Widget build(BuildContext context) => Semantics(
        container: true,
        label: context.tr('shell.primaryNavigation'),
        child: Container(
          key: const Key('reference-desktop-sidebar-v5'),
          width: 250,
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          padding: const EdgeInsets.fromLTRB(13, 13, 13, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Semantics(
                label: 'ILAIOS',
                image: true,
                child: SizedBox(
                  height: 72,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Image.asset(
                        _symbol,
                        width: 46,
                        height: 46,
                        fit: BoxFit.contain,
                        filterQuality: FilterQuality.high,
                        excludeFromSemantics: true,
                      ),
                      const SizedBox(width: 9),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'ILAIOS',
                              maxLines: 1,
                              style: TextStyle(
                                fontSize: 26,
                                height: 1,
                                fontWeight: FontWeight.w800,
                                letterSpacing: 1.2,
                              ),
                            ),
                            const SizedBox(height: 6),
                            Text(
                              'Integrated Learning, Autonomous\nIntelligence & Orchestration Systems',
                              maxLines: 2,
                              style: TextStyle(
                                fontSize: 6.8,
                                height: 1.2,
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
              ),
              const SizedBox(height: 8),
              Expanded(
                child: ListView(
                  padding: EdgeInsets.zero,
                  children: [
                    for (final section in DesktopSection.values)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
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
  const _NavItem({
    required this.section,
    required this.selected,
    required this.onTap,
  });

  final DesktopSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: selected
            ? IlaiosTheme.enterpriseCyan.withValues(alpha: .12)
            : Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(6),
          side: BorderSide(
            color: selected
                ? IlaiosTheme.enterpriseCyan.withValues(alpha: .5)
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
                    size: 19,
                    color: selected
                        ? IlaiosTheme.enterpriseCyan
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Text(
                      section.localizedLabel(context),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 12.8,
                        fontWeight:
                            selected ? FontWeight.w700 : FontWeight.w500,
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
  const _TenantSummary({
    required this.projection,
    required this.snapshot,
    required this.userSession,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) {
    final region = _runtimeText(
      snapshot,
      const ['region', 'runtime_region', 'location'],
    );
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(7),
        border: Border.all(
          color: Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            context.tr('shell.tenant'),
            style: const TextStyle(fontSize: 8.8),
          ),
          const SizedBox(height: 3),
          Row(
            children: [
              Expanded(
                child: Text(
                  userSession?.tenantId ?? context.tr('shell.unavailable'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 9.6,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              Icon(
                Icons.circle,
                size: 6,
                color: userSession == null
                    ? Theme.of(context).colorScheme.outline
                    : IlaiosTheme.success,
              ),
            ],
          ),
          const SizedBox(height: 7),
          Divider(
            height: 1,
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          const SizedBox(height: 7),
          Text(
            _isTr(context) ? 'Bölge' : 'Region',
            style: const TextStyle(fontSize: 8.5),
          ),
          const SizedBox(height: 2),
          Text(
            region ?? context.tr('shell.unavailable'),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(
              fontSize: 9.2,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            projection.schemaVersion == null
                ? '—'
                : 'v${projection.schemaVersion}',
            style: const TextStyle(fontSize: 8.4),
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
        key: const Key('reference-desktop-topbar-v5'),
        height: 80,
        padding: const EdgeInsets.symmetric(horizontal: 18),
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
            SizedBox(
              width: 300,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    context.tr('shell.project'),
                    style: const TextStyle(fontSize: 9),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Expanded(
                        child: Material(
                          color: Theme.of(context)
                              .colorScheme
                              .surfaceContainerLowest,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(6),
                            side: BorderSide(
                              color:
                                  Theme.of(context).colorScheme.outlineVariant,
                            ),
                          ),
                          clipBehavior: Clip.antiAlias,
                          child: InkWell(
                            onTap: () => onNavigate(DesktopSection.goals),
                            child: SizedBox(
                              height: 34,
                              child: Padding(
                                padding:
                                    const EdgeInsets.symmetric(horizontal: 10),
                                child: Row(
                                  children: [
                                    Expanded(
                                      child: Text(
                                        _projectLabel(snapshot) ??
                                            context.tr('shell.unavailable'),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontSize: 10.5,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                    const Icon(
                                      Icons.keyboard_arrow_down_rounded,
                                      size: 17,
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 9),
                      Icon(
                        Icons.circle,
                        size: 7,
                        color: projection.connected
                            ? IlaiosTheme.success
                            : Theme.of(context).colorScheme.outline,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        projection.connected
                            ? context.tr('shell.connected')
                            : context.tr('shell.offline'),
                        style: const TextStyle(fontSize: 8.7),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const Spacer(),
            SizedBox(
              width: 240,
              height: 34,
              child: OutlinedButton.icon(
                onPressed: () => onNavigate(DesktopSection.goals),
                icon: const Icon(Icons.search_rounded, size: 17),
                label: Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    context.tr('shell.search'),
                    style: const TextStyle(fontSize: 9.5),
                  ),
                ),
              ),
            ),
            const SizedBox(width: 12),
            IconButton(
              tooltip: context.tr('shell.notifications'),
              onPressed: () => _showNotice(context),
              visualDensity: VisualDensity.compact,
              icon: const Icon(Icons.notifications_none_rounded, size: 19),
            ),
            PopupMenuButton<IlaiosLocale>(
              tooltip: context.tr('shell.language'),
              icon: const Icon(Icons.language_rounded, size: 19),
              onSelected: (locale) =>
                  IlaiosLocaleScope.of(context).onChanged(locale),
              itemBuilder: (context) => [
                for (final locale in IlaiosLocale.values)
                  PopupMenuItem(
                    value: locale,
                    child: Text(locale.displayName),
                  ),
              ],
            ),
            IconButton(
              key: const Key('theme-toggle'),
              tooltip: context.tr('shell.darkTheme'),
              visualDensity: VisualDensity.compact,
              onPressed: () => onThemeModeChanged?.call(
                themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark,
              ),
              icon: Icon(
                themeMode == ThemeMode.dark
                    ? Icons.light_mode_outlined
                    : Icons.dark_mode_outlined,
                size: 19,
              ),
            ),
            const SizedBox(width: 8),
            Container(
              height: 40,
              padding: const EdgeInsets.only(left: 10),
              decoration: BoxDecoration(
                border: Border(
                  left: BorderSide(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
              ),
              child: Row(
                children: [
                  CircleAvatar(
                    radius: 16,
                    backgroundColor:
                        IlaiosTheme.enterpriseCyan.withValues(alpha: .12),
                    child: const Icon(
                      Icons.person_outline_rounded,
                      size: 18,
                      color: IlaiosTheme.enterpriseCyan,
                    ),
                  ),
                  const SizedBox(width: 8),
                  SizedBox(
                    width: 150,
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          userSession?.displayIdentity ??
                              userSession?.principalId ??
                              context.tr('shell.identityUnavailable'),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 9.5,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        Text(
                          userSession == null
                              ? context.tr('shell.signedOut')
                              : context.tr('shell.authenticated'),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 8.2),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.keyboard_arrow_down_rounded, size: 16),
                ],
              ),
            ),
          ],
        ),
      );

  void _showNotice(BuildContext context) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(context.tr('shell.notifications')),
        content: Text(
          _isTr(context)
              ? 'Yetkili bildirim kaydı yok. ILAIOS sentetik bildirim üretmez.'
              : 'No authoritative notification records are available. ILAIOS does not fabricate notifications.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('OK'),
          ),
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
    final queues = _authoritativeCount(
      snapshot.schedulerState,
      const ['queue_count', 'queues'],
    );
    final eventsPerMinute = _runtimeText(
      snapshot,
      const ['events_per_minute', 'event_rate'],
    );

    return Container(
      key: const Key('reference-bottom-status-v2'),
      height: 46,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        border: Border(
          top: BorderSide(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
      ),
      child: Row(
        children: [
          _StatusChip(
            label: context.tr('shell.systemHealth'),
            value: projection.connected
                ? context.tr('shell.healthy')
                : context.tr('shell.offline'),
            live: projection.connected,
          ),
          const SizedBox(width: 10),
          _StatusChip(
            label: context.tr('shell.workers'),
            value: '$leases',
          ),
          const SizedBox(width: 10),
          _StatusChip(
            label: context.tr('shell.queues'),
            value: queues ?? '—',
          ),
          if (eventsPerMinute != null) ...[
            const SizedBox(width: 10),
            _StatusChip(
              label: context.tr('shell.eventsPerMinute'),
              value: eventsPerMinute,
            ),
          ],
          const Spacer(),
          Text(
            '© 2026 ILAIOS',
            style: TextStyle(
              fontSize: 8.7,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const Spacer(),
          Row(
            children: [
              Text(
                context.tr('shell.realTime'),
                style: const TextStyle(fontSize: 9),
              ),
              const SizedBox(width: 6),
              Icon(
                Icons.circle,
                size: 7,
                color: projection.connected
                    ? IlaiosTheme.success
                    : Theme.of(context).colorScheme.outline,
              ),
              const SizedBox(width: 5),
              Text(
                projection.connected
                    ? context.tr('shell.connected')
                    : context.tr('shell.offline'),
                style: const TextStyle(
                  fontSize: 9.2,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  const _StatusChip({
    required this.label,
    required this.value,
    this.live = false,
  });

  final String label;
  final String value;
  final bool live;

  @override
  Widget build(BuildContext context) => Container(
        height: 30,
        padding: const EdgeInsets.symmetric(horizontal: 9),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label, style: const TextStyle(fontSize: 8.5)),
            const SizedBox(width: 7),
            if (live) ...[
              const Icon(
                Icons.circle,
                size: 6,
                color: IlaiosTheme.success,
              ),
              const SizedBox(width: 4),
            ],
            Text(
              value,
              style: const TextStyle(
                fontSize: 8.8,
                fontWeight: FontWeight.w700,
              ),
            ),
          ],
        ),
      );
}

bool _isTr(BuildContext context) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;

String? _projectLabel(OperationalSnapshot snapshot) {
  if (snapshot.liveEvents.isEmpty) return null;
  final event = snapshot.liveEvents.last;
  return _text(
    event,
    const ['project_name', 'project', 'goal', 'objective', 'job_id'],
  );
}

String? _runtimeText(OperationalSnapshot snapshot, List<String> keys) {
  final sources = <Map<String, Object?>>[
    if (snapshot.liveEvents.isNotEmpty) snapshot.liveEvents.last,
    snapshot.schedulerState,
    snapshot.governanceState,
  ];
  for (final source in sources) {
    final value = _text(source, keys);
    if (value != null) return value;
  }
  return null;
}

String? _authoritativeCount(
  Map<String, Object?> source,
  List<String> keys,
) {
  for (final key in keys) {
    final value = source[key];
    if (value is num) return '$value';
    if (value is List<Object?>) return '${value.length}';
    if (value is String && value.trim().isNotEmpty) return value.trim();
  }
  return null;
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

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return value.whereType<Map<String, Object?>>().toList(growable: false);
}
