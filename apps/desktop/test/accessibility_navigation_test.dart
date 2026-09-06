import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

import 'secondary_navigation_test_support.dart';

void main() {
  testWidgets('Desktop navigation is semantic and every destination is reachable', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final semantics = tester.ensureSemantics();

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(
      find.bySemanticsLabel(RegExp(r'ILAIOS Desktop primary navigation')),
      findsOneWidget,
    );
    expect(find.bySemanticsLabel(RegExp(r'ILAIOS')), findsWidgets);

    for (final destination in <DesktopSection>[
      DesktopSection.home,
      DesktopSection.workflows,
      DesktopSection.agents,
      DesktopSection.artifacts,
      DesktopSection.approvals,
      DesktopSection.evidence,
      DesktopSection.settings,
    ]) {
      final navigation = find.byKey(ValueKey('nav-${destination.name}'));
      expect(
        navigation,
        findsOneWidget,
        reason: 'Missing ${destination.name} primary navigation',
      );
      await tester.tap(navigation);
      await tester.pumpAndSettle();
      expect(
        tester.takeException(),
        isNull,
        reason: '${destination.name} navigation threw during rendering',
      );
    }

    for (final destination in <DesktopSection>[
      DesktopSection.goals,
      DesktopSection.liveWorkspace,
      DesktopSection.costs,
    ]) {
      expect(
        find.byKey(ValueKey('nav-${destination.name}')),
        findsNothing,
        reason: '${destination.name} must remain secondary, not primary',
      );
      await openSecondaryDesktopSection(tester, destination);
      expect(
        tester.takeException(),
        isNull,
        reason: '${destination.name} secondary navigation threw during rendering',
      );
    }

    semantics.dispose();
  });
}
