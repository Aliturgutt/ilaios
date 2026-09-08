import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_theme.dart';

void main() {
  test('reserved logo colors stay isolated from Desktop UI aliases', () {
    expect(IlaiosTheme.logoCyan, const Color(0xFF00C2D1));
    expect(IlaiosTheme.logoBlue, const Color(0xFF146BFF));

    expect(IlaiosTheme.enterpriseCyan, IlaiosTheme.textSecondary);
    expect(IlaiosTheme.coreBlue, IlaiosTheme.textSecondary);
    expect(IlaiosTheme.cyan, IlaiosTheme.textSecondary);
    expect(IlaiosTheme.blue, IlaiosTheme.textSecondary);

    expect(IlaiosTheme.enterpriseCyan, isNot(IlaiosTheme.logoCyan));
    expect(IlaiosTheme.coreBlue, isNot(IlaiosTheme.logoBlue));
  });
}
