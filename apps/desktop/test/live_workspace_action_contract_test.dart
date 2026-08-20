import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  Future<void> openWorkspace(WidgetTester tester) async {
    await tester.tap(find.byKey(const ValueKey('nav-liveWorkspace')));
    await tester.pumpAndSettle();
  }

  Future<void> expectUnavailableAction(
    WidgetTester tester,
    Finder action,
    Pattern message,
  ) async {
    await tester.ensureVisible(action);
    await tester.tap(action);
    await tester.pumpAndSettle();
    expect(find.textContaining(message), findsOneWidget);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
  }

  testWidgets(
    'Live Workspace visible write-like actions fail closed without a governed API contract',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1600, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        const IlaiosDesktopApp(
          projection: ControlPlaneProjection(
            connected: true,
            status: 'Connected to authoritative control plane',
            goalCount: 1,
            jobCount: 1,
            lastEvent: 'workspace.updated',
            schemaVersion: '1',
          ),
          operationalSnapshot: OperationalSnapshot(
            runtimeRoutes: <Map<String, Object?>>[],
            schedulerState: <String, Object?>{
              'workers': <Object?>[
                <String, Object?>{
                  'worker_id': 'worker-1',
                  'name': 'Software Worker',
                  'status': 'active',
                  'principal_id': 'principal-a',
                },
              ],
            },
            grantsState: <String, Object?>{},
            governanceState: <String, Object?>{},
            evidenceRecords: <Never>[],
            liveEvents: <Map<String, Object?>>[],
          ),
          operationalStatus: 'Operational APIs connected',
        ),
      );
      await tester.pumpAndSettle();
      await openWorkspace(tester);

      for (final label in <String>['Full Screen', 'Share', 'Save']) {
        await expectUnavailableAction(
          tester,
          find.text(label),
          'not yet bound to an authoritative workspace API contract',
        );
      }

      await expectUnavailableAction(
        tester,
        find.text('Invite Agent'),
        'No authoritative Desktop API contract is available for inviting agents.',
      );

      final header = find.byKey(const Key('live-workspace-header'));
      final additionalActions = find.descendant(
        of: header,
        matching: find.byIcon(Icons.more_horiz_rounded),
      );
      expect(additionalActions, findsOneWidget);
      await expectUnavailableAction(
        tester,
        additionalActions,
        'No authoritative Desktop API contract is available for additional workspace actions.',
      );
    },
  );
}
