import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('command-center right rail remains fully visible at reference size', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    final session = find.byKey(const Key('command-center-session'));
    final activities = find.byKey(const Key('command-center-activities'));
    final alerts = find.byKey(const Key('command-center-alerts'));
    expect(session, findsOneWidget);
    expect(activities, findsOneWidget);
    expect(alerts, findsOneWidget);
    expect(tester.getTopLeft(session).dy, greaterThanOrEqualTo(70));
    expect(tester.getBottomRight(alerts).dy, lessThan(978));
  });
}
