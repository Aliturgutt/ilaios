import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _verified = EvidenceRecord(
  sequence: 1,
  executionId: 'exec-verified',
  artifactDigest: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  action: 'web.finished_product',
  previousHash: '',
  recordHash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
);

void main() {
  testWidgets('Deliveries ignores finished-product claims that exist only in live telemetry', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const unverifiedTelemetry = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{},
      evidenceRecords: <EvidenceRecord>[],
      liveEvents: <Map<String, Object?>>[
        <String, Object?>{
          'sequence': 1,
          'execution_id': 'exec-telemetry-only',
          'action': 'web.finished_product',
          'artifact_digest': 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
        },
      ],
    );

    await tester.pumpWidget(
      const IlaiosDesktopApp(operationalSnapshot: unverifiedTelemetry),
    );
    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('outputs-table')), findsOneWidget);
    expect(find.textContaining('exec-telemetry-only'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Deliveries accepts finished products only from verified evidence records', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{},
      evidenceRecords: <EvidenceRecord>[_verified],
      liveEvents: <Map<String, Object?>>[],
    );

    await tester.pumpWidget(
      const IlaiosDesktopApp(operationalSnapshot: snapshot),
    );
    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();

    expect(find.textContaining('exec-verified'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
