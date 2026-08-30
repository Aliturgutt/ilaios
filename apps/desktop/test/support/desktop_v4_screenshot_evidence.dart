import 'dart:convert';
import 'dart:io';
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

Future<void> _pumpEvidenceFrame(WidgetTester tester) async {
  await tester.pump();
  await tester.pump(const Duration(milliseconds: 16));
  await tester.pump(const Duration(milliseconds: 100));
  await tester.pump(const Duration(milliseconds: 250));
  await tester.pump(const Duration(milliseconds: 500));
  expect(tester.takeException(), isNull);
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
      await tester.tap(find.byKey(ValueKey(page.$2!)));
      await _pumpEvidenceFrame(tester);
    }

    final boundary = captureKey.currentContext!.findRenderObject()!
        as RenderRepaintBoundary;
    final image = await boundary.toImage(pixelRatio: 1);
    final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
    expect(byteData, isNotNull);
    final bytes = byteData!.buffer.asUint8List();
    expect(bytes, isNotEmpty);
    expect(image.width, width);
    expect(image.height, height);

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
