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
    final costUsd = _firstValue(sources, const ['total_cost_usd', 'cost_usd']);
    final costMinor = _firstValue(
      sources,
      const ['total_cost_minor', 'spent_minor', 'used_minor'],
    );
    final budgetUsd = _firstValue(sources, const ['budget_usd']);
    final budgetMinor = _firstValue(
      sources,
      const ['budget_minor', 'hard_cap_minor'],
    );
    final anyCostTelemetry =
        costUsd != null || costMinor != null || budgetUsd != null || budgetMinor != null;
    final unavailable = context.tr('common.unavailable');

    return _Surface(
      title: context.tr('costs.title'),
      icon: Icons.paid_outlined,
      accent: IlaiosTheme.coreBlue,
      status: _localizedStatus(context, status),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Wrap(
            spacing: 12,
            runSpacing: 12,
            children: [
              _Metric(
                label: context.tr('costs.totalUsd'),
                value: costUsd ?? unavailable,
                icon: Icons.attach_money,
                accent: IlaiosTheme.enterpriseCyan,
              ),
              _Metric(
                label: context.tr('costs.totalMinor'),
                value: costMinor ?? unavailable,
                icon: Icons.calculate_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
              _Metric(
                label: context.tr('costs.budgetUsd'),
                value: budgetUsd ?? unavailable,
                icon: Icons.account_balance_wallet_outlined,
                accent: IlaiosTheme.violet,
              ),
              _Metric(
                label: context.tr('costs.budgetCapMinor'),
                value: budgetMinor ?? unavailable,
                icon: Icons.speed_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
              _Metric(
                label: context.tr('costs.tokenUsage'),
                value: unavailable,
                icon: Icons.token_outlined,
                accent: IlaiosTheme.enterpriseCyan,
              ),
              _Metric(
                label: context.tr('costs.gpuRuntime'),
                value: unavailable,
                icon: Icons.memory_outlined,
                accent: IlaiosTheme.violet,
              ),
              _Metric(
                label: context.tr('costs.providerModel'),
                value: unavailable,
                icon: Icons.hub_outlined,
                accent: IlaiosTheme.coreBlue,
              ),
            ],
          ),
          if (!anyCostTelemetry) ...[
            const SizedBox(height: 18),
            _InfoBanner(
              icon: Icons.info_outline,
              accent: IlaiosTheme.coreBlue,
              title: _isTr(context) ? 'Yetkili telemetri bekleniyor' : 'Waiting for authoritative telemetry',
              body: context.tr('costs.noTelemetry'),
            ),
          ],
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
    final light = Theme.of(context).brightness == Brightness.light;
    return _Surface(
      title: context.tr('settings.title'),
      icon: Icons.settings_outlined,
      accent: IlaiosTheme.enterpriseCyan,
      status: _localizedStatus(context, projection.status),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _isTr(context) ? 'Hızlı ayarlar' : 'Quick settings',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 10),
          LayoutBuilder(
            builder: (context, constraints) {
              final itemWidth = constraints.maxWidth >= 980
                  ? (constraints.maxWidth - 48) / 5
                  : constraints.maxWidth >= 620
                      ? (constraints.maxWidth - 12) / 2
                      : constraints.maxWidth;
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  _SettingsAction(
                    key: const Key('settings-notifications-action'),
                    width: itemWidth,
                    icon: Icons.notifications_outlined,
                    label: _isTr(context) ? 'Bildirimler' : 'Notifications',
                    accent: IlaiosTheme.coreBlue,
                    onTap: () => _showSettingsInfo(
                      context,
                      icon: Icons.notifications_outlined,
                      accent: IlaiosTheme.coreBlue,
                      title: _isTr(context) ? 'Bildirimler' : 'Notifications',
                      body: _isTr(context)
                          ? 'Yetkili çalışma zamanı şu anda masaüstüne ayrı bir bildirim tercihi sunmuyor. Bildirim verisi eklenmeden sahte bir ayar gösterilmez.'
                          : 'The authoritative runtime does not currently expose a separate Desktop notification preference. No synthetic setting is fabricated.',
                    ),
                  ),
                  _SettingsAction(
                    key: const Key('settings-language-action'),
                    width: itemWidth,
                    icon: Icons.language,
                    label: _isTr(context) ? 'Dil' : 'Language',
                    accent: IlaiosTheme.enterpriseCyan,
                    onTap: () => _showLocalePicker(context),
                  ),
                  _SettingsAction(
                    key: const Key('settings-appearance-action'),
                    width: itemWidth,
                    icon: light ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                    label: _isTr(context) ? 'Görünüm' : 'Appearance',
                    accent: IlaiosTheme.violet,
                    onTap: () => _showSettingsInfo(
                      context,
                      icon: light ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                      accent: IlaiosTheme.violet,
                      title: _isTr(context) ? 'Görünüm' : 'Appearance',
                      body: _isTr(context)
                          ? 'Geçerli tema: ${light ? 'Açık' : 'Koyu'}. Temayı anında değiştirmek için üst çubuktaki güneş/ay düğmesini kullan.'
                          : 'Current theme: ${light ? 'Light' : 'Dark'}. Use the sun/moon button in the top bar to switch it immediately.',
                    ),
                  ),
                  _SettingsAction(
                    key: const Key('settings-storage-action'),
                    width: itemWidth,
                    icon: Icons.folder_outlined,
                    label: _isTr(context) ? 'Veri ve depolama' : 'Data & storage',
                    accent: IlaiosTheme.coreBlue,
                    onTap: () => _showSettingsInfo(
                      context,
                      icon: Icons.folder_outlined,
                      accent: IlaiosTheme.coreBlue,
                      title: _isTr(context) ? 'Veri ve depolama' : 'Data & storage',
                      body: _isTr(context)
                          ? 'Yerel çalışma verisi: %LOCALAPPDATA%\\ILAIOS. Kullanıcıya kaydedilen teslimler: %USERPROFILE%\\Downloads\\ILAIOS.'
                          : 'Local runtime data: %LOCALAPPDATA%\\ILAIOS. User-saved deliveries: %USERPROFILE%\\Downloads\\ILAIOS.',
                    ),
                  ),
                  _SettingsAction(
                    key: const Key('settings-diagnostics-action'),
                    width: itemWidth,
                    icon: Icons.monitor_heart_outlined,
                    label: _isTr(context) ? 'Teşhis' : 'Diagnostics',
                    accent: IlaiosTheme.enterpriseCyan,
                    onTap: () => _showSettingsInfo(
                      context,
                      icon: Icons.monitor_heart_outlined,
                      accent: IlaiosTheme.enterpriseCyan,
                      title: _isTr(context) ? 'Teşhis' : 'Diagnostics',
                      body: _diagnosticSummary(context),
                    ),
                  ),
                ],
              );
            },
          ),
          const SizedBox(height: 22),
          Text(
            _isTr(context) ? 'Bağlantı ve kimlik' : 'Connection & identity',
            style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  fontWeight: FontWeight.w800,
                ),
          ),
          const SizedBox(height: 10),
          LayoutBuilder(
            builder: (context, constraints) {
              final twoColumns = constraints.maxWidth >= 760;
              final rows = <Widget>[
                _SettingsTile(
                  icon: Icons.dns_outlined,
                  label: context.tr('settings.controlPlane'),
                  value: projection.connected
                      ? context.tr('shell.connected')
                      : context.tr('shell.offline'),
                  accent: IlaiosTheme.coreBlue,
                ),
                _SettingsTile(
                  icon: Icons.verified_user_outlined,
                  label: context.tr('settings.identity'),
                  value: _localizedIdentity(context, identityStatus),
                  accent: IlaiosTheme.enterpriseCyan,
                ),
                _SettingsTile(
                  icon: Icons.apartment_outlined,
                  label: context.tr('settings.tenant'),
                  value: userSession?.tenantId ?? context.tr('common.unavailable'),
                  accent: IlaiosTheme.violet,
                ),
                _SettingsTile(
                  icon: Icons.badge_outlined,
                  label: context.tr('settings.principal'),
                  value: userSession?.principalId ?? context.tr('common.unavailable'),
                  accent: IlaiosTheme.coreBlue,
                ),
                _SettingsTile(
                  icon: Icons.account_circle_outlined,
                  label: context.tr('settings.provider'),
                  value: userSession?.providerId ??
                      (providers.isEmpty
                          ? context.tr('common.notConfigured')
                          : context.tr('common.signedOut')),
                  accent: IlaiosTheme.enterpriseCyan,
                ),
                _SettingsTile(
                  icon: Icons.language,
                  label: context.tr('settings.locale'),
                  value: locale.displayName,
                  accent: IlaiosTheme.coreBlue,
                  onTap: () => _showLocalePicker(context),
                ),
                _SettingsTile(
                  icon: light ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                  label: context.tr('settings.theme'),
                  value: light
                      ? (_isTr(context) ? 'Açık' : 'Light')
                      : context.tr('settings.dark'),
                  accent: IlaiosTheme.violet,
                  onTap: () => _showSettingsInfo(
                    context,
                    icon: light ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                    accent: IlaiosTheme.violet,
                    title: context.tr('settings.theme'),
                    body: _isTr(context)
                        ? 'Tema kontrolü üst çubukta etkin. Güneş/ay düğmesi değişikliği hemen uygular.'
                        : 'Theme control is active in the top bar. The sun/moon button applies the change immediately.',
                  ),
                ),
              ];
              if (!twoColumns) {
                return Column(
                  children: [
                    for (final row in rows)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 10),
                        child: row,
                      ),
                  ],
                );
              }
              return Wrap(
                spacing: 12,
                runSpacing: 12,
                children: [
                  for (final row in rows)
                    SizedBox(width: (constraints.maxWidth - 12) / 2, child: row),
                ],
              );
            },
          ),
          const SizedBox(height: 18),
          _InfoBanner(
            icon: Icons.shield_outlined,
            accent: IlaiosTheme.violet,
            title: _isTr(context) ? 'Yetki sınırı' : 'Authority boundary',
            body: context.tr('settings.authorityNote'),
          ),
        ],
      ),
    );
  }

  String _diagnosticSummary(BuildContext context) {
    final connection = projection.connected
        ? context.tr('shell.connected')
        : context.tr('shell.offline');
    final identity = _localizedIdentity(context, identityStatus);
    final provider = userSession?.providerId ?? context.tr('common.unavailable');
    return _isTr(context)
        ? 'Kontrol düzlemi: $connection\nKimlik: $identity\nSağlayıcı: $provider'
        : 'Control plane: $connection\nIdentity: $identity\nProvider: $provider';
  }
}

