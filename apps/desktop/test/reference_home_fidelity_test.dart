import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('1536x1024 dark Home renders the V4 reference hierarchy', (
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
      const Key('command-center-focus'),
      const Key('command-center-attention'),
      const Key('command-center-artifacts'),
      const Key('command-center-completed'),
      const Key('reference-brand-lockup-v9'),
      const Key('reference-bottom-status-v2'),
    ]) {
      expect(find.byKey(key), findsOneWidget, reason: 'missing $key');
    }

    expect(find.byKey(const Key('command-center-metrics')), findsNothing);
    expect(find.byKey(const Key('command-center-quick-actions')), findsNothing);
    expect(find.byKey(const Key('command-center-session')), findsNothing);
    expect(find.byKey(const Key('command-center-activities')), findsNothing);
    expect(find.byKey(const Key('command-center-alerts')), findsNothing);
    expect(find.text('Main Control Center'), findsNothing);
    expect(find.text('Start work'), findsOneWidget);
    expect(find.text('FOCUS WORK'), findsOneWidget);
    expect(find.text('NEEDS ATTENTION'), findsOneWidget);
    expect(find.text('LATEST OUTPUTS'), findsOneWidget);
    expect(find.text('RECENTLY COMPLETED'), findsOneWidget);

    expect(find.text('12'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });

  testWidgets('compact 1320x720 keeps the V4 Home in a bounded viewport', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1320, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsOneWidget);
    expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
    expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
    expect(find.byKey(const Key('command-center-focus')), findsOneWidget);
    expect(find.byKey(const Key('command-center-artifacts')), findsOneWidget);
    expect(find.byKey(const Key('command-center-completed')), findsOneWidget);
    expect(find.byKey(const Key('command-center-session')), findsNothing);
    expect(find.byKey(const Key('command-center-alerts')), findsNothing);
    expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);

    final artifacts = tester.getRect(find.byKey(const Key('command-center-artifacts')));
    final completed = tester.getRect(find.byKey(const Key('command-center-completed')));
    final bottomStatus = tester.getRect(find.byKey(const Key('reference-bottom-status-v2')));
    expect(artifacts.bottom, lessThanOrEqualTo(bottomStatus.top + 1));
    expect(completed.bottom, lessThanOrEqualTo(bottomStatus.top + 1));
    expect(bottomStatus.bottom, lessThanOrEqualTo(720.01));
  });

  testWidgets('1382x733 DPI-compressed client preserves native V4 typography', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1382, 733));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsNothing);
    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
    expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);
  });

  testWidgets('1640x890 Windows client keeps V4 bottom content and status visible', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1640, 890));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsNothing);
    final outputs = tester.getRect(find.byKey(const Key('command-center-artifacts')));
    final completed = tester.getRect(find.byKey(const Key('command-center-completed')));
    final status = tester.getRect(find.byKey(const Key('reference-bottom-status-v2')));
    expect(outputs.bottom, lessThanOrEqualTo(status.top + 1));
    expect(completed.bottom, lessThanOrEqualTo(status.top + 1));
    expect(status.bottom, lessThanOrEqualTo(890.01));
  });

  testWidgets('Turkish light V4 reference renders without mixing dark or legacy state', (
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
    expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
    expect(find.text('Ana Kontrol Merkezi'), findsNothing);
    expect(find.text('İş başlat'), findsOneWidget);
    expect(find.text('ODAK İŞLER'), findsOneWidget);
    expect(find.text('DİKKAT GEREKTİRENLER'), findsOneWidget);
    expect(find.text('SON ÇIKTILAR'), findsOneWidget);
    expect(find.text('SON TAMAMLANANLAR'), findsOneWidget);
    expect(find.byKey(const Key('command-center-quick-actions')), findsNothing);
    expect(find.byKey(const Key('command-center-session')), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
  });
}
