import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/main.dart';

const _canonicalSections = <String>[
  'home',
  'workflows',
  'agents',
  'artifacts',
  'approvals',
  'evidence',
  'settings',
];

void _expectCanonicalShell() {
  expect(find.byKey(const Key('reference-responsive-viewport-v11')), findsOneWidget);
  expect(find.byKey(const Key('canonical-7-page-sidebar')), findsOneWidget);
  expect(find.byKey(const Key('canonical-7-page-topbar')), findsOneWidget);
  expect(find.byKey(const Key('canonical-reference-logo')), findsOneWidget);
  for (final section in _canonicalSections) {
    expect(find.byKey(ValueKey('nav-$section')), findsOneWidget);
  }
  for (final legacy in <String>['goals', 'liveWorkspace', 'costs']) {
    expect(find.byKey(ValueKey('nav-$legacy')), findsNothing);
  }
  expect(find.byKey(const Key('reference-secondary-navigation')), findsNothing);
}

void main() {
  testWidgets('canonical 7-page Home stays overflow-free across desktop widths', (
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
            'Canonical 7-page layout overflowed or threw at ${size.width}x${size.height}',
      );
      _expectCanonicalShell();
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
      expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    }
  });

  testWidgets('canonical Home keeps the governed prompt and attachment surface', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    _expectCanonicalShell();
    final prompt = find.byKey(const Key('home-command-prompt'));
    final attachments = find.byKey(const Key('home-prompt-attachments'));
    expect(prompt, findsOneWidget);
    expect(attachments, findsOneWidget);
    expect(find.byKey(const Key('home-new-work')), findsOneWidget);
    expect(
      tester.getTopLeft(attachments).dy,
      greaterThan(tester.getBottomLeft(prompt).dy),
    );
  });

  testWidgets('shell exposes exactly seven top-level destinations', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    _expectCanonicalShell();
    expect(find.byKey(const Key('reference-bottom-status-v2')), findsOneWidget);
  });

  testWidgets('1536x1024 canonical Home uses scroll-safe geometry', (
    WidgetTester tester,
  ) async {
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.binding.setSurfaceSize(const Size(1536, 1024));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    _expectCanonicalShell();
    expect(
      find.byKey(const Key('command-center-short-viewport-scroll')),
      findsOneWidget,
    );
  });

  testWidgets('canonical Home remains overflow-free at 125 and 150 percent text scaling', (
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
        reason: 'Canonical 7-page layout failed at ${scale}x text scaling',
      );
      _expectCanonicalShell();
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
      expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
      expect(
        find.byKey(const Key('command-center-short-viewport-scroll')),
        findsWidgets,
        reason: 'Windows text scaling must preserve readable typography by scrolling',
      );
    }
  });

  testWidgets('Turkish canonical Home remains on the 7-page shell when resized', (
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
        reason:
            'Turkish canonical 7-page layout failed at ${size.width}x${size.height}',
      );
      _expectCanonicalShell();
      expect(find.text('İş başlat'), findsOneWidget);
      expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    }
  });
}
