import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import 'create_view_impl.dart' as impl;

/// Presentation boundary for the Goals surface.
///
/// Raw control-plane event identifiers remain unchanged in the authoritative
/// projection and evidence surfaces. This wrapper only converts known internal
/// event identifiers into human-readable copy for the Goals UI.
class CreateView extends StatelessWidget {
  const CreateView({
    required this.projection,
    required this.status,
    this.identityProviders = const <IdentityProviderOption>[],
    this.userSession,
    this.identityStatus = 'Account sign-in is not configured',
    this.onSignIn,
    this.onLogout,
    this.onSubmit,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String status;
  final List<IdentityProviderOption> identityProviders;
  final DesktopUserSession? userSession;
  final String identityStatus;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;
  final Future<PromptSubmission> Function(String objective)? onSubmit;

  @override
  Widget build(BuildContext context) {
    final displayProjection = ControlPlaneProjection(
      connected: projection.connected,
      status: projection.status,
      goalCount: projection.goalCount,
      jobCount: projection.jobCount,
      lastEvent: _displayEvent(context, projection.lastEvent),
      schemaVersion: projection.schemaVersion,
    );
    return impl.CreateView(
      projection: displayProjection,
      status: status,
      identityProviders: identityProviders,
      userSession: userSession,
      identityStatus: identityStatus,
      onSignIn: onSignIn,
      onLogout: onLogout,
      onSubmit: onSubmit,
    );
  }
}

String? _displayEvent(BuildContext context, String? raw) {
  final value = raw?.trim();
  if (value == null || value.isEmpty) return raw;
  if (value != 'job.updated') return value;
  return IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish
      ? 'İş güncellemesi'
      : 'Job update';
}
