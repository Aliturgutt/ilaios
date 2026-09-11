import 'package:flutter/foundation.dart';

import 'evidence_record.dart';

@immutable
class OperationalSnapshot {
  const OperationalSnapshot({
    required this.runtimeRoutes,
    required this.schedulerState,
    required this.grantsState,
    required this.governanceState,
    required this.evidenceRecords,
    required this.liveEvents,
    this.agentState = const <String, Object?>{},
  });

  const OperationalSnapshot.unavailable()
      : runtimeRoutes = const <Map<String, Object?>>[],
        schedulerState = const <String, Object?>{},
        grantsState = const <String, Object?>{},
        governanceState = const <String, Object?>{},
        evidenceRecords = const <EvidenceRecord>[],
        liveEvents = const <Map<String, Object?>>[],
        agentState = const <String, Object?>{};

  final List<Map<String, Object?>> runtimeRoutes;
  final Map<String, Object?> schedulerState;
  final Map<String, Object?> grantsState;
  final Map<String, Object?> governanceState;
  final List<EvidenceRecord> evidenceRecords;
  final List<Map<String, Object?>> liveEvents;
  final Map<String, Object?> agentState;

  bool get available =>
      runtimeRoutes.isNotEmpty ||
      schedulerState.isNotEmpty ||
      grantsState.isNotEmpty ||
      governanceState.isNotEmpty ||
      evidenceRecords.isNotEmpty ||
      liveEvents.isNotEmpty ||
      agentState.isNotEmpty;

  int get runtimeRouteCount => runtimeRoutes.length;
  int get evidenceCount => evidenceRecords.length;
  int get liveEventCount => liveEvents.length;

  /// Server-declared authority that produced the canonical agent projection.
  ///
  /// Desktop must never synthesize this value. Missing or malformed provenance
  /// stays unavailable so presentation layers can fail closed.
  String? get agentRuntimeSource {
    final value = agentState['source'];
    if (value is! String || value.isEmpty || value.trim() != value) return null;
    return value;
  }

  /// Highest authoritative sequence observed in the incremental live feed.
  ///
  /// This is deliberately not a client-generated counter: it is derived only
  /// from control-plane event sequence values. Any malformed sequence makes the
  /// version unavailable instead of allowing Desktop to invent freshness.
  int? get authoritativeLiveSequence {
    if (liveEvents.isEmpty) return null;
    int? highest;
    for (final event in liveEvents) {
      final sequence = event['sequence'];
      if (sequence is! int || sequence < 1) return null;
      if (highest == null || sequence > highest) highest = sequence;
    }
    return highest;
  }

  /// Latest parseable authoritative timestamp carried by runtime evidence.
  ///
  /// Only server-owned event/readiness timestamps participate. Desktop local
  /// wall-clock time is never substituted for missing authority.
  DateTime? get authoritativeTimestamp {
    DateTime? latest;

    bool consider(Object? raw) {
      if (raw == null) return true;
      if (raw is! String || raw.isEmpty || raw.trim() != raw) return false;
      final parsed = DateTime.tryParse(raw);
      if (parsed == null || !parsed.isUtc) return false;
      final utc = parsed.toUtc();
      if (latest == null || utc.isAfter(latest!)) latest = utc;
      return true;
    }

    for (final event in liveEvents) {
      if (!consider(event['timestamp'])) return null;
    }

    final rawAgents = agentState['agents'];
    if (rawAgents != null) {
      if (rawAgents is! List<Object?>) return null;
      for (final rawAgent in rawAgents) {
        if (rawAgent is! Map<String, dynamic>) return null;
        if (!consider(rawAgent['readiness_updated_at'])) return null;
      }
    }
    return latest;
  }

  /// Freshness is true only when authoritative UTC evidence exists, is not in
  /// the future, and remains inside the caller's bounded age window.
  bool isAuthoritativelyFresh({
    required DateTime now,
    required Duration maxAge,
  }) {
    if (maxAge.isNegative) return false;
    final timestamp = authoritativeTimestamp;
    if (timestamp == null) return false;
    final current = now.toUtc();
    if (timestamp.isAfter(current)) return false;
    return current.difference(timestamp) <= maxAge;
  }
}
