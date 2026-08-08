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
    expect(find.text('—'), findsNWidgets(3));
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
        ),
        onRefreshRequested: () => refreshRequests += 1,
      ),
    );

    expect(find.text('2'), findsOneWidget);
    expect(find.text('5'), findsOneWidget);
    expect(find.text('job.updated'), findsOneWidget);
    await tester.tap(find.byKey(const Key('refresh-command')));
    expect(refreshRequests, 1);
  });
}
