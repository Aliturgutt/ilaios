import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../create/create_view.dart';
import '../create/reference_asset_picker.dart';
import '../deliveries/deliveries_view.dart';
import '../li/li_view.dart';
import '../navigation/desktop_section.dart';
import '../operations/live_workspace_view.dart';
import '../operations/operational_views.dart';
import '../operations/support_views.dart';
import 'control_center_view.dart';
import 'reference_agents_view.dart';
import 'reference_home_dashboard_v2.dart';

/// Reference-faithful Desktop shell for the approved Home dark/light designs.
///
/// The shell never routes back to the legacy Home when the Windows window is
/// restored or made smaller. Compact desktop windows preserve native text
/// scaling and layout dimensions instead of shrinking the entire UI surface.
/// Runtime values remain authority-derived; the reference screenshots provide
/// layout/theme guidance only.
class ReferenceDesktopShellV10 extends StatefulWidget {
  const ReferenceDesktopShellV10({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.themeMode = ThemeMode.dark,
    this.referenceAssets,
    this.onThemeModeChanged,
    this.onSignIn,
    this.onLogout,
    this.onPromptSubmit,
    this.onSaveArtifact,
    this.onFetchLiState,
    this.onFetchLiMemories,
    this.onRememberLiMemory,
    this.onRefreshRequested,
    this.onProvisionAgent,
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
  final ReferenceAssetPickerController? referenceAssets;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final Future<DesktopLiState> Function()? onFetchLiState;
  final Future<List<DesktopLiMemory>> Function()? onFetchLiMemories;
  final Future<DesktopLiMemory> Function(String kind, String content)?
      onRememberLiMemory;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String agentId)? onProvisionAgent;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  @override
  State<ReferenceDesktopShellV10> createState() =>
      _ReferenceDesktopShellV10State();
}

class _ReferenceDesktopShellV10State extends State<ReferenceDesktopShellV10> {
  DesktopSection _section = DesktopSection.home;
  bool _liSelected = false;

  @override
  void didUpdateWidget(covariant ReferenceDesktopShellV10 oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (_liSelected && widget.userSession?.liFounder != true) {
      _liSelected = false;
      _section = DesktopSection.home;
    }
  }

  void _select(DesktopSection section) {
    if (_section != section || _liSelected) {
      setState(() {
        _section = section;
        _liSelected = false;
      });
    }
  }

  void _selectLi() {
    if (!_liSelected) setState(() => _liSelected = true);
  }

