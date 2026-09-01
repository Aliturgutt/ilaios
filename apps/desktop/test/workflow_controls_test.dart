import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/control_plane/projection.dart';
import 'package:ilaios_desktop/features/dashboard/reference_workflows_view.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';

void main() {
  const projection = ControlPlaneProjection(
    connected: true,
    status: 'Connected',
    goalCount: 0,
    jobCount: 7,
    lastEvent: null,
  );

  OperationalSnapshot snapshot() => OperationalSnapshot(
        runtimeRoutes: const <Map<String, Object?>>[],
        schedulerState: const <String, Object?>{},
        grantsState: const <String, Object?>{},
        governanceState: const <String, Object?>{},
        evidenceRecords: const [],
        liveEvents: List<Map<String, Object?>>.generate(
          7,
          (index) => <String, Object?>{
            'workflow_id': 'workflow-${index + 1}',
            'workflow_name': 'Workflow ${index + 1}',
            'description': 'Authoritative workflow ${index + 1}',
            'workflow_type': index.isEven ? 'Video' : 'Web',
            'phase': index == 6 ? 'Verification' : 'Execution',
            'progress': (index + 1) / 10,
            'owner': index.isEven ? 'owner-a' : 'owner-b',
            'priority': index < 3 ? 'High' : 'Medium',
            'eta': '2026-08-${20 + index}',
            'created_at': '2026-08-19T00:0$index:00Z',
          },
        ),
      );

  Widget subject({ValueChanged<DesktopSection>? onNavigate}) => IlaiosLocaleScope(
        locale: IlaiosLocale.english,
        onChanged: (_) {},
        child: MaterialApp(
          home: Scaffold(
            body: ReferenceWorkflowsView(
              projection: projection,
              snapshot: snapshot(),
              status: 'Operational APIs connected',
              onNavigate: onNavigate ?? (_) {},
              onRefreshRequested: () {},
            ),
          ),
        ),
      );

  testWidgets('workflow paging exposes the second authoritative page', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(subject());
    await tester.pumpAndSettle();

    expect(find.byKey(const Key('workflow-page-indicator')), findsOneWidget);
    expect(find.text('1/2'), findsOneWidget);
    expect(find.byKey(const ValueKey('workflow-row-workflow-7')), findsOneWidget);
    expect(find.byKey(const ValueKey('workflow-row-workflow-1')), findsNothing);

    await tester.tap(find.byKey(const Key('workflow-page-next')));
    await tester.pumpAndSettle();

    expect(find.text('2/2'), findsOneWidget);
    expect(find.byKey(const ValueKey('workflow-row-workflow-2')), findsOneWidget);
    expect(find.byKey(const ValueKey('workflow-row-workflow-1')), findsOneWidget);
  });

  testWidgets('workflow filters are real and clear restores the full result set', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    await tester.pumpWidget(subject());
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const ValueKey('workflow-filter-type')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Video').last);
    await tester.pumpAndSettle();

    expect(find.textContaining('/ 4 results'), findsOneWidget);
    expect(find.text('Type: All'), findsNothing);

    await tester.enterText(
      find.byKey(const Key('workflow-search')),
      'Workflow 7',
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('/ 1 results'), findsOneWidget);

    await tester.tap(find.byKey(const Key('workflow-clear-filters')));
    await tester.pumpAndSettle();
    expect(find.textContaining('/ 7 results'), findsOneWidget);
    expect(
      tester.widget<TextField>(find.byKey(const Key('workflow-search'))).controller?.text,
      isEmpty,
    );
  });

  testWidgets('V4 workflow actions stay bounded and do not fabricate creation authority', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));
    DesktopSection? destination;
    await tester.pumpWidget(subject(onNavigate: (value) => destination = value));
    await tester.pumpAndSettle();

    await tester.tap(find.byKey(const Key('workflows-more-menu')));
    await tester.pumpAndSettle();
    expect(find.text('Refresh'), findsWidgets);
    expect(find.text('New Workflow'), findsNothing);

    await tester.tapAt(const Offset(10, 10));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('workflow-row-menu-workflow-7')));
    await tester.pumpAndSettle();
    expect(find.text('View Approvals'), findsWidgets);
    expect(find.text('Live Workspace'), findsWidgets);
    await tester.tap(find.text('View Approvals').last);
    await tester.pumpAndSettle();
    expect(destination, DesktopSection.approvals);
  });
}
