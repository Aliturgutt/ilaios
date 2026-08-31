import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/desktop_v4_screenshot_evidence.dart';

void main() {
  testWidgets('V4 dark 1440x900 screenshot evidence', (tester) async {
    await captureV4ScreenshotEvidence(
      tester,
      viewport: const Size(1440, 900),
      themeName: 'dark',
      themeMode: ThemeMode.dark,
    );
  });
}
