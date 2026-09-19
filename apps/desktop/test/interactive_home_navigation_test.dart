import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('canonical Home exposes only real bounded navigation actions', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    expect(find.text('Advanced'), findsNothing);
    expect(find.byKey(const Key('home-templates')), findsNothing);
    expect(find.byKey(const Key('home-last-session')), findsNothing);
    expect(find.byKey(const Key('home-assign-agent')), findsNothing);
    expect(find.byKey(const Key('home-factory-web')), findsNothing);

    final viewAgents = find.text('View all agents');
    expect(viewAgents, findsOneWidget);
    await tester.tap(viewAgents);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('reference-agents-page')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('empty canonical Home remains truth-preserving', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.text('Main Control Center'), findsNothing);
    expect(find.text('Start work'), findsOneWidget);
    expect(find.byKey(const Key('command-center-metrics')), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('theme control switches the application to light mode', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    BuildContext scaffoldContext = tester.element(find.byType(Scaffold).first);
    expect(Theme.of(scaffoldContext).brightness, Brightness.dark);

    await tester.tap(find.byKey(const Key('theme-toggle')));
    await tester.pumpAndSettle();

    scaffoldContext = tester.element(find.byType(Scaffold).first);
    expect(Theme.of(scaffoldContext).brightness, Brightness.light);
    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
  });

  testWidgets('every canonical Desktop destination renders in real light theme', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(themeMode: ThemeMode.light),
    );
    await tester.pumpAndSettle();

    expect(
      Theme.of(tester.element(find.byType(Scaffold).first)).brightness,
      Brightness.light,
    );

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
      expect(navigation, findsOneWidget);
      await tester.tap(navigation);
      await tester.pumpAndSettle();
      expect(
        tester.takeException(),
        isNull,
        reason: '${destination.name} failed to render in light mode',
      );
      expect(
        Theme.of(tester.element(find.byType(Scaffold).first)).brightness,
        Brightness.light,
      );
    }

    for (final destination in <DesktopSection>[
      DesktopSection.goals,
      DesktopSection.liveWorkspace,
      DesktopSection.costs,
    ]) {
      expect(find.byKey(ValueKey('nav-${destination.name}')), findsNothing);
    }
  });
}
