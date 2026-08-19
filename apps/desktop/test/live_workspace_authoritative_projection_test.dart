import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('unrelated live event cannot override workspace session authority', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{
        'workspace_mode': 'Authoritative Mode',
        'project_name': 'Authoritative Project',
        'owner': 'authoritative-owner',
        'preview_url': 'https://authoritative.invalid',
        'session_id': 'authoritative-session',
      },
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{},
      evidenceRecords: [],
      liveEvents: <Map<String, Object?>>[
        <String, Object?>{
          'event_type': 'provider.request.completed',
          'project_name': 'POISON PROJECT',
          'owner': 'poison-owner',
          'mode': 'poison-mode',
          'url': 'https://poison.invalid',
          'message': 'provider request completed',
        },
      ],
    );

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        operationalSnapshot: snapshot,
        operationalStatus: 'Connected to authoritative control plane',
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-liveWorkspace')));
    await tester.pumpAndSettle();

    expect(find.text('Authoritative Project'), findsWidgets);
    expect(find.text('Authoritative Mode'), findsWidgets);
    expect(find.text('authoritative-owner'), findsOneWidget);
    expect(find.text('https://authoritative.invalid'), findsWidgets);
    expect(find.text('POISON PROJECT'), findsNothing);
    expect(find.text('poison-owner'), findsNothing);
    expect(find.text('poison-mode'), findsNothing);
    expect(find.text('https://poison.invalid'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
