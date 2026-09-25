import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_text_scale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  for (final scale in <double>[0.9, 1.0, 1.2, 1.5]) {
    testWidgets('Settings appearance has no overflow at $scale', (tester) async {
      desktopTextScale.value = scale;
      addTearDown(() => desktopTextScale.value = 1.0);
      await tester.binding.setSurfaceSize(const Size(1600, 900));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      await tester.pumpWidget(const IlaiosDesktopApp(themeMode: ThemeMode.light));
      await tester.pumpAndSettle();
      await tester.tap(find.byKey(const ValueKey('nav-settings')));
      await tester.pumpAndSettle();
      expect(find.byKey(const Key('settings-appearance-panel')), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }
}