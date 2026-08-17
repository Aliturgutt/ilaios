import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('operational right rail remains fully visible at reference size', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    final status = find.byKey(const Key('reference-status-card'));
    final logs = find.byKey(const Key('reference-latest-logs'));
    expect(status, findsOneWidget);
    expect(logs, findsOneWidget);
    expect(tester.getTopLeft(status).dy, greaterThanOrEqualTo(80));
    expect(tester.getBottomRight(logs).dy, lessThan(978));
  });
}
