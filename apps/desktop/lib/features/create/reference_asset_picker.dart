export 'reference_asset_picker_core.dart'
    hide ReferenceAssetPicker, ReferenceAssetPickerController;

import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../reference_assets/reference_asset_draft.dart';
import 'company_knowledge_picker.dart';
import 'reference_asset_picker_core.dart' as core;
import 'source_video_picker.dart';

const MethodChannel _referenceDropChannel = MethodChannel(
  'ilaios/reference-assets-drop',
);

/// Existing picker controller plus Windows-native image drag/drop, one
/// separately governed source-video draft, and persistent company Knowledge
/// documents. Each path retains its existing server authority.
class ReferenceAssetPickerController extends core.ReferenceAssetPickerController {
  ReferenceAssetPickerController() {
    if (Platform.isWindows) {
      _referenceDropChannel.setMethodCallHandler(_handleNativeDrop);
    }
  }

  final SourceVideoPickerController sourceVideo = SourceVideoPickerController();
  final CompanyKnowledgePickerController companyKnowledge =
      CompanyKnowledgePickerController();

  Future<Object?> _handleNativeDrop(MethodCall call) async {
    if (call.method != 'droppedPaths') return null;
    final raw = call.arguments;
    if (raw is! List) return null;
    final paths = raw
        .whereType<String>()
        .where((value) => value.trim().isNotEmpty)
        .toList(growable: false);
    if (paths.isEmpty) return null;
    await addDroppedPaths(paths);
    return null;
  }

  Future<void> addDroppedPaths(List<String> paths) async {
    final current = assets.toList(growable: true);
    var totalBytes = current.fold<int>(0, (sum, asset) => sum + asset.sizeBytes);
    final knownDigests = current.map((asset) => asset.sha256Hex).toSet();

    for (final rawPath in paths) {
      if (current.length >= core.maxVideoReferenceAssets) break;
      final path = rawPath.trim();
      if (path.isEmpty) continue;
      final file = File(path);
      FileStat stat;
      try {
        stat = await file.stat();
      } on FileSystemException {
        continue;
      }
      if (stat.type != FileSystemEntityType.file ||
          stat.size <= 0 ||
          stat.size > core.maxVideoReferenceAssetBytes ||
          totalBytes + stat.size > core.maxVideoReferenceTotalBytes) {
        continue;
      }
      final extension = _extension(path);
      final mimeType = switch (extension) {
        'jpg' || 'jpeg' => 'image/jpeg',
        'png' => 'image/png',
        'webp' => 'image/webp',
        _ => null,
      };
      if (mimeType == null) continue;
      final bytes = await file.readAsBytes();
      if (bytes.length != stat.size) continue;
      final digest = sha256.convert(bytes).toString();
      if (!knownDigests.add(digest)) continue;
      current.add(
        ReferenceAssetDraft(
          filename: _basename(path),
          mimeType: mimeType,
          bytes: bytes,
          sha256Hex: digest,
        ),
      );
      totalBytes += bytes.length;
    }
    replace(current);
  }

  @override
  void clear() {
    super.clear();
    sourceVideo.clear();
    companyKnowledge.clear();
  }

  @override
  void dispose() {
    if (Platform.isWindows) {
      _referenceDropChannel.setMethodCallHandler(null);
    }
    sourceVideo.dispose();
    companyKnowledge.dispose();
    super.dispose();
  }
}

/// Read-only presentation scope for the single existing attachment controller.
/// This does not own upload, identity, session, routing, or governance authority.
class ReferenceAssetPickerScope extends InheritedWidget {
  const ReferenceAssetPickerScope({
    required this.controller,
    required super.child,
    super.key,
  });

  final ReferenceAssetPickerController? controller;

  static ReferenceAssetPickerController? maybeOf(BuildContext context) =>
      context.dependOnInheritedWidgetOfExactType<ReferenceAssetPickerScope>()?.controller;

  @override
  bool updateShouldNotify(ReferenceAssetPickerScope oldWidget) =>
      controller != oldWidget.controller;
}

/// Shared private-input surface. Company documents are deliberately shown in
/// the same prompt attachment surface, but are labeled persistent Knowledge
/// because the current authenticated API does not provide a task-only document
/// contract.
class ReferenceAssetPicker extends StatelessWidget {
  const ReferenceAssetPicker({
    required this.controller,
    required this.enabled,
    this.compact = false,
    super.key,
  });

  final ReferenceAssetPickerController controller;
  final bool enabled;
  final bool compact;

  Widget _images() => core.ReferenceAssetPicker(
        controller: controller,
        enabled: enabled,
        compact: compact,
      );

  Widget _sourceVideo() => SourceVideoPicker(
        controller: controller.sourceVideo,
        enabled: enabled,
        compact: compact,
      );

  Widget _companyKnowledge() => CompanyKnowledgePicker(
        controller: controller.companyKnowledge,
        enabled: enabled,
        compact: compact,
      );

  Widget _safeCompactStack() => Column(
        key: const Key('compact-reference-asset-stack'),
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(flex: 3, child: _images()),
              const SizedBox(width: 8),
              Expanded(flex: 2, child: _sourceVideo()),
            ],
          ),
          const SizedBox(height: 6),
          _companyKnowledge(),
        ],
      );

  @override
  Widget build(BuildContext context) {
    if (!compact) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _images(),
          const SizedBox(height: 8),
          _sourceVideo(),
          const SizedBox(height: 8),
          _companyKnowledge(),
        ],
      );
    }

    final inlineHome = key == const Key('home-prompt-attachments');
    if (!inlineHome) return _safeCompactStack();

    return LayoutBuilder(
      builder: (context, constraints) {
        if (constraints.maxWidth < 1080) return _safeCompactStack();

        return Row(
          key: const Key('compact-reference-asset-row'),
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(child: _companyKnowledge()),
            const SizedBox(width: 8),
            Expanded(child: _images()),
            const SizedBox(width: 8),
            Expanded(child: _sourceVideo()),
          ],
        );
      },
    );
  }
}

String _extension(String path) {
  final name = _basename(path);
  final index = name.lastIndexOf('.');
  return index < 0 ? '' : name.substring(index + 1).toLowerCase();
}

String _basename(String path) {
  final normalized = path.replaceAll('\\', '/');
  final parts = normalized.split('/').where((part) => part.isNotEmpty).toList();
  return parts.isEmpty ? path : parts.last;
}
