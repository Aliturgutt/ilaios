import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/dashboard/reference_home_motion_surface.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Home renders closure viewports in both themes without geometry regressions', (
    WidgetTester tester,
  ) async {
    for (final mode in <ThemeMode>[ThemeMode.dark, ThemeMode.light]) {
      for (final size in <Size>[
        const Size(1366, 768),
        const Size(1440, 900),
        const Size(1920, 1080),
      ]) {
        await tester.binding.setSurfaceSize(size);
        await tester.pumpWidget(IlaiosDesktopApp(themeMode: mode));
        await tester.pump(const Duration(milliseconds: 40));

        expect(tester.takeException(), isNull, reason: '$mode viewport $size');
        expect(find.byKey(const Key('command-center-home')), findsOneWidget);
        expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
        expect(find.byKey(const Key('command-center-orbit-motion')), findsOneWidget);
        expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);
      }
    }
    await tester.binding.setSurfaceSize(null);
  });

  testWidgets('Turkish light Home remains truthful with the layered motion field present', (
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
    await tester.pump(const Duration(milliseconds: 40));

    expect(tester.takeException(), isNull);
    expect(find.text('Ana Kontrol Merkezi'), findsOneWidget);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsOneWidget);
    expect(find.text('96%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });

  testWidgets('live theme switch preserves one motion component and geometry', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp(themeMode: ThemeMode.dark));
    await tester.pump(const Duration(milliseconds: 80));
    final motionFinder = find.byType(ReferenceHomeMotionSurface);
    expect(motionFinder, findsOneWidget);
    final beforeState = tester.state(motionFinder);
    final beforeRect = tester.getRect(find.byKey(const Key('command-center-orbit-motion')));

    await tester.pumpWidget(const IlaiosDesktopApp(themeMode: ThemeMode.light));
    await tester.pump(const Duration(milliseconds: 40));

    final afterState = tester.state(motionFinder);
    final afterRect = tester.getRect(find.byKey(const Key('command-center-orbit-motion')));
    expect(identical(beforeState, afterState), isTrue);
    expect(afterRect, beforeRect);
    expect(tester.takeException(), isNull);
  });

  testWidgets('platform reduced motion freezes a static layered symbol', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      MaterialApp(
        builder: (context, child) => MediaQuery(
          data: MediaQuery.of(context).copyWith(disableAnimations: true),
          child: child!,
        ),
        home: const Scaffold(
          body: ReferenceHomeMotionSurface(
            child: SizedBox.expand(key: Key('static-home-underlay')),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('static-home-underlay')), findsOneWidget);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsOneWidget);
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
    await tester.pump(const Duration(milliseconds: 40));

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
    await tester.pump(const Duration(milliseconds: 40));

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