class _Surface extends StatelessWidget {
  const _Surface({
    required this.title,
    required this.icon,
    required this.accent,
    required this.status,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Color accent;
  final String status;
  final Widget child;

  @override
  Widget build(BuildContext context) => SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Align(
          alignment: Alignment.topLeft,
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1240),
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.all(24),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 42,
                        height: 42,
                        decoration: BoxDecoration(
                          color: accent.withValues(alpha: .12),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(icon, color: accent),
                      ),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              title,
                              style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w800),
                            ),
                            const SizedBox(height: 3),
                            Text(status, style: Theme.of(context).textTheme.bodySmall),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 22),
                  child,
                ],
              ),
            ),
          ),
        ),
      );
}

class _Metric extends StatefulWidget {
  const _Metric({
    required this.label,
    required this.value,
    required this.icon,
    required this.accent,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color accent;

  @override
  State<_Metric> createState() => _MetricState();
}

class _MetricState extends State<_Metric> {
  bool hovered = false;

  @override
  Widget build(BuildContext context) => MouseRegion(
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: Material(
          color: hovered
              ? widget.accent.withValues(alpha: .08)
              : Theme.of(context).colorScheme.surfaceContainerLowest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: hovered
                  ? widget.accent.withValues(alpha: .55)
                  : Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: () => _showValue(context, widget.label, widget.value, widget.icon, widget.accent),
            child: SizedBox(
              width: 230,
              height: 112,
              child: Padding(
                padding: const EdgeInsets.all(15),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(widget.icon, color: widget.accent, size: 20),
                        const Spacer(),
                        Icon(Icons.arrow_outward, size: 15, color: hovered ? widget.accent : Theme.of(context).colorScheme.outline),
                      ],
                    ),
                    const Spacer(),
                    Text(widget.label, style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 4),
                    Text(
                      widget.value,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w800),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}

class _SettingsAction extends StatefulWidget {
  const _SettingsAction({
    required this.width,
    required this.icon,
    required this.label,
    required this.accent,
    required this.onTap,
    super.key,
  });

  final double width;
  final IconData icon;
  final String label;
  final Color accent;
  final VoidCallback onTap;

  @override
  State<_SettingsAction> createState() => _SettingsActionState();
}

class _SettingsActionState extends State<_SettingsAction> {
  bool hovered = false;

  @override
  Widget build(BuildContext context) => MouseRegion(
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: Material(
          color: hovered
              ? widget.accent.withValues(alpha: .09)
              : Theme.of(context).colorScheme.surfaceContainerLowest,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
            side: BorderSide(
              color: hovered
                  ? widget.accent.withValues(alpha: .58)
                  : Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: widget.onTap,
            child: SizedBox(
              width: widget.width,
              height: 92,
              child: Padding(
                padding: const EdgeInsets.all(13),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Icon(widget.icon, color: widget.accent, size: 21),
                        const Spacer(),
                        Icon(
                          Icons.arrow_forward_ios_rounded,
                          size: 13,
                          color: hovered
                              ? widget.accent
                              : Theme.of(context).colorScheme.outline,
                        ),
                      ],
                    ),
                    const Spacer(),
                    Text(
                      widget.label,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                            fontWeight: FontWeight.w800,
                          ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      );
}

class _SettingsTile extends StatelessWidget {
  const _SettingsTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.accent,
    this.onTap,
  });

  final IconData icon;
  final String label;
  final String value;
  final Color accent;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final content = Padding(
      padding: const EdgeInsets.all(14),
      child: Row(
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: accent.withValues(alpha: .11),
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(icon, size: 19, color: accent),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 3),
                Text(
                  value,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.labelLarge?.copyWith(fontWeight: FontWeight.w800),
                ),
              ],
            ),
          ),
          if (onTap != null) ...[
            const SizedBox(width: 8),
            const Icon(Icons.chevron_right, size: 18),
          ],
        ],
      ),
    );
    return Material(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
      ),
      clipBehavior: Clip.antiAlias,
      child: onTap == null ? content : InkWell(onTap: onTap, child: content),
    );
  }
}

