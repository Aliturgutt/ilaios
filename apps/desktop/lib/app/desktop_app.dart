import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

import '../control_plane/client.dart';
import '../control_plane/evidence_record.dart';
import '../control_plane/operational_snapshot.dart';
import '../control_plane/projection.dart';
import '../features/dashboard/reference_desktop_shell_v9.dart';
import '../identity/identity_client.dart';
import 'ilaios_locale.dart';
import 'ilaios_theme.dart';
import 'ilaios_theme_mode.dart';

class IlaiosDesktopApp extends StatefulWidget {
  const IlaiosDesktopApp({
    super.key,
    this.projection = const ControlPlaneProjection.unavailable(),
    this.operationalSnapshot = const OperationalSnapshot.unavailable(),
    this.operationalStatus = 'Operational APIs not connected',
    this.approverId,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.locale = IlaiosLocale.english,
    this.themeMode = ThemeMode.dark,
    this.onLocaleChanged,
    this.onThemeModeChanged,
    this.onSignIn,
    this.onLogout,
    this.onPromptSubmit,
    this.onSaveArtifact,
    this.onRefreshRequested,
    this.onGovernanceDecision,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot operationalSnapshot;
  final String operationalStatus;
  final String? approverId;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final IlaiosLocale locale;
  final ThemeMode themeMode;
  final ValueChanged<IlaiosLocale>? onLocaleChanged;
  final ValueChanged<ThemeMode>? onThemeModeChanged;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final VoidCallback? onRefreshRequested;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onGovernanceDecision;

  @override
  State<IlaiosDesktopApp> createState() => _IlaiosDesktopAppState();
}

class _IlaiosDesktopAppState extends State<IlaiosDesktopApp> {
  late ThemeMode _localThemeMode = widget.themeMode;

  @override
  void initState() {
    super.initState();
    if (kReleaseMode && widget.onThemeModeChanged == null) {
      unawaited(_loadTheme());
    }
  }

  @override
  void didUpdateWidget(covariant IlaiosDesktopApp oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.themeMode != oldWidget.themeMode &&
        widget.onThemeModeChanged != null) {
      _localThemeMode = widget.themeMode;
    }
  }

  Future<void> _loadTheme() async {
    final mode = await IlaiosThemeModeStore.load();
    if (!mounted || widget.onThemeModeChanged != null || mode == _localThemeMode) {
      return;
    }
    setState(() => _localThemeMode = mode);
  }

  void _changeTheme(ThemeMode mode) {
    if (widget.onThemeModeChanged != null) {
      widget.onThemeModeChanged!(mode);
      return;
    }
    if (_localThemeMode != mode) setState(() => _localThemeMode = mode);
    if (kReleaseMode) unawaited(IlaiosThemeModeStore.save(mode));
  }

  @override
  Widget build(BuildContext context) {
    final effectiveTheme =
        widget.onThemeModeChanged == null ? _localThemeMode : widget.themeMode;
    return MaterialApp(
      title: 'ILAIOS Desktop',
      debugShowCheckedModeBanner: false,
      theme: IlaiosTheme.light,
      darkTheme: IlaiosTheme.dark,
      themeMode: effectiveTheme,
      home: IlaiosLocaleScope(
        locale: widget.locale,
        onChanged: (value) => widget.onLocaleChanged?.call(value),
        child: ReferenceDesktopShellV9(
          projection: widget.projection,
          operationalSnapshot: widget.operationalSnapshot,
          operationalStatus: widget.operationalStatus,
          approverId: widget.approverId,
          identityProviders: widget.identityProviders,
          userSession: widget.userSession,
          identityStatus: widget.identityStatus,
          themeMode: effectiveTheme,
          onThemeModeChanged: _changeTheme,
          onSignIn: widget.onSignIn,
          onLogout: widget.onLogout,
          onPromptSubmit: widget.onPromptSubmit,
          onSaveArtifact: widget.onSaveArtifact,
          onRefreshRequested: widget.onRefreshRequested,
          onGovernanceDecision: widget.onGovernanceDecision,
        ),
      ),
    );
  }
}
