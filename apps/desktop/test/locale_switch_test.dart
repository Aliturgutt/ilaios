import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale renders the primary Desktop shell in Turkish', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    expect(find.text('Ana Sayfa'), findsOneWidget);
    expect(find.text('Hedefler'), findsOneWidget);
    expect(find.text('İş Akışları'), findsOneWidget);
    expect(find.text('Proje'), findsOneWidget);
    expect(find.text('Çevrimdışı'), findsWidgets);
    expect(find.text('Home'), findsNothing);
  });

  testWidgets('world language control exposes English and Turkish', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    IlaiosLocale? selected;
    await tester.pumpWidget(
      IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        onLocaleChanged: (value) => selected = value,
      ),
    );
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Dil'));
    await tester.pumpAndSettle();
    expect(find.text('English'), findsOneWidget);
    expect(find.text('Türkçe'), findsOneWidget);

    await tester.tap(find.text('English'));
    await tester.pumpAndSettle();
    expect(selected, IlaiosLocale.english);
  });
}
