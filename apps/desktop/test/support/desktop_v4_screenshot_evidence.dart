import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

const v4EvidencePages = <(String, String?)>[
  ('home', null),
  ('goals', 'nav-goals'),
  ('workflows', 'nav-workflows'),
  ('agents', 'nav-agents'),
  ('liveWorkspace', 'nav-liveWorkspace'),
  ('artifacts', 'nav-artifacts'),
  ('approvals', 'nav-approvals'),
  ('evidence', 'nav-evidence'),
  ('costs', 'nav-costs'),
  ('settings', 'nav-settings'),
];

const _secondaryNavigationLabels = <String, String>{
  'nav-goals': 'Goals',
  'nav-liveWorkspace': 'Live Workspace',
  'nav-costs': 'Costs',
};

Future<void> _pumpEvidenceFrame(WidgetTester tester) async {
  await tester.pump();
  expect(tester.takeException(), isNull);
}

Future<void> _navigateWithoutPointerGesture(
  WidgetTester tester,
  String navigationKey,
) async {
  final secondaryLabel = _secondaryNavigationLabels[navigationKey];
  if (secondaryLabel != null) {
    final menu = find.byKey(const Key('reference-secondary-navigation'));
    expect(menu, findsOneWidget);
    await tester.tap(menu);
    await tester.pumpAndSettle();
    final item = find.text(secondaryLabel);
    expect(item, findsOneWidget);
    await tester.tap(item);
    return;
  }

  final finder = find.byKey(ValueKey(navigationKey));
  expect(finder, findsOneWidget);
  final nav = tester.widget<InkWell>(finder);
  expect(nav.onTap, isNotNull);
  nav.onTap!();
}

Future<Uint8List> _encodeBoundaryPng(
  WidgetTester tester,
  RenderRepaintBoundary boundary,
) async {
  final bytes = await tester.runAsync(() async {
    final image = await boundary.toImage(pixelRatio: 1).timeout(
      const Duration(seconds: 30),
      onTimeout: () => throw TimeoutException('RenderRepaintBoundary.toImage timed out'),
    );
    try {
      final byteData = await image
          .toByteData(format: ui.ImageByteFormat.png)
          .timeout(
            const Duration(seconds: 30),
            onTimeout: () => throw TimeoutException('ui.Image.toByteData timed out'),
          );
      if (byteData == null) {
        throw StateError('PNG encoding returned null byte data');
      }
      return byteData.buffer.asUint8List();
    } finally {
      image.dispose();
    }
  });
  if (bytes == null) {
    throw StateError('WidgetTester.runAsync returned null screenshot bytes');
  }
  return bytes;
}

Future<void> captureV4ScreenshotEvidence(
  WidgetTester tester, {
  required Size viewport,
  required String themeName,
  required ThemeMode themeMode,
}) async {
  final width = viewport.width.toInt();
  final height = viewport.height.toInt();
  final combination = '$themeName-${width}x$height';
  final evidenceRoot = Directory(
    'build/windows/x64/runner/Release/visual-evidence/$combination',
  );
  if (evidenceRoot.existsSync()) {
    evidenceRoot.deleteSync(recursive: true);
  }
  evidenceRoot.createSync(recursive: true);

  final sourceShaResult = Process.runSync(
    'git',
    const <String>['rev-parse', 'HEAD'],
    workingDirectory: Directory.current.path,
  );
  expect(sourceShaResult.exitCode, 0);
  final sourceSha = sourceShaResult.stdout.toString().trim();
  expect(sourceSha, matches(RegExp(r'^[0-9a-f]{40}$')));

  await tester.binding.setSurfaceSize(viewport);
  addTearDown(() => tester.binding.setSurfaceSize(null));

  final captureKey = GlobalKey();
  await tester.pumpWidget(
    RepaintBoundary(
      key: captureKey,
      child: IlaiosDesktopApp(themeMode: themeMode),
    ),
  );
  await _pumpEvidenceFrame(tester);

  final files = <Map<String, Object>>[];
  for (final page in v4EvidencePages) {
    if (page.$2 != null) {
      await _navigateWithoutPointerGesture(tester, page.$2!);
      await _pumpEvidenceFrame(tester);
    }

    final boundary = captureKey.currentContext!.findRenderObject()!
        as RenderRepaintBoundary;
    final bytes = await _encodeBoundaryPng(tester, boundary);
    expect(bytes, isNotEmpty);

    final fileName = '${page.$1}-$combination.png';
    final file = File('${evidenceRoot.path}/$fileName');
    file.writeAsBytesSync(bytes, flush: true);
    files.add(<String, Object>{
      'file': fileName,
      'page': page.$1,
      'theme': themeName,
      'width': width,
      'height': height,
      'bytes': bytes.length,
    });
  }

  expect(files, hasLength(10));
  final pngFiles = evidenceRoot
      .listSync()
      .whereType<File>()
      .where((file) => file.path.endsWith('.png'))
      .toList();
  expect(pngFiles, hasLength(10));

  File('${evidenceRoot.path}/manifest.json').writeAsStringSync(
    const JsonEncoder.withIndent('  ').convert(<String, Object>{
      'schema': 'ilaios.desktop.v4.screenshot-evidence.v1',
      'source_sha': sourceSha,
      'screenshot_count': files.length,
      'theme': themeName,
      'viewport': <String, int>{'width': width, 'height': height},
      'pages': v4EvidencePages.map((page) => page.$1).toList(),
      'screenshots': files,
    }),
    flush: true,
  );
}
