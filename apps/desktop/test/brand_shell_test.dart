import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

Finder _asset(String name) => find.byWidgetPredicate((widget) {
      if (widget is! Image || widget.image is! AssetImage) return false;
      return (widget.image as AssetImage).assetName == name;
    });

void main() {
  const darkLogo = '../../brand/assets/02-ilaios-primary-horizontal-dark.jpg';
  const lightLogo = '../../brand/assets/13-ilaios-primary-horizontal-light.jpg';

  testWidgets('dark Desktop uses the canonical dark horizontal brand master', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
    expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);
    expect(_asset(darkLogo), findsOneWidget);
    expect(_asset(lightLogo), findsNothing);
  });

  testWidgets('light Desktop uses the canonical light horizontal brand master', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(themeMode: ThemeMode.light),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
    expect(find.byKey(const Key('reference-brand-horizontal-light')), findsOneWidget);
    expect(_asset(lightLogo), findsOneWidget);
    expect(_asset(darkLogo), findsNothing);
  });
}