class _InfoBanner extends StatelessWidget {
  const _InfoBanner({
    required this.icon,
    required this.accent,
    required this.title,
    required this.body,
  });

  final IconData icon;
  final Color accent;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: accent.withValues(alpha: .055),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: accent.withValues(alpha: .22)),
        ),
        child: Row(
          children: [
            Icon(icon, color: accent),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontWeight: FontWeight.w800)),
                  const SizedBox(height: 4),
                  Text(body, style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
          ],
        ),
      );
}

Future<void> _showLocalePicker(BuildContext context) async {
  final scope = context.ilaiosLocale;
  final selected = await showDialog<IlaiosLocale>(
    context: context,
    builder: (context) => SimpleDialog(
      title: Text(_isTr(context) ? 'Dil seç' : 'Choose language'),
      children: [
        RadioListTile<IlaiosLocale>(
          value: IlaiosLocale.turkish,
          groupValue: scope.locale,
          onChanged: (value) => Navigator.of(context).pop(value),
          title: const Text('Türkçe'),
        ),
        RadioListTile<IlaiosLocale>(
          value: IlaiosLocale.english,
          groupValue: scope.locale,
          onChanged: (value) => Navigator.of(context).pop(value),
          title: const Text('English'),
        ),
      ],
    ),
  );
  if (selected != null) scope.onChanged(selected);
}

Future<void> _showSettingsInfo(
  BuildContext context, {
  required IconData icon,
  required Color accent,
  required String title,
  required String body,
}) =>
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: Icon(icon, color: accent),
        title: Text(title),
        content: SelectableText(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_isTr(context) ? 'Kapat' : 'Close'),
          ),
        ],
      ),
    );

Future<void> _showValue(
  BuildContext context,
  String label,
  String value,
  IconData icon,
  Color accent,
) => showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        icon: Icon(icon, color: accent),
        title: Text(label),
        content: SelectableText(value),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: Text(_isTr(context) ? 'Kapat' : 'Close'),
          ),
        ],
      ),
    );

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

String _localizedStatus(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    _ => value,
  };
}

String _localizedIdentity(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  if (value.startsWith('Signed in as ')) {
    return 'Oturum açık: ${value.substring('Signed in as '.length)}';
  }
  if (value == 'Signed out') return 'Oturum kapalı';
  return value;
}

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;
