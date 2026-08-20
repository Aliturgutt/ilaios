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

Future<void> _pumpIo(WidgetTester tester, {int frames = 8}) async {
  for (var i = 0; i < frames; i += 1) {
    await tester.pump(const Duration(milliseconds: 25));
  }
}

Future<void> _pumpUntil(
  WidgetTester tester,
  Finder finder, {
  required bool present,
}) async {
  for (var i = 0; i < 40; i += 1) {
    await tester.pump(const Duration(milliseconds: 25));
    final found = finder.evaluate().isNotEmpty;
    if (found == present) return;
  }
  fail('Timed out waiting for $finder present=$present');
}

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
    await _pumpIo(tester);

    expect(find.byKey(const ValueKey('save-artifact-1')), findsOneWidget);
    expect(find.byKey(const ValueKey('save-artifact-2')), findsNothing);
    expect(find.text('Completed'), findsWidgets);

    await tester.tap(find.byKey(const ValueKey('delete-local-artifact-1')));
    await _pumpIo(tester, frames: 2);
    await tester.tap(find.text('Remove from list'));
    await _pumpUntil(
      tester,
      find.byKey(const ValueKey('save-artifact-1')),
      present: false,
    );

    expect(find.textContaining('moved to Archive'), findsOneWidget);

    await tester.tap(find.text('Archive'));
    await _pumpIo(tester, frames: 2);
    expect(find.byKey(const ValueKey('save-artifact-1')), findsOneWidget);
    expect(find.text('Archived'), findsWidgets);

    await tester.tap(find.byKey(const ValueKey('delete-local-artifact-1')));
    await _pumpIo(tester, frames: 2);
    await tester.tap(find.text('Restore'));
    await _pumpUntil(
      tester,
      find.byKey(const ValueKey('save-artifact-1')),
      present: false,
    );

    await tester.tap(find.text('All'));
    await _pumpUntil(
      tester,
      find.byKey(const ValueKey('save-artifact-1')),
      present: true,
    );
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
    await _pumpIo(tester);

    expect(find.byKey(const ValueKey('save-artifact-1')), findsOneWidget);
    expect(find.byKey(const ValueKey('save-artifact-2')), findsNothing);
    expect(find.text('1'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
