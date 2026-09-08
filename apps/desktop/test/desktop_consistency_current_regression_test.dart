import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('canonical seven-page shell keeps projection truth without restoring Goals', (
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
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('canonical-7-page-sidebar')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-goals')), findsNothing);
    expect(find.byKey(const Key('reference-secondary-navigation')), findsNothing);
    expect(projection.lastEvent, 'job.updated');

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: projection,
        locale: IlaiosLocale.turkish,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('canonical-7-page-sidebar')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-goals')), findsNothing);
    expect(projection.lastEvent, 'job.updated');
  });

  testWidgets('pending work without approval admission stays out of Approvals', (
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

    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-approvals-page')), findsOneWidget);
    expect(find.byKey(const Key('approvals-table')), findsOneWidget);
    expect(find.text('req-no-human-approval'), findsNothing);
    expect(find.byKey(const Key('approvals-selected-request')), findsNothing);
    expect(find.byKey(const Key('approvals-right-rail')), findsOneWidget);
  });
}
