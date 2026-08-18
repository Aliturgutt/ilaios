import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';

const int maxVideoReferenceImages = 8;
const int maxVideoReferenceImageBytes = 10 * 1024 * 1024;
const int maxVideoReferencePoolBytes = 40 * 1024 * 1024;

enum VideoReferenceRole {
  subjectPrimary('subject_primary'),
  subjectSecondary('subject_secondary'),
  detail('detail'),
  style('style'),
  environment('environment');

  const VideoReferenceRole(this.wireValue);
  final String wireValue;
}

class VideoReferenceDraft {
  VideoReferenceDraft({
    required this.fileName,
    required this.bytes,
    required this.mediaType,
    this.role = VideoReferenceRole.subjectPrimary,
  }) : sha256Digest = sha256.convert(bytes).toString();

  final String fileName;
  final Uint8List bytes;
  final String mediaType;
  final String sha256Digest;
  final VideoReferenceRole role;

  int get sizeBytes => bytes.length;

  VideoReferenceDraft copyWith({VideoReferenceRole? role}) => VideoReferenceDraft(
        fileName: fileName,
        bytes: bytes,
        mediaType: mediaType,
        role: role ?? this.role,
      );
}

class VideoReferencePickerException implements Exception {
  const VideoReferencePickerException(this.message);
  final String message;

  @override
  String toString() => message;
}

abstract interface class VideoReferenceFilePicker {
  Future<List<VideoReferenceDraft>> pick();
}

class WindowsVideoReferenceFilePicker implements VideoReferenceFilePicker {
  const WindowsVideoReferenceFilePicker();

  @override
  Future<List<VideoReferenceDraft>> pick() async {
    if (!Platform.isWindows) {
      throw const VideoReferencePickerException(
        'Native video reference selection is currently available on Windows.',
      );
    }
    const script = r'''
Add-Type -AssemblyName System.Windows.Forms
$dialog = New-Object System.Windows.Forms.OpenFileDialog
$dialog.Multiselect = $true
$dialog.Filter = 'Images (*.jpg;*.jpeg;*.png;*.webp)|*.jpg;*.jpeg;*.png;*.webp'
$dialog.Title = 'Select up to 8 video reference images'
if ($dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
  @($dialog.FileNames) | ConvertTo-Json -Compress
} else {
  '[]'
}
''';
    final result = await Process.run(
      'powershell.exe',
      const <String>[
        '-NoLogo',
        '-NoProfile',
        '-NonInteractive',
        '-Command',
        script,
      ],
      runInShell: false,
    );
    if (result.exitCode != 0) {
      throw VideoReferencePickerException(
        'Reference image picker failed: ${result.stderr}'.trim(),
      );
    }
    final output = result.stdout.toString().trim();
    if (output.isEmpty || output == '[]') return const <VideoReferenceDraft>[];
    final decoded = jsonDecode(output);
    final paths = decoded is String
        ? <String>[decoded]
        : (decoded as List<dynamic>).cast<String>();
    if (paths.length > maxVideoReferenceImages) {
      throw const VideoReferencePickerException(
        'You can select at most 8 video reference images.',
      );
    }

    final drafts = <VideoReferenceDraft>[];
    final digests = <String>{};
    var totalBytes = 0;
    for (final path in paths) {
      final file = File(path);
      final bytes = await file.readAsBytes();
      if (bytes.isEmpty || bytes.length > maxVideoReferenceImageBytes) {
        throw VideoReferencePickerException(
          '${file.uri.pathSegments.last} exceeds the 10 MiB image limit.',
        );
      }
      final mediaType = _detectMediaType(bytes);
      if (mediaType == null) {
        throw VideoReferencePickerException(
          '${file.uri.pathSegments.last} is not a valid JPG, PNG or WebP image.',
        );
      }
      final digest = sha256.convert(bytes).toString();
      if (!digests.add(digest)) continue;
      totalBytes += bytes.length;
      if (totalBytes > maxVideoReferencePoolBytes) {
        throw const VideoReferencePickerException(
          'Reference images exceed the 40 MiB total upload limit.',
        );
      }
      drafts.add(
        VideoReferenceDraft(
          fileName: file.uri.pathSegments.last,
          bytes: bytes,
          mediaType: mediaType,
        ),
      );
    }
    return List<VideoReferenceDraft>.unmodifiable(drafts);
  }
}

