import 'dart:io';

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/desktop_identity_action_scope.dart';
import '../../identity/identity_client.dart';
import '../../presentation/desktop_runtime_status.dart';
import '../create/governed_lifecycle_projection.dart';
import '../create/reference_asset_picker.dart';
import '../deliveries/deliveries_view.dart';
import '../deliveries/delivery_identity_scope.dart';
import '../navigation/desktop_section.dart';
import '../operations/operational_views.dart';
import '../operations/support_views.dart';
import 'agent_provisioning_scope.dart';
import 'home_runtime_binding.dart';
import 'reference_agents_summary_view.dart';
import 'reference_home_dashboard_v3.dart';
import 'reference_workflows_view.dart';

/// Active canonical Desktop shell for the 7-page migration.
///
/// Visual geometry follows the user-approved 1536x1024 reference set. Runtime,
/// identity, governance and provider callbacks remain the existing authorities.
/// Superseded 10-screen visual constants are intentionally not consulted here.
class ReferenceDesktopShellV11 extends StatefulWidget {
  const ReferenceDesktopShellV11({
    required this.projection,
    required this.operationalSnapshot,
    required this.operationalStatus,
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.themeMode = ThemeMode.light,
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
  State<ReferenceDesktopShellV11> createState() =>
      _ReferenceDesktopShellV11State();
}

class _ReferenceDesktopShellV11State extends State<ReferenceDesktopShellV11> {
  static const _canonicalSections = <DesktopSection>[
    DesktopSection.home,
    DesktopSection.workflows,
    DesktopSection.agents,
    DesktopSection.artifacts,
    DesktopSection.approvals,
    DesktopSection.evidence,
    DesktopSection.settings,
  ];

  DesktopSection _section = DesktopSection.home;

  bool _isCanonical(DesktopSection section) =>
      _canonicalSections.contains(section);

  void _select(DesktopSection section) {
    if (!_isCanonical(section) || _section == section) return;
    setState(() => _section = section);
  }

  Widget _buildSection(String presentedStatus) => switch (_section) {
        DesktopSection.home => ReferenceHomeDashboardV3(
            projection: widget.projection,
            snapshot: widget.operationalSnapshot,
            status: presentedStatus,
            userSession: widget.userSession,
            onPromptSubmit: widget.onPromptSubmit,
            onNavigate: _select,
            onRefreshRequested: widget.onRefreshRequested,
          ),
        DesktopSection.workflows => ReferenceWorkflowsView(
            projection: widget.projection,
            snapshot: widget.operationalSnapshot,
            status: presentedStatus,
            onRefreshRequested: widget.onRefreshRequested,
            onNavigate: _select,
          ),
        DesktopSection.agents => ReferenceAgentsSummaryView(
            projection: widget.projection,
            snapshot: widget.operationalSnapshot,
            status: presentedStatus,
            onNavigate: _select,
            onRefreshRequested: widget.onRefreshRequested,
          ),
        DesktopSection.artifacts => DeliveriesView(
            snapshot: widget.operationalSnapshot,
            status: presentedStatus,
            onSaveArtifact: widget.onSaveArtifact,
          ),
        DesktopSection.approvals => GovernanceView(
            snapshot: widget.operationalSnapshot,
            status: presentedStatus,
            approverId: widget.approverId,
            onDecision: widget.onGovernanceDecision,
          ),
        DesktopSection.evidence => EvidenceView(
            snapshot: widget.operationalSnapshot,
            status: presentedStatus,
            onSaveArtifact: widget.onSaveArtifact,
          ),
        DesktopSection.settings => SettingsView(
            projection: widget.projection,
            identityStatus: widget.identityStatus,
            userSession: widget.userSession,
            providers: widget.identityProviders,
          ),
        _ => const SizedBox.shrink(),
      };

  Widget _scopedShell(BuildContext context) {
    final locale = IlaiosLocaleScope.of(context).locale;
    final presentedStatus = presentDesktopRuntimeStatus(
      widget.operationalStatus,
      connected: widget.projection.connected,
      turkish: locale == IlaiosLocale.turkish,
    );

    return ReferenceAssetPickerScope(
      controller: widget.referenceAssets,
      child: DesktopIdentityActionScope(
        onSignIn: widget.onSignIn,
        onLogout: widget.onLogout,
        child: DeliveryIdentityScope(
          session: widget.userSession,
          child: AgentProvisioningScope(
            onProvisionAgent: widget.onProvisionAgent,
            child: HomeRuntimeBinding(
              userSession: widget.userSession,
              onPromptSubmit: widget.onPromptSubmit,
              child: Scaffold(
                backgroundColor: Theme.of(context).scaffoldBackgroundColor,
                body: Row(
                  children: [
                    _CanonicalSidebar(
                      selected: _section,
                      projection: widget.projection,
                      snapshot: widget.operationalSnapshot,
                      onSelected: _select,
                    ),
                    Container(
                      width: 1,
                      color: Theme.of(context).colorScheme.outlineVariant,
                    ),
                    Expanded(
                      child: Column(
                        children: [
                          _CanonicalTopBar(
                            identityProviders: widget.identityProviders,
                            userSession: widget.userSession,
                            themeMode: widget.themeMode,
                            onThemeModeChanged: widget.onThemeModeChanged,
                            onSignIn: widget.onSignIn,
                            onLogout: widget.onLogout,
                          ),
                          Expanded(
                            child: _buildSection(presentedStatus.label),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (widget.userSession == null) {
      GovernedLifecycleProjectionStore.clear();
    } else {
      GovernedLifecycleProjectionStore.replace(widget.operationalSnapshot);
    }

    return SizedBox.expand(
      key: const Key('reference-responsive-viewport-v11'),
      child: _scopedShell(context),
    );
  }
}

class _CanonicalSidebar extends StatelessWidget {
  const _CanonicalSidebar({
    required this.selected,
    required this.projection,
    required this.snapshot,
    required this.onSelected,
  });

  static const _logo = '../../brand/assets/13-ilaios-primary-horizontal-light.jpg';
  static const _sections = <DesktopSection>[
    DesktopSection.home,
    DesktopSection.workflows,
    DesktopSection.agents,
    DesktopSection.artifacts,
    DesktopSection.approvals,
    DesktopSection.evidence,
    DesktopSection.settings,
  ];

  final DesktopSection selected;
  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final ValueChanged<DesktopSection> onSelected;

  Widget _logoWidget() {
    final executableDir = File(Platform.resolvedExecutable).parent.path;
    final fallbackFile = File(
      '$executableDir${Platform.pathSeparator}brand${Platform.pathSeparator}assets${Platform.pathSeparator}13-ilaios-primary-horizontal-light.jpg',
    );

    return SizedBox(
      height: 56,
      child: Align(
        alignment: Alignment.centerLeft,
        child: Image.asset(
          _logo,
          key: const Key('canonical-reference-logo'),
          width: 184,
          height: 48,
          fit: BoxFit.contain,
          alignment: Alignment.centerLeft,
          filterQuality: FilterQuality.high,
          gaplessPlayback: true,
          errorBuilder: (context, error, stackTrace) {
            if (!fallbackFile.existsSync()) return const SizedBox.shrink();
            return Image.file(
              fallbackFile,
              width: 184,
              height: 48,
              fit: BoxFit.contain,
              alignment: Alignment.centerLeft,
              filterQuality: FilterQuality.high,
              gaplessPlayback: true,
            );
          },
        ),
      ),
    );
  }

  Widget _navigationContent(BuildContext context, {required bool compactHeight}) {
    final children = <Widget>[
      _logoWidget(),
      const SizedBox(height: 20),
      for (final section in _sections) ...[
        _CanonicalNavItem(
          section: section,
          selected: selected == section,
          onTap: () => onSelected(section),
        ),
        const SizedBox(height: 8),
      ],
    ];

    if (compactHeight) {
      children.add(
        _CanonicalSystemStatus(
          projection: projection,
          snapshot: snapshot,
        ),
      );
      return SingleChildScrollView(
        primary: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: children,
        ),
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ...children,
        const Spacer(),
        _CanonicalSystemStatus(
          projection: projection,
          snapshot: snapshot,
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final light = Theme.of(context).brightness == Brightness.light;
    final background = light
        ? const Color(0xFFF8FAFC)
        : Theme.of(context).colorScheme.surface;
    final semanticsLabel = IlaiosLocaleScope.of(context).text('shell.primaryNavigation');

    return Container(
      key: const Key('canonical-7-page-sidebar'),
      width: 219,
      color: background,
      padding: const EdgeInsets.fromLTRB(14, 20, 14, 14),
      child: Semantics(
        container: true,
        label: semanticsLabel,
        child: LayoutBuilder(
          builder: (context, constraints) => _navigationContent(
            context,
            compactHeight: constraints.maxHeight < 580,
          ),
        ),
      ),
    );
  }
}

class _CanonicalNavItem extends StatelessWidget {
  const _CanonicalNavItem({
    required this.section,
    required this.selected,
    required this.onTap,
  });

  final DesktopSection section;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final light = Theme.of(context).brightness == Brightness.light;
    final selectedColor = light
        ? const Color(0xFFF0F2F5)
        : Theme.of(context).colorScheme.surfaceContainerHighest;

    return Material(
      color: selected ? selectedColor : Colors.transparent,
      borderRadius: BorderRadius.circular(8),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        key: ValueKey('nav-${section.name}'),
        onTap: onTap,
        child: SizedBox(
          height: 54,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Row(
              children: [
                Icon(
                  section.icon,
                  size: 22,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: Text(
                    section.localizedLabel(context),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 16,
                      height: 1.15,
                      fontWeight: FontWeight.w600,
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
}

class _CanonicalSystemStatus extends StatelessWidget {
  const _CanonicalSystemStatus({
    required this.projection,
    required this.snapshot,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    final hasEvidence = snapshot.liveEvents.isNotEmpty ||
        snapshot.evidenceRecords.isNotEmpty ||
        snapshot.governanceState.isNotEmpty;
    final title = projection.connected
        ? (tr ? 'Sistem Çalışıyor' : 'System Connected')
        : (tr ? 'Sistem Çevrimdışı' : 'System Offline');
    final subtitle = projection.connected
        ? (hasEvidence
            ? (tr ? 'Canlı durum verisi mevcut' : 'Live status data available')
            : (tr ? 'Bağlantı doğrulandı' : 'Connection verified'))
        : (tr ? 'Yetkili bağlantı yok' : 'No authorized connection');

    return Container(
      key: const Key('reference-bottom-status-v2'),
      constraints: const BoxConstraints(minHeight: 67),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          Icon(
            Icons.circle,
            size: 12,
            color: projection.connected
                ? const Color(0xFF16B85A)
                : Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  subtitle,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12.5,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right_rounded, size: 18),
        ],
      ),
    );
  }
}

class _CanonicalTopBar extends StatelessWidget {
  const _CanonicalTopBar({
    required this.identityProviders,
    required this.userSession,
    required this.themeMode,
    required this.onThemeModeChanged,
    required this.onSignIn,
    required this.onLogout,
  });

  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    final light = Theme.of(context).brightness == Brightness.light;
    final background = light
        ? const Color(0xFFF7F9FB)
        : Theme.of(context).colorScheme.surfaceContainerLow;

    return Container(
      key: const Key('canonical-7-page-topbar'),
      height: 68,
      padding: const EdgeInsets.symmetric(horizontal: 20),
      decoration: BoxDecoration(
        color: background,
        border: Border(
          bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
      ),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final compact = constraints.maxWidth < 600;
          return Row(
            mainAxisAlignment: MainAxisAlignment.end,
            children: [
              if (!compact) ...[
                Text(
                  tr ? 'Bildirimler' : 'Notifications',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w500),
                ),
                const SizedBox(width: 10),
              ],
              IconButton(
                tooltip: tr ? 'Bildirimler' : 'Notifications',
                onPressed: () => _showNotificationState(context, tr),
                visualDensity: VisualDensity.compact,
                icon: const Icon(Icons.notifications_none_rounded, size: 22),
              ),
              SizedBox(width: compact ? 4 : 12),
              if (!compact)
                Text(
                  tr ? 'TR' : 'EN',
                  style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
                ),
              PopupMenuButton<IlaiosLocale>(
                tooltip: tr ? 'Dil' : 'Language',
                icon: const Icon(Icons.language_rounded, size: 21),
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
                tooltip: tr ? 'Tema' : 'Theme',
                visualDensity: VisualDensity.compact,
                onPressed: () => onThemeModeChanged?.call(
                  themeMode == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark,
                ),
                icon: Icon(
                  themeMode == ThemeMode.dark
                      ? Icons.light_mode_outlined
                      : Icons.dark_mode_outlined,
                  size: 22,
                ),
              ),
              SizedBox(width: compact ? 4 : 12),
              _CanonicalAccountControl(
                identityProviders: identityProviders,
                userSession: userSession,
                onSignIn: onSignIn,
                onLogout: onLogout,
                compact: compact,
              ),
            ],
          );
        },
      ),
    );
  }

  void _showNotificationState(BuildContext context, bool tr) {
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(tr ? 'Bildirimler' : 'Notifications'),
        content: Text(
          tr
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

class _CanonicalAccountControl extends StatelessWidget {
  const _CanonicalAccountControl({
    required this.identityProviders,
    required this.userSession,
    required this.onSignIn,
    required this.onLogout,
    required this.compact,
  });

  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final bool compact;

  IdentityProviderOption? get _googleProvider {
    for (final provider in identityProviders) {
      final id = provider.providerId.toLowerCase();
      final name = provider.displayName.toLowerCase();
      if (id.contains('google') || name.contains('google')) return provider;
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    final google = _googleProvider;
    final signedOut = userSession == null;
    final identity = userSession?.displayIdentity ?? userSession?.principalId;
    final label = signedOut
        ? (tr ? 'Oturum kapalı' : 'Signed out')
        : (identity ?? (tr ? 'Oturum açık' : 'Signed in'));

    final content = Container(
      key: const Key('top-account-control'),
      constraints: BoxConstraints(
        minWidth: compact ? 148 : 194,
        maxWidth: compact ? 176 : 220,
      ),
      height: 46,
      padding: EdgeInsets.symmetric(horizontal: compact ? 10 : 14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Row(
        children: [
          const Icon(Icons.person_outline_rounded, size: 22),
          SizedBox(width: compact ? 8 : 12),
          Expanded(
            child: Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
            ),
          ),
          const Icon(Icons.keyboard_arrow_down_rounded, size: 20),
        ],
      ),
    );

    if (signedOut) {
      if (google == null || onSignIn == null) return content;
      return InkWell(
        key: const Key('top-account-google-sign-in'),
        borderRadius: BorderRadius.circular(24),
        onTap: () async => onSignIn!(google.providerId),
        child: content,
      );
    }

    if (onLogout == null) return content;
    return PopupMenuButton<String>(
      tooltip: tr ? 'Hesap' : 'Account',
      onSelected: (value) {
        if (value == 'signout') onLogout?.call();
      },
      itemBuilder: (context) => [
        if (identity != null)
          PopupMenuItem<String>(
            enabled: false,
            value: 'identity',
            child: Text(identity, overflow: TextOverflow.ellipsis),
          ),
        PopupMenuItem<String>(
          value: 'signout',
          child: Row(
            children: [
              const Icon(Icons.logout_rounded, size: 18),
              const SizedBox(width: 8),
              Text(tr ? 'Çıkış yap' : 'Sign out'),
            ],
          ),
        ),
      ],
      child: content,
    );
  }
}
