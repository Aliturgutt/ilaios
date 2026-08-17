import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('command-center quick actions navigate to real Desktop destinations', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-templates')), findsOneWidget);
    expect(find.byKey(const Key('home-assign-agent')), findsOneWidget);
    expect(find.byKey(const Key('home-factory-web')), findsOneWidget);

    await tester.tap(find.byKey(const Key('home-templates')));
    await tester.pumpAndSettle();
    expect(find.text('Control Center'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('nav-home')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('home-assign-agent')));
    await tester.pumpAndSettle();
    expect(find.text('Live Execution'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('nav-home')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('home-factory-web')));
    await tester.pumpAndSettle();
    expect(find.text('What do you want ILAIOS to build?'), findsOneWidget);
  });

  testWidgets('empty command center remains truth-preserving', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.text('Main Control Center'), findsOneWidget);
    expect(find.text('—'), findsWidgets);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
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
