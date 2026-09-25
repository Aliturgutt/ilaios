import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _agentId = 'ilaios.agent.core.disconnect.v1';
const _online = ControlPlaneProjection(
  connected: true,
  status: 'Connected',
  goalCount: 0,
  jobCount: 0,
  lastEvent: null,
);
const _offline = ControlPlaneProjection.unavailable();
const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[
    <String, Object?>{
      'agent_id': _agentId,
      'status': 'working',
      'current_task': 'LIVE_TASK_123',
      'capacity': 0.72,
      'success_rate': 0.84,
      'last_activity': 'LIVE_ACTIVITY_123',
    },
  ],
  schedulerState: <String, Object?>{},
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{},
  evidenceRecords: <Never>[],
  liveEvents: <Map<String, Object?>>[],
  agentState: <String, Object?>{
    'agents': <Map<String, Object?>>[
      <String, Object?>{
        'agent_id': _agentId,
        'alias': 'Disconnect Agent',
        'team': 'core',
        'registered': true,
        'status': 'working',
        'current_task': 'LIVE_TASK_123',
        'capacity': 0.72,
        'success_rate': 0.84,
        'last_activity': 'LIVE_ACTIVITY_123',
      },
    ],
  },
);

void main() {
  testWidgets(
    'home and Agents discard stale runtime after disconnect and restore on reconnect',
    (tester) async {
      await tester.binding.setSurfaceSize(const Size(1648, 1024));
      addTearDown(() => tester.binding.setSurfaceSize(null));
      Future<void> show(bool connected) async {
        await tester.pumpWidget(
          IlaiosDesktopApp(
            projection: connected ? _online : _offline,
            operationalSnapshot: _snapshot,
          ),
        );
        await tester.pumpAndSettle();
      }

      await show(true);
      // Home does not display agent telemetry; validate it on Agents below.
      expect(find.text('1 busy'), findsNothing);
      await show(false);
      expect(find.text('1 busy'), findsNothing);
      await show(true);
      expect(find.text('1 busy'), findsNothing);

      await tester.tap(find.byKey(const Key('nav-agents')));
      await tester.pumpAndSettle();
      final row = find.byKey(const ValueKey('agent-row-$_agentId'));
      expect(
        find.descendant(of: row, matching: find.text('LIVE_TASK_123')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: row, matching: find.text('LIVE_ACTIVITY_123')),
        findsOneWidget,
      );
      expect(find.byKey(const Key('agents-summary-busy')), findsOneWidget);
      expect(
        find.descendant(of: row, matching: find.text('84.0%')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: row, matching: find.text('72%')),
        findsOneWidget,
      );

      await show(false);
      final disconnectedRow = find.byKey(const ValueKey('agent-row-$_agentId'));
      expect(
        find.descendant(
          of: disconnectedRow,
          matching: find.text('LIVE_TASK_123'),
        ),
        findsNothing,
      );
      expect(
        find.descendant(
          of: disconnectedRow,
          matching: find.text('LIVE_ACTIVITY_123'),
        ),
        findsNothing,
      );
      expect(
        find.descendant(of: disconnectedRow, matching: find.text('84.0%')),
        findsNothing,
      );
      expect(
        find.descendant(of: disconnectedRow, matching: find.text('72%')),
        findsNothing,
      );
      for (final key in ['total', 'active', 'busy', 'idle']) {
        final card = find.byKey(ValueKey('agents-summary-$key'));
        expect(
          find.descendant(of: card, matching: find.text('—')),
          findsOneWidget,
        );
      }
      await show(true);
      final restoredRow = find.byKey(const ValueKey('agent-row-$_agentId'));
      expect(
        find.descendant(of: restoredRow, matching: find.text('LIVE_TASK_123')),
        findsOneWidget,
      );
      expect(
        find.descendant(
          of: restoredRow,
          matching: find.text('LIVE_ACTIVITY_123'),
        ),
        findsOneWidget,
      );
      expect(
        find.descendant(of: restoredRow, matching: find.text('84.0%')),
        findsOneWidget,
      );
      expect(
        find.descendant(of: restoredRow, matching: find.text('72%')),
        findsOneWidget,
      );
      expect(tester.takeException(), isNull);
    },
  );
}
