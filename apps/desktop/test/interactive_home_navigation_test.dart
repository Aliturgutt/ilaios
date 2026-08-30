import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('V4 Home exposes only real bounded navigation actions', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-templates')), findsOneWidget);
    expect(find.byKey(const Key('home-last-session')), findsOneWidget);
    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    expect(find.byKey(const Key('home-assign-agent')), findsNothing);
    expect(find.byKey(const Key('home-factory-web')), findsNothing);

    await tester.tap(find.byKey(const Key('home-templates')));
    await tester.pumpAndSettle();
    final workflowsPage = find.byKey(const Key('reference-workflows-page'));
    expect(workflowsPage, findsOneWidget);
    expect(
      find.descendant(of: workflowsPage, matching: find.text('Workflows')),
      findsOneWidget,
    );

    await tester.tap(find.byKey(const ValueKey('nav-home')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('home-last-session')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('reference-workflows-page')), findsOneWidget);
  });

  testWidgets('empty V4 Home remains truth-preserving', (
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

  testWidgets('every primary Desktop destination renders in real light theme', (
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
      expect(navigation, findsOneWidget);
      await tester.tap(navigation);
      await tester.pumpAndSettle();
      expect(
        tester.takeException(),
        isNull,
        reason: '$destination failed to render in light mode',
      );
      expect(
        Theme.of(tester.element(find.byType(Scaffold).first)).brightness,
        Brightness.light,
      );
    }
  });
}
