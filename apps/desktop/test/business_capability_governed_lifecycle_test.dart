import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/business_context/business_capability_context.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/create/governed_lifecycle_projection.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/main.dart';

class _IntentTransport implements ControlPlaneTransport {
  String? body;

  @override
  Future<ControlPlaneResponse> get(
    Uri uri, {
    Map<String, String> headers = const <String, String>{},
  }) async => throw StateError('Unexpected GET ${uri.path}');

  @override
  Future<ControlPlaneResponse> post(
    Uri uri, {
    required String body,
    Map<String, String> headers = const <String, String>{},
  }) async {
    if (uri.path != '/v1/desktop/intent') {
      throw StateError('Unexpected POST ${uri.path}');
    }
    this.body = body;
    return const ControlPlaneResponse(
      statusCode: 201,
      body:
          '{"goal_id":"goal-1","job_id":"job-1","state":"PENDING","request_id":"exec-1","execution_status":"PENDING_APPROVAL","business_context_code":"BCF02"}',
    );
  }
}

const _session = DesktopUserSession(
  sessionId: 'session-1',
  providerId: 'google',
  principalId: 'principal-1',
  tenantId: 'tenant-1',
);

const _connectedProjection = ControlPlaneProjection(
  connected: true,
  status: 'Connected to authoritative control plane',
  goalCount: 1,
  jobCount: 1,
  lastEvent: 'execution.updated',
  schemaVersion: '1',
);

const _pendingApprovalSnapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{},
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{
    'work': <Object?>[
      <String, Object?>{
        'request_id': 'exec-1',
        'status': 'pending',
      },
    ],
    'admissions': <Object?>[
      <String, Object?>{
        'request_id': 'exec-1',
        'human_approval_required': true,
      },
    ],
  },
  evidenceRecords: <EvidenceRecord>[],
  liveEvents: <Map<String, Object?>>[
    <String, Object?>{
      'sequence': 1,
      'request_id': 'exec-1',
      'execution_status': 'EXECUTING',
    },
  ],
);

void main() {
  tearDown(() {
    BusinessCapabilitySubmissionBus.clear();
    GovernedLifecycleProjectionStore.clear();
  });

  test('business capability codes stay bounded and one-shot', () {
    expect(
      BusinessCapabilityFamily.values.map((value) => value.contextCode),
      <String>['BCF01', 'BCF02', 'BCF03', 'BCF04', 'BCF05', 'BCF06'],
    );
    const context = BusinessCapabilityContext(BusinessCapabilityFamily.operations);
    BusinessCapabilitySubmissionBus.stage(context);
    expect(BusinessCapabilitySubmissionBus.pending?.contextCode, 'BCF02');
    expect(BusinessCapabilitySubmissionBus.take()?.contextCode, 'BCF02');
    expect(BusinessCapabilitySubmissionBus.take(), isNull);
  });

  test('authenticated intent keeps prompt unchanged and sends context separately', () async {
    final transport = _IntentTransport();
    final client = IdentityClient(
      baseUri: Uri.parse('http://127.0.0.1:43123'),
      transportToken: 'local-token',
      transport: transport,
    );
    const objective = 'Build a quarterly operating plan';

    final result = await client.submitPrompt(
      objective,
      _session,
      businessContext:
          const BusinessCapabilityContext(BusinessCapabilityFamily.operations),
    );

    final payload = jsonDecode(transport.body!) as Map<String, dynamic>;
    expect(payload['objective'], objective);
    expect(payload['business_context_code'], 'BCF02');
    expect(payload.containsKey('provider_id'), isFalse);
    expect(payload.containsKey('worker_id'), isFalse);
    expect(payload.containsKey('route_id'), isFalse);
    expect(payload.containsKey('approval'), isFalse);
    expect(result.requestId, 'exec-1');
    expect(result.executionStatus, 'PENDING_APPROVAL');
  });

  test('pending approval outranks conflicting execution event', () {
    expect(
      resolveGovernedLifecycle(
        _pendingApprovalSnapshot,
        'exec-1',
        admittedStatus: 'EXECUTING',
      ),
      GovernedLifecycleState.pendingApproval,
    );
    expect(
      resolveGovernedLifecycle(
        _pendingApprovalSnapshot,
        'other-request',
        admittedStatus: 'EXECUTING',
      ),
      GovernedLifecycleState.unavailable,
    );
  });

  testWidgets('Create selector sends metadata without rewriting prompt and clears stale lifecycle', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    String? submitted;
    BusinessCapabilityContext? receivedContext;

    Future<PromptSubmission> submit(String objective) async {
      submitted = objective;
      receivedContext = BusinessCapabilitySubmissionBus.take();
      return const GovernedPromptSubmission(
        goalId: 'goal-1',
        jobId: 'job-1',
        state: 'PENDING',
        requestId: 'exec-1',
        executionStatus: 'PENDING_APPROVAL',
      );
    }

    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: _connectedProjection,
        operationalSnapshot: _pendingApprovalSnapshot,
        userSession: _session,
        onPromptSubmit: submit,
      ),
    );
    await tester.tap(find.byKey(const ValueKey('nav-goals')));
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('one-prompt-input')),
      'Build a quarterly operating plan',
    );
    await tester.tap(find.byKey(const Key('business-capability-selector')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('business-context-BCF02')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('one-prompt-submit')));
    await tester.pumpAndSettle();

    expect(submitted, 'Build a quarterly operating plan');
    expect(receivedContext?.contextCode, 'BCF02');
    expect(BusinessCapabilitySubmissionBus.pending, isNull);
    expect(find.text('Lifecycle: Pending approval'), findsOneWidget);
    expect(find.text('Lifecycle: Executing'), findsNothing);

    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: _connectedProjection,
        operationalSnapshot: const OperationalSnapshot.unavailable(),
        userSession: _session,
        onPromptSubmit: submit,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Lifecycle: Unavailable'), findsOneWidget);
    expect(find.text('Lifecycle: Pending approval'), findsNothing);
  });
}
