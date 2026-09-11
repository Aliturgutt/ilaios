import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/dashboard/pixel_agent_presentation.dart';

void main() {
  test('pixel manifest and files contain exactly the approved 208 frames', () {
    final manifestFile = File('assets/pixel_agents/manifest.json');
    final qaFile = File('assets/pixel_agents/QA_REPORT.json');
    expect(manifestFile.existsSync(), isTrue);
    expect(qaFile.existsSync(), isTrue);

    final manifest = jsonDecode(manifestFile.readAsStringSync())
        as Map<String, dynamic>;
    final qa = jsonDecode(qaFile.readAsStringSync()) as Map<String, dynamic>;
    expect(manifest['total_frames'], 208);
    expect(qa['asset_count'], 208);
    expect(qa['expected_asset_count'], 208);
    expect(qa['all_same_size'], isTrue);
    expect(qa['alpha_transparency_failures'], isEmpty);
    expect(qa['empty_frames'], isEmpty);
    expect(qa['exact_duplicate_sequences'], isEmpty);
    expect(qa['status'], 'PASS');

    var observed = 0;
    for (final team in pixelAgentTeams) {
      for (final view in PixelAgentView.values) {
        for (final motion in PixelAgentMotion.values) {
          for (var frame = 1; frame <= pixelFrameCount(motion); frame++) {
            final path = pixelAgentAssetPath(
              team: team,
              view: view,
              motion: motion,
              frame: frame,
            );
            expect(path, isNotNull);
            final file = File(path!);
            expect(file.existsSync(), isTrue, reason: path);
            final bytes = file.readAsBytesSync();
            expect(bytes.length, greaterThan(8), reason: path);
            expect(
              bytes.take(8).toList(),
              <int>[137, 80, 78, 71, 13, 10, 26, 10],
              reason: path,
            );
            observed++;
          }
        }
      }
    }
    expect(observed, 208);
  });

  test('pixel workspace reference is present and packaged separately', () {
    const assetPath = 'assets/pixel_agents/workspace/office_reference.jpg';
    final workspace = File(assetPath);
    expect(workspace.existsSync(), isTrue, reason: assetPath);
    final bytes = workspace.readAsBytesSync();
    expect(bytes.length, greaterThan(1024), reason: assetPath);
    expect(bytes.take(3).toList(), <int>[255, 216, 255], reason: assetPath);

    final pubspec = File('pubspec.yaml').readAsStringSync();
    expect(pubspec, contains('- assets/pixel_agents/workspace/'));

    final agentsView = File(
      'lib/features/dashboard/reference_agents_summary_view.dart',
    ).readAsStringSync();
    expect(agentsView, contains("key: const Key('agents-pixel-workspace')"));
    expect(agentsView, contains(assetPath));
  });
}
