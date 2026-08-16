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
    addTearDown(semantics.dispose);

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(
      find.bySemanticsLabel('ILAIOS Desktop primary navigation'),
      findsOneWidget,
    );
    expect(find.bySemanticsLabel('ILAIOS'), findsOneWidget);

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
  });
}
