import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{
    'agents': <Object?>[
      <String, Object?>{
        'agent_id': 'agent-test-01',
        'agent_name': 'QA Agent',
        'role': 'QA & Test',
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
        'skills': <Object?>['Playwright', 'E2E', 'CI/CD'],
        'performance_7d': <Object?>[72, 81, 76, 90, 84, 92, 88],
      },
      <String, Object?>{
        'agent_id': 'agent-backend-02',
        'agent_name': 'Backend Agent',
        'role': 'Backend',
        'status': 'busy',
        'current_task': 'API validation',
        'capacity': 86,
        'success_rate': 97.3,
      },
      <String, Object?>{
        'agent_id': 'agent-browser-03',
        'agent_name': 'Browser Agent',
        'role': 'Automation',
        'status': 'idle',
        'capacity': 18,
        'success_rate': 97.5,
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
        'agent_id': 'agent-test-01',
        'title': 'Memory threshold review',
        'severity': 'high',
      },
    ],
  },
  evidenceRecords: <EvidenceRecord>[],
  liveEvents: <Map<String, Object?>>[
    <String, Object?>{
      'agent_id': 'agent-test-01',
      'event_type': 'agent.started',
      'timestamp': '14:22',
    },
  ],
);

void main() {
  testWidgets('Agents keeps the approved dark reference hierarchy', (
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
    expect(find.byKey(const Key('selected-agent-panel')), findsWidgets);
    expect(find.byKey(const Key('agents-bottom-panels')), findsOneWidget);
    expect(find.text('QA Agent'), findsWidgets);
    expect(find.text('99.1%'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Agents renders the approved Turkish light surface', (
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
    expect(find.descendant(of: page, matching: find.text('Toplam Ajan')), findsWidgets);
    expect(find.text('Seçili Ajan'), findsOneWidget);
    expect(find.text('Bekleyen Atamalar'), findsOneWidget);
    expect(find.text('Ajan Rolleri'), findsOneWidget);
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
