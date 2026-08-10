import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('disconnected shell never fabricates authoritative state', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const IlaiosDesktopApp());

    expect(
      find.text('Authoritative control plane unavailable'),
      findsOneWidget,
    );
    expect(find.text('—'), findsNWidgets(4));
    final button = tester.widget<FilledButton>(
      find.byKey(const Key('refresh-command')),
    );
    expect(button.onPressed, isNull);
  });

  testWidgets('connected shell projects supplied query and event state', (
    WidgetTester tester,
  ) async {
    var refreshRequests = 0;
    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 2,
          jobCount: 5,
          lastEvent: 'job.updated',
          schemaVersion: '1',
        ),
        onRefreshRequested: () => refreshRequests += 1,
      ),
    );

    expect(find.text('2'), findsOneWidget);
    expect(find.text('5'), findsOneWidget);
    expect(find.text('job.updated'), findsOneWidget);
    expect(find.text('1'), findsOneWidget);
    await tester.tap(find.byKey(const Key('refresh-command')));
    expect(refreshRequests, 1);
  });

  testWidgets('wide navigation exposes only verified backend surfaces', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());

    expect(find.text('Control Center'), findsWidgets);
    expect(find.text('Live Execution'), findsWidgets);
    expect(find.text('Evidence'), findsOneWidget);
    expect(find.text('Governance'), findsWidgets);
    expect(find.text('Agents'), findsNothing);
    expect(find.text('Approvals'), findsNothing);

    await tester.tap(find.byKey(const ValueKey('nav-evidence')));
    await tester.pumpAndSettle();

    expect(
      find.textContaining('Evidence records remain server-owned'),
      findsOneWidget,
    );
  });
}
