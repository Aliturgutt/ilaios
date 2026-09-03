import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';

double _contrastRatio(Color foreground, Color background) {
  final first = foreground.computeLuminance();
  final second = background.computeLuminance();
  final lighter = first > second ? first : second;
  final darker = first > second ? second : first;
  return (lighter + 0.05) / (darker + 0.05);
}

void main() {
  test('dark theme distinguishes disabled actions from active actions', () {
    final theme = IlaiosTheme.dark;
    final outlined = theme.outlinedButtonTheme.style!;
    final filled = theme.filledButtonTheme.style!;

    expect(
      outlined.foregroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.muted,
    );
    expect(
      outlined.side!.resolve({WidgetState.disabled})!.color,
      IlaiosTheme.stone,
    );
    expect(
      outlined.foregroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.white,
    );

    expect(
      filled.foregroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.muted,
    );
    expect(
      filled.backgroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.graphite,
    );
    expect(
      filled.backgroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.textSecondary,
    );
  });

  test('light theme keeps disabled actions neutral and fail-closed visually', () {
    final theme = IlaiosTheme.light;
    final outlined = theme.outlinedButtonTheme.style!;
    final filled = theme.filledButtonTheme.style!;

    expect(
      outlined.foregroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.lightMuted,
    );
    expect(
      outlined.side!.resolve({WidgetState.disabled})!.color,
      IlaiosTheme.lightBorder,
    );
    expect(
      filled.foregroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.lightMuted,
    );
    expect(
      filled.backgroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.lightSurfaceRaised,
    );
  });

  test('primary interactive emphasis stays monochrome and excludes logo colors', () {
    for (final theme in <ThemeData>[IlaiosTheme.dark, IlaiosTheme.light]) {
      final outlined = theme.outlinedButtonTheme.style!;
      final filled = theme.filledButtonTheme.style!;
      final text = theme.textButtonTheme.style!;
      final selectedSwitch =
          theme.switchTheme.trackColor!.resolve({WidgetState.selected});

      final interactiveColors = <Color?>[
        theme.colorScheme.primary,
        outlined.foregroundColor!.resolve(<WidgetState>{}),
        filled.backgroundColor!.resolve(<WidgetState>{}),
        text.foregroundColor!.resolve(<WidgetState>{}),
        selectedSwitch,
      ];

      for (final color in interactiveColors) {
        expect(color, isNot(IlaiosTheme.logoCyan));
        expect(color, isNot(IlaiosTheme.logoBlue));
      }
    }

    expect(IlaiosTheme.dark.colorScheme.primary, IlaiosTheme.textSecondary);
    expect(IlaiosTheme.light.colorScheme.primary, IlaiosTheme.lightText);
    expect(
      IlaiosTheme.dark.outlinedButtonTheme.style!.foregroundColor!
          .resolve(<WidgetState>{}),
      IlaiosTheme.white,
    );
    expect(
      IlaiosTheme.dark.filledButtonTheme.style!.backgroundColor!
          .resolve(<WidgetState>{}),
      IlaiosTheme.textSecondary,
    );
    expect(
      IlaiosTheme.dark.switchTheme.trackColor!
          .resolve({WidgetState.selected}),
      IlaiosTheme.active,
    );
  });

  test('desktop typography keeps normal user text above the micro-text floor', () {
    for (final theme in <ThemeData>[IlaiosTheme.dark, IlaiosTheme.light]) {
      final text = theme.textTheme;

      expect(text.headlineLarge!.fontSize, inInclusiveRange(26, 32));
      expect(text.titleLarge!.fontSize, greaterThanOrEqualTo(18));
      expect(text.titleMedium!.fontSize, greaterThanOrEqualTo(16));
      expect(text.titleSmall!.fontSize, greaterThanOrEqualTo(14));
      expect(text.bodyLarge!.fontSize, greaterThanOrEqualTo(14));
      expect(text.bodyMedium!.fontSize, greaterThanOrEqualTo(13));
      expect(text.bodySmall!.fontSize, greaterThanOrEqualTo(12.5));
      expect(text.labelLarge!.fontSize, greaterThanOrEqualTo(13.5));
      expect(text.labelMedium!.fontSize, greaterThanOrEqualTo(12.5));
      expect(text.labelSmall!.fontSize, greaterThanOrEqualTo(12.5));
      expect(theme.tooltipTheme.textStyle!.fontSize, greaterThanOrEqualTo(12.5));
      expect(theme.inputDecorationTheme.hintStyle!.fontSize, greaterThanOrEqualTo(13));
      expect(theme.inputDecorationTheme.labelStyle!.fontSize, greaterThanOrEqualTo(13.5));
    }
  });

  test('popup labels stay readable while using bounded desktop spacing', () {
    for (final theme in <ThemeData>[IlaiosTheme.dark, IlaiosTheme.light]) {
      final popupStyle = theme.popupMenuTheme.textStyle!;
      expect(popupStyle.fontSize, greaterThanOrEqualTo(13.5));
      expect(popupStyle.letterSpacing, inInclusiveRange(-1.9, -1.7));
    }
  });

  test('light mode readable text colors meet WCAG AA on primary surfaces', () {
    expect(
      _contrastRatio(IlaiosTheme.lightText, IlaiosTheme.lightSurface),
      greaterThanOrEqualTo(4.5),
    );
    expect(
      _contrastRatio(IlaiosTheme.lightMutedStrong, IlaiosTheme.lightSurface),
      greaterThanOrEqualTo(4.5),
    );
    expect(
      _contrastRatio(IlaiosTheme.lightMuted, IlaiosTheme.lightSurface),
      greaterThanOrEqualTo(4.5),
    );
    expect(
      _contrastRatio(IlaiosTheme.lightMuted, IlaiosTheme.lightCanvas),
      greaterThanOrEqualTo(4.5),
    );
  });
}
