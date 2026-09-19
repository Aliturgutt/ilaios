import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/dashboard/pixel_agent_presentation.dart';
import 'package:ilaios_desktop/features/dashboard/pixel_agent_sprite.dart';

void main() {
  testWidgets('eight team sprites animate without scheduling after disposal', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Row(
          children: [
            for (final team in pixelAgentTeams)
              PixelAgentSprite(
                team: team,
                view: PixelAgentView.front,
                motion: PixelAgentMotion.working,
                size: const Size(32, 40),
                frameDuration: const Duration(milliseconds: 16),
              ),
          ],
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 64));
    expect(tester.takeException(), isNull);
    expect(find.byType(PixelAgentSprite), findsNWidgets(8));

    await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
    await tester.pump(const Duration(milliseconds: 64));
    expect(tester.takeException(), isNull);
  });

  testWidgets('offline team row remains static without fake motion', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Row(
          children: [
            for (final team in pixelAgentTeams)
              PixelAgentSprite(
                team: team,
                view: PixelAgentView.rear,
                motion: PixelAgentMotion.offline,
                size: const Size(32, 40),
                frameDuration: const Duration(milliseconds: 1),
              ),
          ],
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 100));
    for (final team in pixelAgentTeams) {
      expect(
        find.byKey(ValueKey('pixel-agent-$team-rear-offline-1')),
        findsOneWidget,
      );
    }
    expect(tester.takeException(), isNull);
  });
}
