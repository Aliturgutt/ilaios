import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

File _repoFile(String relativePath) {
  for (final candidate in <String>[
    relativePath,
    'apps/desktop/$relativePath',
  ]) {
    final file = File(candidate);
    if (file.existsSync()) return file;
  }
  throw StateError('Could not locate $relativePath from ${Directory.current.path}');
}

List<double> _fontSizes(String source) =>
    RegExp(r'fontSize:\s*([0-9]+(?:\.[0-9]+)?)')
        .allMatches(source)
        .map((match) => double.parse(match.group(1)!))
        .toList(growable: false);

void main() {
  test('canonical desktop shell never shrinks the whole UI below system scale', () {
    final v11 = _repoFile(
      'lib/features/dashboard/reference_desktop_shell_v11.dart',
    ).readAsStringSync();

    expect(v11, isNot(contains('TextScaler.linear(.95)')));
    expect(v11, isNot(contains('FittedBox(')));
    expect(v11, contains("Key('reference-responsive-viewport-v11')"));
    expect(v11, contains("Key('canonical-7-page-sidebar')"));
  });

  test('canonical shell user-facing text respects the readability floor', () {
    final source = _repoFile(
      'lib/features/dashboard/reference_desktop_shell_v11.dart',
    ).readAsStringSync();
    final sizes = _fontSizes(source);

    expect(sizes, isNotEmpty);
    expect(
      sizes.where((size) => size < 12.5),
      isEmpty,
      reason: 'Canonical shell text must remain readable at normal Windows viewing distance.',
    );
  });

  test('Home primary prompt stays wired to the existing governed submit callback', () {
    final shell = _repoFile(
      'lib/features/dashboard/reference_desktop_shell_v11.dart',
    ).readAsStringSync();
    final home = _repoFile(
      'lib/features/dashboard/reference_home_dashboard_v3.dart',
    ).readAsStringSync();

    expect(shell, contains('onPromptSubmit: widget.onPromptSubmit'));
    expect(home, contains('final callback = widget.onPromptSubmit'));
    expect(home, contains('final submission = await callback(objective)'));
  });

  test('canonical Home rejects micro-text and synthetic screenshot telemetry', () {
    final source = _repoFile(
      'lib/features/dashboard/reference_home_dashboard_v3.dart',
    ).readAsStringSync();
    final sizes = _fontSizes(source);

    expect(sizes, isNotEmpty);
    expect(
      sizes.where((size) => size < 12.5),
      isEmpty,
      reason: 'Canonical Home must not introduce micro-text.',
    );
    expect(source, isNot(contains('IlaiosTheme.coreBlue')));
    expect(source, isNot(contains(r'$3.21')));
    expect(source, isNot(contains('18.362')));
    expect(source, isNot(contains("Key('command-center-hero')")));
    expect(source, contains("Key('home-command-prompt')"));
  });
}
