import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

import 'secondary_navigation_test_support.dart';

void main() {
  testWidgets('Turkish locale renders the seven-primary Desktop shell in Turkish', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    expect(find.text('Ana Sayfa'), findsOneWidget);
    expect(find.text('İş Akışları'), findsOneWidget);
    expect(find.text('Ajanlar'), findsOneWidget);
    expect(find.text('Çıktılar'), findsOneWidget);
    expect(find.text('Onaylar'), findsOneWidget);
    expect(find.text('Kanıtlar'), findsOneWidget);
    expect(find.text('Ayarlar'), findsOneWidget);
    expect(find.text('Hedefler'), findsNothing);
    expect(find.text('Canlı Çalışma Alanı'), findsNothing);
    expect(find.text('Maliyetler'), findsNothing);
    expect(find.text('Proje'), findsOneWidget);
    expect(find.text('Çevrimdışı'), findsWidgets);
    expect(find.text('Home'), findsNothing);

    await openSecondaryDesktopSection(tester, DesktopSection.goals);
    expect(find.text('Hedefler'), findsWidgets);
    expect(find.text('ILAIOS’un ne oluşturmasını istiyorsun?'), findsOneWidget);
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
