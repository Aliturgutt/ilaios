import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Turkish locale translates V4 Home without fabricating state', (
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

    expect(find.text('Ana Kontrol Merkezi'), findsNothing);
    expect(find.text('İş başlat'), findsOneWidget);
    expect(find.text('Gelişmiş'), findsOneWidget);
    expect(find.text('Şablonlar'), findsNothing);
    expect(find.text('Son işler'), findsNothing);
    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    expect(find.byKey(const Key('command-center-metrics')), findsNothing);
    expect(find.text('ODAK İŞLER'), findsOneWidget);
    expect(find.text('DİKKAT GEREKTİRENLER'), findsOneWidget);
    expect(find.text('SON ÇIKTILAR'), findsOneWidget);
    expect(find.text('SON TAMAMLANANLAR'), findsOneWidget);
    expect(find.byKey(const Key('command-center-quick-actions')), findsNothing);
    expect(find.byKey(const Key('command-center-session')), findsNothing);
    expect(find.byKey(const Key('command-center-activities')), findsNothing);
    expect(find.byKey(const Key('command-center-alerts')), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
