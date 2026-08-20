import 'package:flutter/material.dart';

import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../navigation/desktop_section.dart';
import 'reference_agents_view_impl.dart' as impl;

/// Presentation boundary for the canonical Agents surface.
///
/// When the authoritative canonical registry is available, runtime-only worker
/// identifiers must not inflate the canonical agent count or table. Runtime
/// records are still allowed to enrich matching canonical agent records.
class ReferenceAgentsView extends StatelessWidget {
  const ReferenceAgentsView({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final ValueChanged<DesktopSection> onNavigate;
  final VoidCallback? onRefreshRequested;

  @override
  Widget build(BuildContext context) => impl.ReferenceAgentsView(
        projection: projection,
        snapshot: _canonicalAgentSnapshot(snapshot),
        status: status,
        onNavigate: onNavigate,
        onRefreshRequested: onRefreshRequested,
      );
}

OperationalSnapshot _canonicalAgentSnapshot(OperationalSnapshot snapshot) {
  final rawAgents = snapshot.agentState['agents'];
  if (rawAgents is! List<Object?>) return snapshot;

  final canonicalIds = <String>{};
  for (final raw in rawAgents) {
    if (raw is! Map<String, Object?>) continue;
    final id = _recordId(raw);
    if (id != null && id.isNotEmpty) canonicalIds.add(id);
  }
  if (canonicalIds.isEmpty) return snapshot;

  bool keep(Map<String, Object?> record) {
    final id = _recordId(record);
    return id == null || canonicalIds.contains(id);
  }

  final scheduler = Map<String, Object?>.from(snapshot.schedulerState);
  for (final key in const ['agents', 'workers', 'executors', 'leases']) {
    final raw = scheduler[key];
    if (raw is! List<Object?>) continue;
    scheduler[key] = raw
        .whereType<Map<String, Object?>>()
        .where(keep)
        .toList(growable: false);
  }

  return OperationalSnapshot(
    runtimeRoutes: snapshot.runtimeRoutes.where(keep).toList(growable: false),
    schedulerState: scheduler,
    grantsState: snapshot.grantsState,
    governanceState: snapshot.governanceState,
    evidenceRecords: snapshot.evidenceRecords,
    liveEvents: snapshot.liveEvents.where(keep).toList(growable: false),
    agentState: snapshot.agentState,
  );
}

String? _recordId(Map<String, Object?> item) {
  for (final key in const [
    'agent_id',
    'worker_id',
    'executor_id',
    'agent',
    'worker',
    'id',
  ]) {
    final value = item[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
  }
  return null;
}
