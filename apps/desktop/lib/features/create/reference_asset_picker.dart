export 'reference_asset_picker_core.dart'
    hide ReferenceAssetPicker, ReferenceAssetPickerController;

import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../app/ilaios_locale.dart';
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

enum _AttachmentPane { documents, images, video }

const _factoryFamilies = <(String, String, IconData)>[
  ('Web Factory', 'Web Factory', Icons.language_outlined),
  ('Video / Media Factory', 'Video / Medya Factory', Icons.movie_outlined),
  ('Software Factory', 'Yazılım Factory', Icons.code_outlined),
  ('App Factory', 'Uygulama Factory', Icons.apps_outlined),
  ('Research / Data Factory', 'Araştırma / Veri Factory', Icons.query_stats_outlined),
  ('Security Factory', 'Güvenlik Factory', Icons.shield_outlined),
  ('Creative / Document Factory', 'Yaratıcı / Doküman Factory', Icons.description_outlined),
  ('Commerce / Growth Factory', 'Ticaret / Büyüme Factory', Icons.trending_up_outlined),
  ('Personal Operations Factory', 'Kişisel Operasyonlar Factory', Icons.person_outline_rounded),
];

/// Shared private-input surface. Company documents, reference images and source
/// video keep their existing governed controllers; Home only changes how those
/// controls are revealed. The three heavy pickers are collapsed by default and
/// only one may be expanded at a time.
class ReferenceAssetPicker extends StatefulWidget {
  const ReferenceAssetPicker({
    required this.controller,
    required this.enabled,
    this.compact = false,
    super.key,
  });

  final ReferenceAssetPickerController controller;
  final bool enabled;
  final bool compact;

  @override
  State<ReferenceAssetPicker> createState() => _ReferenceAssetPickerState();
}

class _ReferenceAssetPickerState extends State<ReferenceAssetPicker> {
  _AttachmentPane? _expanded;

  @override
  void initState() {
    super.initState();
    _listen(widget.controller);
  }

