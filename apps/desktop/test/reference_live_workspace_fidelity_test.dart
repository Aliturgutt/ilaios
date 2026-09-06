import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/ilaios_locale.dart';
import 'package:ilaios_desktop/control_plane/evidence_record.dart';
import 'package:ilaios_desktop/control_plane/operational_snapshot.dart';
import 'package:ilaios_desktop/features/navigation/desktop_section.dart';
import 'package:ilaios_desktop/main.dart';

import 'secondary_navigation_test_support.dart';

const _snapshot = OperationalSnapshot(
  runtimeRoutes: <Map<String, Object?>>[],
  schedulerState: <String, Object?>{
    'workspace_mode': 'Development (Live)',
    'branch': 'main',
    'environment': 'preview',
    'sync_state': 'synced',
    'preview_url': 'http://localhost:3000',
    'session_id': 'workspace-session-01',
    'elapsed': '00:18:42',
    'owner': 'runtime-owner',
    'agents': <Object?>[
      <String, Object?>{
        'agent_id': 'frontend-01',
        'agent_name': 'Frontend Agent',
        'owner': 'runtime',
        'status': 'active',
      },
      <String, Object?>{
        'agent_id': 'test-01',
        'agent_name': 'Test Agent',
        'owner': 'runtime',
        'status': 'testing',
      },
    ],
    'workspace_files': <Object?>[
      <String, Object?>{
        'path': 'src/pages/home.tsx',
        'name': 'home.tsx',
        'language': 'TypeScript',
        'state': 'M',
        'updated_at': '10:34',
        'content': 'export default function Home() {\n  return null;\n}',
      },
      <String, Object?>{
        'path': 'src/styles/globals.css',
        'name': 'globals.css',
        'language': 'CSS',
        'updated_at': '10:28',
      },
    ],
  },
  grantsState: <String, Object?>{},
  governanceState: <String, Object?>{},
  evidenceRecords: <EvidenceRecord>[
    EvidenceRecord(
      sequence: 1,
      executionId: 'exec-01',
      artifactDigest: 'sha256:artifact',
      action: 'qa.report.verified',
      previousHash: '',
      recordHash: 'record-hash-01',
    ),
  ],
  liveEvents: <Map<String, Object?>>[
    <String, Object?>{
      'event_type': 'workspace.file.saved',
      'message': 'src/pages/home.tsx saved',
      'timestamp': '2026-08-17T10:36:21Z',
      'project_name': 'Runtime Project',
      'started_at': '2026-08-17T10:18:42Z',
    },
    <String, Object?>{
      'event_type': 'workspace.review.completed',
      'message': 'Header review completed',
      'timestamp': '2026-08-17T10:35:48Z',
      'agent_id': 'test-01',
      'project_name': 'Runtime Project',
    },
  ],
);

void main() {
  Future<void> openWorkspace(WidgetTester tester) =>
      openSecondaryDesktopSection(tester, DesktopSection.liveWorkspace);

  testWidgets('Live Workspace keeps the approved dark reference hierarchy', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        operationalSnapshot: _snapshot,
        operationalStatus: 'Connected to authoritative control plane',
      ),
    );
    await tester.pumpAndSettle();
    await openWorkspace(tester);

    final page = find.byKey(const Key('reference-live-workspace-page'));
    expect(page, findsOneWidget);
    expect(find.byKey(const Key('live-workspace-header')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-summary')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-active-agents')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-tabs')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-files-pane')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-code-pane')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-terminal-pane')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-browser-pane')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-session-panel')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-activity-panel')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-review-panel')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-open-files')), findsOneWidget);
    expect(find.byKey(const Key('live-workspace-evidence')), findsOneWidget);
    expect(
      find.descendant(of: page, matching: find.text('Live Workspace')),
      findsOneWidget,
    );
    expect(find.text('Runtime Project'), findsWidgets);
    expect(find.text('home.tsx'), findsWidgets);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Live Workspace renders the approved Turkish light surface', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1648, 928));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(
      const IlaiosDesktopApp(
        locale: IlaiosLocale.turkish,
        themeMode: ThemeMode.light,
        operationalSnapshot: _snapshot,
        operationalStatus: 'Connected to authoritative control plane',
      ),
    );
    await tester.pumpAndSettle();
    await openWorkspace(tester);

    final page = find.byKey(const Key('reference-live-workspace-page'));
    expect(page, findsOneWidget);
    expect(
      find.descendant(of: page, matching: find.text('Canlı Çalışma Alanı')),
      findsOneWidget,
    );
    expect(find.text('AKTİF OTURUM'), findsOneWidget);
    expect(find.text('Çalışma Modu'), findsOneWidget);
    expect(find.text('Aktif Ajanlar'), findsWidgets);
    expect(find.text('KANIT & DOĞRULAMA'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('Live Workspace empty state never fabricates screenshot content', (
    WidgetTester tester,
  ) async {
    await tester.binding.setSurfaceSize(const Size(1600, 900));
    addTearDown(() => tester.binding.setSurfaceSize(null));

    await tester.pumpWidget(const IlaiosDesktopApp());
    await tester.pumpAndSettle();
    await openWorkspace(tester);

    expect(find.byKey(const Key('reference-live-workspace-page')), findsOneWidget);
    expect(find.text('THE LAST ORIGIN'), findsNothing);
    expect(find.text('12 Bölüm'), findsNothing);
    expect(find.text('100+ Görev'), findsNothing);
    expect(find.text('96% Başarı'), findsNothing);
    expect(find.text('—'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
}
