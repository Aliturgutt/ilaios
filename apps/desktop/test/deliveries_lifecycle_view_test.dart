import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/deliveries/deliveries_view.dart';
import 'package:ilaios_desktop/features/deliveries/delivery_identity_scope.dart';
import 'package:ilaios_desktop/features/deliveries/delivery_local_storage.dart';

void main() {
  const session = DesktopUserSession(
    sessionId: 'session-a',
    providerId: 'google',
    principalId: 'principal-a',
    tenantId: 'tenant-a',
  );
  const finished = EvidenceRecord(
    sequence: 1,
    executionId: 'exec-finished',
    artifactDigest:
        '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
    action: 'web.finished_product',
    previousHash: 'previous-a',
    recordHash: 'record-a',
  );
  const running = EvidenceRecord(
    sequence: 2,
    executionId: 'exec-running',
    artifactDigest:
        'abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789',
    action: 'web.running',
    previousHash: 'previous-b',
    recordHash: 'record-b',
  );
  const snapshot = OperationalSnapshot(
    runtimeRoutes: <Map<String, Object?>>[],
    schedulerState: <String, Object?>{},
    grantsState: <String, Object?>{},
    governanceState: <String, Object?>{},
    evidenceRecords: <EvidenceRecord>[finished, running],
    liveEvents: <Map<String, Object?>>[],
  );

  testWidgets('Archive removes a finished delivery from active list and Restore returns it', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1366, 768));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final root = await Directory.systemTemp.createTemp('ilaios-archive-view-');
    addTearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });

    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          theme: IlaiosTheme.dark,
          home: Scaffold(
            body: DeliveryIdentityScope(
              session: session,
              child: DeliveriesView(
                snapshot: snapshot,
                status: 'Operational APIs connected',
                archiveStoreFactory: (authenticatedSession) =>
                    DeliveryArchiveStore.forSession(
                  authenticatedSession,
                  stateRoot: root,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('save-artifact-1')), findsOneWidget);
    expect(find.byKey(const ValueKey('save-artifact-2')), findsNothing);
    expect(find.text('Completed'), findsWidgets);

    await tester.tap(find.byKey(const ValueKey('delete-local-artifact-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Remove from list'));
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('save-artifact-1')), findsNothing);
    expect(find.textContaining('moved to Archive'), findsOneWidget);

    await tester.tap(find.text('Archive'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('save-artifact-1')), findsOneWidget);
    expect(find.text('Archived'), findsWidgets);

    await tester.tap(find.byKey(const ValueKey('delete-local-artifact-1')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Restore'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('save-artifact-1')), findsNothing);

    await tester.tap(find.text('All'));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('save-artifact-1')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Outputs never promotes non-finished evidence into a delivery', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final root = await Directory.systemTemp.createTemp('ilaios-output-projection-');
    addTearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });

    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          theme: IlaiosTheme.light,
          home: Scaffold(
            body: DeliveryIdentityScope(
              session: session,
              child: DeliveriesView(
                snapshot: snapshot,
                status: 'Operational APIs connected',
                archiveStoreFactory: (authenticatedSession) =>
                    DeliveryArchiveStore.forSession(
                  authenticatedSession,
                  stateRoot: root,
                ),
              ),
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('save-artifact-1')), findsOneWidget);
    expect(find.byKey(const ValueKey('save-artifact-2')), findsNothing);
    expect(find.text('1'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