  @override
  void didUpdateWidget(covariant ReferenceAssetPicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller == widget.controller) return;
    _unlisten(oldWidget.controller);
    _listen(widget.controller);
  }

  @override
  void dispose() {
    _unlisten(widget.controller);
    super.dispose();
  }

  void _listen(ReferenceAssetPickerController controller) {
    controller.addListener(_changed);
    controller.sourceVideo.addListener(_changed);
    controller.companyKnowledge.addListener(_changed);
  }

  void _unlisten(ReferenceAssetPickerController controller) {
    controller.removeListener(_changed);
    controller.sourceVideo.removeListener(_changed);
    controller.companyKnowledge.removeListener(_changed);
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  bool get _isTurkish =>
      IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;

  String _t(String english, String turkish) => _isTurkish ? turkish : english;

  Widget _images() => core.ReferenceAssetPicker(
        controller: widget.controller,
        enabled: widget.enabled,
        compact: true,
      );

  Widget _sourceVideo() => SourceVideoPicker(
        controller: widget.controller.sourceVideo,
        enabled: widget.enabled,
        compact: true,
      );

  Widget _companyKnowledge() => CompanyKnowledgePicker(
        controller: widget.controller.companyKnowledge,
        enabled: widget.enabled,
        compact: true,
      );

  void _toggle(_AttachmentPane pane) {
    setState(() => _expanded = _expanded == pane ? null : pane);
  }

  String _documentSummary() {
    final count = widget.controller.companyKnowledge.documents.length;
    if (count == 0) return 'PDF / DOCX / ZIP';
    return _t('$count document attached', '$count belge eklendi');
  }

  String _imageSummary() {
    final count = widget.controller.assets.length;
    if (count == 0) return 'JPEG / PNG / WebP';
    return _t('$count / 20 images attached', '$count / 20 görsel eklendi');
  }

  String _videoSummary() {
    final source = widget.controller.sourceVideo.source;
    if (source == null) return 'MP4';
    return _t('1 source video attached', '1 kaynak video eklendi');
  }

  Widget _action({
    required Key key,
    required _AttachmentPane pane,
    required IconData icon,
    required String label,
    required String summary,
  }) {
    final selected = _expanded == pane;
    return Expanded(
      child: OutlinedButton(
        key: key,
        onPressed: widget.enabled ? () => _toggle(pane) : null,
        style: OutlinedButton.styleFrom(
          alignment: Alignment.centerLeft,
          minimumSize: const Size(0, 44),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          backgroundColor: selected
              ? Theme.of(context).colorScheme.surfaceContainerHighest
              : Theme.of(context).colorScheme.surfaceContainerLowest,
        ),
        child: Row(
          children: [
            Icon(icon, size: 18),
            const SizedBox(width: 8),
            Expanded(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    summary,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 12.5,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              selected ? Icons.expand_less_rounded : Icons.expand_more_rounded,
              size: 18,
            ),
          ],
        ),
      ),
    );
  }

  Widget _expandedPane() {
    final pane = _expanded;
    if (pane == null) return const SizedBox.shrink();
    final child = switch (pane) {
      _AttachmentPane.documents => _companyKnowledge(),
      _AttachmentPane.images => _images(),
      _AttachmentPane.video => _sourceVideo(),
    };
    return Container(
      key: ValueKey('home-attachment-pane-${pane.name}'),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: child,
    );
  }

  Widget _factoryGrid() => Column(
        key: const Key('home-canonical-factory-grid'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _t('Factories', 'Factory Alanları'),
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 6),
          LayoutBuilder(
            builder: (context, constraints) {
              final columns = constraints.maxWidth >= 900 ? 3 : 2;
              const spacing = 8.0;
              final cardWidth =
                  (constraints.maxWidth - spacing * (columns - 1)) / columns;
              return Wrap(
                spacing: spacing,
                runSpacing: spacing,
                children: [
                  for (var index = 0; index < _factoryFamilies.length; index++)
                    SizedBox(
                      width: cardWidth,
                      child: Container(
                        key: ValueKey('home-factory-${index + 1}'),
                        constraints: const BoxConstraints(minHeight: 48),
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerLowest,
                          border: Border.all(
                            color: Theme.of(context).colorScheme.outlineVariant,
                          ),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(_factoryFamilies[index].$3, size: 18),
                            const SizedBox(width: 8),
                            Expanded(
                              child: Text(
                                _isTurkish
                                    ? _factoryFamilies[index].$2
                                    : _factoryFamilies[index].$1,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                ],
              );
            },
          ),
        ],
      );

  Widget _progressiveHome() => Column(
        key: const Key('home-progressive-attachments'),
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            children: [
              _action(
                key: const Key('home-add-document'),
                pane: _AttachmentPane.documents,
                icon: Icons.description_outlined,
                label: _t('Add file', 'Dosya Ekle'),
                summary: _documentSummary(),
              ),
              const SizedBox(width: 8),
              _action(
                key: const Key('home-add-image'),
                pane: _AttachmentPane.images,
                icon: Icons.image_outlined,
                label: _t('Add image', 'Görsel Ekle'),
                summary: _imageSummary(),
              ),
              const SizedBox(width: 8),
              _action(
                key: const Key('home-add-video'),
                pane: _AttachmentPane.video,
                icon: Icons.video_file_outlined,
                label: _t('Add video', 'Video Ekle'),
                summary: _videoSummary(),
              ),
            ],
          ),
          if (_expanded != null) ...[
            const SizedBox(height: 8),
            _expandedPane(),
          ],
          const SizedBox(height: 10),
          _factoryGrid(),
        ],
      );

  // Preserve the existing non-Home compact geometry because packaging and
  // combined-contract verification depend on this exact governed picker shape.
  // Home does not use this path; it uses progressive disclosure above.
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

  Widget _legacyStack() => Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _images(),
          const SizedBox(height: 8),
          _sourceVideo(),
          const SizedBox(height: 8),
          _companyKnowledge(),
        ],
      );

  @override
  Widget build(BuildContext context) {
    final inlineHome = key == const Key('home-prompt-attachments');
    if (inlineHome) return _progressiveHome();
    if (widget.compact) return _safeCompactStack();
    return _legacyStack();
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
