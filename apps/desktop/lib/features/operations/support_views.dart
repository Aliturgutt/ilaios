import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';

class CostsView extends StatelessWidget {
  const CostsView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  Widget build(BuildContext context) {
    final cost = _firstValue(
      <Map<String, Object?>>[snapshot.governanceState, snapshot.schedulerState],
      const <String>['total_cost', 'cost', 'cost_usd', 'spent'],
    );
    final budget = _firstValue(
      <Map<String, Object?>>[snapshot.governanceState, snapshot.schedulerState],
      const <String>['budget', 'budget_usd', 'hard_cap', 'hard_cap_minor'],
    );
    return _Surface(
      title: 'Costs & Usage',
      icon: Icons.paid_outlined,
      status: status,
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          _Metric(label: 'Total cost', value: cost ?? 'Unavailable'),
          _Metric(label: 'Budget', value: budget ?? 'Unavailable'),
          const _Metric(label: 'Token usage', value: 'Unavailable'),
          const _Metric(label: 'GPU/runtime duration', value: 'Unavailable'),
          const _Metric(label: 'Provider/model usage', value: 'Unavailable'),
          if (cost == null && budget == null)
            const SizedBox(
              width: 480,
              child: Text(
                'The current authenticated Desktop projection does not expose authoritative cost telemetry. No synthetic cost or usage values are shown.',
                style: TextStyle(color: IlaiosTheme.muted, height: 1.5),
              ),
            ),
        ],
      ),
    );
  }
}

class SettingsView extends StatelessWidget {
  const SettingsView({
    required this.projection,
    required this.identityStatus,
    required this.userSession,
    required this.providers,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String identityStatus;
  final DesktopUserSession? userSession;
  final List<IdentityProviderOption> providers;

  @override
  Widget build(BuildContext context) => _Surface(
        title: 'Settings',
        icon: Icons.settings_outlined,
        status: projection.status,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _SettingsRow(
              label: 'Control plane',
              value: projection.connected ? 'Connected' : 'Offline',
            ),
            _SettingsRow(label: 'Identity', value: identityStatus),
            _SettingsRow(
              label: 'Tenant',
              value: userSession?.tenantId ?? 'Unavailable',
            ),
            _SettingsRow(
              label: 'Principal',
              value: userSession?.principalId ?? 'Unavailable',
            ),
            _SettingsRow(
              label: 'Provider',
              value: userSession?.providerId ??
                  (providers.isEmpty ? 'Not configured' : 'Signed out'),
            ),
            const _SettingsRow(
              label: 'Locale',
              value: 'System locale',
            ),
            const _SettingsRow(label: 'Theme', value: 'Dark'),
            const SizedBox(height: 18),
            const Text(
              'Tenant authority, governance, execution and identity verification remain backend/session authoritative. This surface does not widen client authority.',
              style: TextStyle(color: IlaiosTheme.muted, height: 1.5),
            ),
          ],
        ),
      );
}

class _Surface extends StatelessWidget {
  const _Surface({
    required this.title,
    required this.icon,
    required this.status,
    required this.child,
  });
  final String title;
  final IconData icon;
  final String status;
  final Widget child;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1180),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(
                color: IlaiosTheme.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: IlaiosTheme.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Icon(icon, color: IlaiosTheme.cyan),
                      const SizedBox(width: 10),
                      Text(
                        title,
                        style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                  const SizedBox(height: 7),
                  Text(status, style: const TextStyle(color: IlaiosTheme.muted)),
                  const SizedBox(height: 22),
                  child,
                ],
              ),
            ),
          ),
        ),
      );
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        width: 220,
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(label, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11)),
            const SizedBox(height: 7),
            Text(
              value,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700),
            ),
          ],
        ),
      );
}

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({required this.label, required this.value});
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 9),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(9),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Row(
          children: [
            SizedBox(
              width: 140,
              child: Text(label, style: const TextStyle(color: IlaiosTheme.muted)),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                value,
                textAlign: TextAlign.right,
                overflow: TextOverflow.ellipsis,
                maxLines: 2,
              ),
            ),
          ],
        ),
      );
}

String? _firstValue(List<Map<String, Object?>> sources, List<String> keys) {
  for (final source in sources) {
    for (final key in keys) {
      final value = source[key];
      if (value is num) return value.toString();
      if (value is String && value.trim().isNotEmpty) return value.trim();
    }
  }
  return null;
}
