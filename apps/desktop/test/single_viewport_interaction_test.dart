import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('1536x1024 Home stays in one viewport without page scroll', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byType(SingleChildScrollView), findsNothing);

    final artifacts = find.byKey(const Key('reference-artifacts-panel'));
    final evidence = find.byKey(const Key('reference-evidence-panel'));
    final bottomBar = find.byKey(const Key('reference-bottom-status-v2'));

    expect(artifacts, findsOneWidget);
    expect(evidence, findsOneWidget);
    expect(bottomBar, findsOneWidget);
    expect(tester.getBottomRight(artifacts).dy, lessThan(978));
    expect(tester.getBottomRight(evidence).dy, lessThan(978));
    expect(tester.getBottomRight(bottomBar).dy, lessThanOrEqualTo(1024));
  });

  testWidgets('workspace tabs are real interactive controls', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(find.text('Live Code'), findsNWidgets(2));
    expect(find.text('Terminal'), findsWidgets);

    await tester.tap(find.byKey(const Key('workspace-tab-terminal')));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Live Code'), findsOneWidget);
    expect(find.text('Terminal'), findsWidgets);

    await tester.tap(find.byKey(const Key('workspace-tab-browser')));
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Browser'), findsWidgets);
  });
}
