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

  const agentIds = <String>[
    'ilaios.agent.core.orchestrator.v1',
    'ilaios.agent.core.planner.v1',
    'ilaios.agent.core.supervisor.v1',
    'ilaios.agent.engineering.architect.v1',
    'ilaios.agent.engineering.core.v1',
    'ilaios.agent.engineering.frontend.v1',
    'ilaios.agent.engineering.backend.v1',
    'ilaios.agent.engineering.test.v1',
  ];

  OperationalSnapshot snapshot({bool includeCapacity = true}) =>
      OperationalSnapshot(
        runtimeRoutes: const <Map<String, Object?>>[],
        schedulerState: const <String, Object?>{},
        grantsState: const <String, Object?>{},
        governanceState: const <String, Object?>{},
        evidenceRecords: const [],
        liveEvents: const <Map<String, Object?>>[],
        agentState: <String, Object?>{
          'canonical_count': agentIds.length,
          'registered_count': agentIds.length - 1,
          'authority_drift_count': 0,
          'agents': <Object?>[
            for (var index = 0; index < agentIds.length; index++)
              <String, Object?>{
                'agent_id': agentIds[index],
                'alias': 'Canonical ${index + 1}',
                'role': index.isEven ? 'planning' : 'engineering',
                'team': index < 3 ? 'core' : 'engineering',
                'capabilities': <Object?>[
                  index.isEven ? 'workflow.plan' : 'code.propose',
                ],
                'permissions': <Object?>['repository.read'],
                'readiness': index == 7 ? 'verified' : 'registered',
                'registered': index != 7,
                'authority_matches_canonical': true,
                'agent_status': index == 1 ? 'busy' : 'active',
                'current_task': index == 1 ? 'Authoritative task' : '—',
                if (includeCapacity) 'capacity': 0.40 + index * 0.05,
                'success_rate': 0.91 + index * 0.005,
                'latency_ms': 800 + index * 10,
                'last_activity': '2026-08-19T00:00:0${index}Z',
                'health': 'ready',
              },
          ],
        },
      );

  Future<void> openAgents(
    WidgetTester tester, {
    Future<void> Function(String agentId)? onProvision,
    OperationalSnapshot? operationalSnapshot,
  }) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: projection,
        operationalSnapshot: operationalSnapshot ?? snapshot(),
        onProvisionAgent: onProvision,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-agents')));
    await tester.pumpAndSettle();
  }

  tearDown(() async {});

  testWidgets('Agents consumes canonical agent-state and pages real records', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await openAgents(tester);

    expect(find.text('8'), findsWidgets);
    expect(find.byKey(const Key('agent-page-indicator')), findsOneWidget);
    expect(find.text('1/2'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('agent-row-ilaios.agent.engineering.test.v1')),
      findsNothing,
    );

    await tester.tap(find.byKey(const Key('agent-page-next')));
    await tester.pumpAndSettle();
    expect(find.text('2/2'), findsOneWidget);
    expect(
      find.byKey(const ValueKey('agent-row-ilaios.agent.engineering.test.v1')),
      findsOneWidget,
    );
  });

  testWidgets('Agents role filter and clear are real local controls', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await openAgents(tester);

    await tester.tap(find.byKey(const ValueKey('agent-filter-role')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('planning').last);
    await tester.pumpAndSettle();
    expect(find.textContaining('/ 4 agents'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('agent-search')), 'Canonical 1');
    await tester.pumpAndSettle();
    expect(find.textContaining('/ 1 agents'), findsOneWidget);

    await tester.tap(find.byKey(const Key('agent-clear-filters')));
    await tester.pumpAndSettle();
    expect(find.textContaining('/ 8 agents'), findsOneWidget);
    expect(
      tester.widget<TextField>(find.byKey(const Key('agent-search'))).controller?.text,
      isEmpty,
    );
  });

  testWidgets('New Agent provisions only the server-projected canonical identity', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    String? provisioned;
    await openAgents(
      tester,
      onProvision: (agentId) async => provisioned = agentId,
    );

    await tester.tap(find.byKey(const Key('new-agent-button')));
    await tester.pumpAndSettle();

    const candidate = 'ilaios.agent.engineering.test.v1';
    expect(find.byKey(const ValueKey('canonical-agent-$candidate')), findsOneWidget);
    expect(find.text('Canonical 8'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('canonical-agent-$candidate')));
    await tester.pumpAndSettle();

    expect(provisioned, candidate);
    expect(tester.takeException(), isNull);
  });

  testWidgets('V4 Agents keeps provisioning explicit and More limited to real toolbar actions', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await openAgents(tester, onProvision: (_) async {});

    expect(find.byKey(const Key('new-agent-button')), findsOneWidget);
    await tester.tap(find.byKey(const Key('agents-more-menu')));
    await tester.pumpAndSettle();
    expect(find.text('Refresh'), findsWidgets);
    expect(find.text('Provision Canonical Agent'), findsNothing);
    await tester.tapAt(const Offset(20, 20));
    await tester.pumpAndSettle();

    await tester.tap(
      find.byKey(const ValueKey('agent-row-ilaios.agent.core.orchestrator.v1')),
    );
    await tester.pumpAndSettle();
    expect(find.text('Assign Task'), findsOneWidget);
    final assign = tester.widget<OutlinedButton>(
      find.ancestor(
        of: find.text('Assign Task'),
        matching: find.byType(OutlinedButton),
      ),
    );
    expect(assign.onPressed, isNull);
  });

  testWidgets('missing capacity is static unavailable, not loading', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await openAgents(
      tester,
      operationalSnapshot: snapshot(includeCapacity: false),
    );

    final indicator = find.byKey(
      const ValueKey('agent-capacity-ilaios.agent.core.orchestrator.v1'),
    );
    expect(indicator, findsOneWidget);
    expect(
      find.descendant(
        of: indicator,
        matching: find.byType(LinearProgressIndicator),
      ),
      findsNothing,
    );
    expect(
      find.descendant(
        of: indicator,
        matching: find.byKey(const Key('agent-capacity-unavailable-track')),
      ),
      findsOneWidget,
    );
    expect(find.descendant(of: indicator, matching: find.text('—')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
