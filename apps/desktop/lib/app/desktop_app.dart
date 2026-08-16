import 'package:flutter/material.dart';

import '../control_plane/client.dart';
import '../control_plane/evidence_record.dart';
import '../control_plane/operational_snapshot.dart';
import '../control_plane/projection.dart';
import '../features/dashboard/desktop_shell.dart';
import '../identity/identity_client.dart';
import 'ilaios_locale.dart';
import 'ilaios_theme.dart';

class IlaiosDesktopApp extends StatelessWidget {
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
  Widget build(BuildContext context) => MaterialApp(
        title: 'ILAIOS Desktop',
        debugShowCheckedModeBanner: false,
        theme: IlaiosTheme.light,
        darkTheme: IlaiosTheme.dark,
        themeMode: themeMode,
        home: IlaiosLocaleScope(
          locale: locale,
          onChanged: (value) => onLocaleChanged?.call(value),
          child: DesktopShell(
            projection: projection,
            operationalSnapshot: operationalSnapshot,
            operationalStatus: operationalStatus,
            approverId: approverId,
            identityProviders: identityProviders,
            userSession: userSession,
            identityStatus: identityStatus,
            themeMode: themeMode,
            onThemeModeChanged: onThemeModeChanged,
            onSignIn: onSignIn,
            onLogout: onLogout,
            onPromptSubmit: onPromptSubmit,
            onSaveArtifact: onSaveArtifact,
            onRefreshRequested: onRefreshRequested,
            onGovernanceDecision: onGovernanceDecision,
          ),
        ),
      );
}
