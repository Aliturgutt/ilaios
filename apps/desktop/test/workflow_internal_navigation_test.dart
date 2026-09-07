import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

import 'secondary_navigation_test_support.dart';

void main() {
  testWidgets('V4 Workflows uses persistent navigation instead of a fabricated creation shortcut', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('nav-workflows')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('reference-workflows-page')), findsOneWidget);
    expect(find.byKey(const Key('new-workflow-button')), findsNothing);
    expect(find.text('New Workflow'), findsNothing);

    await openSecondaryDesktopSection(tester, DesktopSection.goals);

    expect(find.byKey(const Key('reference-goals-page')), findsOneWidget);
    expect(find.byKey(const Key('reference-workflows-page')), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
