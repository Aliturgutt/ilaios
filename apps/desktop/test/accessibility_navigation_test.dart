import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Desktop navigation is semantic and all seven canonical destinations are reachable', (
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
        reason: 'Missing ${destination.name} canonical navigation',
      );
      await tester.tap(navigation);
      await tester.pumpAndSettle();
      expect(
        tester.takeException(),
        isNull,
        reason: '${destination.name} navigation threw during rendering',
      );
    }

    for (final legacy in <DesktopSection>[
      DesktopSection.goals,
      DesktopSection.liveWorkspace,
      DesktopSection.costs,
    ]) {
      expect(
        find.byKey(ValueKey('nav-${legacy.name}')),
        findsNothing,
        reason: '${legacy.name} must not reappear as a top-level destination',
      );
    }
    expect(find.byKey(const Key('reference-secondary-navigation')), findsNothing);

    semantics.dispose();
  });
}
