import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('connected control plane without runtime data never invents command-center telemetry', (
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

    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
    expect(find.text('Connected'), findsWidgets);
    expect(find.text('—'), findsWidgets);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.text('24'), findsNothing);
  });

  testWidgets('command center projects populated authoritative runtime values', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[
        <String, Object?>{'route_id': 'software'},
        <String, Object?>{'route_id': 'video'},
      ],
      schedulerState: <String, Object?>{
        'leases': <Map<String, Object?>>[
          <String, Object?>{
            'role': 'Frontend Dev',
            'task': 'render-authoritative-ui',
            'status': 'running',
          },
          <String, Object?>{
            'role': 'Test Engineer',
            'task': 'verify-runtime-evidence',
            'status': 'active',
          },
        ],
      },
      grantsState: <String, Object?>{'available': true},
      governanceState: <String, Object?>{
        'total_cost_usd': '2.75',
        'budget_usd': '10.00',
        'admissions': <Map<String, Object?>>[
          <String, Object?>{
            'request_id': 'approval-1',
            'human_approval_required': true,
          },
        ],
        'work': <Map<String, Object?>>[
          <String, Object?>{
            'request_id': 'approval-1',
            'status': 'pending',
          },
          <String, Object?>{
            'request_id': 'approval-2',
            'status': 'approved',
          },
          <String, Object?>{
            'request_id': 'approval-3',
            'status': 'denied',
          },
        ],
      },
      evidenceRecords: <EvidenceRecord>[
        EvidenceRecord(
          sequence: 1,
          executionId: 'execution-authoritative-001',
          artifactDigest: 'sha256-authoritative-artifact',
          action: 'verified_delivery',
          previousHash: '',
          recordHash: 'record-authoritative-001',
        ),
      ],
      liveEvents: <Map<String, Object?>>[
        <String, Object?>{
          'event_type': 'worker_progress',
          'job_id': 'job-authoritative-001',
          'started_at': '2026-08-16T16:00:00Z',
          'elapsed': '00:02:15',
          'estimated_finish': '2026-08-16T16:05:00Z',
          'phase': 'Execution',
          'status': 'running',
          'progress_percent': 64,
          'timestamp': '2026-08-16T16:02:15Z',
        },
      ],
    );

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        projection: ControlPlaneProjection(
          connected: true,
          status: 'Connected to authoritative control plane',
          goalCount: 1,
          jobCount: 1,
          lastEvent: 'worker_progress',
          schemaVersion: '1',
        ),
        operationalSnapshot: snapshot,
        operationalStatus: 'Operational APIs connected',
      ),
    );
    await tester.pumpAndSettle();

    expect(tester.takeException(), isNull);
    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    expect(find.byKey(const Key('command-center-metrics')), findsOneWidget);
    expect(find.text('2.75'), findsOneWidget);
    expect(find.text('approval-1'), findsOneWidget);
    expect(find.text('approval-2'), findsOneWidget);
    expect(find.text('approval-3'), findsOneWidget);
    expect(find.text('verified_delivery'), findsWidgets);
    expect(find.text('2'), findsWidgets);
    expect(find.text('1'), findsWidgets);

    // V4 summarizes runtime activity instead of exposing raw live-event fields.
    expect(find.text('job-authoritative-001'), findsNothing);
    expect(find.text('00:02:15'), findsNothing);

    // Demo reference telemetry is never promoted into runtime truth.
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.text('24'), findsNothing);
  });
}
