import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/dashboard/reference_home_motion_surface.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Home renders exact closure viewports without geometry regressions', (
    WidgetTester tester,
  ) async {
    for (final size in <Size>[
      const Size(1366, 768),
      const Size(1440, 900),
      const Size(1920, 1080),
    ]) {
      await tester.binding.setSurfaceSize(size);
      await tester.pumpWidget(const IlaiosDesktopApp());
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull, reason: 'viewport $size');
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
      expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);
    }
    await tester.binding.setSurfaceSize(null);
  });

  testWidgets('Turkish light Home remains truthful with the motion layer present', (
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
    expect(find.text('Ana Kontrol Merkezi'), findsOneWidget);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsOneWidget);
    expect(find.text('96%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });

  testWidgets('platform reduced motion keeps the existing hero static', (
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
    await tester.pump();

    expect(find.byKey(const Key('static-home-underlay')), findsOneWidget);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);
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
}
