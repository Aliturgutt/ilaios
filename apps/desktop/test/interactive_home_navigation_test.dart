import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('home workflow stage nodes navigate to real Desktop destinations', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('home-stage-goals')), findsOneWidget);
    expect(find.byKey(const ValueKey('home-stage-workflows')), findsOneWidget);
    expect(find.byKey(const ValueKey('home-stage-agents')), findsOneWidget);
    expect(find.byKey(const ValueKey('home-stage-evidence')), findsOneWidget);
    expect(find.byKey(const ValueKey('home-stage-artifacts')), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('home-stage-workflows')));
    await tester.pumpAndSettle();
    expect(find.text('Control Center'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('nav-home')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('home-stage-agents')));
    await tester.pumpAndSettle();
    expect(find.text('Live Execution'), findsOneWidget);
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
  });
}
