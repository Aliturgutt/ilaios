import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/dashboard/agent_runtime_status.dart';

OperationalSnapshot _snapshot({
  required List<Map<String, Object?>> agents,
  Map<String, Object?> schedulerState = const <String, Object?>{},
  List<Map<String, Object?>> runtimeRoutes = const <Map<String, Object?>>[],
  List<Map<String, Object?>> liveEvents = const <Map<String, Object?>>[],
}) =>
    OperationalSnapshot(
      runtimeRoutes: runtimeRoutes,
      schedulerState: schedulerState,
      grantsState: const <String, Object?>{},
      governanceState: const <String, Object?>{},
      evidenceRecords: const [],
      liveEvents: liveEvents,
      agentState: <String, Object?>{'agents': agents},
    );

void main() {
  test('registered agent without runtime state fails closed to offline', () {
    final states = resolveCanonicalAgentRuntimeStates(
      _snapshot(
        agents: const [
          <String, Object?>{
            'agent_id': 'ilaios.agent.core.orchestrator.v1',
            'registered': true,
          },
        ],
      ),
    );

    expect(
      states['ilaios.agent.core.orchestrator.v1'],
      AgentRuntimeDisplayState.offline,
    );
  });

  test('unknown stale and unavailable runtime state fail closed', () {
    for (final value in const ['unknown', 'stale', 'unavailable', 'nonsense']) {
      expect(
        classifyAgentRuntimeDisplayState(value),
        AgentRuntimeDisplayState.offline,
        reason: value,
      );
    }
  });

  test('authoritative working idle waiting and active states remain distinct', () {
    expect(
      classifyAgentRuntimeDisplayState('executing'),
      AgentRuntimeDisplayState.working,
    );
    expect(
      classifyAgentRuntimeDisplayState('available'),
      AgentRuntimeDisplayState.idle,
    );
    expect(
      classifyAgentRuntimeDisplayState('approval_pending'),
      AgentRuntimeDisplayState.waiting,
    );
    expect(
      classifyAgentRuntimeDisplayState('online'),
      AgentRuntimeDisplayState.active,
    );
  });

  test('runtime telemetry only enriches canonical agent identities', () {
    final states = resolveCanonicalAgentRuntimeStates(
      _snapshot(
        agents: const [
          <String, Object?>{
            'agent_id': 'ilaios.agent.security.codesec.v1',
            'registered': true,
          },
        ],
        schedulerState: const <String, Object?>{
          'workers': [
            <String, Object?>{
              'agent_id': 'ilaios.agent.security.codesec.v1',
              'state': 'working',
            },
            <String, Object?>{
              'agent_id': 'ilaios.agent.fake.unregistered.v1',
              'state': 'working',
            },
          ],
        },
      ),
    );

    expect(states, hasLength(1));
    expect(
      states['ilaios.agent.security.codesec.v1'],
      AgentRuntimeDisplayState.working,
    );
    expect(states.containsKey('ilaios.agent.fake.unregistered.v1'), isFalse);
  });

  test('unregistered canonical agent stays offline despite telemetry', () {
    final states = resolveCanonicalAgentRuntimeStates(
      _snapshot(
        agents: const [
          <String, Object?>{
            'agent_id': 'ilaios.agent.web.builder.v1',
            'registered': false,
            'agent_status': 'working',
          },
        ],
      ),
    );

    expect(
      states['ilaios.agent.web.builder.v1'],
      AgentRuntimeDisplayState.offline,
    );
  });
}
