import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('1536x1024 Home stays in one viewport without page scroll', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byType(SingleChildScrollView), findsNothing);

    final hero = find.byKey(const Key('command-center-hero'));
    final artifacts = find.byKey(const Key('command-center-artifacts'));
    final completed = find.byKey(const Key('command-center-completed'));
    final bottomBar = find.byKey(const Key('reference-bottom-status-v2'));

    expect(hero, findsOneWidget);
    expect(artifacts, findsOneWidget);
    expect(completed, findsOneWidget);
    expect(bottomBar, findsOneWidget);
    expect(tester.getBottomRight(artifacts).dy, lessThan(978));
    expect(tester.getBottomRight(completed).dy, lessThan(978));
    expect(tester.getBottomRight(bottomBar).dy, lessThanOrEqualTo(1024));
  });

  testWidgets('command-center controls are real interactive controls', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    expect(find.byKey(const Key('home-templates')), findsOneWidget);
    expect(find.byKey(const Key('home-assign-agent')), findsOneWidget);
    expect(find.byKey(const Key('home-factory-video')), findsOneWidget);

    await tester.tap(find.byKey(const Key('home-factory-video')));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
    expect(find.text('What do you want ILAIOS to build?'), findsOneWidget);
  });
}
