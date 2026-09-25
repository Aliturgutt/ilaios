import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';

/// Desktop-wide text scale. Persistence is only activated by the release app.
final ValueNotifier<double> desktopTextScale = ValueNotifier<double>(1.0);

abstract final class DesktopTextScaleStore {
  static const double minimum = 0.9;
  static const double maximum = 1.5;

  static Future<double> load({File? file}) async {
    final target = file ?? _settingsFile();
    if (target == null) return 1.0;
    try {
      final decoded = jsonDecode(await target.readAsString());
      final value = decoded is Map ? decoded['scale'] : null;
      if (value is num &&
          value.isFinite &&
          value >= minimum &&
          value <= maximum) {
        return value.toDouble();
      }
    } on Object {
      // Missing or corrupt preferences must not prevent Desktop startup.
    }
    return 1.0;
  }

  static Future<void> save(double scale, {File? file}) async {
    if (!scale.isFinite || scale < minimum || scale > maximum) {
      throw ArgumentError.value(scale, 'scale', 'Outside supported range');
    }
    final target = file ?? _settingsFile();
    if (target == null) return;
    await target.parent.create(recursive: true);
    final temporary = File('${target.path}.tmp');
    await temporary.writeAsString(
      jsonEncode(<String, Object>{'schema_version': 1, 'scale': scale}),
      flush: true,
    );
    if (await target.exists()) await target.delete();
    await temporary.rename(target.path);
  }

  static File? _settingsFile() {
    final localAppData = Platform.environment['LOCALAPPDATA']?.trim();
    if (localAppData?.isNotEmpty == true) {
      return File(
        '$localAppData\\ILAIOS\\preferences\\desktop-text-scale.json',
      );
    }
    final home = Platform.environment['HOME']?.trim();
    if (home?.isNotEmpty == true) {
      return File('$home/.ilaios/preferences/desktop-text-scale.json');
    }
    return null;
  }
}
