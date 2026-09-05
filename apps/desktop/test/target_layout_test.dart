import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('V4 Home remains the same design family at all desktop widths', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));

    for (final size in <Size>[
      const Size(1920, 1080),
      const Size(1600, 900),
      const Size(1440, 900),
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
            'Desktop V4 layout overflowed or threw at ${size.width}x${size.height}',
      );
      expect(find.byKey(const ValueKey('nav-home')), findsOneWidget);
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
      expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
      expect(find.text('Main Control Center'), findsNothing);
      expect(find.byKey(const Key('reference-asset-dock-toggle')), findsNothing);
      expect(find.byKey(const Key('reference-brand-lockup-v9')), findsOneWidget);
      expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);
      expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsNothing);
      expect(find.byKey(const Key('reference-responsive-viewport-v11')), findsOneWidget);
      expect(find.byKey(const Key('reference-responsive-viewport-v10')), findsOneWidget);

      // Home receives the content viewport after the fixed 222px sidebar and
      // 1px divider. A 900px Windows surface also leaves Home below the 900px
      // short-height threshold once the shell chrome is accounted for.
      final homeContentWidth = size.width - 223;
      final shouldScrollCompactViewport =
          homeContentWidth < 1300 || size.height <= 900;
      expect(
        find.byKey(const Key('command-center-short-viewport-scroll')),
        shouldScrollCompactViewport ? findsOneWidget : findsNothing,
        reason: shouldScrollCompactViewport
            ? 'Compact Desktop viewport must scroll without shrinking typography'
            : 'Standard Desktop viewport should retain the one-viewport composition',
      );
    }
  });

  testWidgets('V4 Home keeps prompt, focus and attention surfaces without a permanent detail rail', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
    expect(find.byKey(const Key('command-center-focus')), findsOneWidget);
    expect(find.byKey(const Key('command-center-attention')), findsOneWidget);
    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    expect(find.byKey(const Key('command-center-session')), findsNothing);
    expect(find.byKey(const Key('command-center-quick-actions')), findsNothing);
  });

  testWidgets('V4 Home places the existing governed attachment surface below the prompt', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    final prompt = find.byKey(const Key('home-command-prompt'));
    final attachments = find.byKey(const Key('home-prompt-attachments'));
    expect(prompt, findsOneWidget);
    expect(attachments, findsOneWidget);
    expect(
      tester.getTopLeft(attachments).dy,
      greaterThan(tester.getBottomLeft(prompt).dy),
    );
  });

  testWidgets('shell renders the canonical dark runtime symbol master', (
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

  testWidgets('V4 Home remains overflow-free under 125 and 150 percent text scaling', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1920, 1080));

    for (final scale in <double>[1.25, 1.5]) {
      await tester.pumpWidget(const SizedBox.shrink());
      await tester.pump();
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
        reason: 'Desktop V4 layout failed at ${scale}x text scaling',
      );
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
      expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);
      expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsNothing);
      expect(
        find.byKey(const Key('command-center-short-viewport-scroll')),
        findsWidgets,
        reason: 'Windows text scaling must preserve readable typography by scrolling, not shrinking',
      );
    }
  });

  testWidgets('Turkish V4 Home never falls back to the old workflow dashboard when resized', (
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
        reason: 'Turkish Desktop V4 layout failed at ${size.width}x${size.height}',
      );
      expect(find.text('İş başlat'), findsOneWidget);
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.text('Ana Kontrol Merkezi'), findsNothing);
      expect(find.text('Aktif İş Akışı'), findsNothing);
      expect(find.byKey(const Key('reference-brand-horizontal-dark')), findsOneWidget);
      expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsNothing);
    }
  });
}
