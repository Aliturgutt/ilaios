import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale translates command-center Home without fabricating state', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
          schemaVersion: '1',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Ana Kontrol Merkezi'), findsOneWidget);
    expect(find.text('Yeni İş Başlat'), findsOneWidget);
    expect(find.text('Şablonlar'), findsOneWidget);
    expect(find.text('Son Oturumu Aç'), findsOneWidget);
    expect(find.text('Ajan Ata'), findsOneWidget);
    expect(find.text('Devam Eden İşler'), findsOneWidget);
    expect(find.text('Müdahale Gerektiren'), findsOneWidget);
    expect(find.text('Aktif Ajanlar'), findsOneWidget);
    expect(find.text('Bugünkü Harcama'), findsOneWidget);
    expect(find.text('Sistem Sağlığı'), findsOneWidget);
    expect(find.text('ODAK İŞLER'), findsOneWidget);
    expect(find.text('DİKKAT GEREKTİRENLER'), findsOneWidget);
    expect(find.text('SON ÇIKTILAR'), findsOneWidget);
    expect(find.text('SON TAMAMLANANLAR'), findsOneWidget);
    expect(find.text('HIZLI İŞLEMLER'), findsOneWidget);
    expect(find.text('OTURUM DURUMU'), findsOneWidget);
    expect(find.text('SON ETKİNLİKLER'), findsOneWidget);
    expect(find.text('UYARILAR'), findsOneWidget);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
