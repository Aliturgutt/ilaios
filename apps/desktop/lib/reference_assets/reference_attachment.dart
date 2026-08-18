import 'dart:async';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart' as crypto;

const int maxReferenceAssets = 8;
const int maxReferenceAssetBytes = 8 * 1024 * 1024;
const int maxReferenceTotalBytes = 24 * 1024 * 1024;

final Object _referenceAttachmentZoneKey = Object();

class ReferenceAttachmentException implements Exception {
  const ReferenceAttachmentException(this.message);

  final String message;

  @override
  String toString() => message;
}

class ReferenceAttachmentDraft {
  ReferenceAttachmentDraft._({
    required this.originalName,
    required this.mediaType,
    required this.bytes,
    required this.sha256,
  });

  final String originalName;
  final String mediaType;
  final Uint8List bytes;
  final String sha256;

  int get sizeBytes => bytes.length;

  static Future<ReferenceAttachmentDraft> fromFilePath(String path) async {
    final normalized = path.trim();
    if (normalized.isEmpty) {
      throw const ReferenceAttachmentException('Reference image path is empty.');
    }
    final file = File(normalized);
    final stat = await file.stat();
    if (stat.type != FileSystemEntityType.file) {
      throw const ReferenceAttachmentException(
        'Reference image must be a regular file.',
      );
    }
    if (stat.size <= 0 || stat.size > maxReferenceAssetBytes) {
      throw const ReferenceAttachmentException(
        'Reference image must be between 1 byte and 8 MB.',
      );
    }
    final bytes = await file.readAsBytes();
    // Repeat the size check after the read to fail closed if the file changed
    // between stat and read (TOCTOU).
    if (bytes.isEmpty || bytes.length > maxReferenceAssetBytes) {
      throw const ReferenceAttachmentException(
        'Reference image must be between 1 byte and 8 MB.',
      );
    }
    return fromBytes(file.uri.pathSegments.last, bytes);
  }

  static ReferenceAttachmentDraft fromBytes(String name, Uint8List bytes) {
    final normalizedName = name.trim();
    if (normalizedName.isEmpty || normalizedName.length > 255) {
      throw const ReferenceAttachmentException('Reference image filename is invalid.');
    }
    if (bytes.isEmpty || bytes.length > maxReferenceAssetBytes) {
      throw const ReferenceAttachmentException(
        'Reference image must be between 1 byte and 8 MB.',
      );
    }
    final mediaType = _detectMediaType(bytes);
    final dimensions = _dimensions(bytes, mediaType);
    if (dimensions == null ||
        dimensions.$1 <= 0 ||
        dimensions.$2 <= 0 ||
        dimensions.$1 > 16384 ||
        dimensions.$2 > 16384 ||
        dimensions.$1 * dimensions.$2 > 80000000) {
      throw const ReferenceAttachmentException(
        'Reference image dimensions are invalid or unsafe.',
      );
    }
    return ReferenceAttachmentDraft._(
      originalName: normalizedName,
      mediaType: mediaType,
      bytes: Uint8List.fromList(bytes),
      sha256: crypto.sha256.convert(bytes).toString(),
    );
  }

  static String _detectMediaType(Uint8List bytes) {
    if (bytes.length >= 24 &&
        bytes[0] == 0x89 &&
        bytes[1] == 0x50 &&
        bytes[2] == 0x4e &&
        bytes[3] == 0x47 &&
        bytes[4] == 0x0d &&
        bytes[5] == 0x0a &&
        bytes[6] == 0x1a &&
        bytes[7] == 0x0a) {
      return 'image/png';
    }
    if (bytes.length >= 10 &&
        bytes[0] == 0xff &&
        bytes[1] == 0xd8 &&
        bytes[2] == 0xff) {
      return 'image/jpeg';
    }
    if (bytes.length >= 30 &&
        bytes[0] == 0x52 &&
        bytes[1] == 0x49 &&
        bytes[2] == 0x46 &&
        bytes[3] == 0x46 &&
        bytes[8] == 0x57 &&
        bytes[9] == 0x45 &&
        bytes[10] == 0x42 &&
        bytes[11] == 0x50) {
      return 'image/webp';
    }
    throw const ReferenceAttachmentException(
      'Only valid PNG, JPEG, and WebP reference images are accepted.',
    );
  }

