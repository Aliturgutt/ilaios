import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'support/desktop_v4_screenshot_evidence.dart';

void main() {
  testWidgets('V4 dark 1366x768 screenshot evidence', (tester) async {
    await captureV4ScreenshotEvidence(
      tester,
      viewport: const Size(1366, 768),
      themeName: 'dark',
      themeMode: ThemeMode.dark,
    );
  });
}
