import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';

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
      IlaiosTheme.graphite,
    );
    expect(
      outlined.foregroundColor!.resolve(<WidgetState>{}),
      IlaiosTheme.coreBlue,
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
      IlaiosTheme.enterpriseCyan,
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
}
