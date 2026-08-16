import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('primary Desktop navigation is semantic and every destination is reachable', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final semantics = tester.ensureSemantics();

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    // Flutter may merge descendant semantics into the labeled navigation
    // container. Match the required label within that semantic node rather
    // than assuming it is the node's entire synthesized label.
    expect(
      find.bySemanticsLabel(RegExp(r'ILAIOS Desktop primary navigation')),
      findsOneWidget,
    );
    expect(find.bySemanticsLabel(RegExp(r'ILAIOS')), findsWidgets);

    for (final destination in <String>[
      'home',
      'goals',
      'workflows',
      'agents',
      'liveWorkspace',
      'artifacts',
      'approvals',
      'evidence',
      'costs',
      'settings',
    ]) {
      final navigation = find.byKey(ValueKey('nav-$destination'));
      expect(navigation, findsOneWidget, reason: 'Missing $destination navigation');
      await tester.tap(navigation);
      await tester.pumpAndSettle();
      expect(
        tester.takeException(),
        isNull,
        reason: '$destination navigation threw during rendering',
      );
    }

    // WidgetTester verifies semantics handles before tearDown callbacks run.
    // Dispose explicitly while the test body is still active.
    semantics.dispose();
  });
}
