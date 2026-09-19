import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/dashboard/pixel_agent_presentation.dart';
import 'package:ilaios_desktop/features/dashboard/pixel_agent_sprite.dart';

void main() {
  testWidgets('offline sprite is static and uses the single real frame', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: PixelAgentSprite(
          team: 'core',
          view: PixelAgentView.front,
          motion: PixelAgentMotion.offline,
          frameDuration: Duration(milliseconds: 10),
        ),
      ),
    );
    expect(find.byKey(const ValueKey('pixel-agent-core-front-offline-1')), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 50));
    expect(find.byKey(const ValueKey('pixel-agent-core-front-offline-1')), findsOneWidget);
  });

  testWidgets('working sprite advances only across manifest-backed frames', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: PixelAgentSprite(
          team: 'engineering',
          view: PixelAgentView.rear,
          motion: PixelAgentMotion.working,
          frameDuration: Duration(milliseconds: 10),
        ),
      ),
    );
    expect(find.byKey(const ValueKey('pixel-agent-engineering-rear-working-1')), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 10));
    expect(find.byKey(const ValueKey('pixel-agent-engineering-rear-working-2')), findsOneWidget);
    await tester.pump(const Duration(milliseconds: 30));
    expect(find.byKey(const ValueKey('pixel-agent-engineering-rear-working-1')), findsOneWidget);
  });

  testWidgets('unknown team fails closed without fabricated image', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: PixelAgentSprite(
          team: 'invented',
          view: PixelAgentView.front,
          motion: PixelAgentMotion.working,
        ),
      ),
    );
    expect(find.byKey(const Key('pixel-agent-missing-frame')), findsOneWidget);
    expect(find.byType(Image), findsNothing);
  });

  testWidgets('disposing animated sprite cancels presentation timer', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: PixelAgentSprite(
          team: 'media',
          view: PixelAgentView.front,
          motion: PixelAgentMotion.waiting,
          frameDuration: Duration(milliseconds: 10),
        ),
      ),
    );
    await tester.pump(const Duration(milliseconds: 20));
    await tester.pumpWidget(const MaterialApp(home: SizedBox.shrink()));
    await tester.pump(const Duration(milliseconds: 50));
    expect(tester.takeException(), isNull);
  });
}
