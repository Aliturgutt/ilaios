import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';

void main() {
  test('desktop theme uses the canonical neutral ILAIOS UI palette', () {
    expect(IlaiosTheme.carbon, const Color(0xFF0A0A0A));
    expect(IlaiosTheme.charcoal, const Color(0xFF141414));
    expect(IlaiosTheme.graphite, const Color(0xFF1E1E1E));
    expect(IlaiosTheme.stone, const Color(0xFF2A2A2A));
    expect(IlaiosTheme.white, const Color(0xFFFFFFFF));
    expect(IlaiosTheme.textSecondary, const Color(0xFFE6E6E6));
    expect(IlaiosTheme.textTertiary, const Color(0xFFB3B3B3));
    expect(IlaiosTheme.disabled, const Color(0xFF808080));
    expect(IlaiosTheme.hover, const Color(0xFF242424));
    expect(IlaiosTheme.active, const Color(0xFF2F2F2F));

    expect(IlaiosTheme.canvas, IlaiosTheme.carbon);
    expect(IlaiosTheme.sidebar, IlaiosTheme.charcoal);
    expect(IlaiosTheme.surface, IlaiosTheme.charcoal);
    expect(IlaiosTheme.surfaceRaised, IlaiosTheme.graphite);
    expect(IlaiosTheme.border, IlaiosTheme.stone);
    expect(IlaiosTheme.primary, IlaiosTheme.textSecondary);

    final scheme = IlaiosTheme.dark.colorScheme;
    expect(scheme.primary, IlaiosTheme.textSecondary);
    expect(scheme.secondary, IlaiosTheme.textSecondary);
    expect(scheme.surface, IlaiosTheme.charcoal);
    expect(scheme.onSurface, IlaiosTheme.white);
  });

  test('reserved logo colors are not bound to dark UI interaction states', () {
    expect(IlaiosTheme.logoCyan, const Color(0xFF00C2D1));
    expect(IlaiosTheme.logoBlue, const Color(0xFF146BFF));

    final theme = IlaiosTheme.dark;
    expect(theme.focusColor, IlaiosTheme.hover);
    expect(theme.hoverColor, IlaiosTheme.hover);
    expect(theme.highlightColor, IlaiosTheme.active);
    expect(theme.progressIndicatorTheme.color, IlaiosTheme.textSecondary);
    expect(theme.colorScheme.primary, isNot(IlaiosTheme.logoCyan));
    expect(theme.colorScheme.primary, isNot(IlaiosTheme.logoBlue));
  });
}
