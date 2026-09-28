import 'agent_runtime_status.dart';
import 'pixel_agent_presentation.dart';

/// Display-only counts from canonical, freshness-checked runtime states.
/// Missing team identity never gets attributed to a department.
class OfficeTeamCounts {
  const OfficeTeamCounts({
    required this.working,
    required this.waiting,
    required this.idle,
    required this.registered,
  });
  final int working;
  final int waiting;
  final int idle;
  final int registered;
}

Map<String, OfficeTeamCounts> countVerifiedOfficeTeams(
  Map<String, AgentRuntimeDisplayState> states,
  Map<String, String> canonicalTeams,
) {
  final result = <String, OfficeTeamCounts>{};
  for (final team in pixelAgentTeams) {
    final entries = states.entries
        .where((entry) => canonicalTeams[entry.key]?.toLowerCase() == team)
        .toList();
    result[team] = OfficeTeamCounts(
      registered: entries.length,
      working: entries
          .where((e) => e.value == AgentRuntimeDisplayState.working)
          .length,
      waiting: entries
          .where((e) => e.value == AgentRuntimeDisplayState.waiting)
          .length,
      idle: entries
          .where((e) => e.value == AgentRuntimeDisplayState.idle)
          .length,
    );
  }
  return Map.unmodifiable(result);
}
