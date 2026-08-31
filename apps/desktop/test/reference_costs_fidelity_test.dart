import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/operations/reference_costs_view_v2.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Costs V4 collapses analytics when authoritative telemetry is unavailable', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-costs')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-costs-page')), findsOneWidget);
    expect(find.byKey(const Key('costs-summary-strip')), findsNothing);
    expect(find.byKey(const Key('costs-trend-panel')), findsNothing);
    expect(find.byKey(const Key('costs-distribution-panel')), findsNothing);
    expect(find.byKey(const Key('costs-resources-panel')), findsNothing);
    expect(find.byKey(const Key('costs-alerts-panel')), findsNothing);
    expect(find.byKey(const Key('costs-recommendations-panel')), findsNothing);
    expect(find.byKey(const Key('costs-reports-panel')), findsNothing);
    expect(find.text('Cost data is not available yet'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Costs empty state never fabricates reference screenshot money', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.turkish,
        onChanged: (_) {},
        child: MaterialApp(
          theme: IlaiosTheme.light,
          home: const Scaffold(
            body: ReferenceCostsViewV2(
              snapshot: OperationalSnapshot.unavailable(),
              status: 'Operational APIs unavailable',
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Maliyetler'), findsOneWidget);
    expect(find.textContaining(r'$12,842.45'), findsNothing);
    expect(find.textContaining(r'$13,210.00'), findsNothing);
    expect(find.textContaining(r'$20,000'), findsNothing);
    expect(find.text('Maliyet verisi henüz mevcut değil'), findsOneWidget);
    expect(find.textContaining('Yetkili sağlayıcı veya yürütme maliyet telemetrisi'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Costs renders only authority-derived cost telemetry', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{
        'costs': <String, Object?>{
          'total_cost_usd': 4321.25,
          'forecast_cost_usd': 4700.00,
          'budget_usd': 10000.00,
          'savings_usd': 310.50,
          'next_month_forecast_usd': 4850.00,
          'billing_period': 'August 2026',
          'cost_trend': <Object?>[
            <String, Object?>{'date': '17 Aug', 'cost_usd': 210.0},
            <String, Object?>{'date': '18 Aug', 'cost_usd': 275.0},
          ],
          'service_costs': <Object?>[
            <String, Object?>{'service': 'Compute', 'cost_usd': 2100.0},
            <String, Object?>{'service': 'Storage', 'cost_usd': 900.0},
          ],
          'resources': <Object?>[
            <String, Object?>{
              'name': 'worker-01',
              'type': 'Compute',
              'service': 'Runtime',
              'usage': '12 h',
              'cost_usd': 122.75,
            },
          ],
          'budget_alerts': <Object?>[
            <String, Object?>{'title': 'Budget threshold', 'description': '80% threshold configured'},
          ],
          'recommendations': <Object?>[
            <String, Object?>{'title': 'Idle runtime', 'description': 'Review idle capacity', 'value': r'$40'},
          ],
          'reports': <Object?>[
            <String, Object?>{'title': 'Monthly report', 'format': 'PDF'},
          ],
        },
      },
      evidenceRecords: <Never>[],
      liveEvents: <Map<String, Object?>>[],
    );

    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          theme: IlaiosTheme.dark,
          home: const Scaffold(
            body: ReferenceCostsViewV2(snapshot: snapshot, status: 'Operational APIs connected'),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('costs-summary-strip')), findsOneWidget);
    expect(find.text(r'$4,321.25'), findsWidgets);
    expect(find.text(r'$4,700.00'), findsOneWidget);
    expect(find.text('Compute'), findsWidgets);
    expect(find.text('worker-01'), findsOneWidget);
    expect(find.text('Budget threshold'), findsOneWidget);
    expect(find.text('Idle runtime'), findsOneWidget);
    expect(find.text('Monthly report'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
