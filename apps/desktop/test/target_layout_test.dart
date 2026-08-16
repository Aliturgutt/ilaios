import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('target dashboard renders without overflow at required desktop widths', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));

    for (final size in <Size>[
      const Size(1920, 1080),
      const Size(2560, 1440),
      const Size(1280, 720),
      const Size(1024, 720),
      const Size(820, 700),
    ]) {
      await tester.binding.setSurfaceSize(size);
      await tester.pumpWidget(const IlaiosDesktopApp());
      await tester.pumpAndSettle();

      expect(
        tester.takeException(),
        isNull,
        reason: 'Desktop target layout overflowed or threw at ${size.width}x${size.height}',
      );
      expect(find.text('Active Workflow'), findsOneWidget);
      expect(find.text('Goal Intake'), findsOneWidget);
      expect(find.text('Execution'), findsOneWidget);
      expect(find.text('Verification'), findsOneWidget);
      expect(find.text('Delivery'), findsOneWidget);
    }
  });

  testWidgets('premium target composition keeps operational right rail and workspace panes', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('STATUS'), findsOneWidget);
    expect(find.text('COST & USAGE'), findsOneWidget);
    expect(find.text('APPROVALS'), findsOneWidget);
    expect(find.text('LATEST LOGS'), findsOneWidget);
    expect(find.text('Live Code'), findsWidgets);
    expect(find.text('Terminal'), findsWidgets);
    expect(find.text('Browser'), findsWidgets);
    expect(find.text('LATEST ARTIFACTS'), findsOneWidget);
    expect(find.text('EVIDENCE & VERIFICATION'), findsOneWidget);
  });

  testWidgets('wide shell renders the canonical horizontal ILAIOS wordmark', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    final wordmark = find.byWidgetPredicate((widget) {
      if (widget is! Image || widget.image is! AssetImage) return false;
      return (widget.image as AssetImage).assetName ==
          '../../brand/assets/02-ilaios-primary-horizontal-dark.jpg';
    });

    expect(tester.takeException(), isNull);
    expect(wordmark, findsOneWidget);
  });

  testWidgets('target dashboard tolerates 125 and 150 percent text scaling', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1920, 1080));

    for (final scale in <double>[1.25, 1.5]) {
      await tester.pumpWidget(
        MediaQuery(
          data: MediaQueryData(textScaler: TextScaler.linear(scale)),
          child: const IlaiosDesktopApp(),
        ),
      );
      await tester.pumpAndSettle();
      expect(
        tester.takeException(),
        isNull,
        reason: 'Desktop target layout failed at ${scale}x text scaling',
      );
    }
  });
}
