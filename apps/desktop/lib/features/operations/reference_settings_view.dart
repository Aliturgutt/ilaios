import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';

/// Reference-faithful Settings surface for the approved dark/light Desktop UI.
///
/// The supplied screenshots define presentation only. Runtime connection,
/// identity and provider state remain authority-derived. Unsupported connector,
/// notification and policy telemetry is rendered unavailable rather than
/// synthesized from the screenshots.
class ReferenceSettingsView extends StatefulWidget {
  const ReferenceSettingsView({
    required this.projection,
    required this.identityStatus,
    required this.userSession,
    required this.providers,
    required this.themeMode,
    this.onThemeModeChanged,
    super.key,
  });

  final ControlPlaneProjection projection;
  final String identityStatus;
  final DesktopUserSession? userSession;
  final List<IdentityProviderOption> providers;
  final ThemeMode themeMode;
  final ValueChanged<ThemeMode>? onThemeModeChanged;

  @override
  State<ReferenceSettingsView> createState() => _ReferenceSettingsViewState();
}

class _ReferenceSettingsViewState extends State<ReferenceSettingsView> {
  int _section = 1;
  bool _compact = false;
  bool _dense = true;
  bool _sidebarCollapsed = false;
  bool _animations = true;
  double _fontScale = 1;
  late ThemeMode _previewTheme = widget.themeMode;
  String? _message;
  final List<String> _changes = <String>[];

  void _record(String en, String tr) {
    final text = _copy(context, en, tr);
    setState(() {
      _message = null;
      _changes.insert(0, text);
      if (_changes.length > 4) _changes.removeLast();
    });
  }

  void _select(int value) => setState(() {
        _section = value;
        _message = null;
      });