String? _detectMediaType(Uint8List bytes) {
  if (bytes.length >= 3 &&
      bytes[0] == 0xff &&
      bytes[1] == 0xd8 &&
      bytes[2] == 0xff) {
    return 'image/jpeg';
  }
  const png = <int>[0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a];
  if (bytes.length >= png.length) {
    var match = true;
    for (var index = 0; index < png.length; index++) {
      if (bytes[index] != png[index]) {
        match = false;
        break;
      }
    }
    if (match) return 'image/png';
  }
  if (bytes.length >= 12 &&
      ascii.decode(bytes.sublist(0, 4), allowInvalid: true) == 'RIFF' &&
      ascii.decode(bytes.sublist(8, 12), allowInvalid: true) == 'WEBP') {
    return 'image/webp';
  }
  return null;
}

class VideoReferenceTray extends StatelessWidget {
  const VideoReferenceTray({
    required this.references,
    required this.onAdd,
    required this.onRemove,
    required this.onRoleChanged,
    this.busy = false,
    super.key,
  });

  final List<VideoReferenceDraft> references;
  final VoidCallback onAdd;
  final ValueChanged<int> onRemove;
  final void Function(int index, VideoReferenceRole role) onRoleChanged;
  final bool busy;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Material(
      key: const Key('video-reference-tray'),
      elevation: 8,
      borderRadius: BorderRadius.circular(10),
      color: scheme.surfaceContainerHigh,
      child: SizedBox(
        width: 430,
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  const Icon(Icons.collections_outlined, size: 18),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      'Video references · ${references.length}/$maxVideoReferenceImages',
                      style: const TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                  TextButton.icon(
                    key: const Key('video-reference-add'),
                    onPressed: busy || references.length >= maxVideoReferenceImages
                        ? null
                        : onAdd,
                    icon: const Icon(Icons.add_photo_alternate_outlined, size: 16),
                    label: const Text('Add images'),
                  ),
                ],
              ),
              if (references.isEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: 2, bottom: 4),
                  child: Text(
                    'Optional: add product, character, detail, style or environment references. '
                    'ILAIOS chooses the smallest provider-safe subset automatically.',
                    style: TextStyle(fontSize: 9, color: scheme.onSurfaceVariant),
                  ),
                )
              else
                SizedBox(
                  height: 104,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: references.length,
                    separatorBuilder: (_, __) => const SizedBox(width: 7),
                    itemBuilder: (context, index) {
                      final reference = references[index];
                      return SizedBox(
                        width: 92,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(
                              child: Stack(
                                fit: StackFit.expand,
                                children: [
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(6),
                                    child: Image.memory(
                                      reference.bytes,
                                      fit: BoxFit.cover,
                                      errorBuilder: (_, __, ___) => const Center(
                                        child: Icon(Icons.broken_image_outlined),
                                      ),
                                    ),
                                  ),
                                  Positioned(
                                    right: 2,
                                    top: 2,
                                    child: IconButton.filledTonal(
                                      visualDensity: VisualDensity.compact,
                                      padding: EdgeInsets.zero,
                                      constraints: const BoxConstraints.tightFor(
                                        width: 22,
                                        height: 22,
                                      ),
                                      onPressed: () => onRemove(index),
                                      icon: const Icon(Icons.close, size: 13),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            const SizedBox(height: 3),
                            DropdownButtonHideUnderline(
                              child: DropdownButton<VideoReferenceRole>(
                                value: reference.role,
                                isDense: true,
                                isExpanded: true,
                                style: TextStyle(
                                  fontSize: 8,
                                  color: scheme.onSurface,
                                ),
                                items: VideoReferenceRole.values
                                    .map(
                                      (role) => DropdownMenuItem(
                                        value: role,
                                        child: Text(
                                          _roleLabel(role),
                                          overflow: TextOverflow.ellipsis,
                                        ),
                                      ),
                                    )
                                    .toList(growable: false),
                                onChanged: busy
                                    ? null
                                    : (role) {
                                        if (role != null) onRoleChanged(index, role);
                                      },
                              ),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

String _roleLabel(VideoReferenceRole role) => switch (role) {
      VideoReferenceRole.subjectPrimary => 'Main subject',
      VideoReferenceRole.subjectSecondary => 'Extra subject',
      VideoReferenceRole.detail => 'Detail',
      VideoReferenceRole.style => 'Style',
      VideoReferenceRole.environment => 'Environment',
    };
