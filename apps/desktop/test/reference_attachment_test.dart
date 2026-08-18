import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:ilaios_desktop/reference_assets/reference_attachment.dart';

Uint8List pngBytes({int width = 320, int height = 180}) {
  final bytes = Uint8List(64);
  bytes.setRange(0, 8, const <int>[0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
  bytes.setRange(8, 12, const <int>[0, 0, 0, 13]);
  bytes.setRange(12, 16, 'IHDR'.codeUnits);
  bytes[16] = (width >> 24) & 0xff;
  bytes[17] = (width >> 16) & 0xff;
  bytes[18] = (width >> 8) & 0xff;
  bytes[19] = width & 0xff;
  bytes[20] = (height >> 24) & 0xff;
  bytes[21] = (height >> 16) & 0xff;
  bytes[22] = (height >> 8) & 0xff;
  bytes[23] = height & 0xff;
  return bytes;
}

void main() {
  test('valid reference image is content addressed', () {
    final attachment = ReferenceAttachmentDraft.fromBytes(
      'reference.png',
      pngBytes(),
    );
    expect(attachment.mediaType, 'image/png');
    expect(attachment.sha256.length, 64);
    expect(attachment.sizeBytes, 64);
  });

  test('spoofed or unsupported content is rejected', () {
    expect(
      () => ReferenceAttachmentDraft.fromBytes(
        'fake.png',
        Uint8List.fromList(<int>[1, 2, 3, 4]),
      ),
      throwsA(isA<ReferenceAttachmentException>()),
    );
  });

  test('oversized file is rejected before reference ingest', () async {
    final directory = await Directory.systemTemp.createTemp('ilaios-reference-');
    addTearDown(() => directory.delete(recursive: true));
    final file = File('${directory.path}${Platform.pathSeparator}oversized.png');
    final handle = await file.open(mode: FileMode.write);
    try {
      await handle.truncate(maxReferenceAssetBytes + 1);
    } finally {
      await handle.close();
    }

    await expectLater(
      ReferenceAttachmentDraft.fromFilePath(file.path),
      throwsA(isA<ReferenceAttachmentException>()),
    );
  });

  test('reference context is request scoped and restored', () async {
    final attachment = ReferenceAttachmentDraft.fromBytes(
      'reference.png',
      pngBytes(),
    );
    expect(currentReferenceAttachments, isEmpty);
    await withReferenceAttachments(<ReferenceAttachmentDraft>[attachment], () async {
      expect(currentReferenceAttachments.single.sha256, attachment.sha256);
    });
    expect(currentReferenceAttachments, isEmpty);
  });
}
