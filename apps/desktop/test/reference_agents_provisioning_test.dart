import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/features/dashboard/agent_provision_scope.dart';
import 'package:ilaios_desktop/features/dashboard/reference_agents_view.dart';

const _projection = ControlPlaneProjection(
  connected: true,
  status: 'Connected',
  goalCount: 0,
  jobCount: 0,
  lastEvent: null,
);

OperationalSnapshot _snapshot() => const OperationalSnapshot(
      runtimeRoutes: <Map<String, Object?>>[],
      schedulerState: <String, Object?>{},
      grantsState: <String, Object?>{},
      governanceState: <String, Object?>{},
      evidenceRecords: [],
      liveEvents: <Map<String, Object?>>[],
      agentState: <String, Object?>{
        'agents': <Object?>[
          <String, Object?>{
            'agent_id': 'ilaios.agent.alpha.v1',
            'alias': 'Alpha',
            'role': 'Security',
            'team': 'Platform',
            'capabilities': <Object?>['security.sast'],
            'registered': false,
            'authority_matches_canonical': true,
          },
          <String, Object?>{
            'agent_id': 'ilaios.agent.registered.v1',
            'alias': 'Registered',
            'role': 'QA',
            'team': 'Platform',
            'capabilities': <Object?>['quality.test'],
            'registered': true,
            'authority_matches_canonical': true,
          },
          <String, Object?>{
            'agent_id': 'ilaios.agent.drift.v1',
            'alias': 'Drifted',
            'role': 'Backend',
            'team': 'Platform',
            'capabilities': <Object?>['backend.execute'],
            'registered': false,
            'authority_matches_canonical': false,
          },
        ],
      },
    );

Widget _app({Future<void> Function(String agentId)? onProvisionAgent}) =>
    IlaiosLocaleScope(
      locale: IlaiosLocale.english,
      onChanged: (_) {},
      child: MaterialApp(
        home: AgentProvisionScope(
          onProvisionAgent: onProvisionAgent,
          child: Scaffold(
            body: SizedBox(
              width: 1500,
              height: 900,
              child: ReferenceAgentsView(
                projection: _projection,
                snapshot: _snapshot(),
                status: 'Connected',
                onNavigate: (_) {},
              ),
            ),
          ),
        ),
      ),
    );

void main() {
  testWidgets('new agent is disabled without authenticated provision callback',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1500, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(_app());

    final button = tester.widget<FilledButton>(
      find.byKey(const Key('new-agent-button')),
    );
    expect(button.onPressed, isNull);
  });

  testWidgets('chooser exposes only canonical state and sends exact agent id',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1500, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final provisioned = <String>[];

    await tester.pumpWidget(
      _app(onProvisionAgent: (agentId) async => provisioned.add(agentId)),
    );
    await tester.tap(find.byKey(const Key('new-agent-button')));
    await tester.pumpAndSettle();

    final dialog = find.byKey(const Key('canonical-agent-provision-dialog'));
    expect(dialog, findsOneWidget);
    expect(
      find.descendant(of: dialog, matching: find.byType(TextField)),
      findsNothing,
    );
    expect(find.text('Alpha'), findsOneWidget);
    expect(find.text('Registered'), findsOneWidget);
    expect(find.text('Drifted'), findsOneWidget);

    final registeredTile = tester.widget<ListTile>(
      find.byKey(const Key('canonical-agent-option-ilaios.agent.registered.v1')),
    );
    final driftTile = tester.widget<ListTile>(
      find.byKey(const Key('canonical-agent-option-ilaios.agent.drift.v1')),
    );
    expect(registeredTile.enabled, isFalse);
    expect(registeredTile.onTap, isNull);
    expect(driftTile.enabled, isFalse);
    expect(driftTile.onTap, isNull);

    await tester.tap(
      find.byKey(const Key('canonical-agent-option-ilaios.agent.alpha.v1')),
    );
    await tester.pumpAndSettle();

    expect(provisioned, <String>['ilaios.agent.alpha.v1']);
    expect(dialog, findsNothing);
  });

  testWidgets('failed provision does not fabricate registered UI state',
      (tester) async {
    await tester.binding.setSurfaceSize(const Size(1500, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      _app(
        onProvisionAgent: (_) async {
          throw StateError('control plane rejected provision');
        },
      ),
    );
    await tester.tap(find.byKey(const Key('new-agent-button')));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byKey(const Key('canonical-agent-option-ilaios.agent.alpha.v1')),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('failed; no UI state was fabricated'), findsOneWidget);
    expect(find.text('Alpha'), findsOneWidget);
  });
}