  @override
  Widget build(BuildContext context) {
    Widget canvas(double width, double height) => SizedBox(
          width: width,
          height: height,
          child: Scaffold(
            body: Row(
              children: [
                _Sidebar(
                  selected: _section,
                  liSelected: _liSelected,
                  projection: widget.projection,
                  snapshot: widget.operationalSnapshot,
                  userSession: widget.userSession,
                  onSelected: _select,
                  onLiSelected: _selectLi,
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
                        onLogout: widget.onLogout,
                        onNavigate: _select,
                      ),
                      Expanded(child: _buildSection()),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );

    return LayoutBuilder(
      builder: (context, constraints) => SizedBox.expand(
        key: const Key('reference-responsive-viewport-v10'),
        child: canvas(constraints.maxWidth, constraints.maxHeight),
      ),
    );
  }

  Widget _buildSection() {
    if (_liSelected) {
      return LiView(
        userSession: widget.userSession,
        onFetchState: widget.onFetchLiState,
        onFetchMemories: widget.onFetchLiMemories,
        onRemember: widget.onRememberLiMemory,
      );
    }
    return switch (_section) {
      DesktopSection.home => ReferenceHomeDashboardV2(
          projection: widget.projection,
          snapshot: widget.operationalSnapshot,
          status: widget.operationalStatus,
          userSession: widget.userSession,
          onPromptSubmit: widget.onPromptSubmit,
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
          referenceAssets: widget.referenceAssets,
          onSubmit: widget.onPromptSubmit,
        ),
      DesktopSection.workflows => ControlCenterView(
          projection: widget.projection,
          operationalSnapshot: widget.operationalSnapshot,
          operationalStatus: widget.operationalStatus,
          onRefreshRequested: widget.onRefreshRequested,
          onNavigate: _select,
        ),
      DesktopSection.agents => ReferenceAgentsView(
          projection: widget.projection,
          snapshot: widget.operationalSnapshot,
          status: widget.operationalStatus,
          onNavigate: _select,
          onRefreshRequested: widget.onRefreshRequested,
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

class _Sidebar extends StatelessWidget {
  const _Sidebar({
    required this.selected,
    required this.liSelected,
    required this.projection,
    required this.snapshot,
    required this.userSession,
    required this.onSelected,
    required this.onLiSelected,
  });

  static const _darkLogo = '../../brand/assets/05-ilaios-app-icon.jpg';
  static const _lightLogo = '../../brand/assets/13-ilaios-primary-horizontal-light.jpg';
  static const _primarySections = <DesktopSection>[
    DesktopSection.home,
    DesktopSection.workflows,
    DesktopSection.agents,
    DesktopSection.artifacts,
    DesktopSection.approvals,
    DesktopSection.evidence,
    DesktopSection.settings,
  ];

  final DesktopSection selected;
  final bool liSelected;
  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onSelected;
  final VoidCallback onLiSelected;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Semantics(
      container: true,
      label: context.tr('shell.primaryNavigation'),
      child: Container(
        key: const Key('reference-desktop-sidebar-v5'),
        width: 222,
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Semantics(
              label: 'ILAIOS canonical brand lockup',
              image: true,
              child: SizedBox(
                key: const Key('reference-brand-lockup-v9'),
                height: 76,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: Image.asset(
                    isDark ? _darkLogo : _lightLogo,
                    key: Key(isDark
                        ? 'reference-brand-horizontal-dark'
                        : 'reference-brand-horizontal-light'),
                    width: isDark ? 64 : 184,
                    height: isDark ? 64 : 50,
                    fit: BoxFit.contain,
                    alignment: Alignment.centerLeft,
                    filterQuality: FilterQuality.high,
                    gaplessPlayback: true,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children: [
                  for (final section in _primarySections)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: _NavItem(
                        section: section,
                        selected: !liSelected && selected == section,
                        onTap: () => onSelected(section),
                      ),
                    ),
                  if (userSession?.liFounder == true)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: _LiNavItem(
                        selected: liSelected,
                        onTap: onLiSelected,
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            _BottomStatusBar(
              projection: projection,
              snapshot: snapshot,
            ),
          ],
        ),
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
  Widget build(BuildContext context) => Material(
        color: selected
            ? Theme.of(context).colorScheme.surfaceContainerHighest
            : Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(5),
          side: BorderSide(
            color: selected
                ? Theme.of(context).colorScheme.outline
                : Colors.transparent,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          key: ValueKey('nav-${section.name}'),
          onTap: onTap,
          child: SizedBox(
            height: 44,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  Icon(
                    section.icon,
                    size: 18,
                    color: selected
                        ? Theme.of(context).colorScheme.onSurface
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Text(
                      section.localizedLabel(context),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                        color: Theme.of(context).colorScheme.onSurface,
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

class _LiNavItem extends StatelessWidget {
  const _LiNavItem({required this.selected, required this.onTap});

  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: selected
            ? Theme.of(context).colorScheme.surfaceContainerHighest
            : Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(5),
          side: BorderSide(
            color: selected
                ? Theme.of(context).colorScheme.outline
                : Colors.transparent,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          key: const ValueKey('nav-li'),
          onTap: onTap,
          child: SizedBox(
            height: 44,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Row(
                children: [
                  Icon(
                    Icons.auto_awesome_outlined,
                    size: 18,
                    color: selected
                        ? Theme.of(context).colorScheme.onSurface
                        : Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: 11),
                  Expanded(
                    child: Text(
                      context.tr('nav.li'),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: selected ? FontWeight.w600 : FontWeight.w500,
                        color: Theme.of(context).colorScheme.onSurface,
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

class _TopBar extends StatelessWidget {
  const _TopBar({
    required this.projection,
    required this.snapshot,
    required this.userSession,
    required this.themeMode,
    required this.onThemeModeChanged,
    required this.onLogout,
    required this.onNavigate,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function()? onLogout;
  final ValueChanged<DesktopSection> onNavigate;

  static const _secondarySections = <DesktopSection>[
    DesktopSection.goals,
    DesktopSection.liveWorkspace,
    DesktopSection.costs,
  ];

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-desktop-topbar-v5'),
        constraints: const BoxConstraints(minHeight: 72),
        padding: const EdgeInsets.symmetric(horizontal: 18),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          border: Border(
            bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
          ),
        ),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 760;
            final showSearch = constraints.maxWidth >= 930;
            final projectWidth = compact ? 190.0 : 230.0;

            return Row(
              children: [
                SizedBox(
                  width: projectWidth,
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        context.tr('shell.project'),
                        style: const TextStyle(fontSize: 12.5),
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Expanded(
                            child: Material(
                              color: Theme.of(context).colorScheme.surfaceContainerLowest,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(5),
                                side: BorderSide(
                                  color: Theme.of(context).colorScheme.outlineVariant,
                                ),
                              ),
                              clipBehavior: Clip.antiAlias,
                              child: InkWell(
                                onTap: () => onNavigate(DesktopSection.goals),
                                child: SizedBox(
                                  height: 36,
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(horizontal: 10),
                                    child: Row(
                                      children: [
                                        Expanded(
                                          child: Text(
                                            _projectLabel(snapshot) ??
                                                context.tr('shell.unavailable'),
                                            maxLines: 1,
                                            overflow: TextOverflow.ellipsis,
                                            style: const TextStyle(
                                              fontSize: 13.5,
                                              fontWeight: FontWeight.w600,
                                            ),
                                          ),
                                        ),
                                        const Icon(
                                          Icons.chevron_right_rounded,
                                          size: 16,
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
                            size: 6,
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 4),
                          if (!compact)
                            Text(
                              projection.connected
                                  ? context.tr('shell.connected')
                                  : context.tr('shell.offline'),
                              style: const TextStyle(fontSize: 12.5),
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
                const Spacer(),
                if (showSearch) ...[
                  SizedBox(
                    width: 180,
                    height: 38,
                    child: OutlinedButton.icon(
                      onPressed: () => onNavigate(DesktopSection.goals),
                      icon: const Icon(Icons.search_rounded, size: 17),
                      label: Align(
                        alignment: Alignment.centerLeft,
                        child: Text(
                          context.tr('shell.search'),
                          style: const TextStyle(fontSize: 13.5),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                ],
                PopupMenuButton<DesktopSection>(
                  key: const Key('reference-secondary-navigation'),
                  tooltip: _isTr(context) ? 'Diğer bölümler' : 'More sections',
                  onSelected: onNavigate,
                  icon: const Icon(Icons.more_horiz_rounded, size: 20),
                  itemBuilder: (context) => [
                    for (final section in _secondarySections)
                      PopupMenuItem<DesktopSection>(
                        value: section,
                        child: Row(
                          children: [
                            Icon(section.icon, size: 17),
                            const SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                section.localizedLabel(context),
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
                IconButton(
                  tooltip: context.tr('shell.notifications'),
                  onPressed: () => _showNotice(context),
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.notifications_none_rounded, size: 18),
                ),
                PopupMenuButton<IlaiosLocale>(
                  tooltip: context.tr('shell.language'),
                  icon: const Icon(Icons.language_rounded, size: 18),
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
                    themeMode == ThemeMode.dark
                        ? ThemeMode.light
                        : ThemeMode.dark,
                  ),
                  icon: Icon(
                    themeMode == ThemeMode.dark
                        ? Icons.light_mode_outlined
                        : Icons.dark_mode_outlined,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 8),
                _AccountControl(
                  userSession: userSession,
                  onLogout: onLogout,
                  compact: compact,
                ),
              ],
            );
          },
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

class _AccountControl extends StatelessWidget {
  const _AccountControl({
    required this.userSession,
    required this.onLogout,
    this.compact = false,
  });

  final DesktopUserSession? userSession;
  final Future<void> Function()? onLogout;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final identity = userSession?.displayIdentity ??
        userSession?.principalId ??
        context.tr('shell.identityUnavailable');
    final content = Container(
      constraints: const BoxConstraints(minHeight: 42),
      padding: const EdgeInsets.only(left: 10),
      decoration: BoxDecoration(
        border: Border(
          left: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          CircleAvatar(
            radius: 14,
            backgroundColor: Theme.of(context).colorScheme.surfaceContainerHighest,
            child: Icon(
              Icons.person_outline_rounded,
              size: 17,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          if (!compact) ...[
            const SizedBox(width: 7),
            SizedBox(
              width: 150,
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    identity,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  Text(
                    userSession == null
                        ? context.tr('shell.signedOut')
                        : context.tr('shell.authenticated'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12.5),
                  ),
                ],
              ),
            ),
          ],
          if (userSession != null && onLogout != null)
            const Icon(Icons.keyboard_arrow_down_rounded, size: 15),
        ],
      ),
    );

    final labeledContent = compact ? Tooltip(message: identity, child: content) : content;

    if (userSession == null || onLogout == null) return labeledContent;
    return PopupMenuButton<String>(
      tooltip: _isTr(context) ? 'Hesap' : 'Account',
      onSelected: (value) {
        if (value == 'signout') onLogout?.call();
      },
      itemBuilder: (context) => [
        PopupMenuItem<String>(
          enabled: false,
          value: 'identity',
          child: Text(identity, overflow: TextOverflow.ellipsis),
        ),
        PopupMenuItem<String>(
          value: 'signout',
          child: Row(
            children: [
              const Icon(Icons.logout_rounded, size: 17),
              const SizedBox(width: 8),
              Text(_isTr(context) ? 'Çıkış yap' : 'Sign out'),
            ],
          ),
        ),
      ],
      child: labeledContent,
    );
  }
}

class _BottomStatusBar extends StatelessWidget {
  const _BottomStatusBar({required this.projection, required this.snapshot});

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    return Container(
      key: const Key('reference-bottom-status-v2'),
      constraints: const BoxConstraints(minHeight: 68),
      padding: const EdgeInsets.fromLTRB(10, 9, 10, 8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(6),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          _FlatStatus(
            label: context.tr('shell.systemHealth'),
            value: projection.connected
                ? context.tr('shell.healthy')
                : context.tr('shell.offline'),
            live: projection.connected,
          ),
          const SizedBox(height: 6),
          Text(
            '© 2026 ILAIOS',
            style: TextStyle(
              fontSize: 12.5,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _FlatStatus extends StatelessWidget {
  const _FlatStatus({
    required this.label,
    required this.value,
    this.live = false,
  });

  final String label;
  final String value;
  final bool live;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 12.5,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.circle,
                size: 6,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 6),
              Flexible(
                child: Text(
                  value,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600),
                ),
              ),
            ],
          ),
        ],
      );
}

bool _isTr(BuildContext context) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;

String? _projectLabel(OperationalSnapshot snapshot) {
  if (snapshot.liveEvents.isEmpty) return null;
  return _text(
    snapshot.liveEvents.last,
    const ['project_name', 'project', 'workspace', 'goal', 'objective'],
  );
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
