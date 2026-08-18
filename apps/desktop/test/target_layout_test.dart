import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('command center remains the same design family at all desktop widths', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));

    for (final size in <Size>[
      const Size(1920, 1080),
      const Size(1600, 900),
      const Size(1382, 733),
      const Size(1320, 720),
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
        reason:
            'Desktop target layout overflowed or threw at ${size.width}x${size.height}',
      );
      expect(find.byKey(const ValueKey('nav-home')), findsOneWidget);
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.text('Main Control Center'), findsOneWidget);
      expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
      expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);

      final shouldScaleCompactViewport =
          size.width <= 1320 || size.height < 720;
      expect(
        find.byKey(const Key('reference-scaled-viewport-v9')),
        shouldScaleCompactViewport ? findsOneWidget : findsNothing,
        reason: shouldScaleCompactViewport
            ? 'Compact Desktop viewport should use the bounded safety fit'
            : 'Normal/DPI-compressed Desktop viewport must remain native 1:1',
      );
    }
  });

  testWidgets('premium target composition keeps command center and operational rail', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.text('Main Control Center'), findsOneWidget);
    expect(find.byKey(const Key('command-center-focus')), findsOneWidget);
    expect(find.byKey(const Key('command-center-attention')), findsOneWidget);
    expect(find.byKey(const Key('command-center-artifacts')), findsOneWidget);
    expect(find.byKey(const Key('command-center-completed')), findsOneWidget);
    expect(find.byKey(const Key('command-center-quick-actions')), findsOneWidget);
    expect(find.byKey(const Key('command-center-session')), findsOneWidget);
    expect(find.byKey(const Key('command-center-activities')), findsOneWidget);
    expect(find.byKey(const Key('command-center-alerts')), findsOneWidget);
  });

  testWidgets('shell renders the canonical horizontal dark brand master', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
    expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);
  });

  testWidgets('target dashboard keeps command center under 125 and 150 percent text scaling', (
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
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
      expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);
    }
  });

  testWidgets('Turkish Home never falls back to the old workflow dashboard when resized', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));

    for (final size in <Size>[
      const Size(1600, 900),
      const Size(1382, 733),
      const Size(1320, 720),
      const Size(1280, 720),
      const Size(1024, 720),
      const Size(820, 700),
    ]) {
      await tester.binding.setSurfaceSize(size);
      await tester.pumpWidget(
        const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
      );
      await tester.pumpAndSettle();

      expect(
        tester.takeException(),
        isNull,
        reason: 'Turkish Desktop layout failed at ${size.width}x${size.height}',
      );
      expect(find.text('Ana Kontrol Merkezi'), findsOneWidget);
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.text('Aktif İş Akışı'), findsNothing);
      expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);
    }
  });
}
