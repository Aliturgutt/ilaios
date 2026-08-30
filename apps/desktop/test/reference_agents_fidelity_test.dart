import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _agentId = 'ilaios.agent.engineering.runtime-qa.v1';

const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{
    'agents': <Object?>[
      <String, Object?>{
        'agent_id': _agentId,
        'status': 'active',
        'current_task': 'Desktop acceptance',
        'task_stage': 'E2E',
        'capacity': 54,
        'success_rate': 99.1,
        'success_delta': 1.2,
        'response_ms': 1420,
        'last_activity': 'now',
        'owner': 'runtime',
        'created_at': '2026-08-17',
        'active_tasks': 1,
        'token_usage': 128400,
        'token_budget': 250000,
        'health': '98%',
      },
    ],
    'pending_assignments': <Object?>[
      <String, Object?>{
        'id': 'assign-1',
        'title': 'Validation queue',
        'role': 'QA',
        'priority': 'medium',
      },
    ],
  },
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{
    'pending_reviews': <Object?>[
      <String, Object?>{
        'id': 'review-1',
        'agent_id': _agentId,
        'title': 'Memory threshold review',
        'severity': 'high',
      },
    ],
  },
  evidenceRecords: <EvidenceRecord>[],
  liveEvents: <Map<String, Object?>>[
    <String, Object?>{
      'agent_id': _agentId,
      'event_type': 'agent.started',
      'timestamp': '14:22',
    },
  ],
  agentState: <String, Object?>{
    'canonical_count': 1,
    'registered_count': 1,
    'authority_drift_count': 0,
    'agents': <Object?>[
      <String, Object?>{
        'agent_id': _agentId,
        'alias': 'Argus',
        'role': 'runtime quality assurance',
        'team': 'engineering',
        'capabilities': <Object?>['runtime.verify'],
        'permissions': <Object?>['telemetry.read', 'verification.propose'],
        'readiness': 'registered',
        'registered': true,
        'authority_matches_canonical': true,
        'agent_status': 'offline',
      },
    ],
  },
);

Future<void> _selectAgent(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('agent-row-$_agentId')));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('Agents keeps the V4 dark hierarchy and reveals details contextually', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(operationalSnapshot: _snapshot),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-agents')));
    await tester.pumpAndSettle();

    final page = find.byKey(const Key('reference-agents-page'));
    expect(page, findsOneWidget);
    expect(find.descendant(of: page, matching: find.text('Agents')), findsOneWidget);
    expect(find.byKey(const Key('agents-metrics')), findsOneWidget);
    expect(find.byKey(const Key('agents-table-panel')), findsWidgets);
    expect(find.byKey(const Key('selected-agent-panel')), findsNothing);
    expect(find.byKey(const Key('agents-bottom-panels')), findsOneWidget);
    expect(find.text('Argus'), findsWidgets);

    await _selectAgent(tester);
    expect(find.byKey(const Key('selected-agent-panel')), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Agents renders the V4 Turkish light surface', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
        operationalSnapshot: _snapshot,
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-agents')));
    await tester.pumpAndSettle();

    final page = find.byKey(const Key('reference-agents-page'));
    expect(page, findsOneWidget);
    expect(find.descendant(of: page, matching: find.text('Ajanlar')), findsOneWidget);
    expect(find.descendant(of: page, matching: find.text('Toplam')), findsWidgets);
    expect(find.byKey(const Key('selected-agent-panel')), findsNothing);

    await _selectAgent(tester);
    expect(find.byKey(const Key('selected-agent-panel')), findsWidgets);
    expect(find.text('Bekleyen Atamalar'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Agents empty state never fabricates screenshot telemetry', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-agents')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('reference-agents-page')), findsOneWidget);
    expect(find.text('34'), findsNothing);
    expect(find.text('98.4%'), findsNothing);
    expect(find.text('1.42 sn'), findsNothing);
    expect(find.text('—'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
