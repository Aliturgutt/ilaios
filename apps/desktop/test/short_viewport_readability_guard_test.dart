import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets(
    'short desktop viewports scroll instead of shrinking typography',
    (tester) async {
      addTearDown(() => tester.binding.setSurfaceSize(null));
      for (final size in [const Size(1366, 768), const Size(1180, 720)]) {
        await tester.binding.setSurfaceSize(size);
        await tester.pumpWidget(const IlaiosDesktopApp());
        await tester.pumpAndSettle();
        final viewport = find.byKey(
          const Key('reference-responsive-viewport-v11'),
        );
        expect(tester.getSize(viewport), size);
        expect(
          find.byKey(const Key('reference-scaled-viewport-v9')),
          findsNothing,
        );
        expect(
          find.byKey(const Key('command-center-short-viewport-scroll')),
          findsOneWidget,
        );
        final input = find.byKey(const Key('home-command-prompt'));
        expect(tester.widget<TextField>(input).style?.fontSize, 15);
        final status = tester.getRect(
          find.byKey(const Key('reference-bottom-status-v2')),
        );
        expect(status.bottom, lessThanOrEqualTo(size.height));
        expect(tester.takeException(), isNull);
      }
    },
  );
}
