import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

const canonical7PageEvidence = <(String, String?)>[
  ('01_Ana_Sayfa.png', null),
  ('02_Is_Akislari.png', 'nav-workflows'),
  ('03_Ajanlar.png', 'nav-agents'),
  ('04_Ciktilar.png', 'nav-artifacts'),
  ('05_Onaylar.png', 'nav-approvals'),
  ('06_Kanitlar.png', 'nav-evidence'),
  ('07_Ayarlar.png', 'nav-settings'),
];

Future<Uint8List> _encodeBoundaryPng(
  WidgetTester tester,
  RenderRepaintBoundary boundary,
) async {
  final bytes = await tester.runAsync(() async {
    final image = await boundary.toImage(pixelRatio: 1).timeout(
      const Duration(seconds: 30),
      onTimeout: () =>
          throw TimeoutException('RenderRepaintBoundary.toImage timed out'),
    );
    try {
      final byteData = await image.toByteData(format: ui.ImageByteFormat.png).timeout(
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

Future<void> captureCanonical7PageScreenshotEvidence(
  WidgetTester tester,
) async {
  const viewport = Size(1536, 1024);
  const combination = 'canonical-light-1536x1024';
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
      child: const IlaiosDesktopApp(themeMode: ThemeMode.light),
    ),
  );
  await tester.pumpAndSettle();
  expect(tester.takeException(), isNull);
  expect(find.byKey(const Key('canonical-7-page-sidebar')), findsOneWidget);
  expect(find.byKey(const Key('canonical-7-page-topbar')), findsOneWidget);
  expect(find.byKey(const Key('reference-secondary-navigation')), findsNothing);

  final files = <Map<String, Object>>[];
  for (final page in canonical7PageEvidence) {
    final navigationKey = page.$2;
    if (navigationKey != null) {
      final finder = find.byKey(ValueKey(navigationKey));
      expect(finder, findsOneWidget);
      await tester.ensureVisible(finder);
      await tester.tap(finder);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }

    final boundary = captureKey.currentContext!.findRenderObject()!
        as RenderRepaintBoundary;
    final bytes = await _encodeBoundaryPng(tester, boundary);
    expect(bytes, isNotEmpty);

    final file = File('${evidenceRoot.path}/${page.$1}');
    file.writeAsBytesSync(bytes, flush: true);
    files.add(<String, Object>{
      'file': page.$1,
      'bytes': bytes.length,
    });
  }

  expect(files, hasLength(7));
  final pngFiles = evidenceRoot
      .listSync()
      .whereType<File>()
      .where((file) => file.path.endsWith('.png'))
      .toList();
  expect(pngFiles, hasLength(7));

  File('${evidenceRoot.path}/manifest.json').writeAsStringSync(
    const JsonEncoder.withIndent('  ').convert(<String, Object>{
      'schema': 'ilaios.desktop.7page.screenshot-evidence.v1',
      'source_sha': sourceSha,
      'screenshot_count': files.length,
      'theme': 'light',
      'viewport': <String, int>{'width': 1536, 'height': 1024},
      'screenshots': files,
    }),
    flush: true,
  );
}
