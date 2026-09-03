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
      IlaiosTheme.textDisabled,
    );
    expect(
      outlined.side!.resolve({WidgetState.disabled})!.color,
      IlaiosTheme.stone,
    );
    expect(
      outlined.foregroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.textSecondary,
    );

    expect(
      filled.foregroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.textDisabled,
    );
    expect(
      filled.backgroundColor!.resolve({WidgetState.disabled}),
      IlaiosTheme.graphite,
    );
    expect(
      filled.backgroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.white,
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

  test('dark interactive emphasis is neutral while light behavior stays unchanged', () {
    final dark = IlaiosTheme.dark;
    final darkOutlined = dark.outlinedButtonTheme.style!;
    final darkFilled = dark.filledButtonTheme.style!;
    final darkText = dark.textButtonTheme.style!;
    final darkSelectedSwitch =
        dark.switchTheme.trackColor!.resolve({WidgetState.selected});

    expect(dark.colorScheme.primary, IlaiosTheme.white);
    expect(
      darkOutlined.foregroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.textSecondary,
    );
    expect(
      darkFilled.backgroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.white,
    );
    expect(
      darkText.foregroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.textSecondary,
    );
    expect(darkSelectedSwitch, IlaiosTheme.white);

    for (final color in <Color>[
      dark.colorScheme.primary,
      darkOutlined.foregroundColor!.resolve(<WidgetState>{})!,
      darkFilled.backgroundColor!.resolve(<WidgetState>{})!,
      darkText.foregroundColor!.resolve(<WidgetState>{})!,
      darkSelectedSwitch!,
    ]) {
      expect(color, isNot(IlaiosTheme.enterpriseCyan));
      expect(color, isNot(IlaiosTheme.coreBlue));
    }

    final light = IlaiosTheme.light;
    final lightOutlined = light.outlinedButtonTheme.style!;
    final lightFilled = light.filledButtonTheme.style!;
    final lightTextButton = light.textButtonTheme.style!;
    final lightSelectedSwitch =
        light.switchTheme.trackColor!.resolve({WidgetState.selected});

    expect(light.colorScheme.primary, IlaiosTheme.coreBlue);
    expect(
      lightOutlined.foregroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.coreBlue,
    );
    expect(
      lightFilled.backgroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.coreBlue,
    );
    expect(
      lightTextButton.foregroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.coreBlue,
    );
    expect(lightSelectedSwitch, IlaiosTheme.coreBlue);
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
