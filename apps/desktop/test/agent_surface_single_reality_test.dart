import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/dashboard/agent_runtime_status.dart';

void main() {
  test('presentation snapshot normalizes every surface to shared runtime state', () {
    const source = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[
        <String, Object?>{
          'agent_id': 'ilaios.agent.core.one',
          'status': 'unavailable',
          'current_task': 'job-1',
        },
      ],
      schedulerState: <String, Object?>{
        'agents': <Map<String, Object?>>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.engineering.two',
            'status': 'working',
            'current_task': 'job-2',
          },
        ],
      },
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{},
      evidenceRecords: [],
      liveEvents: <Map<String, Object?>>[],
      agentState: <String, Object?>{
        'agents': <Map<String, Object?>>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.core.one',
            'team': 'core',
            'registered': true,
          },
          <String, Object?>{
            'agent_id': 'ilaios.agent.engineering.two',
            'team': 'engineering',
            'registered': true,
          },
        ],
      },
    );

    final states = resolveCanonicalAgentRuntimeStates(source);
    expect(states['ilaios.agent.core.one'], AgentRuntimeDisplayState.offline);
    expect(
      states['ilaios.agent.engineering.two'],
      AgentRuntimeDisplayState.working,
    );

    final projected = canonicalAgentPresentationSnapshot(source);
    final agents = projected.agentState['agents']! as List<Object?>;
    final core = agents
        .whereType<Map<String, Object?>>()
        .singleWhere((item) => item['agent_id'] == 'ilaios.agent.core.one');
    final engineering = agents
        .whereType<Map<String, Object?>>()
        .singleWhere((item) => item['agent_id'] == 'ilaios.agent.engineering.two');
    expect(core['status'], 'offline');
    expect(engineering['status'], 'working');
    expect(projected.runtimeRoutes.single['status'], 'offline');
    expect(projected.runtimeRoutes.single['current_task'], 'job-1');
    final schedulerAgents = projected.schedulerState['agents']! as List<Object?>;
    final schedulerEngineering = schedulerAgents.single as Map<String, Object?>;
    expect(schedulerEngineering['status'], 'working');
    expect(schedulerEngineering['current_task'], 'job-2');
  });

  test('disconnect forces projected surfaces to the same offline state', () {
    const source = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{},
      evidenceRecords: [],
      liveEvents: <Map<String, Object?>>[],
      agentState: <String, Object?>{
        'agents': <Map<String, Object?>>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.web.one',
            'team': 'web',
            'registered': true,
            'status': 'working',
          },
        ],
      },
    );

    final projected = canonicalAgentPresentationSnapshot(
      source,
      runtimeConnected: false,
    );
    final agent = (projected.agentState['agents']! as List<Object?>)
        .single as Map<String, Object?>;
    expect(agent['status'], 'offline');
    expect(
      resolveCanonicalAgentRuntimeStates(source, runtimeConnected: false)
          .values
          .single,
      AgentRuntimeDisplayState.offline,
    );
  });
}
