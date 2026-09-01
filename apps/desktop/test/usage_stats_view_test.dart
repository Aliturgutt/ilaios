import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/operations/support_views.dart';
import 'package:ilaios_desktop/features/operations/usage_stats_view.dart';

void main() {
  const snapshot = OperationalSnapshot(
    runtimeRoutes: <Map<String, Object?>>[
      <String, Object?>{
        'sequence': 1,
        'created_at': '2026-08-18T18:00:00Z',
        'agent_id': 'ilaios.agent.web',
        'skill_id': 'web.build',
        'capability': 'web-generation',
        'provider_id': 'openrouter',
        'output': <String, Object?>{
          'model_id': 'model-a',
          'input_tokens': 100,
          'output_tokens': 20,
          'cache_read_tokens': 5,
          'actual_cost_usd': 0.10,
          'reserved_cost_usd': 0.20,
          'latency_ms': 100,
          'status': 'completed',
        },
      },
      <String, Object?>{
        'sequence': 2,
        'created_at': '2026-08-18T18:01:00Z',
        'agent_id': 'ilaios.agent.video',
        'skill_id': 'video.route',
        'capability': 'video-generation',
        'provider_id': 'google',
        'output': <String, Object?>{
          'model_id': 'model-b',
          'input_tokens': 80,
          'output_tokens': 40,
          'actual_cost_usd': 0.05,
          'reserved_cost_usd': 0.08,
          'latency_ms': 300,
          'status': 'failed',
        },
      },
      <String, Object?>{
        'sequence': 3,
        'created_at': '2026-08-18T18:02:00Z',
        'agent_id': 'ilaios.agent.web',
        'skill_id': 'web.verify',
        'capability': 'web-verification',
        'provider_id': 'openrouter',
        'output': <String, Object?>{
          'model_id': 'model-a',
          'latency_ms': 200,
        },
      },
    ],
    schedulerState: <String, Object?>{},
    grantsState: <String, Object?>{},
    governanceState: <String, Object?>{},
    evidenceRecords: <Never>[],
    liveEvents: <Map<String, Object?>>[],
  );

  test('UsageStatsModel aggregates only observed runtime-route telemetry', () {
    final model = UsageStatsModel.fromSnapshot(snapshot);

    expect(model.observedRoutes, 3);
    expect(model.routesWithTokenTelemetry, 2);
    expect(model.routesWithInputTokens, 2);
    expect(model.routesWithOutputTokens, 2);
    expect(model.routesWithCacheReadTokens, 1);
    expect(model.routesWithCacheWriteTokens, 0);
    expect(model.routesWithCostTelemetry, 2);
    expect(model.routesWithReservedCostTelemetry, 2);
    expect(model.routesWithLatencyTelemetry, 3);
    expect(model.routesWithProvider, 3);
    expect(model.routesWithModel, 3);
    expect(model.routesWithStatus, 2);
    expect(model.successfulRoutes, 1);
    expect(model.failedRoutes, 1);
    expect(model.routesWithOutcomeTelemetry, 2);
    expect(model.observedSuccessRate, 50);
    expect(model.inputTokens, 180);
    expect(model.outputTokens, 60);
    expect(model.cacheReadTokens, 5);
    expect(model.cacheWriteTokens, 0);
    expect(model.observedTokens, 245);
    expect(model.observedActualCostUsd, closeTo(0.15, 0.000001));
    expect(model.observedReservedCostUsd, closeTo(0.28, 0.000001));
    expect(model.averageLatencyMs, closeTo(200, 0.000001));
    expect(model.p95LatencyMs, 300);

    expect(
      model.providers.map((row) => row.label).toList(),
      <String>['openrouter', 'google'],
    );
    expect(model.providers.first.routes, 2);
    expect(
      model.models.map((row) => row.label).toList(),
      <String>['model-a', 'model-b'],
    );
    expect(model.models.first.routes, 2);
    expect(model.history.first.sequence, 3);
    expect(model.history.last.sequence, 1);
  });

  test('UsageStatsModel does not fabricate unavailable totals', () {
    final model = UsageStatsModel.fromSnapshot(
      const OperationalSnapshot.unavailable(),
    );

    expect(model.observedRoutes, 0);
    expect(model.observedTokens, isNull);
    expect(model.observedActualCostUsd, isNull);
    expect(model.observedReservedCostUsd, isNull);
    expect(model.averageLatencyMs, isNull);
    expect(model.p95LatencyMs, isNull);
    expect(model.observedSuccessRate, isNull);
    expect(model.providers, isEmpty);
    expect(model.models, isEmpty);
    expect(model.history, isEmpty);
  });

  testWidgets('Costs surface opens and closes Usage & Stats without changing authority', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1500, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          theme: IlaiosTheme.dark,
          home: const Scaffold(
            body: CostsView(
              snapshot: snapshot,
              status: 'Operational APIs connected',
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-costs-page')), findsOneWidget);
    expect(find.byKey(const Key('usage-stats-page')), findsNothing);

    await tester.tap(find.byKey(const Key('costs-stats-toggle')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('usage-stats-page')), findsOneWidget);
    expect(find.text('Usage & Stats'), findsWidgets);
    expect(find.text('245'), findsWidgets);
    expect(find.text(r'$0.1500'), findsWidgets);
    expect(find.text('50.0%'), findsOneWidget);
    expect(find.text('openrouter'), findsWidgets);
    expect(find.text('model-a'), findsWidgets);
    expect(find.text('Cache write'), findsOneWidget);

    await tester.tap(find.byKey(const Key('costs-stats-toggle')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('usage-stats-page')), findsNothing);
    expect(find.byKey(const Key('reference-costs-page')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Usage & Stats remains overflow-safe on compact Desktop width', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(720, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: IlaiosTheme.dark,
        home: const Scaffold(
          body: UsageStatsView(
            snapshot: snapshot,
            status: 'Operational APIs connected',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('usage-stats-page')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Usage & Stats empty state keeps unavailable telemetry explicit', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1200, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        theme: IlaiosTheme.dark,
        home: const Scaffold(
          body: UsageStatsView(
            snapshot: OperationalSnapshot.unavailable(),
            status: 'Operational APIs unavailable',
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('usage-stats-page')), findsOneWidget);
    expect(find.text('—'), findsWidgets);
    expect(
      find.textContaining(
        'No synthetic token, cost, provider, model, latency or success-rate values are generated',
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });
}
