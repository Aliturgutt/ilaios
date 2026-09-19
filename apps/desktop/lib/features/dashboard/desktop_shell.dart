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
import 'home_dashboard_v2.dart';

class DesktopShell extends StatefulWidget {
  const DesktopShell({
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
  State<DesktopShell> createState() => _DesktopShellState();
}

class _DesktopShellState extends State<DesktopShell> {
  DesktopSection _section = DesktopSection.home;

  void _selectSection(DesktopSection section) {
    if (_section != section) setState(() => _section = section);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        body: LayoutBuilder(
          builder: (context, constraints) {
            final compact = constraints.maxWidth < 900;
            final content = Column(
              children: [
                compact
                    ? _CompactTopBar(
                        projection: widget.projection,
                        section: _section,
                        onSectionSelected: _selectSection,
                        themeMode: widget.themeMode,
                        onThemeModeChanged: widget.onThemeModeChanged,
                      )
                    : _TopBar(
                        projection: widget.projection,
                        snapshot: widget.operationalSnapshot,
                        userSession: widget.userSession,
                        themeMode: widget.themeMode,
                        onThemeModeChanged: widget.onThemeModeChanged,
                        onNavigate: _selectSection,
                      ),
                Expanded(child: _buildSection()),
                _BottomStatusBar(
                  projection: widget.projection,
                  snapshot: widget.operationalSnapshot,
                  onNavigate: _selectSection,
                ),
              ],
            );
            if (compact) return content;
            return Row(
              children: [
                _NavigationRail(
                  selected: _section,
                  userSession: widget.userSession,
                  onSelected: _selectSection,
                ),
                VerticalDivider(
                  width: 1,
                  thickness: 1,
                  color: Theme.of(context).colorScheme.outlineVariant,
                ),
                Expanded(child: content),
              ],
            );
          },
        ),
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
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Semantics(
      container: true,
      label: context.tr('shell.primaryNavigation'),
      child: Material(
        color: scheme.surfaceContainerLow,
        child: SizedBox(
          width: 258,
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const _BrandHeader(),
                const SizedBox(height: 12),
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
}

class _BrandHeader extends StatelessWidget {
  const _BrandHeader();

  static const _wordmark =
      '../../brand/assets/05-ilaios-app-icon.jpg';

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'ILAIOS',
        image: true,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(2, 0, 2, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                width: 186,
                height: 42,
                child: Image.asset(
                  _wordmark,
                  fit: BoxFit.contain,
                  alignment: Alignment.centerLeft,
                  filterQuality: FilterQuality.high,
                  excludeFromSemantics: true,
                ),
              ),
              const SizedBox(height: 5),
              Text(
                'Integrated Learning, Autonomous\nIntelligence & Orchestration Systems',
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 7.25,
                  height: 1.3,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                  letterSpacing: .12,
                ),
              ),
              const SizedBox(height: 9),
              ClipRRect(
                borderRadius: BorderRadius.circular(10),
                child: const SizedBox(
                  width: 186,
                  height: 3,
                  child: Row(
                    children: [
                      Expanded(
                        flex: 5,
                        child: ColoredBox(color: IlaiosTheme.enterpriseCyan),
                      ),
                      Expanded(
                        flex: 3,
                        child: ColoredBox(color: IlaiosTheme.coreBlue),
                      ),
                      Expanded(
                        flex: 2,
                        child: ColoredBox(color: IlaiosTheme.violet),
                      ),
                    ],
                  ),
                ),
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

  Color _accent() => switch (section) {
        DesktopSection.home || DesktopSection.goals =>
          IlaiosTheme.enterpriseCyan,
        DesktopSection.workflows || DesktopSection.liveWorkspace =>
          IlaiosTheme.coreBlue,
        DesktopSection.agents || DesktopSection.approvals => IlaiosTheme.violet,
        DesktopSection.artifacts || DesktopSection.evidence =>
          IlaiosTheme.enterpriseCyan,
        DesktopSection.costs || DesktopSection.settings => IlaiosTheme.coreBlue,
      };

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final accent = _accent();
    return Padding(
      padding: const EdgeInsets.only(bottom: 5),
      child: Material(
        color: selected ? accent.withValues(alpha: .13) : Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: selected
              ? BorderSide(color: accent.withValues(alpha: .72))
              : const BorderSide(color: Colors.transparent),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          key: ValueKey('nav-${section.name}'),
          onTap: onTap,
          overlayColor: WidgetStatePropertyAll(accent.withValues(alpha: .10)),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
            child: Row(
              children: [
                Container(
                  width: 31,
                  height: 31,
                  decoration: BoxDecoration(
                    color: selected
                        ? accent.withValues(alpha: .16)
                        : scheme.surfaceContainerHighest,
                    borderRadius: BorderRadius.circular(9),
                  ),
                  child: Icon(
                    section.icon,
                    size: 19,
                    color: selected ? accent : scheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    section.localizedLabel(context),
                    style: TextStyle(
                      color: scheme.onSurface,
                      fontSize: 12.5,
                      fontWeight: selected ? FontWeight.w800 : FontWeight.w500,
                    ),
                  ),
                ),
                if (selected)
                  Icon(Icons.chevron_right, size: 17, color: accent),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TenantSummary extends StatelessWidget {
  const _TenantSummary({required this.userSession});

  final DesktopUserSession? userSession;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final tenant = userSession?.tenantId;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(11),
        border: Border.all(
          color: tenant == null
              ? scheme.outlineVariant
              : IlaiosTheme.violet.withValues(alpha: .42),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            context.tr('shell.tenant'),
            style: Theme.of(context).textTheme.labelSmall?.copyWith(
                  color: tenant == null ? null : IlaiosTheme.violet,
                ),
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              Expanded(
                child: Text(
                  tenant ?? context.tr('shell.unavailable'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelMedium,
                ),
              ),
              if (tenant != null)
                const Icon(Icons.circle, size: 7, color: IlaiosTheme.success),
            ],
          ),
          const SizedBox(height: 7),
          Text(
            context.tr('shell.regionPlan'),
            style: Theme.of(context).textTheme.bodySmall,
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
    required this.themeMode,
    required this.onThemeModeChanged,
  });

  final ControlPlaneProjection projection;
  final DesktopSection section;
  final ValueChanged<DesktopSection> onSectionSelected;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;

  @override
  Widget build(BuildContext context) => Container(
        height: 64,
        padding: const EdgeInsets.symmetric(horizontal: 14),
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
            PopupMenuButton<DesktopSection>(
              tooltip: context.tr('shell.navigate'),
              onSelected: onSectionSelected,
              itemBuilder: (context) => [
                for (final item in DesktopSection.values)
                  PopupMenuItem(
                    value: item,
                    child: Row(
                      children: [
                        Icon(item.icon, size: 18),
                        const SizedBox(width: 10),
                        Text(item.localizedLabel(context)),
                      ],
                    ),
                  ),
              ],
              child: Row(
                children: [
                  const _BrandMark(size: 34),
                  const SizedBox(width: 9),
                  Text(
                    section.localizedLabel(context),
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(width: 4),
                  const Icon(
                    Icons.expand_more,
                    size: 17,
                    color: IlaiosTheme.enterpriseCyan,
                  ),
                ],
              ),
            ),
            const Spacer(),
            const _LanguageMenu(compact: true),
            const SizedBox(width: 7),
            _ThemeButton(
              compact: true,
              themeMode: themeMode,
              onChanged: onThemeModeChanged,
            ),
            const SizedBox(width: 7),
            _ConnectionPill(projection: projection, compact: true),
          ],
        ),
      );
}

class _BrandMark extends StatelessWidget {
  const _BrandMark({this.size = 36});

  final double size;
  static const _asset = '../../brand/assets/05-ilaios-app-icon.jpg';

  @override
  Widget build(BuildContext context) => Semantics(
        label: 'ILAIOS',
        image: true,
        child: ClipRRect(
          borderRadius: BorderRadius.circular(9),
          child: Image.asset(
            _asset,
            width: size,
            height: size,
            fit: BoxFit.contain,
            filterQuality: FilterQuality.high,
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
    required this.onNavigate,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final DesktopUserSession? userSession;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) => Container(
          height: 78,
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
              _ProjectSelector(
                project: _projectLabel(snapshot),
                onTap: () => onNavigate(DesktopSection.goals),
              ),
              const Spacer(),
              if (constraints.maxWidth >= 1180) ...[
                _SearchButton(onNavigate: onNavigate),
                const SizedBox(width: 12),
              ],
              _TopActionButton(
                icon: Icons.notifications_none_rounded,
                tooltip: context.tr('shell.notifications'),
                accent: IlaiosTheme.coreBlue,
                onPressed: () => _showNotifications(context),
              ),
              const SizedBox(width: 9),
              const _LanguageMenu(),
              const SizedBox(width: 9),
              _ThemeButton(
                themeMode: themeMode,
                onChanged: onThemeModeChanged,
              ),
              const SizedBox(width: 12),
              if (constraints.maxWidth >= 1080) ...[
                _ProfileSummary(
                  userSession: userSession,
                  onTap: () => onNavigate(DesktopSection.settings),
                ),
                const SizedBox(width: 11),
              ],
              _ConnectionPill(
                projection: projection,
                onTap: () => onNavigate(DesktopSection.workflows),
              ),
            ],
          ),
        ),
      );
}

class _ProjectSelector extends StatelessWidget {
  const _ProjectSelector({required this.project, required this.onTap});

  final String? project;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 220,
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              context.tr('shell.project'),
              style: Theme.of(context).textTheme.labelSmall,
            ),
            const SizedBox(height: 4),
            Material(
              color: project == null
                  ? Theme.of(context).colorScheme.surfaceContainerLowest
                  : IlaiosTheme.coreBlue.withValues(alpha: .08),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(9),
                side: BorderSide(
                  color: project == null
                      ? Theme.of(context).colorScheme.outlineVariant
                      : IlaiosTheme.coreBlue.withValues(alpha: .52),
                ),
              ),
              clipBehavior: Clip.antiAlias,
              child: InkWell(
                onTap: onTap,
                child: SizedBox(
                  height: 38,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 11),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            project ?? context.tr('shell.unavailable'),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: Theme.of(context).textTheme.labelMedium,
                          ),
                        ),
                        const Icon(Icons.expand_more_rounded, size: 17),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      );
}

class _SearchButton extends StatelessWidget {
  const _SearchButton({required this.onNavigate});

  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => SizedBox(
        width: 260,
        child: OutlinedButton(
          onPressed: () => _showCommandPalette(context, onNavigate),
          style: OutlinedButton.styleFrom(
            foregroundColor: Theme.of(context).colorScheme.onSurfaceVariant,
            side: BorderSide(
              color: IlaiosTheme.coreBlue.withValues(alpha: .55),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          ),
          child: Row(
            children: [
              const Icon(
                Icons.search,
                color: IlaiosTheme.enterpriseCyan,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  context.tr('shell.search'),
                  textAlign: TextAlign.left,
                ),
              ),
              Text(
                '⌘K',
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: IlaiosTheme.coreBlue,
                    ),
              ),
            ],
          ),
        ),
      );
}

class _TopActionButton extends StatelessWidget {
  const _TopActionButton({
    required this.icon,
    required this.tooltip,
    required this.accent,
    required this.onPressed,
  });

  final IconData icon;
  final String tooltip;
  final Color accent;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => IconButton(
        tooltip: tooltip,
        onPressed: onPressed,
        style: IconButton.styleFrom(
          backgroundColor: accent.withValues(alpha: .10),
          side: BorderSide(color: accent.withValues(alpha: .30)),
        ),
        icon: Icon(icon, color: accent, size: 20),
      );
}

class _LanguageMenu extends StatelessWidget {
  const _LanguageMenu({this.compact = false});

  final bool compact;

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
      child: Container(
        width: compact ? 36 : 42,
        height: compact ? 36 : 42,
        decoration: BoxDecoration(
          color: IlaiosTheme.enterpriseCyan.withValues(alpha: .11),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: IlaiosTheme.enterpriseCyan.withValues(alpha: .34),
          ),
        ),
        child: const Icon(
          Icons.language,
          color: IlaiosTheme.enterpriseCyan,
          size: 20,
        ),
      ),
    );
  }
}

class _ThemeButton extends StatelessWidget {
  const _ThemeButton({
    required this.themeMode,
    required this.onChanged,
    this.compact = false,
  });

  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onChanged;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    final light = Theme.of(context).brightness == Brightness.light;
    final tooltip = light
        ? (_isTr(context) ? 'Koyu temaya geç' : 'Switch to dark theme')
        : (_isTr(context) ? 'Açık temaya geç' : 'Switch to light theme');
    return IconButton(
      key: const Key('theme-toggle'),
      tooltip: tooltip,
      onPressed: onChanged == null
          ? null
          : () => onChanged!(light ? ThemeMode.dark : ThemeMode.light),
      style: IconButton.styleFrom(
        fixedSize: Size.square(compact ? 36 : 42),
        backgroundColor: IlaiosTheme.violet.withValues(alpha: .10),
        side: BorderSide(color: IlaiosTheme.violet.withValues(alpha: .32)),
      ),
      icon: Icon(
        light ? Icons.dark_mode_outlined : Icons.light_mode_outlined,
        color: IlaiosTheme.violet,
        size: 20,
      ),
    );
  }
}

