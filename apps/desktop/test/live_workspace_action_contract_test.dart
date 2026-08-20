import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  Widget testApp({
    required OperationalSnapshot snapshot,
  }) {
    return IlaiosLocaleScope(
      locale: IlaiosLocale.english,
      onChanged: (_) {},
      child: IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 1,
          jobCount: 1,
          lastEvent: 'workspace.updated',
          schemaVersion: '1',
        ),
        operationalSnapshot: snapshot,
        operationalStatus: 'Operational APIs connected',
      ),
    );
  }

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
        testApp(
          snapshot: const OperationalSnapshot(
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

  testWidgets(
    'scheduler and governance session state outrank stale generic live events',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1600, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(
        testApp(
          snapshot: const OperationalSnapshot(
            runtimeRoutes: <Map<String, Object?>>[],
            schedulerState: <String, Object?>{
              'project_name': 'Authoritative Project',
              'workspace_mode': 'governed',
              'owner': 'principal-a',
            },
            grantsState: <String, Object?>{},
            governanceState: <String, Object?>{
              'sync_state': 'authoritative-sync',
            },
            evidenceRecords: <Never>[],
            liveEvents: <Map<String, Object?>>[
              <String, Object?>{
                'event_type': 'unrelated.telemetry.updated',
                'project_name': 'Poisoned Project',
                'workspace_mode': 'poisoned',
                'owner': 'attacker',
                'sync_state': 'stale-sync',
              },
            ],
          ),
        ),
      );
      await tester.pumpAndSettle();
      await openWorkspace(tester);

      expect(find.text('Authoritative Project'), findsWidgets);
      expect(find.text('governed'), findsWidgets);
      expect(find.text('authoritative-sync'), findsWidgets);
      expect(find.text('Poisoned Project'), findsNothing);
      expect(find.text('poisoned'), findsNothing);
      expect(find.text('stale-sync'), findsNothing);
    },
  );
}
