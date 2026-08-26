import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/desktop_identity_action_scope.dart';
import '../../identity/identity_client.dart';
import 'reference_costs_view_v3.dart';
import 'reference_settings_view.dart';
import 'usage_stats_view.dart';

/// Compatibility entry point used by every Desktop shell generation.
///
/// Existing callers keep their original constructor contract. The approved
/// reference-faithful Costs surface remains the default, while a bounded
/// Usage & Stats projection can be opened without adding a second telemetry
/// authority. Both surfaces render only authenticated OperationalSnapshot data.
class CostsView extends StatefulWidget {
  const CostsView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  State<CostsView> createState() => _CostsViewState();
}

class _CostsViewState extends State<CostsView> {
  var _showStats = false;

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    return Stack(
      children: [
        Positioned.fill(
          child: _showStats
              ? UsageStatsView(
                  snapshot: widget.snapshot,
                  status: widget.status,
                )
              : ReferenceCostsViewV3(
                  snapshot: widget.snapshot,
                  status: widget.status,
                ),
        ),
        Positioned(
          right: 22,
          bottom: 18,
          child: Semantics(
            button: true,
            label: _showStats
                ? (tr ? 'Maliyetler ekranına dön' : 'Return to Costs')
                : (tr ? 'Kullanım ve istatistikleri aç' : 'Open Usage & Stats'),
            child: FilledButton.tonalIcon(
              key: const Key('costs-stats-toggle'),
              onPressed: () => setState(() => _showStats = !_showStats),
              icon: Icon(
                _showStats ? Icons.paid_outlined : Icons.query_stats_outlined,
                size: 18,
              ),
              label: Text(
                _showStats
                    ? (tr ? 'Maliyetler' : 'Costs')
                    : (tr ? 'Kullanım ve İstatistikler' : 'Usage & Stats'),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Compatibility entry point used by every Desktop shell generation.
///
/// Identity remains authoritative in DesktopBootstrap. This surface only
/// exposes the existing callbacks; it never creates a second browser/auth path.
class SettingsView extends StatefulWidget {
  const SettingsView({
    required this.projection,
    required this.identityStatus,
    required this.userSession,
    required this.providers,
    this.onSignIn,
    this.onLogout,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String identityStatus;
  final DesktopUserSession? userSession;
  final List<IdentityProviderOption> providers;
  final Future<void> Function(String providerId)? onSignIn;
  final Future<void> Function()? onLogout;

  @override
  State<SettingsView> createState() => _SettingsViewState();
}

class _SettingsViewState extends State<SettingsView> {
  String? _pendingProviderId;
  String? _error;

  Future<void> _connect(
    IdentityProviderOption provider,
    Future<void> Function(String providerId) callback,
  ) async {
    if (widget.userSession != null || _pendingProviderId != null) return;
    setState(() {
      _pendingProviderId = provider.providerId;
      _error = null;
    });
    try {
      await callback(provider.providerId);
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _pendingProviderId = null);
    }
  }

  Future<void> _logout(Future<void> Function() callback) async {
    if (widget.userSession == null || _pendingProviderId != null) return;
    setState(() {
      _pendingProviderId = widget.userSession!.providerId;
      _error = null;
    });
    try {
      await callback();
    } catch (error) {
      if (!mounted) return;
      setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _pendingProviderId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final mode = Theme.of(context).brightness == Brightness.dark
        ? ThemeMode.dark
        : ThemeMode.light;
    final scope = DesktopIdentityActionScope.maybeOf(context);
    final signIn = widget.onSignIn ?? scope?.onSignIn;
    final logout = widget.onLogout ?? scope?.onLogout;
    return Stack(
      children: [
        Positioned.fill(
          child: ReferenceSettingsView(
            projection: widget.projection,
            identityStatus: widget.identityStatus,
            userSession: widget.userSession,
            providers: widget.providers,
            themeMode: mode,
          ),
        ),
        if (widget.providers.isNotEmpty)
          Positioned(
            right: 29,
            bottom: 20,
            width: 286,
            child: _ProviderActions(
              providers: widget.providers,
              session: widget.userSession,
              pendingProviderId: _pendingProviderId,
              error: _error,
              onSignIn: signIn == null
                  ? null
                  : (provider) => _connect(provider, signIn),
              onLogout: logout == null ? null : () => _logout(logout),
            ),
          ),
      ],
    );
  }
}

class _ProviderActions extends StatelessWidget {
  const _ProviderActions({
    required this.providers,
    required this.session,
    required this.pendingProviderId,
    required this.error,
    required this.onSignIn,
    required this.onLogout,
  });

  final List<IdentityProviderOption> providers;
  final DesktopUserSession? session;
  final String? pendingProviderId;
  final String? error;
  final Future<void> Function(IdentityProviderOption provider)? onSignIn;
  final Future<void> Function()? onLogout;

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    return Material(
      elevation: 0,
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            for (final provider in providers.take(4))
              Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: _ProviderActionRow(
                  provider: provider,
                  connected: session?.providerId == provider.providerId,
                  pending: pendingProviderId == provider.providerId,
                  connectEnabled: onSignIn != null &&
                      session == null &&
                      pendingProviderId == null,
                  logoutEnabled: onLogout != null &&
                      session?.providerId == provider.providerId &&
                      pendingProviderId == null,
                  onConnect: onSignIn == null ? null : () => onSignIn!(provider),
                  onLogout: onLogout,
                ),
              ),
            if (error != null)
              Text(
                tr
                    ? 'Bağlantı işlemi başarısız: $error'
                    : 'Identity action failed: $error',
                key: const Key('settings-provider-error'),
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 8,
                  color: Theme.of(context).colorScheme.error,
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ProviderActionRow extends StatelessWidget {
  const _ProviderActionRow({
    required this.provider,
    required this.connected,
    required this.pending,
    required this.connectEnabled,
    required this.logoutEnabled,
    required this.onConnect,
    required this.onLogout,
  });

  final IdentityProviderOption provider;
  final bool connected;
  final bool pending;
  final bool connectEnabled;
  final bool logoutEnabled;
  final VoidCallback? onConnect;
  final VoidCallback? onLogout;

  @override
  Widget build(BuildContext context) {
    final tr = Localizations.localeOf(context).languageCode == 'tr';
    final label = pending
        ? (tr ? 'İşleniyor…' : 'Working…')
        : connected
            ? (tr ? 'Çıkış' : 'Sign out')
            : (tr ? 'Bağlan' : 'Connect');
    final enabled = connected ? logoutEnabled : connectEnabled;
    final action = connected ? onLogout : onConnect;
    return Row(
      children: [
        const Icon(Icons.cloud_outlined, size: 13),
        const SizedBox(width: 6),
        Expanded(
          child: Text(
            provider.displayName,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600),
          ),
        ),
        const SizedBox(width: 6),
        Semantics(
          button: true,
          enabled: enabled,
          label: connected
              ? '${tr ? 'Çıkış yap' : 'Sign out'} ${provider.displayName}'
              : '${tr ? 'Bağlan' : 'Connect'} ${provider.displayName}',
          child: SizedBox(
            height: 26,
            child: OutlinedButton(
              key: ValueKey('settings-provider-connect-${provider.providerId}'),
              onPressed: pending || !enabled ? null : action,
              child: Text(label, style: const TextStyle(fontSize: 8)),
            ),
          ),
        ),
      ],
    );
  }
}
