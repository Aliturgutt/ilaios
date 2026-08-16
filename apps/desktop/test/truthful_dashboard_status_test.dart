import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('connected control plane without runtime event never claims active workflow', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
          schemaVersion: '1',
        ),
        operationalSnapshot: OperationalSnapshot.unavailable(),
        operationalStatus: 'Operational APIs connected',
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('NO ACTIVE DATA'), findsOneWidget);
    expect(find.text('LIVE'), findsNothing);
    expect(find.text('Project'), findsOneWidget);
    expect(find.text('Unavailable'), findsWidgets);
    expect(find.text('73%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });
}
