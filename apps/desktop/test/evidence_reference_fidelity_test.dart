import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/operations/operational_views.dart';

void main() {
  const first = EvidenceRecord(
    sequence: 1,
    executionId: 'execution-test-001',
    artifactDigest: 'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
    action: 'QA validation completed',
    previousHash: '',
    recordHash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
  );
  const second = EvidenceRecord(
    sequence: 2,
    executionId: 'execution-release-002',
    artifactDigest: 'sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
    action: 'Release artifact verified',
    previousHash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
    recordHash: 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
  );
  const snapshot = OperationalSnapshot(
    runtimeRoutes: <Map<String, Object?>>[],
    schedulerState: <String, Object?>{},
    grantsState: <String, Object?>{},
    governanceState: <String, Object?>{},
    evidenceRecords: <EvidenceRecord>[first, second],
    liveEvents: <Map<String, Object?>>[],
  );

  Future<void> pump(
    WidgetTester tester, {
    required ThemeData theme,
    required IlaiosLocale locale,
  }) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: locale,
        onChanged: (_) {},
        child: MaterialApp(
          theme: theme,
          home: const Scaffold(
            body: EvidenceView(
              snapshot: snapshot,
              status: 'Operational APIs connected',
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();
  }

  testWidgets('evidence V4 surface renders authoritative records and contextual detail in dark mode', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await pump(tester, theme: IlaiosTheme.dark, locale: IlaiosLocale.turkish);

    expect(find.byKey(const Key('reference-evidence-page')), findsOneWidget);
    expect(find.byKey(const Key('evidence-kpis')), findsOneWidget);
    expect(find.byKey(const Key('evidence-table')), findsOneWidget);
    expect(find.byKey(const Key('selected-evidence-panel')), findsNothing);
    expect(find.text('Kanıtlar'), findsOneWidget);
    expect(find.text('Release artifact verified'), findsOneWidget);
    expect(find.text('312'), findsNothing);

    await tester.tap(find.byKey(const ValueKey('evidence-row-2')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('selected-evidence-panel')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('evidence V4 surface remains valid in light mode', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await pump(tester, theme: IlaiosTheme.light, locale: IlaiosLocale.english);

    expect(find.text('Evidence'), findsOneWidget);
    expect(find.byKey(const Key('evidence-tabs')), findsOneWidget);
    expect(find.byKey(const ValueKey('evidence-row-2')), findsOneWidget);
    expect(find.byKey(const Key('selected-evidence-panel')), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
