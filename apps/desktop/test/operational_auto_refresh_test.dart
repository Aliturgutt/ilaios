import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('Desktop requests authoritative refresh automatically', (
    WidgetTester tester,
  ) async {
    var refreshCalls = 0;

    await tester.pumpWidget(
      IlaiosDesktopApp(
        onRefreshRequested: () {
          refreshCalls += 1;
        },
      ),
    );

    expect(refreshCalls, 0);

    await tester.pump(const Duration(seconds: 2));
    expect(refreshCalls, 1);

    await tester.pump(const Duration(seconds: 2));
    expect(refreshCalls, 2);
  });
}