class _ProfileSummary extends StatelessWidget {
  const _ProfileSummary({required this.userSession, required this.onTap});

  final DesktopUserSession? userSession;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final identity =
        userSession?.displayIdentity ?? context.tr('shell.signedOut');
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: IlaiosTheme.coreBlue.withValues(alpha: .14),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.person,
                color: IlaiosTheme.enterpriseCyan,
                size: 20,
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 135,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    identity,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelMedium,
                  ),
                  Text(
                    userSession == null
                        ? context.tr('shell.signedOut')
                        : context.tr('shell.authenticated'),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.labelSmall?.copyWith(
                          color: IlaiosTheme.coreBlue,
                        ),
                  ),
                ],
              ),
            ),
            const Icon(Icons.expand_more, size: 15),
          ],
        ),
      ),
    );
  }
}

class _ConnectionPill extends StatelessWidget {
  const _ConnectionPill({
    required this.projection,
    this.compact = false,
    this.onTap,
  });

  final ControlPlaneProjection projection;
  final bool compact;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final connected = projection.connected;
    final accent = connected
        ? IlaiosTheme.enterpriseCyan
        : Theme.of(context).colorScheme.outline;
    return Material(
      color: accent.withValues(alpha: .10),
      shape: StadiumBorder(
        side: BorderSide(color: accent.withValues(alpha: .66)),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.symmetric(
            horizontal: compact ? 9 : 12,
            vertical: compact ? 7 : 9,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.circle,
                size: 7,
                color: connected ? IlaiosTheme.success : accent,
              ),
              if (!compact) ...[
                const SizedBox(width: 7),
                Text(
                  connected
                      ? context.tr('shell.connected')
                      : context.tr('shell.offline'),
                  style: TextStyle(
                    color: connected ? accent : null,
                    fontWeight: FontWeight.w800,
                    fontSize: 10.5,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

class _BottomStatusBar extends StatelessWidget {
  const _BottomStatusBar({
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
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      height: 30,
      padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(
        color: scheme.surfaceContainerLow,
        border: Border(top: BorderSide(color: scheme.outlineVariant)),
      ),
      child: Row(
        children: [
          _StatusLink(
            label: context.tr('shell.systemHealth'),
            value: projection.connected
                ? context.tr('shell.healthy')
                : context.tr('shell.offline'),
            accent: projection.connected
                ? IlaiosTheme.success
                : scheme.outline,
            onTap: () => onNavigate(DesktopSection.workflows),
          ),
          const SizedBox(width: 18),
          _StatusLink(
            label: context.tr('shell.workers'),
            value: '${_listLength(snapshot.schedulerState, 'leases')}',
            accent: IlaiosTheme.violet,
            onTap: () => onNavigate(DesktopSection.agents),
          ),
          const SizedBox(width: 18),
          _StatusLink(
            label: context.tr('shell.eventsPerMinute'),
            value: '${snapshot.liveEventCount}',
            accent: IlaiosTheme.coreBlue,
            onTap: () => onNavigate(DesktopSection.liveWorkspace),
          ),
          const Spacer(),
          Icon(
            Icons.circle,
            size: 6,
            color: projection.connected
                ? IlaiosTheme.enterpriseCyan
                : scheme.outline,
          ),
          const SizedBox(width: 6),
          Text(
            context.tr('shell.realTime'),
            style: Theme.of(context).textTheme.labelSmall,
          ),
        ],
      ),
    );
  }
}

class _StatusLink extends StatelessWidget {
  const _StatusLink({
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
        borderRadius: BorderRadius.circular(6),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 3),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(label, style: Theme.of(context).textTheme.labelSmall),
              const SizedBox(width: 6),
              Text(
                value,
                style: Theme.of(context).textTheme.labelSmall?.copyWith(
                      color: accent,
                      fontWeight: FontWeight.w800,
                    ),
              ),
            ],
          ),
        ),
      );
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
            width: 460,
            height: 420,
            child: Column(
              children: [
                TextField(
                  autofocus: true,
                  controller: controller,
                  onChanged: (_) => setState(() {}),
                  decoration: InputDecoration(
                    prefixIcon: const Icon(
                      Icons.search,
                      color: IlaiosTheme.enterpriseCyan,
                    ),
                    hintText: _isTr(context)
                        ? 'Sayfa veya özellik ara'
                        : 'Search pages or features',
                  ),
                ),
                const SizedBox(height: 12),
                Expanded(
                  child: ListView(
                    children: [
                      for (final section in items)
                        ListTile(
                          leading: Icon(
                            section.icon,
                            color: IlaiosTheme.coreBlue,
                          ),
                          title: Text(section.localizedLabel(context)),
                          trailing: const Icon(Icons.arrow_forward, size: 16),
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

Future<void> _showNotifications(BuildContext context) => showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: const Icon(
          Icons.notifications_none,
          color: IlaiosTheme.coreBlue,
        ),
        title: Text(_isTr(context) ? 'Bildirimler' : 'Notifications'),
        content: Text(
          _isTr(context)
              ? 'Yetkili çalışma zamanı tarafından sunulmuş bir bildirim kaydı yok. Sentetik bildirim oluşturulmaz.'
              : 'No notification records are exposed by the authoritative runtime. Synthetic notifications are not fabricated.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_isTr(context) ? 'Kapat' : 'Close'),
          ),
        ],
      ),
    );

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

bool _isTr(BuildContext context) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish;
