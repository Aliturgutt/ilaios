import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_app.dart';
import 'package:ilaios_desktop/control_plane/client.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';

void main() {
  testWidgets('prompt editor previews all modes without starting work', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1600, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    var submitCalls = 0;
    PromptRefinementMode? requestedMode;

    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
        ),
        onPromptSubmit: (objective) async {
          submitCalls += 1;
          return const PromptSubmission(
            goalId: 'goal-1',
            jobId: 'job-1',
            state: 'PENDING',
          );
        },
        onPromptRefine: (prompt, mode) async {
          requestedMode = mode;
          return PromptRefinementPreview(
            originalPrompt: prompt,
            refinedPrompt: 'Objective: $prompt\nConstraints:\n- Never deploy.',
            mode: mode,
            transformed: true,
            detectedIssues: const [],
            preservedConstraints: const ['Never deploy.'],
            unresolvedAmbiguities: const [],
            warnings: const [],
            constraintsDetected: true,
            riskCues: const ['deploy'],
            riskCuesPreserved: true,
          );
        },
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('prompt-editor-panel')), findsOneWidget);
    for (final mode in PromptRefinementMode.values) {
      expect(find.byKey(ValueKey('prompt-mode-${mode.wireValue}')), findsOneWidget);
    }

    await tester.enterText(
      find.byKey(const Key('home-command-prompt')),
      'Build a website. Never deploy.',
    );
    await tester.tap(find.byKey(const ValueKey('prompt-mode-structure')));
    await tester.tap(find.byKey(const Key('prompt-refine-action')));
    await tester.pumpAndSettle();

    expect(requestedMode, PromptRefinementMode.structure);
    expect(submitCalls, 0);
    expect(find.byKey(const Key('prompt-before-after')), findsOneWidget);
    expect(find.byKey(const Key('prompt-before')), findsOneWidget);
    expect(find.byKey(const Key('prompt-after')), findsOneWidget);
    expect(find.byKey(const Key('prompt-constraint-status')), findsOneWidget);
    expect(find.byKey(const Key('prompt-risk-status')), findsOneWidget);

    await tester.tap(find.byKey(const Key('prompt-use-refined')));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(
      find.byKey(const Key('home-command-prompt')),
    );
    expect(field.controller!.text, contains('Objective:'));
    expect(submitCalls, 0);
  });

  testWidgets('unsafe risk preservation keeps refined text non-applicable', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1600, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
        ),
        onPromptRefine: (prompt, mode) async => PromptRefinementPreview(
          originalPrompt: prompt,
          refinedPrompt: 'Build a website.',
          mode: mode,
          transformed: true,
          detectedIssues: const [],
          preservedConstraints: const [],
          unresolvedAmbiguities: const [],
          warnings: const ['risk cue changed'],
          constraintsDetected: false,
          riskCues: const ['production'],
          riskCuesPreserved: false,
        ),
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('home-command-prompt')),
      'Build a website. Never deploy to production.',
    );
    await tester.tap(find.byKey(const Key('prompt-refine-action')));
    await tester.pumpAndSettle();

    final apply = tester.widget<FilledButton>(
      find.byKey(const Key('prompt-use-refined')),
    );
    expect(apply.onPressed, isNull);
  });

  testWidgets('source edits invalidate in-flight and completed previews', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1600, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    final pending = Completer<PromptRefinementPreview>();

    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
        ),
        onPromptRefine: (prompt, mode) => pending.future,
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('home-command-prompt')),
      'Original prompt. Never deploy.',
    );
    await tester.tap(find.byKey(const Key('prompt-refine-action')));
    await tester.pump();
    await tester.enterText(
      find.byKey(const Key('home-command-prompt')),
      'Changed prompt. Never deploy.',
    );
    await tester.pump();

    pending.complete(
      const PromptRefinementPreview(
        originalPrompt: 'Original prompt. Never deploy.',
        refinedPrompt: 'Stale refined prompt.',
        mode: PromptRefinementMode.preserveIntent,
        transformed: true,
        detectedIssues: [],
        preservedConstraints: ['Never deploy.'],
        unresolvedAmbiguities: [],
        warnings: [],
        constraintsDetected: true,
        riskCues: ['deploy'],
        riskCuesPreserved: true,
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('prompt-before-after')), findsNothing);
    final field = tester.widget<TextField>(
      find.byKey(const Key('home-command-prompt')),
    );
    expect(field.controller!.text, 'Changed prompt. Never deploy.');
  });

  testWidgets('refinement failures do not expose raw exception text', (tester) async {
    await tester.binding.setSurfaceSize(const Size(1600, 1000));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      IlaiosDesktopApp(
        projection: const ControlPlaneProjection(
          connected: true,
          status: 'Connected',
          goalCount: 0,
          jobCount: 0,
          lastEvent: null,
        ),
        onPromptRefine: (prompt, mode) async {
          throw StateError('secret-token=should-not-leak');
        },
      ),
    );
    await tester.pumpAndSettle();

    await tester.enterText(
      find.byKey(const Key('home-command-prompt')),
      'Build a website.',
    );
    await tester.tap(find.byKey(const Key('prompt-refine-action')));
    await tester.pumpAndSettle();

    expect(find.textContaining('secret-token'), findsNothing);
    expect(find.byKey(const Key('prompt-refinement-error')), findsOneWidget);
  });
}
