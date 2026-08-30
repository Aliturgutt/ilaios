import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{},
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{},
  evidenceRecords: <EvidenceRecord>[
    EvidenceRecord(
      sequence: 1,
      executionId: 'exec-web-01',
      artifactDigest: 'sha256:web-artifact',
      action: 'web.finished_product',
      previousHash: '',
      recordHash: 'record-hash-01',
    ),
    EvidenceRecord(
      sequence: 2,
      executionId: 'exec-video-02',
      artifactDigest: 'sha256:video-artifact',
      action: 'video.finished_product',
      previousHash: 'record-hash-01',
      recordHash: 'record-hash-02',
    ),
    EvidenceRecord(
      sequence: 3,
      executionId: 'exec-qa-03',
      artifactDigest: 'sha256:qa-report',
      action: 'qa.report.verified',
      previousHash: 'record-hash-02',
      recordHash: 'record-hash-03',
    ),
  ],
  liveEvents: <Map<String, Object?>>[],
);

void main() {
  Future<void> openOutputs(WidgetTester tester) async {
    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();
  }

  testWidgets('Outputs keeps the V4 dark hierarchy without legacy analytics', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        operationalSnapshot: _snapshot,
        operationalStatus: 'Connected to authoritative control plane',
      ),
    );
    await tester.pumpAndSettle();
    await openOutputs(tester);

    expect(find.byKey(const Key('reference-outputs-page')), findsOneWidget);
    expect(find.byKey(const Key('outputs-header')), findsOneWidget);
    expect(find.byKey(const Key('outputs-kpis')), findsOneWidget);
    expect(find.byKey(const Key('outputs-tabs')), findsOneWidget);
    expect(find.byKey(const Key('outputs-filters')), findsOneWidget);
    expect(find.byKey(const Key('outputs-table')), findsOneWidget);
    expect(find.byKey(const Key('outputs-distribution')), findsNothing);
    expect(find.byKey(const Key('outputs-activity')), findsNothing);
    expect(find.byKey(const Key('outputs-storage')), findsNothing);
    expect(find.text('Outputs'), findsOneWidget);
    expect(find.text('Web'), findsWidgets);
    expect(find.text('Video'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Outputs renders the V4 Turkish light surface', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
        operationalSnapshot: _snapshot,
        operationalStatus: 'Connected to authoritative control plane',
      ),
    );
    await tester.pumpAndSettle();
    await openOutputs(tester);

    expect(find.byKey(const Key('reference-outputs-page')), findsOneWidget);
    expect(find.text('Çıktılar'), findsWidgets);
    expect(find.text('Toplam Çıktı'), findsOneWidget);
    expect(find.text('Çıktı Dağılımı'), findsNothing);
    expect(find.text('Son Çıktı Aktivitesi'), findsNothing);
    expect(find.text('Depolama Kullanımı'), findsNothing);
    expect(find.text('2'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Outputs empty state never fabricates screenshot telemetry', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();
    await openOutputs(tester);

    expect(find.byKey(const Key('reference-outputs-page')), findsOneWidget);
    expect(find.byKey(const Key('outputs-kpis')), findsNothing);
    expect(find.text('248'), findsNothing);
    expect(find.text('186'), findsNothing);
    expect(find.text('128.4 GB'), findsNothing);
    expect(find.text('92'), findsNothing);
    expect(find.byKey(const Key('outputs-distribution')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Outputs remains on the same design family at compact viewport', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1180, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        operationalSnapshot: _snapshot,
      ),
    );
    await tester.pumpAndSettle();
    await openOutputs(tester);

    expect(find.byKey(const Key('reference-outputs-page')), findsOneWidget);
    expect(find.byKey(const Key('outputs-table')), findsOneWidget);
    expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsOneWidget);
    expect(find.text('Çıktılar'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
