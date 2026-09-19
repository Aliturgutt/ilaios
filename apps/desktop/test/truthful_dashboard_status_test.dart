import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('connected control plane without runtime data never invents canonical Home telemetry', (
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
    expect(find.byKey(const Key('home-command-prompt')), findsOneWidget);
    expect(find.text('No verified runtime agent data'), findsOneWidget);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.text('24'), findsNothing);
  });

  testWidgets('canonical Home projects only authority-derived agent runtime values', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    const snapshot = OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{
        'leases': <Map<String, Object?>>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.core.1',
            'status': 'running',
          },
        ],
      },
      grantsState: <String, Object?>{'available': true},
      governanceState: <String, Object?>{
        'total_cost_usd': '2.75',
        'budget_usd': '10.00',
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
      liveEvents: <Map<String, Object?>>[],
      agentState: <String, Object?>{
        'agents': <Map<String, Object?>>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.core.1',
            'team': 'core',
          },
        ],
      },
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
    expect(find.text('Core'), findsOneWidget);
    expect(find.text('1 busy'), findsOneWidget);
    expect(find.text('execution-authoritative-001'), findsNothing);
    expect(find.textContaining(r'$3.21'), findsNothing);
    expect(find.textContaining('18.362'), findsNothing);
    expect(find.text('96%'), findsNothing);
    expect(find.text('24'), findsNothing);
  });
}
