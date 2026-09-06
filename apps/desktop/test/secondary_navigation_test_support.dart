import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> openSecondaryDesktopSection(
  WidgetTester tester,
  String localizedLabel,
) async {
  final menu = find.byKey(const Key('reference-secondary-navigation'));
  expect(menu, findsOneWidget);
  await tester.tap(menu);
  await tester.pumpAndSettle();

  final destination = find.text(localizedLabel).last;
  expect(destination, findsOneWidget);
  await tester.tap(destination);
  await tester.pumpAndSettle();
}
