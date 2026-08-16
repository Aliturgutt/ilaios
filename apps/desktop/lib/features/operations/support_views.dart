import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
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
    final sources = <Map<String, Object?>>[
      snapshot.governanceState,
      snapshot.schedulerState,
      ..._mapList(snapshot.governanceState['costs']),
    ];
    final costUsd = _firstValue(
      sources,
      const <String>['total_cost_usd', 'cost_usd'],
    );
    final costMinor = _firstValue(
      sources,
      const <String>['total_cost_minor', 'spent_minor', 'used_minor'],
    );
    final budgetUsd = _firstValue(sources, const <String>['budget_usd']);
    final budgetMinor = _firstValue(
      sources,
      const <String>['budget_minor', 'hard_cap_minor'],
    );
    final anyCostTelemetry =
        costUsd != null ||
        costMinor != null ||
        budgetUsd != null ||
        budgetMinor != null;
    final unavailable = context.tr('common.unavailable');
    return _Surface(
      title: context.tr('costs.title'),
      icon: Icons.paid_outlined,
      status: status,
      child: Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          _Metric(
            label: context.tr('costs.totalUsd'),
            value: costUsd ?? unavailable,
          ),
          _Metric(
            label: context.tr('costs.totalMinor'),
            value: costMinor ?? unavailable,
          ),
          _Metric(
            label: context.tr('costs.budgetUsd'),
            value: budgetUsd ?? unavailable,
          ),
          _Metric(
            label: context.tr('costs.budgetCapMinor'),
            value: budgetMinor ?? unavailable,
          ),
          _Metric(label: context.tr('costs.tokenUsage'), value: unavailable),
          _Metric(label: context.tr('costs.gpuRuntime'), value: unavailable),
          _Metric(label: context.tr('costs.providerModel'), value: unavailable),
          if (!anyCostTelemetry)
            SizedBox(
              width: 480,
              child: Text(
                context.tr('costs.noTelemetry'),
                style: const TextStyle(color: IlaiosTheme.muted, height: 1.5),
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
  Widget build(BuildContext context) {
    final locale = context.ilaiosLocale.locale;
    return _Surface(
      title: context.tr('settings.title'),
      icon: Icons.settings_outlined,
      status: projection.status,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _SettingsRow(
            label: context.tr('settings.controlPlane'),
            value: projection.connected
                ? context.tr('shell.connected')
                : context.tr('shell.offline'),
          ),
          _SettingsRow(label: context.tr('settings.identity'), value: identityStatus),
          _SettingsRow(
            label: context.tr('settings.tenant'),
            value: userSession?.tenantId ?? context.tr('common.unavailable'),
          ),
          _SettingsRow(
            label: context.tr('settings.principal'),
            value: userSession?.principalId ?? context.tr('common.unavailable'),
          ),
          _SettingsRow(
            label: context.tr('settings.provider'),
            value: userSession?.providerId ??
                (providers.isEmpty
                    ? context.tr('common.notConfigured')
                    : context.tr('common.signedOut')),
          ),
          _SettingsRow(
            label: context.tr('settings.locale'),
            value: locale.displayName,
          ),
          _SettingsRow(
            label: context.tr('settings.theme'),
            value: context.tr('settings.dark'),
          ),
          const SizedBox(height: 18),
          Text(
            context.tr('settings.authorityNote'),
            style: const TextStyle(color: IlaiosTheme.muted, height: 1.5),
          ),
        ],
      ),
    );
  }
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

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return <Map<String, Object?>>[
    for (final item in value)
      if (item is Map<String, dynamic>) Map<String, Object?>.from(item),
  ];
}
