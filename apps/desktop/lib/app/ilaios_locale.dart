import 'dart:convert';
import 'dart:io';
import 'dart:ui';

import 'package:flutter/widgets.dart';

enum IlaiosLocale {
  english('en', 'English'),
  turkish('tr', 'Türkçe');

  const IlaiosLocale(this.code, this.displayName);

  final String code;
  final String displayName;

  static IlaiosLocale fromCode(String? value) =>
      value?.toLowerCase() == 'tr' ? IlaiosLocale.turkish : IlaiosLocale.english;
}

abstract final class IlaiosLocaleStore {
  static IlaiosLocale platformDefault() =>
      PlatformDispatcher.instance.locale.languageCode.toLowerCase() == 'tr'
          ? IlaiosLocale.turkish
          : IlaiosLocale.english;

  static Future<IlaiosLocale> load() async {
    final file = _settingsFile();
    if (file == null || !await file.exists()) return platformDefault();
    try {
      final document = jsonDecode(await file.readAsString());
      if (document is Map<String, dynamic>) {
        return IlaiosLocale.fromCode(document['locale'] as String?);
      }
    } on Object {
      // Corrupt or unreadable preference data must not block Desktop startup.
    }
    return platformDefault();
  }

  static Future<void> save(IlaiosLocale locale) async {
    final file = _settingsFile();
    if (file == null) return;
    await file.parent.create(recursive: true);
    final temporary = File('${file.path}.tmp');
    await temporary.writeAsString(
      jsonEncode(<String, Object?>{
        'schema_version': 1,
        'locale': locale.code,
      }),
      flush: true,
    );
    if (await file.exists()) await file.delete();
    await temporary.rename(file.path);
  }

  static File? _settingsFile() {
    final localAppData = Platform.environment['LOCALAPPDATA']?.trim();
    if (localAppData?.isNotEmpty == true) {
      return File('$localAppData\\ILAIOS\\preferences\\desktop-locale.json');
    }
    final home = Platform.environment['HOME']?.trim();
    if (home?.isNotEmpty == true) {
      return File('$home/.ilaios/preferences/desktop-locale.json');
    }
    return null;
  }
}

class IlaiosLocaleScope extends InheritedWidget {
  const IlaiosLocaleScope({
    required this.locale,
    required this.onChanged,
    required super.child,
    super.key,
  });

  final IlaiosLocale locale;
  final ValueChanged<IlaiosLocale> onChanged;

  static IlaiosLocaleScope of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<IlaiosLocaleScope>();
    assert(scope != null, 'IlaiosLocaleScope is missing above this context');
    return scope!;
  }

  String text(String key) => IlaiosStrings.text(locale, key);

  @override
  bool updateShouldNotify(IlaiosLocaleScope oldWidget) => locale != oldWidget.locale;
}

abstract final class IlaiosStrings {
  static const Map<String, String> _en = <String, String>{
    'nav.home': 'Home',
    'nav.goals': 'Goals',
    'nav.workflows': 'Workflows',
    'nav.agents': 'Agents',
    'nav.liveWorkspace': 'Live Workspace',
    'nav.artifacts': 'Artifacts',
    'nav.approvals': 'Approvals',
    'nav.evidence': 'Evidence',
    'nav.costs': 'Costs',
    'nav.settings': 'Settings',
    'shell.primaryNavigation': 'ILAIOS Desktop primary navigation',
    'shell.navigate': 'Navigate ILAIOS Desktop',
    'shell.tenant': 'Tenant',
    'shell.unavailable': 'Unavailable',
    'shell.regionPlan': 'Region —    Plan —',
    'shell.project': 'Project',
    'shell.search': 'Search',
    'shell.notifications': 'Notifications',
    'shell.language': 'Language',
    'shell.darkTheme': 'Dark theme',
    'shell.identityUnavailable': 'Identity unavailable',
    'shell.signedOut': 'Signed out',
    'shell.authenticated': 'Authenticated',
    'shell.connected': 'Connected',
    'shell.offline': 'Offline',
    'shell.systemHealth': 'System Health',
    'shell.healthy': 'Healthy',
    'shell.workers': 'Workers',
    'shell.queues': 'Queues',
    'shell.eventsPerMinute': 'Events / min',
    'shell.realTime': 'Real-time',
    'language.english': 'English',
    'language.turkish': 'Türkçe',
  };

  static const Map<String, String> _tr = <String, String>{
    'nav.home': 'Ana Sayfa',
    'nav.goals': 'Hedefler',
    'nav.workflows': 'İş Akışları',
    'nav.agents': 'Ajanlar',
    'nav.liveWorkspace': 'Canlı Çalışma Alanı',
    'nav.artifacts': 'Çıktılar',
    'nav.approvals': 'Onaylar',
    'nav.evidence': 'Kanıtlar',
    'nav.costs': 'Maliyetler',
    'nav.settings': 'Ayarlar',
    'shell.primaryNavigation': 'ILAIOS Desktop ana gezinme',
    'shell.navigate': 'ILAIOS Desktop içinde gezin',
    'shell.tenant': 'Kiracı',
    'shell.unavailable': 'Kullanılamıyor',
    'shell.regionPlan': 'Bölge —    Plan —',
    'shell.project': 'Proje',
    'shell.search': 'Ara',
    'shell.notifications': 'Bildirimler',
    'shell.language': 'Dil',
    'shell.darkTheme': 'Koyu tema',
    'shell.identityUnavailable': 'Kimlik kullanılamıyor',
    'shell.signedOut': 'Oturum kapalı',
    'shell.authenticated': 'Kimlik doğrulandı',
    'shell.connected': 'Bağlı',
    'shell.offline': 'Çevrimdışı',
    'shell.systemHealth': 'Sistem Sağlığı',
    'shell.healthy': 'Sağlıklı',
    'shell.workers': 'Çalışanlar',
    'shell.queues': 'Kuyruklar',
    'shell.eventsPerMinute': 'Olay / dk',
    'shell.realTime': 'Gerçek zaman',
    'language.english': 'English',
    'language.turkish': 'Türkçe',
  };

  static String text(IlaiosLocale locale, String key) {
    final catalog = locale == IlaiosLocale.turkish ? _tr : _en;
    return catalog[key] ?? _en[key] ?? key;
  }
}

extension IlaiosLocaleContext on BuildContext {
  IlaiosLocaleScope get ilaiosLocale => IlaiosLocaleScope.of(this);
  String tr(String key) => ilaiosLocale.text(key);
}
