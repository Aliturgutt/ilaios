import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';

abstract final class IlaiosThemeModeStore {
  static Future<ThemeMode> load() async {
    final file = _settingsFile();
    if (file == null || !await file.exists()) return ThemeMode.dark;
    try {
      final document = jsonDecode(await file.readAsString());
      if (document is Map<String, dynamic>) {
        final value = document['theme'] as String?;
        return switch (value) {
          'light' => ThemeMode.light,
          'system' => ThemeMode.system,
          _ => ThemeMode.dark,
        };
      }
    } on Object {
      // Preference corruption must never block Desktop startup.
    }
    return ThemeMode.dark;
  }

  static Future<void> save(ThemeMode mode) async {
    final file = _settingsFile();
    if (file == null) return;
    await file.parent.create(recursive: true);
    final temporary = File('${file.path}.tmp');
    if (await temporary.exists()) await temporary.delete();
    await temporary.writeAsString(
      jsonEncode(<String, Object?>{
        'schema_version': 1,
        'theme': switch (mode) {
          ThemeMode.light => 'light',
          ThemeMode.system => 'system',
          ThemeMode.dark => 'dark',
        },
      }),
      flush: true,
    );
    if (await file.exists()) await file.delete();
    await temporary.rename(file.path);
  }

  static File? _settingsFile() {
    final localAppData = Platform.environment['LOCALAPPDATA']?.trim();
    if (localAppData?.isNotEmpty == true) {
      return File('$localAppData\\ILAIOS\\preferences\\desktop-theme.json');
    }
    final home = Platform.environment['HOME']?.trim();
    if (home?.isNotEmpty == true) {
      return File('$home/.ilaios/preferences/desktop-theme.json');
    }
    return null;
  }
}
