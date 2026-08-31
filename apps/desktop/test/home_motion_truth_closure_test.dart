import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('V4 Home renders closure viewports in both themes without decorative motion', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    for (final mode in <ThemeMode>[ThemeMode.dark, ThemeMode.light]) {
      for (final size in <Size>[
        const Size(1366, 768),
        const Size(1440, 900),
        const Size(1920, 1080),
      ]) {
        await tester.binding.setSurfaceSize(size);
        await tester.pumpWidget(IlaiosDesktopApp(themeMode: mode));
        await tester.pumpAndSettle();

        expect(tester.takeException(), isNull, reason: '$mode viewport $size');
        expect(find.byKey(const Key('command-center-home')), findsOneWidget);
        expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
        expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);
        expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);
      }
    }
  });

  testWidgets('Turkish light V4 Home remains truthful without the removed motion field', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('İş başlat'), findsOneWidget);
    expect(find.text('Ana Kontrol Merkezi'), findsNothing);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });

  testWidgets('live theme switch preserves V4 Home geometry without restoring motion', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp(themeMode: ThemeMode.dark));
    await tester.pumpAndSettle();
    final beforeRect = tester.getRect(find.byKey(const Key('command-center-hero')));
    expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);

    await tester.pumpWidget(const IlaiosDesktopApp(themeMode: ThemeMode.light));
    await tester.pumpAndSettle();

    final afterRect = tester.getRect(find.byKey(const Key('command-center-hero')));
    expect(afterRect, beforeRect);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('platform reduced-motion setting does not reintroduce removed V4 decoration', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MediaQuery(
        data: const MediaQueryData(disableAnimations: true),
        child: const IlaiosDesktopApp(),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('missing work progress renders an unavailable track, never fake zero', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{
        'work': <Map<String, Object?>>[
          <String, Object?>{
            'request_id': 'work-without-authoritative-progress',
            'status': 'running',
          },
        ],
      },
      evidenceRecords: [],
      liveEvents: <Map<String, Object?>>[],
    );

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 1,
          jobCount: 1,
          lastEvent: null,
          schemaVersion: '1',
        ),
        operationalSnapshot: snapshot,
        operationalStatus: 'Operational APIs connected',
      ),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('work-without-authoritative-progress'), findsOneWidget);
    expect(find.byKey(const Key('focus-progress-unavailable-track')), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsNothing);
  });

  testWidgets('malformed Home telemetry fails closed instead of fabricating metrics', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{
        'health_percent': 'NaN',
      },
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{
        'total_cost_usd': 'not-a-number',
        'work': <Map<String, Object?>>[
          <String, Object?>{
            'request_id': 'invalid-negative-progress',
            'status': 'running',
            'progress_percent': -1,
          },
          <String, Object?>{
            'request_id': 'invalid-overflow-progress',
            'status': 'running',
            'progress': 101,
          },
          <String, Object?>{
            'request_id': 'invalid-nan-progress',
            'status': 'running',
            'progress_percent': 'NaN',
          },
        ],
      },
      evidenceRecords: [],
      liveEvents: <Map<String, Object?>>[],
    );

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 1,
          jobCount: 3,
          lastEvent: null,
          schemaVersion: '1',
        ),
        operationalSnapshot: snapshot,
        operationalStatus: 'Operational APIs connected',
      ),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('invalid-negative-progress'), findsOneWidget);
    expect(find.text('invalid-overflow-progress'), findsOneWidget);
    expect(find.text('invalid-nan-progress'), findsOneWidget);
    expect(
      find.byKey(const Key('focus-progress-unavailable-track')),
      findsNWidgets(3),
    );
    expect(find.byType(LinearProgressIndicator), findsNothing);
    expect(find.text('Connected'), findsWidgets);
    expect(find.textContaining('NaN'), findsNothing);
    expect(find.textContaining('not-a-number'), findsNothing);
  });
}
