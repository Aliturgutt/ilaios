import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
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

  testWidgets('dashboard projects populated authoritative runtime values without fixtures', (
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
    expect(find.text('RUNNING'), findsOneWidget);
    expect(find.text('64%'), findsOneWidget);
    expect(find.text('Frontend Dev'), findsOneWidget);
    expect(find.text('Test Engineer'), findsOneWidget);
    expect(find.text('render-authoritative-ui'), findsOneWidget);
    expect(find.text('verify-runtime-evidence'), findsOneWidget);
    expect(find.text('job-authoritative-001'), findsOneWidget);
    expect(find.text('00:02:15'), findsOneWidget);
    expect(find.text('Execution'), findsWidgets);
    expect(find.text('2.75'), findsOneWidget);
    expect(find.text('10.00'), findsOneWidget);
    expect(find.text('verified_delivery'), findsOneWidget);
    expect(find.text('2'), findsWidgets);
    expect(find.text('1'), findsWidgets);
    expect(find.textContaining('worker_progress'), findsWidgets);

    // Role slots are fixed reference-layout chrome, but activity and telemetry
    // remain authority-derived. Missing roles must not be presented as active.
    expect(find.text('Architect Agent'), findsOneWidget);
    expect(find.text('Backend Dev'), findsOneWidget);
    expect(find.text('Security Agent'), findsOneWidget);
    expect(find.text('Browser Agent'), findsOneWidget);
    expect(find.text('Deploy Agent'), findsOneWidget);

    // The UI must not invent telemetry that is absent from the authoritative
    // snapshot, even while rendering the populated values above.
    expect(find.text('73%'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
  });
}
