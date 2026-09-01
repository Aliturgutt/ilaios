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
  static const Set<String> _nestedRootKeys = <String>{
    'costs',
    'finops',
    'cost_telemetry',
  };

  static const Set<String> _allowedCostKeys = <String>{
    'total_cost_usd',
    'cost_usd',
    'current_cost_usd',
    'spend_usd',
    'forecast_cost_usd',
    'estimated_month_cost_usd',
    'forecast_usd',
    'budget_usd',
    'hard_cap_usd',
    'monthly_budget_usd',
    'savings_usd',
    'optimized_savings_usd',
    'monthly_savings_usd',
    'next_month_forecast_usd',
    'next_month_cost_usd',
    'period_label',
    'billing_period',
    'date_range',
    'total_cost_delta',
    'cost_delta',
    'forecast_delta',
    'savings_delta',
    'next_month_delta',
    'cost_trend',
    'trend',
    'daily_costs',
    'service_costs',
    'cost_distribution',
    'services',
    'resources',
    'top_resources',
    'resource_costs',
    'budget_alerts',
    'alerts',
    'recommendations',
    'optimization_recommendations',
    'reports',
    'cost_reports',
  };

  static const Set<String> _sensitiveKeys = <String>{
    'api_key',
    'authorization',
    'password',
    'secret',
    'token',
    'cookie',
  };

  static bool canExport(OperationalSnapshot snapshot) {
    try {
      return _buildProjections(snapshot).isNotEmpty;
    } on CostExportException {
      return false;
    }
  }

  static Future<String> export(
    OperationalSnapshot snapshot, {
    Directory? rootDirectory,
    DateTime? now,
  }) async {
    final projections = _buildProjections(snapshot);
    if (projections.isEmpty) {
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
      'projections': projections,
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

  static List<Map<String, Object?>> _buildProjections(
    OperationalSnapshot snapshot,
  ) {
    final roots = <({String source, Map<String, Object?> values})>[
      (source: 'governance', values: snapshot.governanceState),
      (source: 'scheduler', values: snapshot.schedulerState),
      ..._nestedRoots('governance', snapshot.governanceState),
      ..._nestedRoots('scheduler', snapshot.schedulerState),
    ];

    final projections = <Map<String, Object?>>[];
    for (final root in roots) {
      final selected = <String, Object?>{};
      for (final entry in root.values.entries) {
        if (!_allowedCostKeys.contains(entry.key)) continue;
        selected[entry.key] = _jsonSafe(entry.value);
      }
      if (selected.isNotEmpty) {
        projections.add(<String, Object?>{
          'source': root.source,
          'values': Map<String, Object?>.unmodifiable(selected),
        });
      }
    }
    return List<Map<String, Object?>>.unmodifiable(projections);
  }

  static List<({String source, Map<String, Object?> values})> _nestedRoots(
    String parent,
    Map<String, Object?> source,
  ) {
    final roots = <({String source, Map<String, Object?> values})>[];
    for (final key in _nestedRootKeys) {
      final value = source[key];
      if (value is Map<Object?, Object?>) {
        roots.add((
          source: '$parent.$key',
          values: _stringKeyedMap(value),
        ));
      } else if (value is List<Object?>) {
        var index = 0;
        for (final item in value) {
          if (item is! Map<Object?, Object?>) continue;
          roots.add((
            source: '$parent.$key[$index]',
            values: _stringKeyedMap(item),
          ));
          index += 1;
        }
      }
    }
    return roots;
  }

  static Map<String, Object?> _stringKeyedMap(Map<Object?, Object?> source) {
    final output = <String, Object?>{};
    for (final entry in source.entries) {
      final key = entry.key;
      if (key is! String) {
        throw const CostExportException(
          'Authoritative cost telemetry is malformed',
        );
      }
      output[key] = entry.value;
    }
    return output;
  }

  static Object? _jsonSafe(Object? value) {
    if (value == null || value is bool || value is num || value is String) {
      return value;
    }
    if (value is List<Object?>) {
      return List<Object?>.unmodifiable(value.map(_jsonSafe));
    }
    if (value is Map<Object?, Object?>) {
      final output = <String, Object?>{};
      for (final entry in value.entries) {
        final key = entry.key;
        if (key is! String) {
          throw const CostExportException(
            'Authoritative cost telemetry is malformed',
          );
        }
        if (_sensitiveKeys.contains(key.toLowerCase())) {
          throw const CostExportException(
            'Authoritative cost telemetry contains sensitive data',
          );
        }
        output[key] = _jsonSafe(entry.value);
      }
      return Map<String, Object?>.unmodifiable(output);
    }
    throw const CostExportException(
      'Authoritative cost telemetry contains unsupported export data',
    );
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
