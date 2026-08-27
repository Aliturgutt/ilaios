import 'dart:io';

import 'package:flutter_test/flutter_test.dart';

void main() {
  test('packaged identity shutdown is idempotent after serve loop return', () {
    final source = File('../../services/source_media_desktop.py').readAsStringSync();

    expect(source, contains('self._serve_forever_active = threading.Event()'));
    expect(source, contains('self._serve_forever_active.set()'));
    expect(source, contains('self._serve_forever_active.clear()'));
    expect(
      source,
      contains(
        'if not self._serve_forever_active.is_set():\n'
        '            return\n'
        '        super().shutdown()',
      ),
    );
  });
}
