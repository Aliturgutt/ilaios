import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';

Future<void> openSecondaryDesktopSection(
  WidgetTester tester,
  DesktopSection section,
) async {
  final menu = find.byKey(const Key('reference-secondary-navigation'));
  expect(menu, findsOneWidget);
  await tester.tap(menu);
  await tester.pumpAndSettle();

  final destination = find.byWidgetPredicate(
    (widget) =>
        widget is PopupMenuItem<DesktopSection> && widget.value == section,
  );
  expect(destination, findsOneWidget);
  await tester.tap(destination);
  await tester.pumpAndSettle();
}
