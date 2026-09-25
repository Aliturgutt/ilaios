import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/app/desktop_text_scale.dart';

void main() {
  late Directory directory;
  late File preference;
  setUp(() async {
    directory = await Directory.systemTemp.createTemp('desktop-scale-test-');
    preference = File('${directory.path}/preferences/scale.json');
  });
  tearDown(() async => directory.delete(recursive: true));

  test('text scale survives a new load from disk', () async {
    expect(await DesktopTextScaleStore.load(file: preference), 1.0);
    await DesktopTextScaleStore.save(1.2, file: preference);
    expect(await DesktopTextScaleStore.load(file: preference), 1.2);
    await DesktopTextScaleStore.save(1.0, file: preference);
    expect(await DesktopTextScaleStore.load(file: preference), 1.0);
  });

  test('corrupt and unsupported values fall back safely', () async {
    await preference.parent.create(recursive: true);
    for (final content in ['bad json', '{"scale": 4}', '{"scale": "1.2"}']) {
      await preference.writeAsString(content);
      expect(await DesktopTextScaleStore.load(file: preference), 1.0);
    }
    expect(
      () => DesktopTextScaleStore.save(3, file: preference),
      throwsArgumentError,
    );
  });
}
