import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  for (final size in <Size>[
    const Size(1366, 768),
    const Size(1440, 900),
    const Size(1920, 1080),
  ]) {
    testWidgets('V4 combined Desktop remains bounded at ${size.width.toInt()}x${size.height.toInt()}', (
      WidgetTester tester,
    ) async {
      await tester.binding.setSurfaceSize(size);
      addTearDown(() => tester.binding.setSurfaceSize(null));

      await tester.pumpWidget(const IlaiosDesktopApp());
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
      expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
      expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);
      expect(find.text('Main Control Center'), findsNothing);
      expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);
      expect(find.byKey(const Key('reference-asset-dock-toggle')), findsNothing);
      expect(find.byKey(const Key('command-center-session')), findsNothing);

      final status = tester.getRect(find.byKey(const Key('reference-bottom-status-v2')));
      expect(status.bottom, lessThanOrEqualTo(size.height + .01));

      await tester.tap(find.byKey(const ValueKey('nav-goals')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('reference-goals-page')), findsOneWidget);
      expect(find.byKey(const Key('goals-composer')), findsOneWidget);
      expect(find.byKey(const Key('video-reference-assets')), findsOneWidget);
      expect(tester.takeException(), isNull);

      await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('reference-outputs-page')), findsOneWidget);
      expect(find.byKey(const Key('outputs-table')), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('V4 combined Desktop keeps Turkish light surfaces truthful', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1440, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('İş başlat'), findsOneWidget);
    expect(find.text('Ana Kontrol Merkezi'), findsNothing);
    expect(find.byKey(const Key('command-center-orbit-motion')), findsNothing);
    expect(find.byKey(const Key('reference-asset-dock-toggle')), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
