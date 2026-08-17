import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale reaches every primary Desktop surface', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    Future<void> open(String section) async {
      final nav = find.byKey(ValueKey('nav-$section'));
      await tester.ensureVisible(nav);
      await tester.tap(nav);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }

    expect(find.text('Ana Kontrol Merkezi'), findsOneWidget);

    await open('goals');
    expect(find.text('ILAIOS’un ne oluşturmasını istiyorsun?'), findsOneWidget);

    await open('workflows');
    expect(find.text('Kontrol Merkezi'), findsOneWidget);

    await open('agents');
    expect(find.text('Canlı Yürütme'), findsOneWidget);

    await open('liveWorkspace');
    expect(find.text('Canlı Çalışma Alanı'), findsWidgets);

    await open('artifacts');
    expect(find.text('Teslimatlar'), findsOneWidget);

    await open('approvals');
    expect(find.text('Yönetişim'), findsOneWidget);

    await open('evidence');
    expect(find.text('Kanıt ve Denetim'), findsOneWidget);

    await open('costs');
    expect(find.text('Maliyetler ve Kullanım'), findsOneWidget);

    await open('settings');
    expect(find.text('Ayarlar'), findsWidgets);
    expect(find.text('Dil'), findsWidgets);
  });
}
