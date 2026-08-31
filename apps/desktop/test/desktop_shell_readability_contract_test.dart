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
  test('desktop shell never shrinks the whole UI or forces text below system scale', () {
    final v10 = _repoFile(
      'lib/features/dashboard/reference_desktop_shell_v10.dart',
    ).readAsStringSync();
    final v11 = _repoFile(
      'lib/features/dashboard/reference_desktop_shell_v11.dart',
    ).readAsStringSync();

    expect(v10, isNot(contains('TextScaler.linear(.95)')));
    expect(v10, isNot(contains('FittedBox(')));
    expect(v11, isNot(contains('FittedBox(')));
    expect(v10, contains("Key('reference-responsive-viewport-v10')"));
    expect(v11, contains("Key('reference-responsive-viewport-v11')"));
  });

  test('shell user-facing text respects the final readability floor', () {
    final source = _repoFile(
      'lib/features/dashboard/reference_desktop_shell_v10.dart',
    ).readAsStringSync();
    final sizes = _fontSizes(source);

    expect(sizes, isNotEmpty);
    expect(
      sizes.where((size) => size < 12.5),
      isEmpty,
      reason: 'Shell text must remain comfortably readable at normal Windows viewing distance.',
    );
  });

  test('Home primary prompt is wired directly to the existing governed submit callback', () {
    final source = _repoFile(
      'lib/features/dashboard/reference_desktop_shell_v10.dart',
    ).readAsStringSync();

    expect(source, contains('userSession: widget.userSession'));
    expect(source, contains('onPromptSubmit: widget.onPromptSubmit'));
  });

  test('Home rejects micro-text and keeps raw identifiers secondary', () {
    final source = _repoFile(
      'lib/features/dashboard/reference_home_dashboard_v3.dart',
    ).readAsStringSync();
    final sizes = _fontSizes(source);

    expect(sizes, isNotEmpty);
    expect(
      sizes.where((size) => size < 12.5),
      isEmpty,
      reason: 'Home must not reintroduce micro-text to preserve information density.',
    );
    expect(source, isNot(contains('IlaiosTheme.coreBlue')));
    expect(
      source,
      contains("const ['project_name', 'title', 'objective', 'goal', 'task', 'description']"),
    );
    expect(source, contains("'ID \${_short(record.executionId, 12)}'"));
  });
}