  Future<void> _chooseLanguage() async {
    final current = context.ilaiosLocale.locale;
    final selected = await showDialog<IlaiosLocale>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(_copy(context, 'Choose language', 'Dil seç')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ListTile(
              title: const Text('English'),
              leading: Icon(
                current == IlaiosLocale.english
                    ? Icons.radio_button_checked
                    : Icons.radio_button_off,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              onTap: () =>
                  Navigator.of(dialogContext).pop(IlaiosLocale.english),
            ),
            ListTile(
              title: const Text('Türkçe'),
              leading: Icon(
                current == IlaiosLocale.turkish
                    ? Icons.radio_button_checked
                    : Icons.radio_button_off,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              onTap: () =>
                  Navigator.of(dialogContext).pop(IlaiosLocale.turkish),
            ),
          ],
        ),
      ),
    );
    if (!mounted || selected == null || selected == current) return;
    context.ilaiosLocale.onChanged(selected);
    _record('Language changed', 'Dil değiştirildi');
  }

  void _setTheme(ThemeMode mode) {
    setState(() => _previewTheme = mode);
    widget.onThemeModeChanged?.call(mode);
    _record(
      'Theme preview changed',
      'Tema önizlemesi değiştirildi',
    );
  }

  void _reset() {
    setState(() {
      _compact = false;
      _dense = true;
      _sidebarCollapsed = false;
      _animations = true;
      _fontScale = 1;
      _previewTheme = widget.themeMode;
      _message = null;
    });
    _record('Appearance defaults restored', 'Görünüm varsayılanları geri yüklendi');
  }

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('reference-settings-page'),
        color: Theme.of(context).scaffoldBackgroundColor,
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Header(),
            const SizedBox(height: 7),
            SizedBox(
              key: const Key('settings-summary-strip'),
              height: 72,
              child: _summaryStrip(context),
            ),
            const SizedBox(height: 8),
            Expanded(
              flex: 5,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SizedBox(
                    key: const Key('settings-left-navigation'),
                    width: 172,
                    child: _SectionNavigation(
                      selected: _section,
                      onSelected: _select,
                    ),
                  ),
                  const SizedBox(width: 9),
                  Expanded(
                    child: _section == 1
                        ? _AppearancePanel(
                            compact: _compact,
                            dense: _dense,
                            sidebarCollapsed: _sidebarCollapsed,
                            animations: _animations,
                            fontScale: _fontScale,
                            themeMode: _previewTheme,
                            onLanguage: _chooseLanguage,
                            onTheme: _setTheme,
                            onCompact: (value) {
                              setState(() => _compact = value);
                              _record('Compact mode updated', 'Kompakt mod güncellendi');
                            },
                            onDense: (value) {
                              setState(() => _dense = value);
                              _record('Dense table mode updated', 'Yoğun tablo modu güncellendi');
                            },
                            onSidebar: (value) {
                              setState(() => _sidebarCollapsed = value);
                              _record('Sidebar preview updated', 'Kenar çubuğu önizlemesi güncellendi');
                            },
                            onAnimations: (value) {
                              setState(() => _animations = value);
                              _record('Animation preference updated', 'Animasyon tercihi güncellendi');
                            },
                            onScale: (value) => setState(() => _fontScale = value),
                            onScaleEnd: (_) =>
                                _record('Font scale updated', 'Yazı ölçeği güncellendi'),
                          )
                        : _AuthorityPanel(
                            section: _section,
                            projection: widget.projection,
                            identityStatus: widget.identityStatus,
                            userSession: widget.userSession,
                            providers: widget.providers,
                          ),
                  ),
                  const SizedBox(width: 9),
                  SizedBox(
                    key: const Key('settings-preview-panel'),
                    width: 324,
                    child: _PreviewPanel(
                      compact: _compact,
                      dense: _dense,
                      sidebarCollapsed: _sidebarCollapsed,
                      animations: _animations,
                      fontScale: _fontScale,
                      connected: widget.projection.connected,
                      message: _message,
                      onSave: () => setState(
                        () => _message = _copy(
                          context,
                          'Local appearance preferences applied for this session.',
                          'Yerel görünüm tercihleri bu oturuma uygulandı.',
                        ),
                      ),
                      onReset: _reset,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              flex: 2,
              child: Row(
                key: const Key('settings-bottom-grid'),
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Expanded(child: _RecentChanges(changes: _changes)),
                  const SizedBox(width: 9),
                  Expanded(
                    child: _PolicyCard(
                      projection: widget.projection,
                      identityStatus: widget.identityStatus,
                    ),
                  ),
                  const SizedBox(width: 9),
                  Expanded(
                    child: _ProvidersCard(
                      providers: widget.providers,
                      session: widget.userSession,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );

  Widget _summaryStrip(BuildContext context) => Row(
        children: [
          Expanded(
            child: _SummaryCard(
              key: const Key('settings-storage-action'),
              icon: Icons.settings_outlined,
              title: _copy(context, 'General', 'Genel'),
              subtitle: _copy(context, 'Core preferences', 'Temel ayarlar'),
              status: _copy(context, 'Local', 'Yerel'),
              selected: _section == 0,
              onTap: () => _select(0),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: _SummaryCard(
              key: const Key('settings-appearance-action'),
              icon: Icons.palette_outlined,
              title: _copy(context, 'Appearance', 'Görünüm'),
              subtitle: _copy(context, 'Theme and UI', 'Arayüz tercihleri'),
              status: _copy(context, 'Active', 'Aktif'),
              selected: _section == 1,
              onTap: () => _select(1),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: _SummaryCard(
              key: const Key('settings-notifications-action'),
              icon: Icons.notifications_none_outlined,
              title: _copy(context, 'Notifications', 'Bildirimler'),
              subtitle: _copy(context, 'Runtime preferences', 'Uyarı tercihleri'),
              status: _copy(context, 'Unavailable', 'Kullanılamıyor'),
              selected: _section == 6,
              onTap: () => _select(6),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: _SummaryCard(
              key: const Key('settings-diagnostics-action'),
              icon: Icons.shield_outlined,
              title: _copy(context, 'Security', 'Güvenlik'),
              subtitle: _copy(context, 'Identity boundary', 'Erişim ve kimlik'),
              status: widget.projection.connected
                  ? _copy(context, 'Connected', 'Bağlı')
                  : _copy(context, 'Offline', 'Çevrimdışı'),
              selected: _section == 3,
              onTap: () => _select(3),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: _SummaryCard(
              icon: Icons.cloud_outlined,
              title: _copy(context, 'Providers', 'Sağlayıcılar'),
              subtitle: _copy(context, 'Identity providers', 'Bağlı servisler'),
              status: widget.providers.isEmpty
                  ? _copy(context, 'None', 'Yok')
                  : '${widget.providers.length}',
              selected: _section == 4,
              onTap: () => _select(4),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: _SummaryCard(
              icon: Icons.extension_outlined,
              title: _copy(context, 'Integrations', 'Entegrasyonlar'),
              subtitle: _copy(context, 'External connections', 'Harici bağlantılar'),
              status: _copy(context, 'Unavailable', 'Kullanılamıyor'),
              selected: _section == 5,
              onTap: () => _select(5),
            ),
          ),
        ],
      );
}

class _Header extends StatelessWidget {
  @override
  Widget build(BuildContext context) => SizedBox(
        height: 45,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _copy(context, 'Settings', 'Ayarlar'),
              style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 2),
            Text(
              _copy(
                context,
                'Manage platform configuration, appearance, security and connections.',
                'Platform yapılandırmasını, görünümü, güvenliği ve entegrasyonları yönetin.',
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 9.2,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      );
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.status,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String status;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: selected
            ? Theme.of(context).colorScheme.surfaceContainerHighest
            : Theme.of(context).colorScheme.surfaceContainerLowest,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(7),
          side: BorderSide(
            color: selected
                ? Theme.of(context).colorScheme.outline
                : Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 8),
            child: Row(
              children: [
                Icon(
                  icon,
                  size: 23,
                  color: selected
                      ? Theme.of(context).colorScheme.onSurface
                      : Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 8),
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
                          fontSize: 9.8,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 7.5,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        status,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 7.7,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _SectionNavigation extends StatelessWidget {
  const _SectionNavigation({required this.selected, required this.onSelected});

  final int selected;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final labels = _isTr(context)
        ? const <String>[
            'Genel',
            'Görünüm',
            'Hesap',
            'Güvenlik',
            'Sağlayıcılar',
            'Entegrasyonlar',
            'Bildirimler',
            'Gizlilik',
            'Gelişmiş',
          ]
        : const <String>[
            'General',
            'Appearance',
            'Account',
            'Security',
            'Providers',
            'Integrations',
            'Notifications',
            'Privacy',
            'Advanced',
          ];
    const icons = <IconData>[
      Icons.settings_outlined,
      Icons.palette_outlined,
      Icons.person_outline,
      Icons.shield_outlined,
      Icons.cloud_outlined,
      Icons.extension_outlined,
      Icons.notifications_none_outlined,
      Icons.lock_outline,
      Icons.tune_outlined,
    ];

    return Container(
      decoration: _card(context),
      padding: const EdgeInsets.all(6),
      child: Column(
        children: [
          for (var index = 0; index < labels.length; index++)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: Material(
                  color: selected == index
                      ? Theme.of(context).colorScheme.surfaceContainerHighest
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(5),
                  child: InkWell(
                    onTap: () => onSelected(index),
                    borderRadius: BorderRadius.circular(5),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 8),
                      child: Row(
                        children: [
                          Icon(
                            icons[index],
                            size: 14,
                            color: selected == index
                                ? Theme.of(context).colorScheme.onSurface
                                : Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 7),
                          Expanded(
                            child: Text(
                              labels[index],
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 8.8,
                                fontWeight: selected == index
                                    ? FontWeight.w600
                                    : FontWeight.w500,
                                color: selected == index
                                    ? Theme.of(context).colorScheme.onSurface
                                    : Theme.of(context).colorScheme.onSurface,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _AppearancePanel extends StatelessWidget {
  const _AppearancePanel({
    required this.compact,
    required this.dense,
    required this.sidebarCollapsed,
    required this.animations,
    required this.fontScale,
    required this.themeMode,
    required this.onLanguage,
    required this.onTheme,
    required this.onCompact,
    required this.onDense,
    required this.onSidebar,
    required this.onAnimations,
    required this.onScale,
    required this.onScaleEnd,
  });

  final bool compact;
  final bool dense;
  final bool sidebarCollapsed;
  final bool animations;
  final double fontScale;
  final ThemeMode themeMode;
  final VoidCallback onLanguage;
  final ValueChanged<ThemeMode> onTheme;
  final ValueChanged<bool> onCompact;
  final ValueChanged<bool> onDense;
  final ValueChanged<bool> onSidebar;
  final ValueChanged<bool> onAnimations;
  final ValueChanged<double> onScale;
  final ValueChanged<double> onScaleEnd;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('settings-appearance-panel'),
        decoration: _card(context),
        padding: const EdgeInsets.fromLTRB(12, 9, 12, 8),
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                _copy(context, 'Appearance', 'Görünüm'),
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700),
              ),
              Text(
                _copy(
                  context,
                  'Customize Desktop appearance and preview preferences.',
                  'Arayüz görünümünü ve önizleme tercihlerinizi özelleştirin.',
                ),
                style: TextStyle(
                  fontSize: 7.4,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 5),
              _SettingRow(
                title: _copy(context, 'Language', 'Dil'),
                child: Material(
                  key: const Key('settings-language-action'),
                  color: Theme.of(context).colorScheme.surfaceContainerLowest,
                  borderRadius: BorderRadius.circular(5),
                  child: InkWell(
                    onTap: onLanguage,
                    borderRadius: BorderRadius.circular(5),
                    child: Container(
                      width: 230,
                      height: 27,
                      padding: const EdgeInsets.symmetric(horizontal: 9),
                      decoration: BoxDecoration(
                        border: Border.all(
                          color: Theme.of(context).colorScheme.outlineVariant,
                        ),
                        borderRadius: BorderRadius.circular(5),
                      ),
                      child: Row(
                        children: [
                          Expanded(
                            child: Text(
                              context.ilaiosLocale.locale.displayName,
                              style: const TextStyle(fontSize: 8.3),
                            ),
                          ),
                          const Icon(Icons.keyboard_arrow_down, size: 14),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
              _SettingRow(
                title: _copy(context, 'Theme', 'Tema'),
                child: SizedBox(
                  width: 230,
                  height: 27,
                  child: Row(
                    children: [
                      Expanded(
                        child: _ThemeButton(
                          key: const Key('settings-theme-dark'),
                          label: _copy(context, 'Dark', 'Koyu'),
                          selected: themeMode == ThemeMode.dark,
                          onTap: () => onTheme(ThemeMode.dark),
                        ),
                      ),
                      const SizedBox(width: 3),
                      Expanded(
                        child: _ThemeButton(
                          key: const Key('settings-theme-light'),
                          label: _copy(context, 'Light', 'Açık'),
                          selected: themeMode == ThemeMode.light,
                          onTap: () => onTheme(ThemeMode.light),
                        ),
                      ),
                      const SizedBox(width: 3),
                      Expanded(
                        child: _ThemeButton(
                          key: const Key('settings-theme-system'),
                          label: _copy(context, 'System', 'Sistem'),
                          selected: themeMode == ThemeMode.system,
                          onTap: () => onTheme(ThemeMode.system),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              _SettingRow(
                title: _copy(context, 'UI color policy', 'Arayüz renk politikası'),
                child: SizedBox(
                  key: const Key('settings-neutral-color-policy'),
                  width: 230,
                  height: 27,
                  child: Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      _copy(
                        context,
                        'Neutral black / white / gray',
                        'Nötr siyah / beyaz / gri',
                      ),
                      style: TextStyle(
                        fontSize: 8.1,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ),
              ),
              _SwitchRow(
                title: _copy(context, 'Compact mode', 'Kompakt Mod'),
                subtitle: _copy(
                  context,
                  'Tighter preview spacing.',
                  'Daha sıkı önizleme aralığı.',
                ),
                value: compact,
                onChanged: onCompact,
              ),
              _SwitchRow(
                title: _copy(context, 'Dense table mode', 'Yoğun Tablo Modu'),
                subtitle: _copy(
                  context,
                  'Prefer denser table rows.',
                  'Daha yoğun tablo satırlarını tercih et.',
                ),
                value: dense,
                onChanged: onDense,
              ),
              _SwitchRow(
                title: _copy(
                  context,
                  'Sidebar collapse preview',
                  'Kenar Çubuğu Daraltma Önizleme',
                ),
                subtitle: _copy(
                  context,
                  'Preview collapsed navigation.',
                  'Daraltılmış gezinmeyi önizle.',
                ),
                value: sidebarCollapsed,
                onChanged: onSidebar,
              ),
              _SwitchRow(
                title: _copy(context, 'Animations', 'Animasyonlar'),
                subtitle: _copy(
                  context,
                  'Animate preview transitions.',
                  'Önizleme geçişlerini canlandır.',
                ),
                value: animations,
                onChanged: onAnimations,
              ),
              SizedBox(
                height: 36,
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        _copy(context, 'Font scale', 'Yazı Boyutu Ölçeği'),
                        style: const TextStyle(
                          fontSize: 8.3,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                    SizedBox(
                      width: 230,
                      child: Row(
                        children: [
                          Text(
                            '${(fontScale * 100).round()}%',
                            style: const TextStyle(fontSize: 7.3),
                          ),
                          Expanded(
                            child: Slider(
                              value: fontScale,
                              min: .9,
                              max: 1.5,
                              divisions: 6,
                              onChanged: onScale,
                              onChangeEnd: onScaleEnd,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      );
}

class _SettingRow extends StatelessWidget {
  const _SettingRow({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        height: 35,
        decoration: BoxDecoration(
          border: Border(
            bottom: BorderSide(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Text(
                title,
                style: const TextStyle(fontSize: 8.4, fontWeight: FontWeight.w600),
              ),
            ),
            child,
          ],
        ),
      );
}

class _SwitchRow extends StatelessWidget {
  const _SwitchRow({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.onChanged,
  });

  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 37,
        child: Row(
          children: [
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600),
                  ),
                  Text(
                    subtitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 6.8,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Transform.scale(
              scale: .68,
              child: Switch(value: value, onChanged: onChanged),
            ),
          ],
        ),
      );
}

class _ThemeButton extends StatelessWidget {
  const _ThemeButton({
    required this.label,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: selected
            ? Theme.of(context).colorScheme.surfaceContainerHighest
            : Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(5),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(5),
          child: Container(
            alignment: Alignment.center,
            decoration: BoxDecoration(
              border: Border.all(
                color: selected
                    ? Theme.of(context).colorScheme.outline
                    : Theme.of(context).colorScheme.outlineVariant,
              ),
              borderRadius: BorderRadius.circular(5),
            ),
            child: Text(
              label,
              style: TextStyle(
                fontSize: 7.8,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
          ),
        ),
      );
}

class _PreviewPanel extends StatelessWidget {
  const _PreviewPanel({
    required this.compact,
    required this.dense,
    required this.sidebarCollapsed,
    required this.animations,
    required this.fontScale,
    required this.connected,
    required this.message,
    required this.onSave,
    required this.onReset,
  });

  final bool compact;
  final bool dense;
  final bool sidebarCollapsed;
  final bool animations;
  final double fontScale;
  final bool connected;
  final String? message;
  final VoidCallback onSave;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _card(context),
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _copy(context, 'Workspace & Preview', 'Çalışma Alanı & Önizleme'),
              style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700),
            ),
            Text(
              _copy(
                context,
                'Visual preview only; no runtime telemetry is fabricated.',
                'Yalnızca görsel önizleme; çalışma zamanı telemetrisi üretilmez.',
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 6.8,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 6),
            Expanded(
              child: AnimatedContainer(
                duration: animations
                    ? const Duration(milliseconds: 160)
                    : Duration.zero,
                padding: EdgeInsets.all(compact ? 5 : 8),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerLowest,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
                child: Row(
                  children: [
                    AnimatedContainer(
                      duration: animations
                          ? const Duration(milliseconds: 160)
                          : Duration.zero,
                      width: sidebarCollapsed ? 24 : 52,
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      padding: const EdgeInsets.all(5),
                      child: Column(
                        children: [
                          Row(
                            children: [
                              Icon(
                                Icons.radio_button_checked,
                                size: 9,
                                color: Theme.of(context).colorScheme.onSurfaceVariant,
                              ),
                              if (!sidebarCollapsed) ...[
                                const SizedBox(width: 3),
                                const Expanded(
                                  child: Text(
                                    'ILAIOS',
                                    style: TextStyle(
                                      fontSize: 5.4,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                                ),
                              ],
                            ],
                          ),
                          const SizedBox(height: 7),
                          for (var i = 0; i < 7; i++)
                            Container(
                              margin: EdgeInsets.only(bottom: dense ? 3 : 5),
                              height: 4,
                              width: sidebarCollapsed ? 11 : 34,
                              decoration: BoxDecoration(
                                color: i == 1
                                    ? Theme.of(context).colorScheme.onSurfaceVariant
                                    : Theme.of(context).colorScheme.outlineVariant,
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Column(
                        children: [
                          Row(
                            children: const [
                              Expanded(child: _PreviewBlock()),
                              SizedBox(width: 4),
                              Expanded(child: _PreviewBlock()),
                            ],
                          ),
                          const SizedBox(height: 4),
                          const Expanded(child: _PreviewBlock()),
                          const SizedBox(height: 4),
                          Text(
                            '${(fontScale * 100).round()}%',
                            style: TextStyle(
                              fontSize: 5.5 * fontScale,
                              color: Theme.of(context).colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 6),
            SizedBox(
              height: 28,
              child: FilledButton.icon(
                key: const Key('settings-save'),
                onPressed: onSave,
                icon: const Icon(Icons.save_outlined, size: 13),
                label: Text(
                  _copy(context, 'Apply preferences', 'Değişiklikleri Uygula'),
                  style: const TextStyle(fontSize: 8.2),
                ),
              ),
            ),
            const SizedBox(height: 4),
            SizedBox(
              height: 26,
              child: OutlinedButton.icon(
                onPressed: onReset,
                icon: const Icon(Icons.restore, size: 12),
                label: Text(
                  _copy(context, 'Restore defaults', 'Varsayılanı Geri Yükle'),
                  style: const TextStyle(fontSize: 7.6),
                ),
              ),
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                Icon(
                  connected
                      ? Icons.cloud_done_outlined
                      : Icons.cloud_off_outlined,
                  size: 12,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    message ??
                        (connected
                            ? _copy(
                                context,
                                'Control plane connected',
                                'Kontrol düzlemi bağlı',
                              )
                            : _copy(
                                context,
                                'Control plane offline',
                                'Kontrol düzlemi çevrimdışı',
                              )),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 6.8,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}

class _PreviewBlock extends StatelessWidget {
  const _PreviewBlock();

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(minHeight: 25),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        padding: const EdgeInsets.all(4),
        child: Align(
          alignment: Alignment.topLeft,
          child: Container(
            width: 20,
            height: 3,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
        ),
      );
}

class _AuthorityPanel extends StatelessWidget {
  const _AuthorityPanel({
    required this.section,
    required this.projection,
    required this.identityStatus,
    required this.userSession,
    required this.providers,
  });

  final int section;
  final ControlPlaneProjection projection;
  final String identityStatus;
  final DesktopUserSession? userSession;
  final List<IdentityProviderOption> providers;

  @override
  Widget build(BuildContext context) {
    final titles = _isTr(context)
        ? const <String>[
            'Genel',
            'Görünüm',
            'Hesap',
            'Güvenlik',
            'Sağlayıcılar',
            'Entegrasyonlar',
            'Bildirimler',
            'Gizlilik',
            'Gelişmiş',
          ]
        : const <String>[
            'General',
            'Appearance',
            'Account',
            'Security',
            'Providers',
            'Integrations',
            'Notifications',
            'Privacy',
            'Advanced',
          ];
    final values = <(IconData, String, String)>[
      (
        Icons.dns_outlined,
        _copy(context, 'Control plane', 'Kontrol düzlemi'),
        projection.connected
            ? _copy(context, 'Connected', 'Bağlı')
            : _copy(context, 'Offline', 'Çevrimdışı'),
      ),
      (
        Icons.verified_user_outlined,
        _copy(context, 'Identity', 'Kimlik'),
        identityStatus,
      ),
      (
        Icons.apartment_outlined,
        _copy(context, 'Tenant', 'Kiracı'),
        userSession?.tenantId ?? _copy(context, 'Unavailable', 'Kullanılamıyor'),
      ),
      (
        Icons.account_circle_outlined,
        _copy(context, 'Provider', 'Sağlayıcı'),
        userSession?.providerId ??
            (providers.isEmpty
                ? _copy(context, 'Not configured', 'Yapılandırılmadı')
                : _copy(context, 'Signed out', 'Oturum kapalı')),
      ),
    ];

    return Container(
      decoration: _card(context),
      padding: const EdgeInsets.all(12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            titles[section],
            style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 3),
          Text(
            _copy(
              context,
              'Only authority-backed values are shown. Unsupported screenshot telemetry remains unavailable.',
              'Yalnızca yetkili kaynaktan gelen değerler gösterilir. Desteklenmeyen ekran görüntüsü telemetrisi kullanılamaz durumda kalır.',
            ),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 7.4,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 10),
          for (final value in values)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10),
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerLowest,
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: Theme.of(context).colorScheme.outlineVariant,
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        value.$1,
                        size: 16,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          value.$2,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                            fontSize: 8.3,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Flexible(
                        child: Text(
                          value.$3,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          textAlign: TextAlign.right,
                          style: TextStyle(
                            fontSize: 7.2,
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _RecentChanges extends StatelessWidget {
  const _RecentChanges({required this.changes});
  final List<String> changes;

  @override
  Widget build(BuildContext context) => _BottomCard(
        icon: Icons.history,
        title: _copy(context, 'Recent changes', 'Son Değişiklikler'),
        child: changes.isEmpty
            ? _Empty(
                text: _copy(
                  context,
                  'No local changes in this session.',
                  'Bu oturumda yerel değişiklik yok.',
                ),
              )
            : Column(
                children: [
                  for (final change in changes.take(4))
                    Expanded(
                      child: _StatusLine(
                        icon: Icons.brightness_1,
                        title: change,
                        value: _copy(context, 'This session', 'Bu oturum'),
                      ),
                    ),
                ],
              ),
      );
}

class _PolicyCard extends StatelessWidget {
  const _PolicyCard({required this.projection, required this.identityStatus});
  final ControlPlaneProjection projection;
  final String identityStatus;

  @override
  Widget build(BuildContext context) => _BottomCard(
        icon: Icons.policy_outlined,
        title: _copy(context, 'Policy & authority', 'Politika & Yetki'),
        child: Column(
          children: [
            Expanded(
              child: _StatusLine(
                icon: projection.connected
                    ? Icons.check_circle_outline
                    : Icons.warning_amber_rounded,
                title: _copy(context, 'Control plane', 'Kontrol düzlemi'),
                value: projection.connected
                    ? _copy(context, 'Connected', 'Bağlı')
                    : _copy(context, 'Offline', 'Çevrimdışı'),
              ),
            ),
            Expanded(
              child: _StatusLine(
                icon: Icons.verified_user_outlined,
                title: _copy(context, 'Identity state', 'Kimlik durumu'),
                value: identityStatus,
              ),
            ),
            Expanded(
              child: _StatusLine(
                icon: Icons.shield_outlined,
                title: _copy(context, 'Authority boundary', 'Yetki sınırı'),
                value: _copy(
                  context,
                  'Server/session authoritative',
                  'Sunucu/oturum yetkili',
                ),
              ),
            ),
          ],
        ),
      );
}

class _ProvidersCard extends StatelessWidget {
  const _ProvidersCard({required this.providers, required this.session});
  final List<IdentityProviderOption> providers;
  final DesktopUserSession? session;

  @override
  Widget build(BuildContext context) => _BottomCard(
        icon: Icons.extension_outlined,
        title: _copy(context, 'Connected providers', 'Bağlı Sağlayıcılar'),
        child: providers.isEmpty
            ? _Empty(
                text: _copy(
                  context,
                  'Authoritative integration telemetry is unavailable.',
                  'Yetkili entegrasyon telemetrisi kullanılamıyor.',
                ),
              )
            : Column(
                children: [
                  for (final provider in providers.take(4))
                    Expanded(
                      child: _StatusLine(
                        icon: Icons.cloud_outlined,
                        title: provider.displayName,
                        value: session?.providerId == provider.providerId
                            ? _copy(context, 'Connected', 'Bağlı')
                            : _copy(context, 'Available', 'Kullanılabilir'),
                      ),
                    ),
                ],
              ),
      );
}

class _BottomCard extends StatelessWidget {
  const _BottomCard({
    required this.icon,
    required this.title,
    required this.child,
  });
  final IconData icon;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _card(context),
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 7),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(
                  icon,
                  size: 13,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w700),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Expanded(child: child),
          ],
        ),
      );
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({
    required this.icon,
    required this.title,
    required this.value,
  });
  final IconData icon;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        children: [
          Icon(
            icon,
            size: 11,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
          const SizedBox(width: 5),
          Expanded(
            child: Text(
              title,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 7.4, fontWeight: FontWeight.w600),
            ),
          ),
          const SizedBox(width: 5),
          Flexible(
            child: Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.right,
              style: TextStyle(
                fontSize: 6.8,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      );
}

class _Empty extends StatelessWidget {
  const _Empty({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Center(
        child: Text(
          text,
          textAlign: TextAlign.center,
          maxLines: 3,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 7.4,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );
}

BoxDecoration _card(BuildContext context) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

bool _isTr(BuildContext context) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _copy(BuildContext context, String en, String tr) =>
    _isTr(context) ? tr : en;
