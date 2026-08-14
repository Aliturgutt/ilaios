import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _evidence = EvidenceRecord(
  sequence: 1,
  executionId: 'exec-1',
  artifactDigest: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  action: 'video.local.rendered',
  previousHash: '',
  recordHash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
);

void main() {
  testWidgets('disconnected shell disables one-prompt submission', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const IlaiosDesktopApp());
    expect(find.text('What do you want ILAIOS to build?'), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('one-prompt-submit')))
          .onPressed,
      isNull,
    );
    expect(find.byKey(const Key('one-prompt-accepted')), findsNothing);
  });

  testWidgets('connected shell submits one prompt without claiming completion', (
    WidgetTester tester,
  ) async {
    String? submitted;
    await tester.pumpWidget(IlaiosDesktopApp(
      projection: const ControlPlaneProjection(
        connected: true,
        status: 'Connected to authoritative control plane',
        goalCount: 2,
        jobCount: 5,
        lastEvent: 'job.updated',
        schemaVersion: '1',
      ),
      operationalStatus: 'Operational APIs connected',
      onPromptSubmit: (objective) async {
        submitted = objective;
        return const PromptSubmission(
          goalId: 'goal-00000003',
          jobId: 'job-00000006',
          state: 'PENDING',
        );
      },
    ));

    await tester.enterText(
      find.byKey(const Key('one-prompt-input')),
      'Build a premium website',
    );
    final submit = find.byKey(const Key('one-prompt-submit'));
    await tester.ensureVisible(submit);
    await tester.tap(submit);
    await tester.pumpAndSettle();

    expect(submitted, 'Build a premium website');
    expect(find.byKey(const Key('one-prompt-accepted')), findsOneWidget);
    expect(find.text('Goal: goal-00000003'), findsOneWidget);
    expect(find.text('Job: job-00000006'), findsOneWidget);
    expect(find.text('Authoritative state: PENDING'), findsOneWidget);
    expect(find.textContaining('does not treat submission as completion'), findsOneWidget);
  });

  testWidgets('control center still projects query state and refresh', (
    WidgetTester tester,
  ) async {
    var refreshRequests = 0;
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(IlaiosDesktopApp(
      projection: const ControlPlaneProjection(
        connected: true,
        status: 'Connected to authoritative control plane',
        goalCount: 2,
        jobCount: 5,
        lastEvent: 'job.updated',
        schemaVersion: '1',
      ),
      onRefreshRequested: () => refreshRequests += 1,
    ));
    await tester.tap(find.byKey(const ValueKey('nav-controlCenter')));
    await tester.pumpAndSettle();
    expect(find.text('2'), findsOneWidget);
    expect(find.text('5'), findsOneWidget);
    final refresh = find.byKey(const Key('refresh-command'));
    await tester.ensureVisible(refresh);
    await tester.tap(refresh);
    expect(refreshRequests, 1);
  });

  testWidgets('wide navigation exposes governed product surfaces', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(const IlaiosDesktopApp());
    expect(find.byKey(const ValueKey('nav-create')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-controlCenter')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-liveExecution')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-deliveries')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-evidence')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-governance')), findsOneWidget);
    expect(find.text('Agents'), findsNothing);
    expect(find.text('Approvals'), findsNothing);
  });

  testWidgets('verified evidence renders provenance metadata only', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(const IlaiosDesktopApp(
      projection: ControlPlaneProjection(
        connected: true,
        status: 'Connected to authoritative control plane',
        goalCount: 1,
        jobCount: 1,
        lastEvent: 'job.updated',
        schemaVersion: '1',
      ),
      operationalSnapshot: OperationalSnapshot(
        runtimeRoutes: <Map<String, Object?>>[
          <String, Object?>{'sequence': 1, 'provider_id': 'local'},
        ],
        schedulerState: <String, Object?>{
          'leases': <Object?>[<String, Object?>{'task_id': 'task-1'}],
          'effects': <Object?>[],
        },
        grantsState: <String, Object?>{
          'grants': <Object?>[],
          'revoked': <Object?>[],
          'stopped': <Object?>[],
        },
        governanceState: <String, Object?>{
          'work': <Object?>[],
          'secret_references': <Object?>[],
          'ledger': <String, Object?>{},
        },
        evidenceRecords: <EvidenceRecord>[_evidence],
        liveEvents: <Map<String, Object?>>[
          <String, Object?>{'event_type': 'job.updated'},
        ],
      ),
      operationalStatus: 'Operational APIs connected',
    ));

    await tester.tap(find.byKey(const ValueKey('nav-evidence')));
    await tester.pumpAndSettle();
    expect(find.text('Evidence & Audit'), findsOneWidget);
    expect(find.text('video.local.rendered'), findsOneWidget);
    expect(find.text('Execution: exec-1'), findsOneWidget);
    expect(find.textContaining('aaaaaaaaaaaaaaaaaa'), findsOneWidget);
    expect(find.textContaining('content_base64'), findsNothing);
  });

  testWidgets('deliveries save only verified evidence artifacts', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    EvidenceRecord? saved;
    await tester.pumpWidget(IlaiosDesktopApp(
      projection: const ControlPlaneProjection(
        connected: true,
        status: 'Connected to authoritative control plane',
        goalCount: 1,
        jobCount: 1,
        lastEvent: 'job.updated',
        schemaVersion: '1',
      ),
      operationalSnapshot: const OperationalSnapshot(
        runtimeRoutes: <Map<String, Object?>>[],
        schedulerState: <String, Object?>{},
        grantsState: <String, Object?>{},
        governanceState: <String, Object?>{},
        evidenceRecords: <EvidenceRecord>[_evidence],
        liveEvents: <Map<String, Object?>>[],
      ),
      operationalStatus: 'Operational APIs connected',
      onSaveArtifact: (record) async {
        saved = record;
        return r'C:\Users\test\Downloads\ILAIOS\artifact.mp4';
      },
    ));
    await tester.tap(find.byKey(const ValueKey('nav-deliveries')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('save-artifact-1')));
    await tester.pumpAndSettle();
    expect(saved, _evidence);
    expect(find.byKey(const Key('delivery-message')), findsOneWidget);
  });

  testWidgets('governance decisions require independent approver', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    String? decidedRequest;
    GovernanceDecision? decidedValue;
    await tester.pumpWidget(IlaiosDesktopApp(
      projection: const ControlPlaneProjection(
        connected: true,
        status: 'Connected to authoritative control plane',
        goalCount: 0,
        jobCount: 0,
        lastEvent: null,
        schemaVersion: '1',
      ),
      operationalSnapshot: const OperationalSnapshot(
        runtimeRoutes: <Map<String, Object?>>[],
        schedulerState: <String, Object?>{},
        grantsState: <String, Object?>{
          'grants': <Object?>[],
          'revoked': <Object?>[],
          'stopped': <Object?>[],
        },
        governanceState: <String, Object?>{
          'work': <Object?>[
            <String, Object?>{
              'request_id': 'request-7',
              'requester_id': 'requester-a',
              'status': 'pending',
            },
          ],
          'secret_references': <Object?>[
            <String, Object?>{
              'secret_id': 'secret-1',
              'reference': 'vault://must-never-render',
            },
          ],
          'ledger': <String, Object?>{},
        },
        evidenceRecords: <EvidenceRecord>[],
        liveEvents: <Map<String, Object?>>[],
      ),
      operationalStatus: 'Operational APIs connected',
      approverId: 'approver-b',
      onGovernanceDecision: (requestId, decision) async {
        decidedRequest = requestId;
        decidedValue = decision;
      },
    ));
    await tester.tap(find.byKey(const ValueKey('nav-governance')));
    await tester.pumpAndSettle();
    expect(find.textContaining('vault://must-never-render'), findsNothing);
    final approve = find.byKey(const ValueKey('approve-request-7'));
    await tester.ensureVisible(approve);
    await tester.tap(approve);
    expect(decidedRequest, 'request-7');
    expect(decidedValue, GovernanceDecision.approved);
  });
}
