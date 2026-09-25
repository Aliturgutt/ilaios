import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_text_scale.dart';

void main() {
  tearDown(() => desktopTextScale.value = 1.0);

  testWidgets('desktop-wide scale updates text on separate pages', (
    tester,
  ) async {
    await tester.pumpWidget(
      MaterialApp(
        builder: (context, child) => ValueListenableBuilder<double>(
          valueListenable: desktopTextScale,
          builder: (context, scale, _) => MediaQuery(
            data: MediaQuery.of(
              context,
            ).copyWith(textScaler: TextScaler.linear(scale)),
            child: child!,
          ),
        ),
        home: const Scaffold(
          body: Column(
            children: [
              Text('Agents', key: Key('agents-text')),
              Text('Outputs', key: Key('outputs-text')),
            ],
          ),
        ),
      ),
    );
    double size(String key) {
      final text = tester.widget<Text>(find.byKey(Key(key)));
      final context = tester.element(find.byKey(Key(key)));
      return MediaQuery.textScalerOf(context).scale(text.style?.fontSize ?? 14);
    }

    final initialAgents = size('agents-text');
    final initialOutputs = size('outputs-text');
    desktopTextScale.value = 1.25;
    await tester.pump();
    expect(size('agents-text'), greaterThan(initialAgents));
    expect(size('outputs-text'), greaterThan(initialOutputs));
    desktopTextScale.value = 0.9;
    await tester.pump();
    expect(size('agents-text'), lessThan(initialAgents));
  });
}
