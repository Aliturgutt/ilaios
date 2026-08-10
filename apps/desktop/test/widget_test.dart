import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('disconnected shell never fabricates authoritative state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const IlaiosDesktopApp());

    expect(
      find.text('Authoritative control plane unavailable'),
      findsOneWidget,
    );
    expect(find.text('—'), findsNWidgets(6));
    final button = tester.widget<FilledButton>(
      find.byKey(const Key('refresh-command')),
    );
    expect(button.onPressed, isNull);
  });

  testWidgets('connected shell projects supplied query and event state', (
    WidgetTester tester,
  ) async {
    var refreshRequests = 0;
    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 2,
          jobCount: 5,
          lastEvent: 'job.updated',
          schemaVersion: '1',
        ),
        onRefreshRequested: () => refreshRequests += 1,
      ),
    );

    expect(find.text('2'), findsOneWidget);
    expect(find.text('5'), findsOneWidget);
    expect(find.text('1'), findsOneWidget);
    await tester.tap(find.byKey(const Key('refresh-command')));
    expect(refreshRequests, 1);
  });

  testWidgets('wide navigation exposes only verified backend surfaces', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());

    expect(find.text('Control Center'), findsWidgets);
    expect(find.text('Live Execution'), findsWidgets);
    expect(find.text('Evidence'), findsOneWidget);
    expect(find.text('Governance'), findsWidgets);
    expect(find.text('Agents'), findsNothing);
    expect(find.text('Approvals'), findsNothing);
  });

  testWidgets('verified operational snapshot is projected read-only', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 1,
          jobCount: 1,
          lastEvent: 'job.updated',
          schemaVersion: '1',
        ),
        operationalSnapshot: OperationalSnapshot(
          runtimeRoutes: <Map<String, Object?>>[
            <String, Object?>{'sequence': 1, 'provider_id': 'local'},
          ],
          schedulerState: <String, Object?>{
            'leases': <Object?>[<String, Object?>{'task_id': 'task-1'}],
            'effects': <Object?>[],
          },
          grantsState: <String, Object?>{
            'grants': <Object?>[],
            'revoked': <Object?>[],
            'stopped': <Object?>[],
          },
          governanceState: <String, Object?>{'pending': 0},
          evidenceRecords: <Map<String, Object?>>[
            <String, Object?>{'digest': 'abcdef0123456789abcdef'},
          ],
          liveEvents: <Map<String, Object?>>[
            <String, Object?>{'event_type': 'job.updated'},
          ],
        ),
        operationalStatus: 'Operational APIs connected',
      ),
    );

    expect(find.text('Operational APIs connected'), findsOneWidget);
    expect(find.text('Runtime routes'), findsOneWidget);
    expect(find.text('Live events'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('nav-evidence')));
    await tester.pumpAndSettle();
    expect(find.text('Verified records'), findsOneWidget);
    expect(find.text('1'), findsWidgets);

    await tester.tap(find.byKey(const ValueKey('nav-liveExecution')));
    await tester.pumpAndSettle();
    expect(find.text('Active leases'), findsOneWidget);
    expect(find.text('Last live event'), findsOneWidget);
    expect(find.text('job.updated'), findsOneWidget);
  });
}
