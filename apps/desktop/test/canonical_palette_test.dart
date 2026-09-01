import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';

void main() {
  test('desktop theme uses the canonical ILAIOS brand palette', () {
    expect(IlaiosTheme.carbon, const Color(0xFF0B0F14));
    expect(IlaiosTheme.charcoal, const Color(0xFF111827));
    expect(IlaiosTheme.graphite, const Color(0xFF1F2937));
    expect(IlaiosTheme.white, const Color(0xFFFFFFFF));
    expect(IlaiosTheme.enterpriseCyan, const Color(0xFF00C2D1));
    expect(IlaiosTheme.coreBlue, const Color(0xFF146BFF));
    expect(IlaiosTheme.violet, const Color(0xFF5C58FE));

    expect(IlaiosTheme.canvas, IlaiosTheme.carbon);
    expect(IlaiosTheme.sidebar, IlaiosTheme.charcoal);
    expect(IlaiosTheme.surface, IlaiosTheme.charcoal);
    expect(IlaiosTheme.surfaceRaised, IlaiosTheme.graphite);
    expect(IlaiosTheme.primary, IlaiosTheme.enterpriseCyan);
    expect(IlaiosTheme.blue, IlaiosTheme.coreBlue);
    expect(IlaiosTheme.selectiveAccent, IlaiosTheme.violet);

    final scheme = IlaiosTheme.dark.colorScheme;
    expect(scheme.primary, IlaiosTheme.enterpriseCyan);
    expect(scheme.secondary, IlaiosTheme.coreBlue);
    expect(scheme.tertiary, IlaiosTheme.violet);
    expect(scheme.surface, IlaiosTheme.charcoal);
    expect(scheme.onSurface, IlaiosTheme.white);
  });

  test('desktop vitality tokens remain canonical translucent accents', () {
    expect(IlaiosTheme.cyanWash, const Color(0x2E00C2D1));
    expect(IlaiosTheme.blueWash, const Color(0x2B146BFF));
    expect(IlaiosTheme.violetWash, const Color(0x265C58FE));
    expect(IlaiosTheme.focusRing, const Color(0xE600C2D1));

    final theme = IlaiosTheme.dark;
    expect(theme.focusColor, IlaiosTheme.cyanWash);
    expect(theme.hoverColor, IlaiosTheme.cyanWash);
    expect(theme.highlightColor, IlaiosTheme.violetWash);
    expect(theme.progressIndicatorTheme.color, IlaiosTheme.enterpriseCyan);
  });
}
