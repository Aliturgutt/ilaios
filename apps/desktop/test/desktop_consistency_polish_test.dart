import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Goals presents job.updated as human-readable copy only', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 8,
          jobCount: 8,
          lastEvent: 'job.updated',
          schemaVersion: '1',
        ),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('nav-goals')));
    await tester.pumpAndSettle();

    final goals = find.byKey(const Key('reference-goals-page'));
    expect(goals, findsOneWidget);
    expect(
      find.descendant(of: goals, matching: find.text('Job update')),
      findsWidgets,
    );
    expect(
      find.descendant(of: goals, matching: find.text('job.updated')),
      findsNothing,
    );
  });

  testWidgets('Agents excludes runtime-only workers from canonical registry total', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
          schemaVersion: '1',
        ),
        operationalSnapshot: const OperationalSnapshot(
          runtimeRoutes: <Map<String, Object?>>[
            <String, Object?>{
              'worker_id': 'runtime-only-worker',
              'status': 'active',
            },
          ],
          schedulerState: <String, Object?>{},
          grantsState: <String, Object?>{},
          governanceState: <String, Object?>{},
          evidenceRecords: [],
          liveEvents: <Map<String, Object?>>[],
          agentState: <String, Object?>{
            'canonical_count': 2,
            'agents': <Object?>[
              <String, Object?>{
                'agent_id': 'ilaios.agent.one.v1',
                'alias': 'One',
                'role': 'planning',
                'registered': true,
              },
              <String, Object?>{
                'agent_id': 'ilaios.agent.two.v1',
                'alias': 'Two',
                'role': 'review',
                'registered': true,
              },
            ],
          },
        ),
      ),
    );
    await tester.tap(find.byKey(const ValueKey('nav-agents')));
    await tester.pumpAndSettle();

    final agents = find.byKey(const Key('reference-agents-page'));
    expect(agents, findsOneWidget);
    expect(
      find.descendant(of: agents, matching: find.textContaining('2 total')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: agents, matching: find.textContaining('runtime-only-worker')),
      findsNothing,
    );
  });
}
