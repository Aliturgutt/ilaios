import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('V4 Approvals removes unsupported toolbar no-op controls', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-approvals-page')), findsOneWidget);
    expect(find.text('Export'), findsNothing);
    expect(find.text('Policy Rules'), findsNothing);
    expect(find.byKey(const Key('approvals-table')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
