import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Goals presents job.updated as human-readable copy without changing projection', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const projection = ControlPlaneProjection(
      connected: true,
      status: 'Connected to authoritative control plane',
      goalCount: 1,
      jobCount: 1,
      lastEvent: 'job.updated',
      schemaVersion: '1',
    );

    await tester.pumpWidget(const IlaiosDesktopApp(projection: projection));
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

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: projection,
        locale: IlaiosLocale.turkish,
      ),
    );
    await tester.tap(find.byKey(const ValueKey('nav-goals')));
    await tester.pumpAndSettle();

    final turkishGoals = find.byKey(const Key('reference-goals-page'));
    expect(
      find.descendant(of: turkishGoals, matching: find.text('İş güncellemesi')),
      findsWidgets,
    );
    expect(
      find.descendant(of: turkishGoals, matching: find.text('job.updated')),
      findsNothing,
    );

    expect(projection.lastEvent, 'job.updated');
  });

  testWidgets('Home does not treat all pending work as approvals when admissions are present', (
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
          jobCount: 1,
          lastEvent: null,
          schemaVersion: '1',
        ),
        operationalSnapshot: const OperationalSnapshot(
          runtimeRoutes: <Map<String, Object?>>[],
          schedulerState: <String, Object?>{
            'leases': <Object?>[],
          },
          grantsState: <String, Object?>{},
          governanceState: <String, Object?>{
            'work': <Object?>[
              <String, Object?>{
                'request_id': 'req-no-human-approval',
                'status': 'pending',
              },
            ],
            'admissions': <Object?>[],
          },
          evidenceRecords: [],
          liveEvents: <Map<String, Object?>>[],
          agentState: <String, Object?>{},
        ),
      ),
    );
    await tester.pumpAndSettle();

    final attention = find.byKey(const Key('command-center-attention'));
    expect(attention, findsOneWidget);
    expect(
      find.descendant(of: attention, matching: find.text('No action is required')),
      findsOneWidget,
    );
    expect(
      find.descendant(of: attention, matching: find.textContaining('approval is waiting')),
      findsNothing,
    );
    expect(
      find.descendant(of: attention, matching: find.textContaining('approvals are waiting')),
      findsNothing,
    );
  });
}
