import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';

/// Reference-faithful Settings surface for the approved dark/light Desktop UI.
///
/// The supplied screenshots define presentation only. Runtime connection,
/// identity and provider state remain authority-derived. Unsupported connector,
/// notification and policy telemetry is rendered as unavailable instead of
/// being synthesized from the screenshots.
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
  bool _compactMode = false;
  bool _denseTables = true;
  bool _sidebarPreview = false;
  bool _animations = true;
  double _fontScale = 1;
  int _accentIndex = 0;
  String _dateFormat = 'DD.MM.YYYY HH:mm';
  String? _savedMessage;
  final List<String> _changes = <String>[];

  static const _accents = <Color>[
    IlaiosTheme.coreBlue,
    Color(0xFF34A9E8),
    IlaiosTheme.enterpriseCyan,
    IlaiosTheme.success,
    IlaiosTheme.violet,
    Color(0xFFE52A91),
    Color(0xFFF16522),
    IlaiosTheme.warning,
  ];

  void _record(BuildContext context, String en, String tr) {
    final value = _copy(context, en, tr);
    setState(() {
      _savedMessage = null;
      _changes.insert(0, value);
      if (_changes.length > 4) _changes.removeLast();
    });
  }

  void _selectSection(int value) {
    if (_section == value) return;
    setState(() {
      _section = value;
      _savedMessage = null;
    });
  }

  Future<void> _chooseLanguage() async {
    final current = context.ilaiosLocale.locale;
    final selected = await showDialog<IlaiosLocale>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(_copy(context, 'Choose language', 'Dil seç')),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            RadioListTile<IlaiosLocale>(
              value: IlaiosLocale.english,
              groupValue: current,
              title: const Text('English'),
              onChanged: (value) => Navigator.of(dialogContext).pop(value),
            ),
            RadioListTile<IlaiosLocale>(
              value: IlaiosLocale.turkish,
              groupValue: current,
              title: const Text('Türkçe'),
              onChanged: (value) => Navigator.of(dialogContext).pop(value),
            ),
          ],
        ),
      ),
    );
    if (selected == null || selected == current || !mounted) return;
    context.ilaiosLocale.onChanged(selected);
    _record(context, 'Language changed', 'Dil değiştirildi');
  }

  void _changeTheme(ThemeMode mode) {
    widget.onThemeModeChanged?.call(mode);
    _record(
      context,
      'Theme changed to ${mode.name}',
      'Tema ${mode == ThemeMode.dark ? 'Koyu' : mode == ThemeMode.light ? 'Açık' : 'Sistem'} olarak değiştirildi',
    );
  }

  void _save() {
    setState(() {
      _savedMessage = _copy(
        context,
        'Local appearance preferences applied for this Desktop session.',
        'Yerel görünüm tercihleri bu Desktop oturumuna uygulandı.',
      );
    });
  }

  void _reset() {
    setState(() {
      _compactMode = false;
      _denseTables = true;
      _sidebarPreview = false;
      _animations = true;
      _fontScale = 1;
      _accentIndex = 0;
      _dateFormat = 'DD.MM.YYYY HH:mm';
      _savedMessage = null;
    });
    widget.onThemeModeChanged?.call(ThemeMode.system);
    _record(context, 'Appearance defaults restored', 'Görünüm varsayılanları geri yüklendi');
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      key: const Key('reference-settings-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Header(isDark: isDark),
          const SizedBox(height: 9),
          SizedBox(
            key: const Key('settings-summary-strip'),
            height: 76,
            child: Row(
              children: [
                Expanded(
                  child: _SummaryCard(
                    key: const Key('settings-storage-action'),
                    icon: Icons.settings_outlined,
                    title: _copy(context, 'General', 'Genel'),
                    subtitle: _copy(context, 'Core preferences', 'Temel ayarlar'),
                    status: _copy(context, 'Local', 'Yerel'),
                    accent: IlaiosTheme.coreBlue,
                    selected: _section == 0,
                    onTap: () => _selectSection(0),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    key: const Key('settings-appearance-action'),
                    icon: Icons.palette_outlined,
                    title: _copy(context, 'Appearance', 'Görünüm'),
                    subtitle: _copy(context, 'Theme and UI', 'Arayüz tercihleri'),
                    status: _copy(context, 'Active', 'Aktif'),
                    accent: IlaiosTheme.violet,
                    selected: _section == 1,
                    onTap: () => _selectSection(1),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    key: const Key('settings-notifications-action'),
                    icon: Icons.notifications_none_outlined,
                    title: _copy(context, 'Notifications', 'Bildirimler'),
                    subtitle: _copy(context, 'Runtime preferences', 'Uyarı tercihleri'),
                    status: _copy(context, 'Unavailable', 'Kullanılamıyor'),
                    accent: IlaiosTheme.warning,
                    selected: _section == 6,
                    onTap: () => _selectSection(6),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    key: const Key('settings-diagnostics-action'),
                    icon: Icons.shield_outlined,
                    title: _copy(context, 'Security', 'Güvenlik'),
                    subtitle: _copy(context, 'Identity boundary', 'Erişim ve kimlik'),
                    status: widget.projection.connected
                        ? _copy(context, 'Connected', 'Bağlı')
                        : _copy(context, 'Offline', 'Çevrimdışı'),
                    accent: IlaiosTheme.success,
                    selected: _section == 3,
                    onTap: () => _selectSection(3),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    icon: Icons.cloud_outlined,
                    title: _copy(context, 'Providers', 'Sağlayıcılar'),
                    subtitle: _copy(context, 'Identity providers', 'Bağlı servisler'),
                    status: widget.providers.isEmpty
                        ? _copy(context, 'None', 'Yok')
                        : '${widget.providers.length}',
                    accent: IlaiosTheme.enterpriseCyan,
                    selected: _section == 4,
                    onTap: () => _selectSection(4),
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: _SummaryCard(
                    icon: Icons.extension_outlined,
                    title: _copy(context, 'Integrations', 'Entegrasyonlar'),
                    subtitle: _copy(context, 'External connections', 'Harici bağlantılar'),
                    status: _copy(context, 'Unavailable', 'Kullanılamıyor'),
                    accent: IlaiosTheme.violet,
                    selected: _section == 5,
                    onTap: () => _selectSection(5),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 9),
          SizedBox(
            height: 374,
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                SizedBox(
                  key: const Key('settings-left-navigation'),
                  width: 178,
                  child: _SectionNavigation(
                    selected: _section,
                    onSelected: _selectSection,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _section == 1
                      ? _AppearancePanel(
                          compactMode: _compactMode,
                          denseTables: _denseTables,
                          sidebarPreview: _sidebarPreview,
                          animations: _animations,
                          fontScale: _fontScale,
                          accentIndex: _accentIndex,
                          accents: _accents,
                          dateFormat: _dateFormat,
                          themeMode: widget.themeMode,
                          onChooseLanguage: _chooseLanguage,
                          onThemeChanged: _changeTheme,
                          onAccentChanged: (value) {
                            setState(() => _accentIndex = value);
                            _record(context, 'Accent preview changed', 'Vurgu önizlemesi değiştirildi');
                          },
                          onCompactChanged: (value) {
                            setState(() => _compactMode = value);
                            _record(context, 'Compact mode updated', 'Kompakt mod güncellendi');
                          },
                          onDenseChanged: (value) {
                            setState(() => _denseTables = value);
                            _record(context, 'Dense table preference updated', 'Yoğun tablo tercihi güncellendi');
                          },
                          onSidebarChanged: (value) {
                            setState(() => _sidebarPreview = value);
                            _record(context, 'Sidebar preview updated', 'Kenar çubuğu önizlemesi güncellendi');
                          },
                          onAnimationsChanged: (value) {
                            setState(() => _animations = value);
                            _record(context, 'Animation preference updated', 'Animasyon tercihi güncellendi');
                          },
                          onScaleChanged: (value) => setState(() => _fontScale = value),
                          onScaleEnd: (_) => _record(context, 'Font scale updated', 'Yazı ölçeği güncellendi'),
                          onDateFormatChanged: (value) {
                            if (value == null) return;
                            setState(() => _dateFormat = value);
                            _record(context, 'Date format updated', 'Tarih biçimi güncellendi');
                          },
                        )
                      : _SectionPlaceholder(
                          section: _section,
                          projection: widget.projection,
                          identityStatus: widget.identityStatus,
                          userSession: widget.userSession,
                          providers: widget.providers,
                        ),
                ),
                const SizedBox(width: 10),
                SizedBox(
                  key: const Key('settings-preview-panel'),
                  width: 330,
                  child: _PreviewPanel(
                    compact: _compactMode,
                    dense: _denseTables,
                    sidebarCollapsed: _sidebarPreview,
                    animations: _animations,
                    fontScale: _fontScale,
                    accent: _accents[_accentIndex],
                    savedMessage: _savedMessage,
                    connected: widget.projection.connected,
                    onSave: _save,
                    onReset: _reset,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 9),
          Expanded(
            child: Row(
              key: const Key('settings-bottom-grid'),
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Expanded(child: _RecentChanges(changes: _changes)),
                const SizedBox(width: 10),
                Expanded(
                  child: _PolicyStatus(
                    projection: widget.projection,
                    identityStatus: widget.identityStatus,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: _ConnectedProviders(
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
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.isDark});
  final bool isDark;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 48,
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
              style: TextStyle(
                fontSize: 9.5,
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
    required this.accent,
    required this.selected,
    required this.onTap,
    super.key,
  });

  final IconData icon;
  final String title;
  final String subtitle;
  final String status;
  final Color accent;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: selected
            ? accent.withValues(alpha: .08)
            : Theme.of(context).colorScheme.surfaceContainerLowest,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(8),
          side: BorderSide(
            color: selected
                ? accent.withValues(alpha: .55)
                : Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
            child: Row(
              children: [
                Icon(icon, size: 25, color: accent),
                const SizedBox(width: 9),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        title,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w700),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        subtitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 8,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 3),
                      Text(
                        status,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 8.1, color: accent, fontWeight: FontWeight.w600),
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

  static const _icons = <IconData>[
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

  @override
  Widget build(BuildContext context) {
    final labels = _isTr(context)
        ? const <String>['Genel', 'Görünüm', 'Hesap', 'Güvenlik', 'Sağlayıcılar', 'Entegrasyonlar', 'Bildirimler', 'Gizlilik', 'Gelişmiş']
        : const <String>['General', 'Appearance', 'Account', 'Security', 'Providers', 'Integrations', 'Notifications', 'Privacy', 'Advanced'];
    return Container(
      decoration: _cardDecoration(context),
      padding: const EdgeInsets.all(6),
      child: Column(
        children: [
          for (var i = 0; i < labels.length; i++)
            Expanded(
              child: Padding(
                padding: const EdgeInsets.only(bottom: 2),
                child: Material(
                  color: selected == i
                      ? IlaiosTheme.coreBlue.withValues(alpha: .14)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(5),
                  child: InkWell(
                    onTap: () => onSelected(i),
                    borderRadius: BorderRadius.circular(5),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 9),
                      child: Row(
                        children: [
                          Icon(
                            _icons[i],
                            size: 15,
                            color: selected == i
                                ? IlaiosTheme.coreBlue
                                : Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              labels[i],
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 9.2,
                                fontWeight: selected == i ? FontWeight.w600 : FontWeight.w500,
                                color: selected == i
                                    ? IlaiosTheme.coreBlue
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
    required this.compactMode,
    required this.denseTables,
    required this.sidebarPreview,
    required this.animations,
    required this.fontScale,
    required this.accentIndex,
    required this.accents,
    required this.dateFormat,
    required this.themeMode,
    required this.onChooseLanguage,
    required this.onThemeChanged,
    required this.onAccentChanged,
    required this.onCompactChanged,
    required this.onDenseChanged,
    required this.onSidebarChanged,
    required this.onAnimationsChanged,
    required this.onScaleChanged,
    required this.onScaleEnd,
    required this.onDateFormatChanged,
  });

  final bool compactMode;
  final bool denseTables;
  final bool sidebarPreview;
  final bool animations;
  final double fontScale;
  final int accentIndex;
  final List<Color> accents;
  final String dateFormat;
  final ThemeMode themeMode;
  final VoidCallback onChooseLanguage;
  final ValueChanged<ThemeMode> onThemeChanged;
  final ValueChanged<int> onAccentChanged;
  final ValueChanged<bool> onCompactChanged;
  final ValueChanged<bool> onDenseChanged;
  final ValueChanged<bool> onSidebarChanged;
  final ValueChanged<bool> onAnimationsChanged;
  final ValueChanged<double> onScaleChanged;
  final ValueChanged<double> onScaleEnd;
  final ValueChanged<String?> onDateFormatChanged;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('settings-appearance-panel'),
        decoration: _cardDecoration(context),
        padding: const EdgeInsets.fromLTRB(13, 10, 13, 10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _copy(context, 'Appearance', 'Görünüm'),
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
            ),
            Text(
              _copy(context, 'Customize Desktop appearance and preview preferences.', 'Arayüz görünümünü ve önizleme tercihlerinizi özelleştirin.'),
              style: TextStyle(fontSize: 7.7, color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 7),
            _SettingLine(
              title: _copy(context, 'Language', 'Dil'),
              child: Material(
                key: const Key('settings-language-action'),
                color: Theme.of(context).colorScheme.surfaceContainerLowest,
                borderRadius: BorderRadius.circular(5),
                child: InkWell(
                  onTap: onChooseLanguage,
                  borderRadius: BorderRadius.circular(5),
                  child: Container(
                    width: 238,
                    height: 29,
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                      borderRadius: BorderRadius.circular(5),
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(
                            context.ilaiosLocale.locale.displayName,
                            style: const TextStyle(fontSize: 8.8),
                          ),
                        ),
                        const Icon(Icons.keyboard_arrow_down, size: 15),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            _SettingLine(
              title: _copy(context, 'Theme', 'Tema'),
              child: SizedBox(
                width: 238,
                height: 29,
                child: Row(
                  children: [
                    Expanded(
                      child: _SegmentButton(
                        key: const Key('settings-theme-dark'),
                        label: _copy(context, 'Dark', 'Koyu'),
                        selected: themeMode == ThemeMode.dark,
                        onTap: () => onThemeChanged(ThemeMode.dark),
                      ),
                    ),
                    const SizedBox(width: 3),
                    Expanded(
                      child: _SegmentButton(
                        key: const Key('settings-theme-light'),
                        label: _copy(context, 'Light', 'Açık'),
                        selected: themeMode == ThemeMode.light,
                        onTap: () => onThemeChanged(ThemeMode.light),
                      ),
                    ),
                    const SizedBox(width: 3),
                    Expanded(
                      child: _SegmentButton(
                        key: const Key('settings-theme-system'),
                        label: _copy(context, 'System', 'Sistem'),
                        selected: themeMode == ThemeMode.system,
                        onTap: () => onThemeChanged(ThemeMode.system),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            _SettingLine(
              title: _copy(context, 'Accent preview', 'Vurgu Önizlemesi'),
              subtitle: _copy(context, 'Canonical brand colors only.', 'Yalnızca kanonik marka renkleri.'),
              child: SizedBox(
                width: 238,
                height: 28,
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    for (var i = 0; i < accents.length; i++)
                      InkWell(
                        onTap: () => onAccentChanged(i),
                        borderRadius: BorderRadius.circular(20),
                        child: Container(
                          width: 22,
                          height: 22,
                          decoration: BoxDecoration(
                            color: accents[i],
                            shape: BoxShape.circle,
                            border: Border.all(
                              color: i == accentIndex
                                  ? Theme.of(context).colorScheme.onSurface
                                  : Colors.transparent,
                              width: 2,
                            ),
                          ),
                          child: i == accentIndex
                              ? const Icon(Icons.check, size: 13, color: Colors.white)
                              : null,
                        ),
                      ),
                  ],
                ),
              ),
            ),
            _ToggleLine(
              title: _copy(context, 'Compact mode', 'Kompakt Mod'),
              subtitle: _copy(context, 'Use tighter spacing in the preview.', 'Önizlemede daha sıkı aralık kullan.'),
              value: compactMode,
              onChanged: onCompactChanged,
            ),
            _ToggleLine(
              title: _copy(context, 'Dense table mode', 'Yoğun Tablo Modu'),
              subtitle: _copy(context, 'Prefer denser table rows.', 'Daha yoğun tablo satırlarını tercih et.'),
              value: denseTables,
              onChanged: onDenseChanged,
            ),
            _ToggleLine(
              title: _copy(context, 'Sidebar collapse preview', 'Kenar Çubuğu Daraltma Önizleme'),
              subtitle: _copy(context, 'Preview collapsed navigation.', 'Daraltılmış gezinmeyi önizle.'),
              value: sidebarPreview,
              onChanged: onSidebarChanged,
            ),
            _ToggleLine(
              title: _copy(context, 'Animations', 'Animasyonlar'),
              subtitle: _copy(context, 'Animate preview transitions.', 'Önizleme geçişlerini canlandır.'),
              value: animations,
              onChanged: onAnimationsChanged,
            ),
            SizedBox(
              height: 42,
              child: Row(
                children: [
                  Expanded(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(_copy(context, 'Font scale', 'Yazı Boyutu Ölçeği'), style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w600)),
                        Text(_copy(context, 'Preview text scaling.', 'Önizleme yazı ölçeği.'), style: TextStyle(fontSize: 7.1, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                      ],
                    ),
                  ),
                  SizedBox(
                    width: 238,
                    child: Row(
                      children: [
                        Text('${(fontScale * 100).round()}%', style: const TextStyle(fontSize: 7.7)),
                        Expanded(
                          child: Slider(
                            value: fontScale,
                            min: .9,
                            max: 1.5,
                            divisions: 6,
                            onChanged: onScaleChanged,
                            onChangeEnd: onScaleEnd,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            _SettingLine(
              title: _copy(context, 'Date & time format', 'Tarih & Saat Formatı'),
              child: SizedBox(
                width: 238,
                height: 29,
                child: DropdownButtonFormField<String>(
                  value: dateFormat,
                  isDense: true,
                  decoration: const InputDecoration(contentPadding: EdgeInsets.symmetric(horizontal: 9, vertical: 4)),
                  style: TextStyle(fontSize: 8.2, color: Theme.of(context).colorScheme.onSurface),
                  items: const [
                    DropdownMenuItem(value: 'DD.MM.YYYY HH:mm', child: Text('DD.MM.YYYY HH:mm')),
                    DropdownMenuItem(value: 'YYYY-MM-DD HH:mm', child: Text('YYYY-MM-DD HH:mm')),
                  ],
                  onChanged: onDateFormatChanged,
                ),
              ),
            ),
          ],
        ),
      );
}

class _SettingLine extends StatelessWidget {
  const _SettingLine({required this.title, required this.child, this.subtitle});
  final String title;
  final String? subtitle;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        height: subtitle == null ? 37 : 43,
        decoration: BoxDecoration(
          border: Border(bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant)),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w600)),
                  if (subtitle != null)
                    Text(subtitle!, style: TextStyle(fontSize: 7, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
            child,
          ],
        ),
      );
}

class _ToggleLine extends StatelessWidget {
  const _ToggleLine({required this.title, required this.subtitle, required this.value, required this.onChanged});
  final String title;
  final String subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 39,
        child: Row(
          children: [
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w600)),
                  Text(subtitle, style: TextStyle(fontSize: 7, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ),
            ),
            Transform.scale(scale: .72, child: Switch(value: value, onChanged: onChanged)),
          ],
        ),
      );
}

class _SegmentButton extends StatelessWidget {
  const _SegmentButton({required this.label, required this.selected, required this.onTap, super.key});
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Material(
        color: selected
            ? IlaiosTheme.coreBlue
            : Theme.of(context).colorScheme.surfaceContainerLowest,
        borderRadius: BorderRadius.circular(5),
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(5),
          child: Container(
            alignment: Alignment.center,
            decoration: BoxDecoration(
              border: Border.all(
                color: selected ? IlaiosTheme.coreBlue : Theme.of(context).colorScheme.outlineVariant,
              ),
              borderRadius: BorderRadius.circular(5),
            ),
            child: Text(
              label,
              style: TextStyle(fontSize: 8.2, color: selected ? Colors.white : Theme.of(context).colorScheme.onSurface),
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
    required this.accent,
    required this.savedMessage,
    required this.connected,
    required this.onSave,
    required this.onReset,
  });

  final bool compact;
  final bool dense;
  final bool sidebarCollapsed;
  final bool animations;
  final double fontScale;
  final Color accent;
  final String? savedMessage;
  final bool connected;
  final VoidCallback onSave;
  final VoidCallback onReset;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _cardDecoration(context),
        padding: const EdgeInsets.all(11),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(_copy(context, 'Workspace & Preview', 'Çalışma Alanı & Önizleme'), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text(_copy(context, 'Visual preview only; no runtime telemetry is fabricated.', 'Yalnızca görsel önizleme; çalışma zamanı telemetrisi üretilmez.'), style: TextStyle(fontSize: 7.2, color: Theme.of(context).colorScheme.onSurfaceVariant)),
            const SizedBox(height: 8),
            Expanded(
              child: AnimatedContainer(
                duration: animations ? const Duration(milliseconds: 180) : Duration.zero,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerLowest,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                ),
                padding: EdgeInsets.all(compact ? 6 : 9),
                child: Row(
                  children: [
                    AnimatedContainer(
                      duration: animations ? const Duration(milliseconds: 180) : Duration.zero,
                      width: sidebarCollapsed ? 25 : 54,
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(4),
                      ),
                      padding: const EdgeInsets.all(5),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Icon(Icons.radio_button_checked, size: 10, color: accent),
                              if (!sidebarCollapsed) ...[
                                const SizedBox(width: 3),
                                const Expanded(child: Text('ILAIOS', style: TextStyle(fontSize: 5.7, fontWeight: FontWeight.w700))),
                              ],
                            ],
                          ),
                          const SizedBox(height: 8),
                          for (var i = 0; i < 7; i++)
                            Container(
                              margin: EdgeInsets.only(bottom: dense ? 4 : 6),
                              height: 4,
                              width: sidebarCollapsed ? 12 : 35,
                              decoration: BoxDecoration(
                                color: i == 1 ? accent.withValues(alpha: .65) : Theme.of(context).colorScheme.outlineVariant,
                                borderRadius: BorderRadius.circular(3),
                              ),
                            ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Column(
                        children: [
                          Row(
                            children: [
                              Expanded(child: _PreviewBlock(height: compact ? 22 : 26, accent: accent)),
                              const SizedBox(width: 4),
                              Expanded(child: _PreviewBlock(height: compact ? 22 : 26, accent: accent)),
                            ],
                          ),
                          const SizedBox(height: 5),
                          Expanded(child: _PreviewBlock(height: double.infinity, accent: accent)),
                          const SizedBox(height: 5),
                          Row(
                            children: [
                              Expanded(child: _PreviewBlock(height: compact ? 20 : 24, accent: accent)),
                              const SizedBox(width: 4),
                              Expanded(child: _PreviewBlock(height: compact ? 20 : 24, accent: accent)),
                            ],
                          ),
                          const SizedBox(height: 4),
                          Text('${(fontScale * 100).round()}%', style: TextStyle(fontSize: 5.8 * fontScale, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 7),
            SizedBox(
              height: 29,
              child: FilledButton.icon(
                key: const Key('settings-save'),
                onPressed: onSave,
                icon: const Icon(Icons.save_outlined, size: 14),
                label: Text(_copy(context, 'Apply preferences', 'Değişiklikleri Uygula'), style: const TextStyle(fontSize: 8.7)),
              ),
            ),
            const SizedBox(height: 5),
            SizedBox(
              height: 27,
              child: OutlinedButton.icon(
                onPressed: onReset,
                icon: const Icon(Icons.restore, size: 13),
                label: Text(_copy(context, 'Restore defaults', 'Varsayılanı Geri Yükle'), style: const TextStyle(fontSize: 8)),
              ),
            ),
            const SizedBox(height: 5),
            Row(
              children: [
                Icon(connected ? Icons.cloud_done_outlined : Icons.cloud_off_outlined, size: 13, color: connected ? IlaiosTheme.success : IlaiosTheme.warning),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    savedMessage ?? (connected ? _copy(context, 'Control plane connected', 'Kontrol düzlemi bağlı') : _copy(context, 'Control plane offline', 'Kontrol düzlemi çevrimdışı')),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 7.2, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}

class _PreviewBlock extends StatelessWidget {
  const _PreviewBlock({required this.height, required this.accent});
  final double height;
  final Color accent;

  @override
  Widget build(BuildContext context) => Container(
        height: height,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        padding: const EdgeInsets.all(4),
        child: Align(
          alignment: Alignment.topLeft,
          child: Container(
            width: 22,
            height: 3,
            decoration: BoxDecoration(color: accent.withValues(alpha: .75), borderRadius: BorderRadius.circular(2)),
          ),
        ),
      );
}

class _SectionPlaceholder extends StatelessWidget {
  const _SectionPlaceholder({
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
        ? const <String>['Genel', 'Görünüm', 'Hesap', 'Güvenlik', 'Sağlayıcılar', 'Entegrasyonlar', 'Bildirimler', 'Gizlilik', 'Gelişmiş']
        : const <String>['General', 'Appearance', 'Account', 'Security', 'Providers', 'Integrations', 'Notifications', 'Privacy', 'Advanced'];
    final items = <(IconData, String, String)>[
      (Icons.dns_outlined, _copy(context, 'Control plane', 'Kontrol düzlemi'), projection.connected ? _copy(context, 'Connected', 'Bağlı') : _copy(context, 'Offline', 'Çevrimdışı')),
      (Icons.verified_user_outlined, _copy(context, 'Identity', 'Kimlik'), identityStatus),
      (Icons.apartment_outlined, _copy(context, 'Tenant', 'Kiracı'), userSession?.tenantId ?? _copy(context, 'Unavailable', 'Kullanılamıyor')),
      (Icons.account_circle_outlined, _copy(context, 'Provider', 'Sağlayıcı'), userSession?.providerId ?? (providers.isEmpty ? _copy(context, 'Not configured', 'Yapılandırılmadı') : _copy(context, 'Signed out', 'Oturum kapalı'))),
    ];
    return Container(
      decoration: _cardDecoration(context),
      padding: const EdgeInsets.all(14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(titles[section], style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          Text(
            _copy(context, 'Only authority-backed values are shown on this section. Unsupported screenshot telemetry remains unavailable.', 'Bu bölümde yalnızca yetkili kaynaktan gelen değerler gösterilir. Desteklenmeyen ekran görüntüsü telemetrisi kullanılamaz durumda kalır.'),
            style: TextStyle(fontSize: 7.8, color: Theme.of(context).colorScheme.onSurfaceVariant),
          ),
          const SizedBox(height: 14),
          for (final item in items)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Container(
                height: 50,
                padding: const EdgeInsets.symmetric(horizontal: 11),
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerLowest,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                ),
                child: Row(
                  children: [
                    Icon(item.$1, size: 17, color: IlaiosTheme.coreBlue),
                    const SizedBox(width: 10),
                    Expanded(child: Text(item.$2, style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w600))),
                    Flexible(
                      child: Text(item.$3, maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right, style: TextStyle(fontSize: 7.7, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                    ),
                  ],
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
            ? _EmptyLine(text: _copy(context, 'No local changes in this session.', 'Bu oturumda yerel değişiklik yok.'))
            : Column(
                children: [
                  for (final change in changes.take(4))
                    _StatusLine(icon: Icons.brightness_1, color: IlaiosTheme.coreBlue, title: change, value: _copy(context, 'This session', 'Bu oturum')),
                ],
              ),
      );
}

class _PolicyStatus extends StatelessWidget {
  const _PolicyStatus({required this.projection, required this.identityStatus});
  final ControlPlaneProjection projection;
  final String identityStatus;

  @override
  Widget build(BuildContext context) => _BottomCard(
        icon: Icons.policy_outlined,
        title: _copy(context, 'Policy & authority', 'Politika & Yetki'),
        child: Column(
          children: [
            _StatusLine(
              icon: projection.connected ? Icons.check_circle_outline : Icons.warning_amber_rounded,
              color: projection.connected ? IlaiosTheme.success : IlaiosTheme.warning,
              title: _copy(context, 'Control plane', 'Kontrol düzlemi'),
              value: projection.connected ? _copy(context, 'Connected', 'Bağlı') : _copy(context, 'Offline', 'Çevrimdışı'),
            ),
            _StatusLine(
              icon: Icons.verified_user_outlined,
              color: IlaiosTheme.enterpriseCyan,
              title: _copy(context, 'Identity state', 'Kimlik durumu'),
              value: identityStatus,
            ),
            _StatusLine(
              icon: Icons.shield_outlined,
              color: IlaiosTheme.violet,
              title: _copy(context, 'Authority boundary', 'Yetki sınırı'),
              value: _copy(context, 'Server/session authoritative', 'Sunucu/oturum yetkili'),
            ),
          ],
        ),
      );
}

class _ConnectedProviders extends StatelessWidget {
  const _ConnectedProviders({required this.providers, required this.session});
  final List<IdentityProviderOption> providers;
  final DesktopUserSession? session;

  @override
  Widget build(BuildContext context) => _BottomCard(
        icon: Icons.extension_outlined,
        title: _copy(context, 'Connected providers', 'Bağlı Sağlayıcılar'),
        child: providers.isEmpty
            ? _EmptyLine(text: _copy(context, 'Authoritative integration telemetry is unavailable.', 'Yetkili entegrasyon telemetrisi kullanılamıyor.'))
            : Column(
                children: [
                  for (final provider in providers.take(4))
                    _StatusLine(
                      icon: Icons.cloud_outlined,
                      color: session?.providerId == provider.providerId ? IlaiosTheme.success : IlaiosTheme.enterpriseCyan,
                      title: provider.displayName,
                      value: session?.providerId == provider.providerId
                          ? _copy(context, 'Connected', 'Bağlı')
                          : _copy(context, 'Available', 'Kullanılabilir'),
                    ),
                ],
              ),
      );
}

class _BottomCard extends StatelessWidget {
  const _BottomCard({required this.icon, required this.title, required this.child});
  final IconData icon;
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _cardDecoration(context),
        padding: const EdgeInsets.fromLTRB(11, 9, 11, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Icon(icon, size: 14, color: IlaiosTheme.coreBlue),
                const SizedBox(width: 6),
                Expanded(child: Text(title, style: const TextStyle(fontSize: 9.8, fontWeight: FontWeight.w700))),
              ],
            ),
            const SizedBox(height: 6),
            Expanded(child: child),
          ],
        ),
      );
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({required this.icon, required this.color, required this.title, required this.value});
  final IconData icon;
  final Color color;
  final String title;
  final String value;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 28,
        child: Row(
          children: [
            Icon(icon, size: 12, color: color),
            const SizedBox(width: 6),
            Expanded(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.8, fontWeight: FontWeight.w600))),
            const SizedBox(width: 6),
            Flexible(child: Text(value, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.right, style: TextStyle(fontSize: 7.1, color: Theme.of(context).colorScheme.onSurfaceVariant))),
          ],
        ),
      );
}

class _EmptyLine extends StatelessWidget {
  const _EmptyLine({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Center(
        child: Text(text, textAlign: TextAlign.center, style: TextStyle(fontSize: 7.8, color: Theme.of(context).colorScheme.onSurfaceVariant)),
      );
}

BoxDecoration _cardDecoration(BuildContext context) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLow,
      borderRadius: BorderRadius.circular(8),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;
String _copy(BuildContext context, String en, String tr) => _isTr(context) ? tr : en;
