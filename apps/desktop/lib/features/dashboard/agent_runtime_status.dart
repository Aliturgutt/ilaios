import '../../control_plane/operational_snapshot.dart';

/// Presentation-only state derived from the canonical agent registry and
/// authoritative runtime telemetry already present in [OperationalSnapshot].
///
/// This helper does not create agent identity or runtime authority. Unknown,
/// stale, malformed and unmatched runtime state fails closed to [offline].
enum AgentRuntimeDisplayState { active, working, idle, waiting, offline }

Map<String, AgentRuntimeDisplayState> resolveCanonicalAgentRuntimeStates(
  OperationalSnapshot snapshot, {
  bool runtimeConnected = true,
  DateTime? now,
  Duration? maxAge,
}) {
  final merged = <String, Map<String, Object?>>{};
  for (final item in _maps(snapshot.agentState['agents'])) {
    final id = _text(item, const ['agent_id']);
    if (id == null || !id.startsWith('ilaios.agent.')) continue;
    merged[id] = Map<String, Object?>.of(item);
  }

  Map<String, AgentRuntimeDisplayState> allOffline() =>
      Map<String, AgentRuntimeDisplayState>.unmodifiable(
        merged.map(
          (id, _) => MapEntry(id, AgentRuntimeDisplayState.offline),
        ),
      );

  // Connection and freshness are presentation admission conditions only. They
  // never change the runtime authority. If a caller asks for freshness-bound
  // projection, both clock and age bound are required; ambiguity fails closed.
  if (!runtimeConnected) return allOffline();
  if ((now == null) != (maxAge == null)) return allOffline();
  if (now != null &&
      maxAge != null &&
      !snapshot.isAuthoritativelyFresh(now: now, maxAge: maxAge)) {
    return allOffline();
  }

  void mergeTelemetry(Map<String, Object?> item) {
    String? canonicalId;
    for (final key in const [
      'agent_id',
      'worker_id',
      'executor_id',
      'agent',
      'worker',
      'id',
    ]) {
      final candidate = _text(item, [key]);
      if (candidate != null && merged.containsKey(candidate)) {
        canonicalId = candidate;
        break;
      }
    }
    if (canonicalId == null) return;
    final status = _text(item, const [
      'agent_status',
      'worker_status',
      'status',
      'state',
      'lease_state',
    ]);
    if (status != null) merged[canonicalId]!['runtime_status'] = status;
  }

  for (final key in const ['agents', 'workers', 'executors', 'leases']) {
    for (final item in _maps(snapshot.schedulerState[key])) {
      mergeTelemetry(item);
    }
  }
  for (final item in snapshot.runtimeRoutes) {
    mergeTelemetry(item);
  }
  for (final item in snapshot.liveEvents) {
    mergeTelemetry(item);
  }

  return Map<String, AgentRuntimeDisplayState>.unmodifiable(
    merged.map((id, item) {
      final registered = item['registered'] is bool
          ? item['registered'] as bool
          : true;
      if (!registered) return MapEntry(id, AgentRuntimeDisplayState.offline);
      final raw = _text(item, const [
            'runtime_status',
            'agent_status',
            'worker_status',
            'status',
            'state',
            'lease_state',
          ]) ??
          'unknown';
      return MapEntry(id, classifyAgentRuntimeDisplayState(raw));
    }),
  );
}

AgentRuntimeDisplayState classifyAgentRuntimeDisplayState(String raw) {
  final value = _normalize(raw);
  // Fail-closed states must be classified before positive substring matches.
  // In particular, `unavailable` contains `available` after normalization and
  // must never be projected as idle/available work capacity.
  if (value.contains('unknown') ||
      value.contains('stale') ||
      value.contains('unavailable') ||
      value.contains('offline') ||
      value.contains('disconnected') ||
      value.contains('disabled') ||
      value.contains('stopped') ||
      value.contains('dead') ||
      value.contains('unregistered')) {
    return AgentRuntimeDisplayState.offline;
  }
  if (value.contains('busy') ||
      value.contains('running') ||
      value.contains('executing') ||
      value.contains('working')) {
    return AgentRuntimeDisplayState.working;
  }
  if (value.contains('idle') ||
      value.contains('available') ||
      value.contains('free')) {
    return AgentRuntimeDisplayState.idle;
  }
  if (value.contains('review') ||
      value.contains('approval') ||
      value.contains('waiting') ||
      value.contains('pending')) {
    return AgentRuntimeDisplayState.waiting;
  }
  if (value.contains('active') ||
      value.contains('ready') ||
      value.contains('online')) {
    return AgentRuntimeDisplayState.active;
  }
  return AgentRuntimeDisplayState.offline;
}

List<Map<String, Object?>> _maps(Object? raw) {
  if (raw is! List<Object?>) return const [];
  return raw.whereType<Map<String, Object?>>().toList(growable: false);
}

String? _text(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return '$value';
  }
  return null;
}

String _normalize(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');
