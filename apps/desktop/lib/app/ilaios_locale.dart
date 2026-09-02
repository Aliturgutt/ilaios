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
    if (await temporary.exists()) await temporary.delete();
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
    'nav.li': 'Li',
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
    'shell.eventsPerMinute': 'Events',
    'shell.realTime': 'Real-time',
    'language.english': 'English',
    'language.turkish': 'Türkçe',
    'common.unavailable': 'Unavailable',
    'common.notConfigured': 'Not configured',
    'common.signedOut': 'Signed out',
    'costs.title': 'Costs & Usage',
    'costs.totalUsd': 'Total cost (USD)',
    'costs.totalMinor': 'Total cost (minor units)',
    'costs.budgetUsd': 'Budget (USD)',
    'costs.budgetCapMinor': 'Budget/cap (minor units)',
    'costs.tokenUsage': 'Token usage',
    'costs.gpuRuntime': 'GPU/runtime duration',
    'costs.providerModel': 'Provider/model usage',
    'costs.noTelemetry': 'The current authenticated Desktop projection does not expose authoritative cost telemetry. No synthetic cost, currency conversion, token, GPU, or provider usage values are shown.',
    'settings.title': 'Settings',
    'settings.controlPlane': 'Control plane',
    'settings.identity': 'Identity',
    'settings.tenant': 'Tenant',
    'settings.principal': 'Principal',
    'settings.provider': 'Provider',
    'settings.locale': 'Locale',
    'settings.systemLocale': 'System locale',
    'settings.theme': 'Theme',
    'settings.dark': 'Dark',
    'settings.authorityNote': 'Tenant authority, governance, execution and identity verification remain backend/session authoritative. This surface does not widen client authority.',
    'goals.title': 'What do you want ILAIOS to build?',
    'goals.subtitle': 'Describe the finished outcome. ILAIOS records the intent as an authoritative goal and durable job; provider, worker and privileged execution authority remain server-controlled.',
    'goals.example': 'Example: Build a premium website for my furniture company and deliver the finished result.',
    'goals.submitting': 'Submitting…',
    'goals.startPrompt': 'Start with one prompt',
    'goals.accepted': 'Accepted by the control plane',
    'goals.goal': 'Goal',
    'goals.job': 'Job',
    'goals.authoritativeState': 'Authoritative state',
    'goals.submissionNote': 'Desktop does not treat submission as completion. Progress, governance, evidence and final artifacts must be proven by the authoritative runtime.',
    'goals.account': 'Account',
    'goals.provider': 'Provider',
    'goals.signingOut': 'Signing out…',
    'goals.signOut': 'Sign out',
    'goals.signInNote': 'Sign in before submitting governed work. Authentication opens in your browser; raw identity-provider tokens are kept out of the Flutter UI.',
    'goals.signingIn': 'Signing in…',
    'goals.continueWith': 'Continue with',
    'goals.controlPlaneUnavailable': 'Authoritative control plane is unavailable',
    'goals.signInRequired': 'Sign in to submit governed work',
    'referenceAssets.dock': 'Reference images',
    'videoReferences.dock': 'Reference images',
    'videoReferences.title': 'Reference images',
    'videoReferences.formats': 'JPEG / PNG / WebP · 10 MiB each · 100 MiB total',
    'videoReferences.add': 'Add images',
    'videoReferences.loading': 'Loading…',
    'videoReferences.optional': 'Optional: add subject, product, style, environment, logo or storyboard references for Web Factory or Video Factory.',
    'videoReferences.privacy': 'Reference images are never published as public URLs. Web Factory embeds admitted images only into the generated local source; Video Factory may send normalized copies to the configured free vision provider for visual conditioning.',
    'videoReferences.dialogTitle': 'Reference image instructions',
    'videoReferences.role': 'Role',
    'videoReferences.howUse': 'How should Web Factory or Video Factory use this image?',
    'videoReferences.hint': 'Example: Keep this product shape, materials, colors and logo placement consistent.',
    'videoReferences.cancel': 'Cancel',
    'videoReferences.save': 'Save',
    'videoReferences.moveLeft': 'Move left',
    'videoReferences.instructions': 'Instructions',
    'videoReferences.remove': 'Remove',
    'videoReferences.role.style': 'Style',
    'videoReferences.role.subject': 'Subject',
    'videoReferences.role.product': 'Product',
    'videoReferences.role.environment': 'Environment',
    'videoReferences.role.logo': 'Logo',
    'videoReferences.role.storyboard': 'Storyboard',
    'videoReferences.role.other': 'Other',
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
    'nav.li': 'Li',
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
    'shell.systemHealth': 'Sistem',
    'shell.healthy': 'İyi',
    'shell.workers': 'Ajan',
    'shell.queues': 'Kuyruk',
    'shell.eventsPerMinute': 'Olaylar',
    'shell.realTime': 'Canlı',
    'language.english': 'English',
    'language.turkish': 'Türkçe',
    'common.unavailable': 'Kullanılamıyor',
    'common.notConfigured': 'Yapılandırılmadı',
    'common.signedOut': 'Oturum kapalı',
    'costs.title': 'Maliyetler ve Kullanım',
    'costs.totalUsd': 'Toplam maliyet (USD)',
    'costs.totalMinor': 'Toplam maliyet (alt birim)',
    'costs.budgetUsd': 'Bütçe (USD)',
    'costs.budgetCapMinor': 'Bütçe/üst sınır (alt birim)',
    'costs.tokenUsage': 'Token kullanımı',
    'costs.gpuRuntime': 'GPU/çalışma süresi',
    'costs.providerModel': 'Sağlayıcı/model kullanımı',
    'costs.noTelemetry': 'Mevcut kimliği doğrulanmış Desktop projeksiyonu yetkili maliyet telemetrisi sunmuyor. Sentetik maliyet, para birimi dönüşümü, token, GPU veya sağlayıcı kullanım değerleri gösterilmez.',
    'settings.title': 'Ayarlar',
    'settings.controlPlane': 'Kontrol düzlemi',
    'settings.identity': 'Kimlik',
    'settings.tenant': 'Kiracı',
    'settings.principal': 'Asıl kimlik',
    'settings.provider': 'Sağlayıcı',
    'settings.locale': 'Dil',
    'settings.systemLocale': 'Sistem dili',
    'settings.theme': 'Tema',
    'settings.dark': 'Koyu',
    'settings.authorityNote': 'Kiracı yetkisi, yönetişim, yürütme ve kimlik doğrulama arka uç/oturum tarafından belirlenmeye devam eder. Bu ekran istemci yetkisini genişletmez.',
    'goals.title': 'ILAIOS’un ne oluşturmasını istiyorsun?',
    'goals.subtitle': 'Bitmiş sonucu tarif et. ILAIOS isteği yetkili bir hedef ve kalıcı iş olarak kaydeder; sağlayıcı, çalışan ve ayrıcalıklı yürütme yetkisi sunucu kontrolünde kalır.',
    'goals.example': 'Örnek: Mobilya şirketim için premium bir web sitesi oluştur ve bitmiş sonucu teslim et.',
    'goals.submitting': 'Gönderiliyor…',
    'goals.startPrompt': 'Tek prompt ile başlat',
    'goals.accepted': 'Kontrol düzlemi tarafından kabul edildi',
    'goals.goal': 'Hedef',
    'goals.job': 'İş',
    'goals.authoritativeState': 'Yetkili durum',
    'goals.submissionNote': 'Desktop, gönderimi tamamlanma olarak kabul etmez. İlerleme, yönetişim, kanıt ve nihai çıktılar yetkili çalışma zamanı tarafından doğrulanmalıdır.',
    'goals.account': 'Hesap',
    'goals.provider': 'Sağlayıcı',
    'goals.signingOut': 'Oturum kapatılıyor…',
    'goals.signOut': 'Oturumu kapat',
    'goals.signInNote': 'Yönetilen işi göndermeden önce oturum aç. Kimlik doğrulama tarayıcında açılır; ham kimlik sağlayıcı token’ları Flutter arayüzüne aktarılmaz.',
    'goals.signingIn': 'Oturum açılıyor…',
    'goals.continueWith': 'Şununla devam et:',
    'goals.controlPlaneUnavailable': 'Yetkili kontrol düzlemi kullanılamıyor',
    'goals.signInRequired': 'Yönetilen işi göndermek için oturum aç',
    'referenceAssets.dock': 'Referans görseller',
    'videoReferences.dock': 'Referans görseller',
    'videoReferences.title': 'Referans görseller',
    'videoReferences.formats': 'JPEG / PNG / WebP · görsel başına 10 MiB · toplam 100 MiB',
    'videoReferences.add': 'Görsel ekle',
    'videoReferences.loading': 'Yükleniyor…',
    'videoReferences.optional': 'İsteğe bağlı: Web Factory veya Video Factory için konu, ürün, stil, ortam, logo ya da storyboard referansları ekle.',
    'videoReferences.privacy': 'Referans görseller hiçbir zaman herkese açık URL olarak yayımlanmaz. Web Factory kabul edilen görselleri yalnızca üretilen yerel kaynağa ekler; Video Factory görsel koşullandırma için normalize edilmiş kopyaları yapılandırılmış ücretsiz görsel sağlayıcısına gönderebilir.',
    'videoReferences.dialogTitle': 'Referans görsel talimatları',
    'videoReferences.role': 'Rol',
    'videoReferences.howUse': 'Web Factory veya Video Factory bu görseli nasıl kullanmalı?',
    'videoReferences.hint': 'Örnek: Bu ürünün şeklini, malzemelerini, renklerini ve logo yerleşimini tutarlı koru.',
    'videoReferences.cancel': 'İptal',
    'videoReferences.save': 'Kaydet',
    'videoReferences.moveLeft': 'Sola taşı',
    'videoReferences.instructions': 'Talimatlar',
    'videoReferences.remove': 'Kaldır',
    'videoReferences.role.style': 'Stil',
    'videoReferences.role.subject': 'Konu',
    'videoReferences.role.product': 'Ürün',
    'videoReferences.role.environment': 'Ortam',
    'videoReferences.role.logo': 'Logo',
    'videoReferences.role.storyboard': 'Storyboard',
    'videoReferences.role.other': 'Diğer',
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
