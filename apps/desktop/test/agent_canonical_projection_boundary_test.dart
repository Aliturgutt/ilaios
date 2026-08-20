import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  const projection = ControlPlaneProjection(
    connected: true,
    status: 'Connected',
    goalCount: 0,
    jobCount: 0,
    lastEvent: null,
  );

  const snapshot = OperationalSnapshot(
    runtimeRoutes: <Map<String, Object?>>[
      <String, Object?>{
        'agent_id': 'ilaios.agent.core.orchestrator.v1',
        'role': 'poisoned-runtime-role',
        'readiness': 'verified',
        'registered': false,
        'agent_status': 'busy',
        'current_task': 'Governed runtime task',
        'latency_ms': 900,
      },
      <String, Object?>{
        'id': 'exec-foreign-1',
        'status': 'executed',
        'role': 'execution-record',
      },
    ],
    schedulerState: <String, Object?>{
      'workers': <Object?>[
        <String, Object?>{
          'agent_id': 'ilaios.agent.core.planner.v1',
          'worker_status': 'idle',
          'current_task': 'Scheduler-backed task',
        },
      ],
    },
    grantsState: <String, Object?>{},
    governanceState: <String, Object?>{},
    evidenceRecords: <Never>[],
    liveEvents: <Map<String, Object?>>[
      <String, Object?>{
        'worker_id': 'worker-foreign-2',
        'event_type': 'executed',
      },
    ],
    agentState: <String, Object?>{
      'canonical_count': 2,
      'registered_count': 2,
      'authority_drift_count': 0,
      'agents': <Object?>[
        <String, Object?>{
          'agent_id': 'ilaios.agent.core.orchestrator.v1',
          'alias': 'Orchestrator',
          'role': 'orchestration',
          'team': 'core',
          'capabilities': <Object?>['workflow.coordinate', 'agent.delegate'],
          'permissions': <Object?>['workflow.read', 'agent.invoke'],
          'readiness': 'registered',
          'registered': true,
          'authority_matches_canonical': true,
          'agent_status': 'offline',
        },
        <String, Object?>{
          'agent_id': 'ilaios.agent.core.planner.v1',
          'alias': 'Planner',
          'role': 'planning',
          'team': 'core',
          'capabilities': <Object?>['workflow.plan'],
          'permissions': <Object?>['workflow.read', 'plan.propose'],
          'readiness': 'registered',
          'registered': true,
          'authority_matches_canonical': true,
          'agent_status': 'offline',
        },
      ],
    },
  );

  testWidgets(
    'Agents projection admits telemetry only for canonical identities',
    (WidgetTester tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.binding.setSurfaceSize(const Size(1648, 928));
      await tester.pumpWidget(
        const IlaiosDesktopApp(
          projection: projection,
          operationalSnapshot: snapshot,
        ),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('nav-agents')));
      await tester.pumpAndSettle();

      expect(
        find.byKey(const ValueKey('agent-row-ilaios.agent.core.orchestrator.v1')),
        findsOneWidget,
      );
      expect(
        find.byKey(const ValueKey('agent-row-ilaios.agent.core.planner.v1')),
        findsOneWidget,
      );
      expect(find.byKey(const ValueKey('agent-row-exec-foreign-1')), findsNothing);
      expect(find.byKey(const ValueKey('agent-row-worker-foreign-2')), findsNothing);
      expect(find.textContaining('/ 2 agents · 2 total'), findsOneWidget);

      // Runtime/scheduler events may enrich telemetry for a canonical identity,
      // but must never overwrite registry-owned identity/governance fields.
      expect(find.text('orchestration'), findsWidgets);
      expect(find.text('poisoned-runtime-role'), findsNothing);
      expect(find.text('Governed runtime task'), findsWidgets);
      expect(find.text('Scheduler-backed task'), findsOneWidget);
      expect(tester.takeException(), isNull);
    },
  );
}
