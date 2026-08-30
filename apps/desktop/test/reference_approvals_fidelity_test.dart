import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

const _requests = <Map<String, Object?>>[
  <String, Object?>{
    'request_id': 'req-deploy-001',
    'title': 'Production Deployment Onayı',
    'request_type': 'Dağıtım',
    'requester_id': 'agent-a',
    'requester_name': 'Ayşe K.',
    'owner_name': 'Mert E.',
    'risk': 'high',
    'reason': 'Yeni sürümün kontrollü production dağıtımı.',
    'created_at': '2026-08-17T18:10:00Z',
    'due_at': '2026-08-18T18:00:00Z',
    'wait_seconds': 7980,
    'status': 'pending',
    'affected_scope': <Object?>['Production', 'API Gateway', 'Auth Service'],
  },
  <String, Object?>{
    'request_id': 'req-content-002',
    'title': 'İçerik Yayın Onayı',
    'request_type': 'İçerik',
    'requester_id': 'agent-b',
    'risk': 'low',
    'reason': 'Doğrulanmış kampanya içeriğinin yayınlanması.',
    'created_at': '2026-08-17T17:40:00Z',
    'wait_seconds': 3240,
    'status': 'pending',
  },
  <String, Object?>{
    'request_id': 'req-budget-003',
    'title': 'Bütçe Limiti Artışı',
    'request_type': 'Finans',
    'requester_id': 'agent-c',
    'risk': 'medium',
    'reason': 'Test kapasitesi için limit artışı.',
    'created_at': '2026-08-17T15:20:00Z',
    'status': 'approved',
  },
  <String, Object?>{
    'request_id': 'req-api-004',
    'title': 'Harici API Erişimi',
    'request_type': 'Güvenlik',
    'requester_id': 'agent-d',
    'risk': 'high',
    'reason': 'Yetkili üçüncü taraf API erişimi.',
    'created_at': '2026-08-17T14:10:00Z',
    'status': 'denied',
  },
  <String, Object?>{
    'request_id': 'req-data-005',
    'title': 'Veri Dışı Aktarım Talebi',
    'request_type': 'Veri',
    'requester_id': 'agent-e',
    'risk': 'low',
    'reason': 'Doğrulanmış analitik veri aktarımı.',
    'created_at': '2026-08-17T13:00:00Z',
    'status': 'approved',
  },
];

const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{},
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{
    'work': _requests,
    'admissions': <Object?>[
      <String, Object?>{'request_id': 'req-deploy-001', 'human_approval_required': true},
      <String, Object?>{'request_id': 'req-content-002', 'human_approval_required': true},
      <String, Object?>{'request_id': 'req-budget-003', 'human_approval_required': true},
      <String, Object?>{'request_id': 'req-api-004', 'human_approval_required': true},
      <String, Object?>{'request_id': 'req-data-005', 'human_approval_required': true},
    ],
    'violations': <Object?>[
      <String, Object?>{
        'title': 'IP kısıtlaması ihlal denemesi',
        'created_at': '2026-08-17T12:00:00Z',
      },
    ],
  },
  evidenceRecords: <EvidenceRecord>[
    EvidenceRecord(
      sequence: 1,
      executionId: 'req-deploy-001',
      artifactDigest: 'sha256:approval-evidence',
      action: 'security.scan.verified',
      previousHash: '',
      recordHash: 'approval-record-hash',
    ),
  ],
  liveEvents: <Map<String, Object?>>[],
);

Future<void> _openApprovals(WidgetTester tester) async {
  await tester.tap(find.byKey(const ValueKey('nav-approvals')));
  await tester.pumpAndSettle();
}

Future<void> _selectDeployRequest(WidgetTester tester) async {
  await tester.tap(find.text('Production Deployment Onayı').first);
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('Approvals keeps the V4 dark hierarchy and reveals details on selection', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        approverId: 'operator-1',
        operationalSnapshot: _snapshot,
        operationalStatus: 'Connected to authoritative control plane',
      ),
    );
    await tester.pumpAndSettle();
    await _openApprovals(tester);

    final page = find.byKey(const Key('reference-approvals-page'));
    expect(page, findsOneWidget);
    expect(find.byKey(const Key('approvals-header')), findsOneWidget);
    expect(find.byKey(const Key('approvals-tabs')), findsOneWidget);
    expect(find.byKey(const Key('approvals-filters')), findsOneWidget);
    expect(find.byKey(const Key('approvals-table')), findsOneWidget);
    expect(find.byKey(const Key('approvals-selected-request')), findsNothing);
    expect(find.text('Production Deployment Onayı'), findsWidgets);

    await _selectDeployRequest(tester);
    expect(find.byKey(const Key('approvals-right-rail')), findsOneWidget);
    expect(find.byKey(const Key('approvals-selected-request')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Approvals renders the V4 Turkish light surface', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
        approverId: 'operator-1',
        operationalSnapshot: _snapshot,
        operationalStatus: 'Connected to authoritative control plane',
      ),
    );
    await tester.pumpAndSettle();
    await _openApprovals(tester);

    expect(find.text('Onaylar'), findsWidgets);
    expect(find.textContaining('Bekleyen (2)'), findsOneWidget);
    expect(find.textContaining('Yüksek Risk (2)'), findsOneWidget);
    expect(find.byKey(const Key('approvals-selected-request')), findsNothing);

    await _selectDeployRequest(tester);
    expect(find.text('Seçili Talep'), findsOneWidget);
    expect(find.byKey(const Key('approvals-selected-request')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Approvals decision controls preserve authoritative callback', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    String? decidedRequest;
    GovernanceDecision? decidedValue;

    await tester.pumpWidget(
      IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        approverId: 'operator-1',
        operationalSnapshot: _snapshot,
        onGovernanceDecision: (requestId, decision) async {
          decidedRequest = requestId;
          decidedValue = decision;
        },
      ),
    );
    await tester.pumpAndSettle();
    await _openApprovals(tester);
    await _selectDeployRequest(tester);

    await tester.tap(find.byKey(const ValueKey('approve-req-deploy-001')));
    await tester.pumpAndSettle();

    expect(decidedRequest, 'req-deploy-001');
    expect(decidedValue, GovernanceDecision.approved);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Approvals empty state never fabricates screenshot metrics', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(locale: IlaiosLocale.turkish),
    );
    await tester.pumpAndSettle();
    await _openApprovals(tester);

    expect(find.byKey(const Key('reference-approvals-page')), findsOneWidget);
    expect(find.text('156'), findsNothing);
    expect(find.text('28'), findsNothing);
    expect(find.text('96'), findsNothing);
    expect(find.text('22'), findsNothing);
    expect(find.text('2s 34dk'), findsNothing);
    expect(find.text('Yönetişim verisi kullanılamıyor.'), findsOneWidget);
    expect(find.byKey(const Key('approvals-selected-request')), findsNothing);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Approvals stays in the same design family at compact viewport', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1180, 720));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        operationalSnapshot: _snapshot,
      ),
    );
    await tester.pumpAndSettle();
    await _openApprovals(tester);

    expect(find.byKey(const Key('reference-approvals-page')), findsOneWidget);
    expect(find.byKey(const Key('approvals-table')), findsOneWidget);
    expect(find.byKey(const Key('reference-scaled-viewport-v9')), findsOneWidget);
    expect(find.text('Onaylar'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
