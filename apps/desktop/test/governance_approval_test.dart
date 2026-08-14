import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/identity/identity_client.dart';
import 'package:ilaios_desktop/main.dart';

const _projection = ControlPlaneProjection(
  connected: true,
  status: 'Connected to authoritative control plane',
  goalCount: 1,
  jobCount: 1,
  lastEvent: 'governance.requested',
  schemaVersion: '1',
);

OperationalSnapshot _snapshot(String requesterId) => OperationalSnapshot(
      runtimeRoutes: const <Map<String, Object?>>[],
      schedulerState: const <String, Object?>{},
      grantsState: const <String, Object?>{
        'grants': <Object?>[],
        'revoked': <Object?>[],
        'stopped': <Object?>[],
      },
      governanceState: <String, Object?>{
        'work': <Object?>[
          <String, Object?>{
            'request_id': 'exec-approval-1',
            'requester_id': requesterId,
            'status': 'pending',
          },
        ],
        'secret_references': const <Object?>[],
        'ledger': const <String, Object?>{},
      },
      evidenceRecords: const <EvidenceRecord>[],
      liveEvents: const <Map<String, Object?>>[],
    );

void main() {
  testWidgets('requester session cannot self-approve coordinator execution', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    var calls = 0;
    await tester.pumpWidget(IlaiosDesktopApp(
      projection: _projection,
      operationalSnapshot: _snapshot('principal-requester'),
      operationalStatus: 'Operational APIs connected',
      userSession: const DesktopUserSession(
        sessionId: 'requester-session',
        providerId: 'google',
        principalId: 'principal-requester',
        tenantId: 'tenant-1',
      ),
      onGovernanceDecision: (_, __) async => calls += 1,
    ));

    await tester.tap(find.byKey(const ValueKey('nav-governance')));
    await tester.pumpAndSettle();

    final approve = tester.widget<FilledButton>(
      find.byKey(const ValueKey('approve-exec-approval-1')),
    );
    final deny = tester.widget<OutlinedButton>(
      find.byKey(const ValueKey('deny-exec-approval-1')),
    );
    expect(approve.onPressed, isNull);
    expect(deny.onPressed, isNull);
    expect(
      find.text('Requester cannot approve their own governed execution.'),
      findsOneWidget,
    );
    expect(calls, 0);
  });

  testWidgets('different verified principal can decide coordinator execution', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    String? decidedRequest;
    GovernanceDecision? decidedValue;
    await tester.pumpWidget(IlaiosDesktopApp(
      projection: _projection,
      operationalSnapshot: _snapshot('principal-requester'),
      operationalStatus: 'Operational APIs connected',
      userSession: const DesktopUserSession(
        sessionId: 'approver-session',
        providerId: 'microsoft',
        principalId: 'principal-approver',
        tenantId: 'tenant-1',
      ),
      onGovernanceDecision: (requestId, decision) async {
        decidedRequest = requestId;
        decidedValue = decision;
      },
    ));

    await tester.tap(find.byKey(const ValueKey('nav-governance')));
    await tester.pumpAndSettle();
    final approve = find.byKey(const ValueKey('approve-exec-approval-1'));
    await tester.ensureVisible(approve);
    await tester.tap(approve);

    expect(decidedRequest, 'exec-approval-1');
    expect(decidedValue, GovernanceDecision.approved);
  });

  testWidgets('coordinator approval remains disabled without verified session', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1280, 800));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(IlaiosDesktopApp(
      projection: _projection,
      operationalSnapshot: _snapshot('principal-requester'),
      operationalStatus: 'Operational APIs connected',
      approverId: 'legacy-operator-string',
      onGovernanceDecision: (_, __) async {},
    ));

    await tester.tap(find.byKey(const ValueKey('nav-governance')));
    await tester.pumpAndSettle();

    final approve = tester.widget<FilledButton>(
      find.byKey(const ValueKey('approve-exec-approval-1')),
    );
    expect(approve.onPressed, isNull);
    expect(
      find.text('Sign in as an independent approver to decide this execution.'),
      findsOneWidget,
    );
  });
}
