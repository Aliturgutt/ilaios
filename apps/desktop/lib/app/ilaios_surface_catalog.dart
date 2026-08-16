abstract final class IlaiosSurfaceCatalog {
  static const Map<String, String> _en = <String, String>{
    'deliveries.title': 'Deliveries',
    'deliveries.note': 'Only artifacts present in the verified evidence chain are offered here. Saving is an explicit user action; Desktop retrieves bytes from the authoritative evidence store and never fabricates a finished product.',
    'deliveries.empty': 'No verified deliverable artifacts are available yet.',
    'deliveries.savedPrefix': 'Saved verified artifact to',
    'deliveries.execution': 'Execution',
    'deliveries.saving': 'Saving…',
    'deliveries.save': 'Save',
  };

  static const Map<String, String> _tr = <String, String>{
    'deliveries.title': 'Teslimatlar',
    'deliveries.note': 'Burada yalnızca doğrulanmış kanıt zincirinde bulunan çıktılar sunulur. Kaydetme açık bir kullanıcı işlemidir; Desktop baytları yetkili kanıt deposundan alır ve bitmiş ürün uydurmaz.',
    'deliveries.empty': 'Henüz doğrulanmış teslim edilebilir çıktı yok.',
    'deliveries.savedPrefix': 'Doğrulanmış çıktı şuraya kaydedildi:',
    'deliveries.execution': 'Yürütme',
    'deliveries.saving': 'Kaydediliyor…',
    'deliveries.save': 'Kaydet',
  };

  static String? text(String localeCode, String key) {
    final catalog = localeCode == 'tr' ? _tr : _en;
    return catalog[key] ?? _en[key];
  }
}
