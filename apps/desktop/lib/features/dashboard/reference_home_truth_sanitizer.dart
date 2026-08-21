import '../../control_plane/operational_snapshot.dart';

/// Returns a Home-only projection copy that drops malformed numeric telemetry.
///
/// The canonical [OperationalSnapshot] remains untouched. This is deliberately
/// a render-boundary sanitizer: it never invents values, never changes
/// execution state, and only removes numeric fields that cannot truthfully be
/// represented by the Home metric/progress widgets.
OperationalSnapshot sanitizeReferenceHomeSnapshot(OperationalSnapshot source) {
  return OperationalSnapshot(
    runtimeRoutes: source.runtimeRoutes,
    schedulerState: _sanitizeState(source.schedulerState),
    grantsState: source.grantsState,
    governanceState: _sanitizeGovernance(source.governanceState),
    evidenceRecords: source.evidenceRecords,
    liveEvents: source.liveEvents.map(_sanitizeEvent).toList(growable: false),
    agentState: source.agentState,
  );
}

const _costKeys = <String>{
  'today_cost_usd',
  'daily_cost_usd',
  'total_cost_usd',
  'cost_usd',
  'spent_minor',
};

const _budgetKeys = <String>{
  'budget_usd',
  'daily_budget_usd',
  'hard_cap_usd',
};

const _healthKeys = <String>{
  'system_health_percent',
  'health_percent',
  'health_score',
};

Map<String, Object?> _sanitizeState(Map<String, Object?> source) {
  if (source.isEmpty) return source;
  final result = Map<String, Object?>.of(source);
  _removeMalformedFiniteNumbers(result, _costKeys);
  _removeMalformedFiniteNumbers(result, _budgetKeys);
  _removeMalformedPercentages(result, _healthKeys);
  return result;
}

Map<String, Object?> _sanitizeGovernance(Map<String, Object?> source) {
  if (source.isEmpty) return source;
  final result = _sanitizeState(source);
  final rawWork = source['work'];
  if (rawWork is List<Object?>) {
    result['work'] = rawWork.map((item) {
      if (item is! Map<String, Object?>) return item;
      return _sanitizeProgress(item);
    }).toList(growable: false);
  }
  return result;
}

Map<String, Object?> _sanitizeEvent(Map<String, Object?> source) {
  if (source.isEmpty) return source;
  final result = _sanitizeProgress(source);
  _removeMalformedFiniteNumbers(result, _costKeys);
  _removeMalformedFiniteNumbers(result, _budgetKeys);
  _removeMalformedPercentages(result, _healthKeys);
  return result;
}

Map<String, Object?> _sanitizeProgress(Map<String, Object?> source) {
  final result = Map<String, Object?>.of(source);
  for (final key in const <String>['progress', 'progress_percent']) {
    if (!result.containsKey(key)) continue;
    final value = _finiteNumber(result[key]);
    if (value == null || value < 0 || value > 100) result.remove(key);
  }
  return result;
}

void _removeMalformedFiniteNumbers(
  Map<String, Object?> target,
  Set<String> keys,
) {
  for (final key in keys) {
    if (!target.containsKey(key)) continue;
    if (_finiteNumber(target[key]) == null) target.remove(key);
  }
}

void _removeMalformedPercentages(
  Map<String, Object?> target,
  Set<String> keys,
) {
  for (final key in keys) {
    if (!target.containsKey(key)) continue;
    final value = _finiteNumber(target[key]);
    if (value == null || value < 0 || value > 100) target.remove(key);
  }
}

double? _finiteNumber(Object? raw) {
  final parsed = switch (raw) {
    num value => value.toDouble(),
    String value => double.tryParse(value.trim()),
    _ => null,
  };
  return parsed != null && parsed.isFinite ? parsed : null;
}
