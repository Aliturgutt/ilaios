import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  Future<void> pumpDesktop(
    WidgetTester tester, {
    required OperationalSnapshot snapshot,
  }) async {
    await tester.pumpWidget(
      IlaiosLocaleScope(
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
      ),
    );
    await tester.pumpAndSettle();
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
    expect(tester.takeException(), isNull);
    await tester.tap(find.text('OK'));
    await tester.pumpAndSettle();
  }

  testWidgets(
    'Live Workspace visible write-like actions fail closed without a governed API contract',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1600, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await pumpDesktop(
        tester,
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
      );
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
    'authoritative workspace state outranks an unrelated latest live event',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1600, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await pumpDesktop(
        tester,
        snapshot: const OperationalSnapshot(
          runtimeRoutes: <Map<String, Object?>>[],
          schedulerState: <String, Object?>{
            'session_id': 'workspace-current',
            'project_name': 'Authoritative Project',
            'workspace_mode': 'Governed',
            'owner': 'scheduler-owner',
          },
          grantsState: <String, Object?>{},
          governanceState: <String, Object?>{
            'project_name': 'Governance Project',
          },
          evidenceRecords: <Never>[],
          liveEvents: <Map<String, Object?>>[
            <String, Object?>{
              'event_type': 'unrelated.telemetry',
              'message': 'Historical event',
              'project_name': 'Stale Event Project',
              'workspace_mode': 'stale-mode',
              'owner': 'stale-owner',
            },
          ],
        ),
      );
      await openWorkspace(tester);

      final header = find.byKey(const Key('live-workspace-header'));
      expect(
        find.descendant(
          of: header,
          matching: find.text('Authoritative Project'),
        ),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: header,
          matching: find.text('Stale Event Project'),
        ),
        findsNothing,
      );

      final summary = find.byKey(const Key('live-workspace-summary'));
      expect(
        find.descendant(of: summary, matching: find.text('Governed')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: summary, matching: find.text('stale-mode')),
        findsNothing,
      );
    },
  );
}
