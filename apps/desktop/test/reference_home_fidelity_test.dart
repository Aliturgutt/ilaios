import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('1536x1024 dark Home renders the command-center reference hierarchy', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    for (final key in <Key>[
      const Key('command-center-home'),
      const Key('command-center-hero'),
      const Key('command-center-metrics'),
      const Key('command-center-focus'),
      const Key('command-center-attention'),
      const Key('command-center-artifacts'),
      const Key('command-center-completed'),
      const Key('command-center-quick-actions'),
      const Key('command-center-session'),
      const Key('command-center-activities'),
      const Key('command-center-alerts'),
      const Key('reference-bottom-status-v2'),
    ]) {
      expect(find.byKey(key), findsOneWidget, reason: 'missing $key');
    }

    expect(find.text('Main Control Center'), findsOneWidget);
    expect(find.text('Ongoing Work'), findsOneWidget);
    expect(find.text('Needs Attention'), findsOneWidget);
    expect(find.text('Active Agents'), findsOneWidget);
    expect(find.text("Today's Cost"), findsOneWidget);
    expect(find.text('System Health'), findsWidgets);
    expect(find.text('FOCUS WORK'), findsOneWidget);
    expect(find.text('NEEDS ATTENTION'), findsOneWidget);
    expect(find.text('LATEST OUTPUTS'), findsOneWidget);
    expect(find.text('RECENTLY COMPLETED'), findsOneWidget);
    expect(find.text('QUICK ACTIONS'), findsOneWidget);
    expect(find.text('SESSION STATUS'), findsOneWidget);
    expect(find.text('RECENT ACTIVITY'), findsOneWidget);
    expect(find.text('ALERTS'), findsOneWidget);

    // Reference screenshot telemetry is visual-only and must never be copied.
    expect(find.text('12'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });

  testWidgets('DPI-compressed 1320x720 keeps the full command center in one viewport', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1320, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-dpi-scaled-viewport')), findsOneWidget);
    expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
    expect(find.byKey(const Key('command-center-focus')), findsOneWidget);
    expect(find.byKey(const Key('command-center-artifacts')), findsOneWidget);
    expect(find.byKey(const Key('command-center-session')), findsOneWidget);
    expect(find.byKey(const Key('command-center-alerts')), findsOneWidget);
    expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);

    final artifacts = tester.getRect(find.byKey(const Key('command-center-artifacts')));
    final bottomStatus = tester.getRect(find.byKey(const Key('reference-bottom-status-v2')));
    expect(artifacts.bottom, lessThanOrEqualTo(bottomStatus.top + 1));
    expect(bottomStatus.bottom, lessThanOrEqualTo(720));
  });

  testWidgets('approved Turkish light reference renders without mixing dark state', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    final context = tester.element(find.byKey(const Key('command-center-home')));
    expect(Theme.of(context).brightness, Brightness.light);
    expect(find.text('Ana Kontrol Merkezi'), findsOneWidget);
    expect(find.text('Devam Eden İşler'), findsOneWidget);
    expect(find.text('Müdahale Gerektiren'), findsOneWidget);
    expect(find.text('Aktif Ajanlar'), findsOneWidget);
    expect(find.text('Bugünkü Harcama'), findsOneWidget);
    expect(find.text('Sistem Sağlığı'), findsWidgets);
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
  });
}
