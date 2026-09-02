import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';

const _evidence = EvidenceRecord(
  sequence: 1,
  executionId: 'exec-1',
  artifactDigest: 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
  action: 'video.local.rendered',
  previousHash: '',
  recordHash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
);

const _finishedProductEvidence = EvidenceRecord(
  sequence: 2,
  executionId: 'exec-2',
  artifactDigest: 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
  action: 'video.desktop.finished_product',
  previousHash: 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
  recordHash: 'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
);

void main() {
  testWidgets('disconnected goals surface disables one-prompt submission', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.tap(find.byKey(const ValueKey('nav-goals')));
    await tester.pumpAndSettle();
    expect(find.text('What do you want ILAIOS to build?'), findsOneWidget);
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('one-prompt-submit')))
          .onPressed,
      isNull,
    );
    expect(find.byKey(const Key('one-prompt-accepted')), findsNothing);
  });

  testWidgets('connected goals surface submits without claiming completion', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
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
    await tester.tap(find.byKey(const ValueKey('nav-goals')));
    await tester.pumpAndSettle();

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
    expect(find.text('Lifecycle: Unavailable'), findsOneWidget);
    expect(find.textContaining('missing evidence stays unavailable'), findsOneWidget);
  });

  testWidgets('home renders truthful command center without synthetic telemetry', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('command-center-home')), findsOneWidget);
    expect(find.byKey(const Key('command-center-hero')), findsOneWidget);
    expect(find.byKey(const Key('command-center-metrics')), findsNothing);
    expect(find.byKey(const Key('command-center-session')), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
  });

  testWidgets('Workflows projects authoritative job state and refresh', (
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
    await tester.tap(find.byKey(const ValueKey('nav-workflows')));
    await tester.pumpAndSettle();
    final workflowsPage = find.byKey(const Key('reference-workflows-page'));
    expect(workflowsPage, findsOneWidget);
    expect(
      find.descendant(of: workflowsPage, matching: find.text('Workflows')),
      findsOneWidget,
    );
    expect(find.text('5'), findsOneWidget);
    expect(find.text('2'), findsNothing);
    final refresh = find.byKey(const Key('workflows-refresh'));
    await tester.ensureVisible(refresh);
    await tester.tap(refresh);
    expect(refreshRequests, 1);
  });

  testWidgets('wide navigation exposes target information architecture', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(const IlaiosDesktopApp());
    expect(find.byKey(const ValueKey('nav-home')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-goals')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-workflows')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-agents')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-liveWorkspace')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-artifacts')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-approvals')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-evidence')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-costs')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-settings')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-li')), findsNothing);
  });

  testWidgets('live workspace stays read-only when projections are unavailable', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.tap(find.byKey(const ValueKey('nav-liveWorkspace')));
    await tester.pumpAndSettle();
    expect(find.text('Live Workspace'), findsWidgets);
    expect(find.text('Live Code'), findsWidgets);
    expect(find.text('Terminal'), findsWidgets);
    expect(find.text('Browser'), findsWidgets);
    expect(find.text('Files'), findsWidgets);
    expect(find.text('Logs'), findsWidgets);
    expect(find.text('Events'), findsWidgets);
    expect(
      find.textContaining('Authoritative source-file content'),
      findsOneWidget,
    );
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
    final evidencePage = find.byKey(const Key('reference-evidence-page'));
    expect(evidencePage, findsOneWidget);
    expect(
      find.descendant(of: evidencePage, matching: find.text('Evidence')),
      findsOneWidget,
    );
    expect(find.text('video.local.rendered'), findsWidgets);
    expect(find.byKey(const ValueKey('evidence-row-1')), findsOneWidget);
    expect(find.textContaining('exec-1'), findsWidgets);
    expect(find.textContaining('aaaaaaaaaaaaaaaaaa'), findsWidgets);
    expect(find.textContaining('content_base64'), findsNothing);
  });

  testWidgets('deliveries save only verified finished products', (
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
        evidenceRecords: <EvidenceRecord>[_evidence, _finishedProductEvidence],
        liveEvents: <Map<String, Object?>>[],
      ),
      operationalStatus: 'Operational APIs connected',
      onSaveArtifact: (record) async {
        saved = record;
        return r'C:\Users\test\Downloads\ILAIOS\artifact.mp4';
      },
    ));
    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();
    expect(find.text('video.local.rendered'), findsNothing);
    expect(find.text('video.desktop.finished_product'), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey('save-artifact-2')));
    await tester.pumpAndSettle();
    expect(saved, _finishedProductEvidence);
    expect(find.byKey(const Key('delivery-message')), findsOneWidget);
  });

  testWidgets('approval decisions require independent approver', (
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
    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();
    expect(find.textContaining('vault://must-never-render'), findsNothing);
    final request = find.descendant(
      of: find.byKey(const Key('approvals-table')),
      matching: find.text('Request request-'),
    );
    expect(request, findsOneWidget);
    await tester.tap(request);
    await tester.pumpAndSettle();
    final approve = find.byKey(const ValueKey('approve-request-7'));
    expect(approve, findsOneWidget);
    await tester.ensureVisible(approve);
    await tester.tap(approve);
    await tester.pumpAndSettle();
    expect(decidedRequest, 'request-7');
    expect(decidedValue, GovernanceDecision.approved);
    expect(find.text('Technical ID: request-7'), findsOneWidget);
    await tester.tap(find.byKey(const Key('approvals-back-to-queue')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('approvals-table')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('medium admitted work is never rendered as pending approval', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
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
        grantsState: <String, Object?>{
          'grants': <Object?>[],
          'revoked': <Object?>[],
          'stopped': <Object?>[],
        },
        governanceState: <String, Object?>{
          'work': <Object?>[
            <String, Object?>{
              'request_id': 'exec-medium',
              'requester_id': 'principal-a',
              'status': 'pending',
            },
          ],
          'admissions': <Object?>[
            <String, Object?>{
              'request_id': 'exec-medium',
              'risk': 'medium',
              'admission_decision': 'ALLOW',
              'human_approval_required': false,
            },
          ],
          'secret_references': <Object?>[],
          'ledger': <String, Object?>{},
        },
        evidenceRecords: <EvidenceRecord>[],
        liveEvents: <Map<String, Object?>>[],
      ),
      operationalStatus: 'Operational APIs connected',
      approverId: 'approver-b',
      onGovernanceDecision: (requestId, decision) async {},
    ));
    await tester.tap(find.byKey(const ValueKey('nav-approvals')));
    await tester.pumpAndSettle();
    expect(find.text('There are no matching approval requests right now.'), findsOneWidget);
    expect(find.byKey(const ValueKey('approve-exec-medium')), findsNothing);
    expect(find.byKey(const ValueKey('deny-exec-medium')), findsNothing);
  });


  testWidgets('Li is hidden for a signed-in nonfounder session', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        userSession: DesktopUserSession(
          sessionId: 'customer-session',
          providerId: 'google',
          principalId: 'usr_customer',
          tenantId: 'tnt_customer',
          displayIdentity: 'customer@example.com',
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('nav-settings')), findsOneWidget);
    expect(find.byKey(const ValueKey('nav-li')), findsNothing);
  });

  testWidgets('founder-only Li appears below Settings and revalidates state', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const session = DesktopUserSession(
      sessionId: 'founder-session',
      providerId: 'google',
      principalId: 'usr_founder',
      tenantId: 'tnt_founder',
      displayIdentity: 'founder@example.com',
      liFounder: true,
    );
    var stateRequests = 0;
    await tester.pumpWidget(
      IlaiosDesktopApp(
        userSession: session,
        onFetchLiState: () async {
          stateRequests += 1;
          return const DesktopLiState(
            name: 'Li',
            founderOperator: true,
            userId: 'usr_founder',
            tenantId: 'tnt_founder',
            source: 'canonical_desktop_session',
          );
        },
      ),
    );
    await tester.pumpAndSettle();

    final settings = find.byKey(const ValueKey('nav-settings'));
    final li = find.byKey(const ValueKey('nav-li'));
    expect(settings, findsOneWidget);
    expect(li, findsOneWidget);
    expect(
      tester.getTopLeft(li).dy,
      greaterThan(tester.getTopLeft(settings).dy),
    );

    await tester.tap(li);
    await tester.pumpAndSettle();

    expect(stateRequests, 1);
    expect(find.byKey(const Key('li-founder-view')), findsOneWidget);
    expect(find.text('Founder Operator'), findsOneWidget);
    expect(
      find.text('Server-authoritative founder access verified.'),
      findsOneWidget,
    );
  });

}
