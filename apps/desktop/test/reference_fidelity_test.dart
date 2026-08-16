import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('1536x1024 desktop frame matches the approved reference proportions', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);

    final sidebar = find.byKey(const Key('reference-desktop-sidebar'));
    final topbar = find.byKey(const Key('reference-desktop-topbar'));
    final statusbar = find.byKey(const Key('reference-desktop-statusbar'));

    expect(sidebar, findsOneWidget);
    expect(topbar, findsOneWidget);
    expect(statusbar, findsOneWidget);
    expect(tester.getSize(sidebar).width, 262);
    expect(tester.getSize(topbar).height, 82);
    expect(tester.getSize(statusbar).height, 48);

    expect(find.byKey(const Key('reference-workflow-pipeline')), findsOneWidget);
    expect(find.byKey(const Key('reference-live-execution')), findsOneWidget);
    expect(find.byKey(const Key('reference-workspace')), findsOneWidget);
    expect(find.byKey(const Key('reference-right-rail')), findsOneWidget);
    expect(find.byKey(const Key('reference-latest-artifacts')), findsOneWidget);
    expect(find.byKey(const Key('reference-evidence-verification')), findsOneWidget);
  });

  testWidgets('reference fidelity never fabricates screenshot telemetry', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text(r'$3.21'), findsNothing);
    expect(find.text('73%'), findsNothing);
    expect(find.text('7 / 25'), findsNothing);
    expect(find.text('Unavailable'), findsWidgets);
  });
}
