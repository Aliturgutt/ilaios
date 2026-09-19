import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/dashboard/agent_runtime_status.dart';

void main() {
  test('explicit cross-tenant registry identity is not rendered', () {
    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{},
      evidenceRecords: [],
      liveEvents: <Map<String, Object?>>[],
      agentState: <String, Object?>{
        'agents': <Map<String, Object?>>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.core.allowed',
            'tenant_id': 'tenant-a',
            'registered': true,
            'status': 'active',
          },
          <String, Object?>{
            'agent_id': 'ilaios.agent.core.other',
            'tenant_id': 'tenant-b',
            'registered': true,
            'status': 'active',
          },
        ],
      },
    );

    final states = resolveCanonicalAgentRuntimeStates(
      snapshot,
      authorizedTenantId: 'tenant-a',
    );
    expect(states.keys, contains('ilaios.agent.core.allowed'));
    expect(states.keys, isNot(contains('ilaios.agent.core.other')));
  });

  test('cross-tenant telemetry cannot change authorized agent state', () {
    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{
        'agents': <Map<String, Object?>>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.core.allowed',
            'tenant_id': 'tenant-b',
            'status': 'working',
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
            'agent_id': 'ilaios.agent.core.allowed',
            'tenant_id': 'tenant-a',
            'registered': true,
          },
        ],
      },
    );

    final states = resolveCanonicalAgentRuntimeStates(
      snapshot,
      authorizedTenantId: 'tenant-a',
    );
    expect(
      states['ilaios.agent.core.allowed'],
      AgentRuntimeDisplayState.offline,
    );
  });
}
