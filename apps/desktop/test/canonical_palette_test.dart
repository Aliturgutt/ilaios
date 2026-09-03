import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';

void main() {
  test('desktop dark theme uses the canonical neutral palette', () {
    expect(IlaiosTheme.carbon, const Color(0xFF0A0A0A));
    expect(IlaiosTheme.charcoal, const Color(0xFF141414));
    expect(IlaiosTheme.graphite, const Color(0xFF1E1E1E));
    expect(IlaiosTheme.stone, const Color(0xFF2A2A2A));
    expect(IlaiosTheme.white, const Color(0xFFFFFFFF));
    expect(IlaiosTheme.textSecondary, const Color(0xFFE6E6E6));
    expect(IlaiosTheme.textTertiary, const Color(0xFFB3B3B3));
    expect(IlaiosTheme.textDisabled, const Color(0xFF808080));
    expect(IlaiosTheme.surfaceHover, const Color(0xFF242424));
    expect(IlaiosTheme.surfaceActive, const Color(0xFF2F2F2F));

    expect(IlaiosTheme.canvas, IlaiosTheme.carbon);
    expect(IlaiosTheme.sidebar, IlaiosTheme.charcoal);
    expect(IlaiosTheme.surface, IlaiosTheme.charcoal);
    expect(IlaiosTheme.surfaceRaised, IlaiosTheme.graphite);
    expect(IlaiosTheme.borderStrong, IlaiosTheme.stone);
    expect(IlaiosTheme.primary, IlaiosTheme.white);

    final theme = IlaiosTheme.dark;
    final scheme = theme.colorScheme;
    expect(scheme.primary, IlaiosTheme.white);
    expect(scheme.secondary, IlaiosTheme.textSecondary);
    expect(scheme.tertiary, IlaiosTheme.textTertiary);
    expect(scheme.surface, IlaiosTheme.charcoal);
    expect(scheme.onSurface, IlaiosTheme.white);
    expect(theme.hoverColor, IlaiosTheme.surfaceHover);
    expect(theme.highlightColor, IlaiosTheme.surfaceActive);
    expect(theme.focusColor, IlaiosTheme.surfaceActive);
    expect(theme.progressIndicatorTheme.color, IlaiosTheme.white);
  });

  test('ILAIOS cyan and blue remain reserved identity colors', () {
    expect(IlaiosTheme.enterpriseCyan, const Color(0xFF00C2D1));
    expect(IlaiosTheme.coreBlue, const Color(0xFF146BFF));

    final theme = IlaiosTheme.dark;
    expect(theme.colorScheme.primary, isNot(IlaiosTheme.enterpriseCyan));
    expect(theme.colorScheme.secondary, isNot(IlaiosTheme.coreBlue));
    expect(theme.focusColor, isNot(IlaiosTheme.enterpriseCyan));
    expect(theme.hoverColor, isNot(IlaiosTheme.enterpriseCyan));
    expect(theme.progressIndicatorTheme.color, isNot(IlaiosTheme.enterpriseCyan));
  });
}
