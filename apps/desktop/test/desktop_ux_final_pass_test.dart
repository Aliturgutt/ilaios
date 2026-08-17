import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/create/create_view.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('factory cards pin the selected execution intent before submit', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1200, 850));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    String? submittedObjective;
    await tester.pumpWidget(
      IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          home: Scaffold(
            body: CreateView(
              projection: const ControlPlaneProjection(
                connected: true,
                status: 'Connected to authoritative control plane',
                goalCount: 0,
                jobCount: 0,
                lastEvent: null,
              ),
              status: 'Operational APIs connected',
              onSubmit: (objective) async {
                submittedObjective = objective;
                return const PromptSubmission(
                  goalId: 'goal-test',
                  jobId: 'job-test',
                  state: 'ADMITTED',
                );
              },
            ),
          ),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const ValueKey('factory-preset-web')), findsOneWidget);
    expect(find.byKey(const ValueKey('factory-preset-video')), findsOneWidget);
    expect(find.byKey(const ValueKey('factory-preset-software')), findsOneWidget);

    final video = find.byKey(const ValueKey('factory-preset-video'));
    await tester.ensureVisible(video);
    await tester.tap(video);
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('selected-factory-route')), findsOneWidget);
    expect(find.text('Video Factory'), findsWidgets);

    final submit = find.byKey(const Key('one-prompt-submit'));
    await tester.ensureVisible(submit);
    await tester.tap(submit);
    await tester.pumpAndSettle();

    expect(submittedObjective, isNotNull);
    expect(submittedObjective, startsWith('Video creation task:'));
  });

  testWidgets('settings quick actions are interactive', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-settings')));
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('settings-notifications-action')), findsOneWidget);
    expect(find.byKey(const Key('settings-language-action')), findsOneWidget);
    expect(find.byKey(const Key('settings-appearance-action')), findsOneWidget);
    expect(find.byKey(const Key('settings-storage-action')), findsOneWidget);
    expect(find.byKey(const Key('settings-diagnostics-action')), findsOneWidget);

    await tester.tap(find.byKey(const Key('settings-language-action')));
    await tester.pumpAndSettle();
    expect(find.text('Choose language'), findsOneWidget);
    expect(find.text('Türkçe'), findsOneWidget);
    expect(find.text('English'), findsWidgets);
  });

  testWidgets('workflow uses five structured responsive stages', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-workflows')));
    await tester.pumpAndSettle();

    for (final stage in <String>['goal', 'plan', 'execute', 'verify', 'deliver']) {
      expect(
        find.byKey(ValueKey('workflow-stage-$stage')),
        findsOneWidget,
        reason: '$stage workflow stage is missing',
      );
    }
    expect(tester.takeException(), isNull);
  });

  testWidgets('verified deliveries expose local-delete without deleting evidence', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    final snapshot = OperationalSnapshot(
      runtimeRoutes: const <Map<String, Object?>>[],
      schedulerState: const <String, Object?>{},
      grantsState: const <String, Object?>{},
      governanceState: const <String, Object?>{},
      evidenceRecords: const <EvidenceRecord>[
        EvidenceRecord(
          sequence: 7,
          executionId: 'exec-video-test',
          artifactDigest:
              '0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
          action: 'video.desktop.finished_product',
          previousHash: '',
          recordHash: 'record-hash',
        ),
      ],
      liveEvents: const <Map<String, Object?>>[],
    );

    await tester.pumpWidget(
      IlaiosDesktopApp(operationalSnapshot: snapshot),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('nav-artifacts')));
    await tester.pumpAndSettle();

    expect(
      find.byKey(const ValueKey('delete-local-artifact-7')),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const ValueKey('delete-local-artifact-7')));
    await tester.pumpAndSettle();
    expect(find.text('Delete local copy?'), findsOneWidget);
    expect(
      find.textContaining(
        'evidence record, SHA-256 and provenance chain are retained',
      ),
      findsOneWidget,
    );
    expect(find.text('video.desktop.finished_product'), findsOneWidget);
  });
}
