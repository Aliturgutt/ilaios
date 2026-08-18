import 'dart:convert';
import 'dart:io';

import '../control_plane/operational_snapshot.dart';

class CostExportException implements Exception {
  const CostExportException(this.message);

  final String message;

  @override
  String toString() => 'CostExportException: $message';
}

abstract final class CostExportService {
  static bool canExport(OperationalSnapshot snapshot) {
    final rawCosts = snapshot.governanceState['costs'];
    if (rawCosts is! Map<Object?, Object?> || rawCosts.isEmpty) return false;
    return rawCosts.keys.every((key) => key is String);
  }

  static Future<String> export(
    OperationalSnapshot snapshot, {
    Directory? rootDirectory,
    DateTime? now,
  }) async {
    final costs = _costPayload(snapshot);
    if (costs.isEmpty) {
      throw const CostExportException(
        'Authoritative cost telemetry is unavailable',
      );
    }

    final root = rootDirectory ?? _defaultRootDirectory();
    await root.create(recursive: true);

    final exportedAt = (now ?? DateTime.now()).toUtc();
    final stamp = exportedAt
        .toIso8601String()
        .replaceAll(':', '-')
        .replaceAll('.', '-');
    final output = File(
      '${root.path}${Platform.pathSeparator}ILAIOS-costs-$stamp.json',
    );

    final payload = <String, Object?>{
      'schema_version': 1,
      'source': 'authoritative-operational-snapshot',
      'exported_at': exportedAt.toIso8601String(),
      'costs': costs,
    };

    try {
      await output.writeAsString(
        const JsonEncoder.withIndent('  ').convert(payload),
        flush: true,
      );
    } on JsonUnsupportedObjectError {
      throw const CostExportException(
        'Authoritative cost telemetry contains unsupported export data',
      );
    } on FileSystemException {
      throw const CostExportException('Cost report could not be written');
    }

    if (!await output.exists() || await output.length() == 0) {
      throw const CostExportException('Cost report verification failed');
    }
    return output.path;
  }

  static Map<String, Object?> _costPayload(OperationalSnapshot snapshot) {
    final rawCosts = snapshot.governanceState['costs'];
    if (rawCosts is! Map<Object?, Object?>) {
      throw const CostExportException(
        'Authoritative cost telemetry is unavailable',
      );
    }

    final costs = <String, Object?>{};
    for (final entry in rawCosts.entries) {
      final key = entry.key;
      if (key is! String) {
        throw const CostExportException(
          'Authoritative cost telemetry is malformed',
        );
      }
      costs[key] = entry.value;
    }
    return Map<String, Object?>.unmodifiable(costs);
  }

  static Directory _defaultRootDirectory() {
    final userProfile = Platform.environment['USERPROFILE']?.trim();
    if (Platform.isWindows && userProfile?.isNotEmpty == true) {
      return Directory('$userProfile\\Downloads\\ILAIOS');
    }

    final localAppData = Platform.environment['LOCALAPPDATA']?.trim();
    if (Platform.isWindows && localAppData?.isNotEmpty == true) {
      return Directory('$localAppData\\ILAIOS\\Reports');
    }

    return Directory(
      '${Directory.systemTemp.path}${Platform.pathSeparator}ILAIOS'
      '${Platform.pathSeparator}Reports',
    );
  }
}
