import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _connected = ControlPlaneProjection(
  connected: true,
  status: 'Connected',
  goalCount: 0,
  jobCount: 0,
  lastEvent: null,
);
const _offline = ControlPlaneProjection.unavailable();
const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{},
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{
    'work': <Map<String, Object?>>[
      <String, Object?>{
        'request_id': 'approval-live-123',
        'title': 'LIVE_APPROVAL_123',
        'status': 'pending',
      },
    ],
  },
  evidenceRecords: <EvidenceRecord>[
    EvidenceRecord(
      sequence: 1,
      executionId: 'LIVE_OUTPUT_123',
      artifactDigest: 'sha256:live-output',
      action: 'web.finished_product',
      previousHash: '',
      recordHash: 'live-record-hash',
    ),
  ],
  liveEvents: <Map<String, Object?>>[],
);
void main() {
  testWidgets('Outputs and Approvals hide cached records on disconnect', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    Future<void> show(bool connected) async {
      await tester.pumpWidget(
        IlaiosDesktopApp(
          projection: connected ? _connected : _offline,
          operationalSnapshot: _snapshot,
        ),
      );
      await tester.pumpAndSettle();
    }

    await show(true);
    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();
    expect(find.text('LIVE_OUTPUT_123'), findsWidgets);
    await show(false);
    expect(find.text('LIVE_OUTPUT_123'), findsNothing);
    expect(
      find.text('Connection lost; output data cannot be verified.'),
      findsOneWidget,
    );
    expect(find.byKey(const Key('outputs-kpis')), findsNothing);
    await show(true);
    expect(find.text('LIVE_OUTPUT_123'), findsWidgets);

    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();
    expect(find.text('LIVE_APPROVAL_123'), findsWidgets);
    await show(false);
    expect(find.text('LIVE_APPROVAL_123'), findsNothing);
    expect(
      find.text('Connection lost; approval data cannot be verified.'),
      findsOneWidget,
    );
    await show(true);
    expect(find.text('LIVE_APPROVAL_123'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
  testWidgets('empty, access denied and fresh reconnect are distinct', (
    tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 1024));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    const empty = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{'work': <Map<String, Object?>>[]},
      evidenceRecords: <EvidenceRecord>[],
      liveEvents: <Map<String, Object?>>[],
    );
    const fresh = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{
        'work': <Map<String, Object?>>[
          <String, Object?>{
            'request_id': 'new-request',
            'title': 'NEW_APPROVAL_456',
            'status': 'pending',
          },
        ],
      },
      evidenceRecords: <EvidenceRecord>[
        EvidenceRecord(
          sequence: 2,
          executionId: 'NEW_OUTPUT_456',
          artifactDigest: 'sha256:new-output',
          action: 'web.finished_product',
          previousHash: '',
          recordHash: 'new-record-hash',
        ),
      ],
      liveEvents: <Map<String, Object?>>[],
    );
    Future<void> show(
      OperationalSnapshot snapshot, {
      String status = 'Connected',
    }) async {
      await tester.pumpWidget(
        IlaiosDesktopApp(
          projection: _connected,
          operationalSnapshot: snapshot,
          operationalStatus: status,
        ),
      );
      await tester.pumpAndSettle();
    }

    await show(empty);
    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('outputs-data-unavailable')), findsNothing);
    expect(find.byKey(const Key('outputs-kpis')), findsNothing);
    await show(_snapshot, status: '403 Forbidden');
    expect(find.text('LIVE_OUTPUT_123'), findsNothing);
    expect(find.text('Access to outputs was denied.'), findsOneWidget);
    expect(find.byKey(const Key('outputs-kpis')), findsNothing);
    await show(fresh);
    expect(find.text('NEW_OUTPUT_456'), findsWidgets);
    expect(find.text('LIVE_OUTPUT_123'), findsNothing);
    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();
    expect(find.text('NEW_APPROVAL_456'), findsWidgets);
    await show(empty);
    expect(find.text('No requests in the decision queue.'), findsOneWidget);
    await show(_snapshot, status: '403 Forbidden');
    expect(find.text('LIVE_APPROVAL_123'), findsNothing);
    expect(find.text('Access to approvals was denied.'), findsOneWidget);
    await show(fresh);
    expect(find.text('NEW_APPROVAL_456'), findsWidgets);
    expect(find.text('LIVE_APPROVAL_123'), findsNothing);
    expect(tester.takeException(), isNull);
  });
}
