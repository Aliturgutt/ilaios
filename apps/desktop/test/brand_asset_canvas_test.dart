import 'dart:ui' as ui;

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  Future<List<int>> cornerRgb(String assetPath) async {
    final data = await rootBundle.load(assetPath);
    final codec = await ui.instantiateImageCodec(data.buffer.asUint8List());
    final frame = await codec.getNextFrame();
    try {
      final bytes = await frame.image.toByteData(format: ui.ImageByteFormat.rawRgba);
      expect(bytes, isNotNull);
      return <int>[
        bytes!.getUint8(0),
        bytes.getUint8(1),
        bytes.getUint8(2),
      ];
    } finally {
      frame.image.dispose();
      codec.dispose();
    }
  }

  test('canonical dark icon canvas is exact Carbon', () async {
    final rgb = await cornerRgb('../../brand/assets/05-ilaios-app-icon.jpg');
    expect(rgb, <int>[10, 10, 10]);
  });

  test('canonical light horizontal canvas is visually seamless with white', () async {
    final rgb = await cornerRgb(
      '../../brand/assets/13-ilaios-primary-horizontal-light.jpg',
    );
    for (final channel in rgb) {
      expect((255 - channel).abs(), lessThanOrEqualTo(1));
    }
  });
}
