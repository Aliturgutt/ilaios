import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Approvals toolbar no-op controls fail closed', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();

    for (final label in <String>['Export', 'Policy Rules']) {
      final textFinder = find.text(label);
      expect(textFinder, findsOneWidget);

      final inkFinder = find.ancestor(
        of: textFinder,
        matching: find.byType(InkWell),
      );
      expect(inkFinder, findsOneWidget);
      expect(tester.widget<InkWell>(inkFinder).onTap, isNull);

      final opacityFinder = find.ancestor(
        of: textFinder,
        matching: find.byType(Opacity),
      );
      expect(opacityFinder, findsOneWidget);
      expect(tester.widget<Opacity>(opacityFinder).opacity, .45);
    }

    expect(tester.takeException(), isNull);
  });
}
