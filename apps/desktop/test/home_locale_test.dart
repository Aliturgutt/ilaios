import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale translates premium Home labels without fabricating state', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();

    expect(find.text('Aktif İş Akışı'), findsOneWidget);
    expect(find.text('AKTİF VERİ YOK'), findsOneWidget);
    expect(find.text('Hedef Alımı'), findsOneWidget);
    expect(find.text('Planlama'), findsOneWidget);
    expect(find.text('Genel İlerleme'), findsOneWidget);
    expect(find.text('CANLI YÜRÜTME'), findsOneWidget);
    expect(find.text('CANLI ÇALIŞMA ALANI'), findsOneWidget);
    expect(find.text('DURUM'), findsOneWidget);
    expect(find.text('MALİYET VE KULLANIM'), findsOneWidget);
    expect(find.text('ONAYLAR'), findsOneWidget);
    expect(find.text('SON GÜNLÜKLER'), findsOneWidget);
    expect(find.text('73%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
