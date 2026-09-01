import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/features/create/reference_asset_picker.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('dropped image paths enter the same reference controller with dedupe', () async {
    final directory = await Directory.systemTemp.createTemp('ilaios-reference-drop-');
    final file = File('${directory.path}${Platform.pathSeparator}product.png');
    final bytes = <int>[
      0x89,
      0x50,
      0x4e,
      0x47,
      0x0d,
      0x0a,
      0x1a,
      0x0a,
      0x00,
      0x00,
      0x00,
      0x0d,
      0x49,
      0x48,
      0x44,
      0x52,
    ];
    await file.writeAsBytes(bytes, flush: true);
    final controller = ReferenceAssetPickerController();
    try {
      await controller.addDroppedPaths(<String>[file.path, file.path]);
      expect(controller.assets, hasLength(1));
      expect(controller.assets.single.filename, 'product.png');
      expect(controller.assets.single.mimeType, 'image/png');
      expect(controller.assets.single.sha256Hex, sha256.convert(bytes).toString());
    } finally {
      controller.dispose();
      await directory.delete(recursive: true);
    }
  });

  test('dropped unsupported file type is ignored before upload', () async {
    final directory = await Directory.systemTemp.createTemp('ilaios-reference-drop-');
    final file = File('${directory.path}${Platform.pathSeparator}payload.txt');
    await file.writeAsString('not an image', flush: true);
    final controller = ReferenceAssetPickerController();
    try {
      await controller.addDroppedPaths(<String>[file.path]);
      expect(controller.assets, isEmpty);
    } finally {
      controller.dispose();
      await directory.delete(recursive: true);
    }
  });
}
