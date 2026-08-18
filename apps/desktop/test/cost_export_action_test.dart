import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/operations/reference_costs_view_v3.dart';
import 'package:ilaios_desktop/services/cost_export_service.dart';

const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{},
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{
    'costs': <String, Object?>{
      'total_cost_usd': 4321.25,
      'forecast_cost_usd': 4700.00,
      'billing_period': 'August 2026',
      'service_costs': <Object?>[
        <String, Object?>{'service': 'Compute', 'cost_usd': 2100.0},
      ],
    },
  },
  evidenceRecords: <Never>[],
  liveEvents: <Map<String, Object?>>[],
);

void main() {
  test('cost export writes only authoritative telemetry', () async {
    final root = await Directory.systemTemp.createTemp('ilaios-cost-export-test-');
    addTearDown(() async {
      if (await root.exists()) await root.delete(recursive: true);
    });

    final path = await CostExportService.export(
      _snapshot,
      rootDirectory: root,
      now: DateTime.utc(2026, 8, 18, 9, 30),
    );

    final output = File(path);
    expect(await output.exists(), isTrue);
    final decoded = jsonDecode(await output.readAsString()) as Map<String, dynamic>;
    expect(decoded['schema_version'], 1);
    expect(decoded['source'], 'authoritative-operational-snapshot');
    expect(decoded['exported_at'], '2026-08-18T09:30:00.000Z');
    expect(decoded['costs'], _snapshot.governanceState['costs']);
    expect(decoded.containsKey('token'), isFalse);
    expect(decoded.containsKey('secret'), isFalse);
  });

  test('cost export fails closed without authoritative telemetry', () async {
    expect(
      () => CostExportService.export(
        const OperationalSnapshot.unavailable(),
        rootDirectory: Directory.systemTemp,
      ),
      throwsA(isA<CostExportException>()),
    );
  });

  testWidgets('Costs Export control invokes a real action', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var calls = 0;
    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          theme: IlaiosTheme.dark,
          home: Scaffold(
            body: ReferenceCostsViewV3(
              snapshot: _snapshot,
              status: 'Operational APIs connected',
              onExport: (_) async {
                calls += 1;
                return r'C:\Users\USER\Downloads\ILAIOS\costs.json';
              },
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    final export = find.byKey(const Key('costs-export-action'));
    expect(export, findsOneWidget);
    await tester.tap(export);
    await tester.pump();

    expect(calls, 1);
    expect(find.textContaining('Cost report saved:'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Costs Export is disabled when telemetry is unavailable', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    var calls = 0;
    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          theme: IlaiosTheme.dark,
          home: Scaffold(
            body: ReferenceCostsViewV3(
              snapshot: const OperationalSnapshot.unavailable(),
              status: 'Operational APIs unavailable',
              onExport: (_) async {
                calls += 1;
                return 'should-not-run';
              },
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('costs-export-action')));
    await tester.pump();
    expect(calls, 0);
  });
}
