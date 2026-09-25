import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/dashboard/reference_workflows_view.dart';
import 'package:ilaios_desktop/main.dart';

const _connected = ControlPlaneProjection(
  connected: true,
  status: 'Connected',
  goalCount: 1,
  jobCount: 1,
  lastEvent: null,
);
const _disconnected = ControlPlaneProjection.unavailable();
const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{
    'active_count': 1,
    'completed_count': 0,
    'overdue_count': 0,
    'workflow_templates': <Map<String, Object?>>[
      <String, Object?>{'name': 'LIVE_TEMPLATE_123'},
    ],
  },
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{
    'pending_approvals': <Map<String, Object?>>[
      <String, Object?>{'title': 'LIVE_APPROVAL_123'},
    ],
  },
  evidenceRecords: <Never>[],
  liveEvents: <Map<String, Object?>>[
    <String, Object?>{
      'job_id': 'job-live-123',
      'workflow_name': 'LIVE_WORKFLOW_123',
      'status': 'running',
      'event': 'LIVE_EVENT_123',
    },
  ],
);
void main() {
  testWidgets('Workflows hides stale records and metrics while disconnected', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    Future<void> show(bool connected) async {
      await tester.pumpWidget(
        MaterialApp(
          home: IlaiosLocaleScope(
            locale: IlaiosLocale.english,
            onChanged: (_) {},
            child: Scaffold(
              body: ReferenceWorkflowsView(
                projection: connected ? _connected : _disconnected,
                snapshot: _snapshot,
                status: connected ? 'Connected' : 'Disconnected',
                onNavigate: (_) {},
              ),
            ),
          ),
        ),
      );
      await tester.pumpAndSettle();
    }

    await show(true);
    for (final value in [
      'LIVE_WORKFLOW_123',
      'LIVE_APPROVAL_123',
      'LIVE_TEMPLATE_123',
    ]) {
      expect(find.text(value), findsWidgets);
    }
    final metrics = find.byKey(const Key('workflows-metrics'));
    expect(
      find.descendant(of: metrics, matching: find.text('1')),
      findsWidgets,
    );

    await show(false);
    for (final value in [
      'LIVE_WORKFLOW_123',
      'LIVE_APPROVAL_123',
      'LIVE_TEMPLATE_123',
      'LIVE_EVENT_123',
    ]) {
      expect(find.text(value), findsNothing);
    }
    expect(find.byKey(const Key('workflows-bottom-panels')), findsNothing);
    expect(
      find.descendant(of: metrics, matching: find.text('1')),
      findsNothing,
    );
    expect(
      find.descendant(of: metrics, matching: find.text('0')),
      findsNothing,
    );
    expect(
      find.descendant(of: metrics, matching: find.text('—')),
      findsNWidgets(5),
    );

    await show(true);
    for (final value in [
      'LIVE_WORKFLOW_123',
      'LIVE_APPROVAL_123',
      'LIVE_TEMPLATE_123',
    ]) {
      expect(find.text(value), findsWidgets);
    }
    expect(tester.takeException(), isNull);
  });
}
