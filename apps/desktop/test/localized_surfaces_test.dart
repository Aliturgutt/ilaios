import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale reaches localized goal cost settings and delivery surfaces', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('nav-goals')));
    await tester.pumpAndSettle();
    expect(find.text('ILAIOS’un ne oluşturmasını istiyorsun?'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();
    expect(find.text('Teslimatlar'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('nav-costs')));
    await tester.pumpAndSettle();
    expect(find.text('Maliyetler ve Kullanım'), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey('nav-settings')));
    await tester.pumpAndSettle();
    expect(find.text('Ayarlar'), findsWidgets);
    expect(find.text('Dil'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
