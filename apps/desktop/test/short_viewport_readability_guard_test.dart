import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('short desktop viewports scroll instead of shrinking typography', () {
    final source = File(
      'lib/features/dashboard/reference_desktop_shell_v11.dart',
    ).readAsStringSync();

    expect(source, contains('constraints.maxHeight < 820'));
    expect(source, contains('reference-short-viewport-scroll-v11'));
    expect(source, contains('SingleChildScrollView'));
    expect(source, contains('height: safetyHeight'));
    expect(source, isNot(contains('FittedBox')));
    expect(source, isNot(contains('Transform.scale')));
  });
}
