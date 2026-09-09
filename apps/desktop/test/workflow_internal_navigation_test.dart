import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('canonical Workflows uses persistent seven-page navigation without a fabricated creation shortcut', (
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

    expect(find.byKey(const Key('reference-secondary-navigation')), findsNothing);
    expect(find.byKey(const ValueKey('nav-goals')), findsNothing);
    expect(find.byKey(const ValueKey('nav-liveWorkspace')), findsNothing);
    expect(find.byKey(const ValueKey('nav-costs')), findsNothing);

    await tester.tap(find.byKey(const ValueKey('nav-agents')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('reference-agents-page')), findsOneWidget);
    expect(find.byKey(const Key('reference-workflows-page')), findsNothing);

    expect(tester.takeException(), isNull);
  });
}
