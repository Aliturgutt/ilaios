import 'package:flutter_test/flutter_test.dart';

import 'support/desktop_7_page_screenshot_evidence.dart';

void main() {
  testWidgets('canonical 7-page 1536x1024 screenshot evidence', (tester) async {
    await captureCanonical7PageScreenshotEvidence(tester);
  });
}
