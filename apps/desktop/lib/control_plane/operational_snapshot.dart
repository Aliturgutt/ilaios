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
}
