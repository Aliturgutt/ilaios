import 'dart:convert';
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/main.dart';

void main() {
  testWidgets('V4 produces exact-head 60 screenshot evidence', (
    WidgetTester tester,
  ) async {
    final evidenceRoot = Directory(
      'build/windows/x64/runner/Release/visual-evidence',
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

    const viewports = <Size>[
      Size(1366, 768),
      Size(1440, 900),
      Size(1920, 1080),
    ];
    const themes = <(String, ThemeMode)>[
      ('dark', ThemeMode.dark),
      ('light', ThemeMode.light),
    ];
    const pages = <(String, String?)>[
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

    final files = <Map<String, Object>>[];
    for (final viewport in viewports) {
      await tester.binding.setSurfaceSize(viewport);
      for (final theme in themes) {
        final captureKey = GlobalKey();
        await tester.pumpWidget(
          RepaintBoundary(
            key: captureKey,
            child: IlaiosDesktopApp(themeMode: theme.$2),
          ),
        );
        await tester.pumpAndSettle();
        expect(tester.takeException(), isNull);

        for (final page in pages) {
          if (page.$2 != null) {
            await tester.tap(find.byKey(ValueKey(page.$2!)));
            await tester.pumpAndSettle();
            expect(tester.takeException(), isNull);
          }

          final boundary = captureKey.currentContext!.findRenderObject()!
              as RenderRepaintBoundary;
          final image = await boundary.toImage(pixelRatio: 1);
          final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
          expect(byteData, isNotNull);
          final bytes = byteData!.buffer.asUint8List();
          expect(bytes, isNotEmpty);
          expect(image.width, viewport.width.toInt());
          expect(image.height, viewport.height.toInt());

          final width = viewport.width.toInt();
          final height = viewport.height.toInt();
          final fileName = '${page.$1}-${theme.$1}-${width}x$height.png';
          final file = File('${evidenceRoot.path}/$fileName');
          file.writeAsBytesSync(bytes, flush: true);
          files.add(<String, Object>{
            'file': fileName,
            'page': page.$1,
            'theme': theme.$1,
            'width': width,
            'height': height,
            'bytes': bytes.length,
          });
        }
      }
    }
    await tester.binding.setSurfaceSize(null);

    expect(files, hasLength(60));
    final pngFiles = evidenceRoot
        .listSync()
        .whereType<File>()
        .where((file) => file.path.endsWith('.png'))
        .toList();
    expect(pngFiles, hasLength(60));

    final manifest = <String, Object>{
      'schema': 'ilaios.desktop.v4.screenshot-evidence.v1',
      'source_sha': sourceSha,
      'screenshot_count': files.length,
      'pages': pages.map((page) => page.$1).toList(),
      'themes': themes.map((theme) => theme.$1).toList(),
      'viewports': viewports
          .map((size) => <String, int>{
                'width': size.width.toInt(),
                'height': size.height.toInt(),
              })
          .toList(),
      'screenshots': files,
    };
    File('${evidenceRoot.path}/manifest.json').writeAsStringSync(
      const JsonEncoder.withIndent('  ').convert(manifest),
      flush: true,
    );
  });
}