  static (int, int)? _dimensions(Uint8List bytes, String mediaType) {
    switch (mediaType) {
      case 'image/png':
        if (bytes.length < 24 ||
            bytes[12] != 0x49 ||
            bytes[13] != 0x48 ||
            bytes[14] != 0x44 ||
            bytes[15] != 0x52) {
          return null;
        }
        return (_readBigEndian32(bytes, 16), _readBigEndian32(bytes, 20));
      case 'image/jpeg':
        return _jpegDimensions(bytes);
      case 'image/webp':
        return _webpDimensions(bytes);
    }
    return null;
  }

  static int _readBigEndian32(Uint8List bytes, int offset) =>
      (bytes[offset] << 24) |
      (bytes[offset + 1] << 16) |
      (bytes[offset + 2] << 8) |
      bytes[offset + 3];

  static (int, int)? _jpegDimensions(Uint8List bytes) {
    const markers = <int>{
      0xc0,
      0xc1,
      0xc2,
      0xc3,
      0xc5,
      0xc6,
      0xc7,
      0xc9,
      0xca,
      0xcb,
      0xcd,
      0xce,
      0xcf,
    };
    var offset = 2;
    while (offset + 4 <= bytes.length) {
      if (bytes[offset] != 0xff) {
        offset += 1;
        continue;
      }
      while (offset < bytes.length && bytes[offset] == 0xff) {
        offset += 1;
      }
      if (offset >= bytes.length) return null;
      final marker = bytes[offset++];
      if (marker == 0xd8 || marker == 0xd9) continue;
      if (offset + 2 > bytes.length) return null;
      final length = (bytes[offset] << 8) | bytes[offset + 1];
      if (length < 2 || offset + length > bytes.length) return null;
      if (markers.contains(marker) && length >= 7) {
        final height = (bytes[offset + 3] << 8) | bytes[offset + 4];
        final width = (bytes[offset + 5] << 8) | bytes[offset + 6];
        return (width, height);
      }
      offset += length;
    }
    return null;
  }

  static (int, int)? _webpDimensions(Uint8List bytes) {
    if (bytes.length < 30) return null;
    final chunk = String.fromCharCodes(bytes.sublist(12, 16));
    if (chunk == 'VP8X') {
      final width =
          1 + bytes[24] + (bytes[25] << 8) + (bytes[26] << 16);
      final height =
          1 + bytes[27] + (bytes[28] << 8) + (bytes[29] << 16);
      return (width, height);
    }
    if (chunk == 'VP8 ' &&
        bytes[23] == 0x9d &&
        bytes[24] == 0x01 &&
        bytes[25] == 0x2a) {
      final width = (bytes[26] | (bytes[27] << 8)) & 0x3fff;
      final height = (bytes[28] | (bytes[29] << 8)) & 0x3fff;
      return (width, height);
    }
    if (chunk == 'VP8L' && bytes.length >= 25 && bytes[20] == 0x2f) {
      final b1 = bytes[21];
      final b2 = bytes[22];
      final b3 = bytes[23];
      final b4 = bytes[24];
      final width = 1 + b1 + ((b2 & 0x3f) << 8);
      final height = 1 + (b2 >> 6) + (b3 << 2) + ((b4 & 0x0f) << 10);
      return (width, height);
    }
    return null;
  }
}

List<ReferenceAttachmentDraft> get currentReferenceAttachments {
  final value = Zone.current[_referenceAttachmentZoneKey];
  if (value is List<ReferenceAttachmentDraft>) {
    return List<ReferenceAttachmentDraft>.unmodifiable(value);
  }
  return const <ReferenceAttachmentDraft>[];
}

Future<T> withReferenceAttachments<T>(
  List<ReferenceAttachmentDraft> attachments,
  Future<T> Function() operation,
) =>
    runZoned(
      operation,
      zoneValues: <Object?, Object?>{
        _referenceAttachmentZoneKey:
            List<ReferenceAttachmentDraft>.unmodifiable(attachments),
      },
    );
