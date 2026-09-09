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

const _factoryFamilies = <({
  String en,
  String tr,
  String enDescription,
  String trDescription,
  IconData icon,
  Color color,
})>[
  (
    en: 'Web Factory',
    tr: 'Web Fabrikası',
    enDescription: 'Builds websites and web applications.',
    trDescription: 'Web siteleri ve web uygulamaları üretir.',
    icon: Icons.language_rounded,
    color: Color(0xFF1388F2),
  ),
  (
    en: 'Video and Media Factory',
    tr: 'Video ve Medya Fabrikası',
    enDescription: 'Produces video, animation and visual media.',
    trDescription: 'Video, animasyon ve görsel medya üretir.',
    icon: Icons.smart_display_outlined,
    color: Color(0xFF7A2CF2),
  ),
  (
    en: 'Software Factory',
    tr: 'Yazılım Fabrikası',
    enDescription: 'Builds software, automation and system solutions.',
    trDescription: 'Yazılım, otomasyon ve sistem çözümleri üretir.',
    icon: Icons.code_rounded,
    color: Color(0xFFF06A12),
  ),
  (
    en: 'App Factory',
    tr: 'Uygulama Fabrikası',
    enDescription: 'Builds mobile and desktop applications.',
    trDescription: 'Mobil ve masaüstü uygulamalar üretir.',
    icon: Icons.smartphone_rounded,
    color: Color(0xFF21C86B),
  ),
  (
    en: 'Security Factory',
    tr: 'Güvenlik Fabrikası',
    enDescription: 'Performs governed security analysis, tests and hardening.',
    trDescription: 'Güvenlik analizi, test ve sertleştirme sağlar.',
    icon: Icons.shield_rounded,
    color: Color(0xFFFF3161),
  ),
  (
    en: 'Research and Data Factory',
    tr: 'Araştırma ve Veri Fabrikası',
    enDescription: 'Produces research, data analysis and reports.',
    trDescription: 'Araştırma, veri analizi ve raporlar üretir.',
    icon: Icons.search_rounded,
    color: Color(0xFF10A7C8),
  ),
  (
    en: 'Creative Factory',
    tr: 'Yaratıcı Fabrika',
    enDescription: 'Produces design, brand, content and creative work.',
    trDescription: 'Tasarım, marka, içerik ve yaratıcı işler üretir.',
    icon: Icons.palette_outlined,
    color: Color(0xFFFFB000),
  ),
  (
    en: 'Marketing Factory',
    tr: 'Pazarlama Fabrikası',
    enDescription: 'Produces marketing content and growth workflows.',
    trDescription: 'Pazarlama içerikleri ve büyüme çözümleri üretir.',
    icon: Icons.campaign_rounded,
    color: Color(0xFF19B947),
  ),
  (
    en: 'Operations Factory',
    tr: 'Operasyon Fabrikası',
    enDescription: 'Supports workflows, operations and productivity.',
    trDescription: 'İş süreçleri, operasyon ve verimlilik çözümleri üretir.',
    icon: Icons.settings_suggest_rounded,
    color: Color(0xFF7428E8),
  ),
];

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

  Future<void> _openPane(_AttachmentPane pane) async {
    if (!widget.enabled) return;
    final localeScope = IlaiosLocaleScope.of(context);
    final title = switch (pane) {
      _AttachmentPane.documents => _t('Add file', 'Dosya ekle'),
      _AttachmentPane.images => _t('Add image', 'Görsel ekle'),
      _AttachmentPane.video => _t('Add video', 'Video ekle'),
    };
    final body = switch (pane) {
      _AttachmentPane.documents => CompanyKnowledgePicker(
          controller: widget.controller.companyKnowledge,
          enabled: widget.enabled,
          compact: true,
        ),
      _AttachmentPane.images => core.ReferenceAssetPicker(
          controller: widget.controller,
          enabled: widget.enabled,
          compact: true,
        ),
      _AttachmentPane.video => SourceVideoPicker(
          controller: widget.controller.sourceVideo,
          enabled: widget.enabled,
          compact: true,
        ),
    };

    await showDialog<void>(
      context: context,
      builder: (dialogContext) => IlaiosLocaleScope(
        locale: localeScope.locale,
        onChanged: localeScope.onChanged,
        child: AlertDialog(
          title: Text(title),
          content: SizedBox(width: 620, child: body),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text(_t('Close', 'Kapat')),
            ),
          ],
        ),
      ),
    );
  }

  int _countFor(_AttachmentPane pane) => switch (pane) {
        _AttachmentPane.documents => widget.controller.companyKnowledge.documents.length,
        _AttachmentPane.images => widget.controller.assets.length,
        _AttachmentPane.video => widget.controller.sourceVideo.source == null ? 0 : 1,
      };

  Widget _attachmentButton({
    required Key key,
    required _AttachmentPane pane,
    required IconData icon,
    required String label,
  }) {
    final count = _countFor(pane);
    return OutlinedButton.icon(
      key: key,
      onPressed: widget.enabled ? () => _openPane(pane) : null,
      style: OutlinedButton.styleFrom(
        minimumSize: const Size(143, 47),
        padding: const EdgeInsets.symmetric(horizontal: 16),
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        backgroundColor: Theme.of(context).colorScheme.surfaceContainerLowest,
        side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700),
      ),
      icon: Icon(icon, size: 20),
      label: Text(count == 0 ? label : '$label ($count)'),
    );
  }

  Widget _attachmentRow() => Wrap(
        spacing: 12,
        runSpacing: 8,
        children: [
          _attachmentButton(
            key: const Key('home-add-document'),
            pane: _AttachmentPane.documents,
            icon: Icons.file_upload_outlined,
            label: _t('Add file', 'Dosya ekle'),
          ),
          _attachmentButton(
            key: const Key('home-add-image'),
            pane: _AttachmentPane.images,
            icon: Icons.image_outlined,
            label: _t('Add image', 'Görsel ekle'),
          ),
          _attachmentButton(
            key: const Key('home-add-video'),
            pane: _AttachmentPane.video,
            icon: Icons.video_file_outlined,
            label: _t('Add video', 'Video ekle'),
          ),
        ],
      );

  Widget _factoryGrid() => Column(
        key: const Key('home-canonical-factory-grid'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _t('ILAIOS Factories', 'ILAIOS Fabrikaları'),
            style: const TextStyle(
              fontSize: 22,
              height: 1.1,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            _t(
              'One or more factories can work together depending on the goal.',
              'Hedefine göre bir veya birden fazla fabrika birlikte çalışabilir.',
            ),
            style: TextStyle(
              fontSize: 13.5,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 14),
          LayoutBuilder(
            builder: (context, constraints) {
              final columns = constraints.maxWidth >= 980 ? 3 : 2;
              const horizontalGap = 14.0;
              const verticalGap = 13.0;
              final cardWidth =
                  ((constraints.maxWidth - horizontalGap * (columns - 1)) / columns)
                      .floorToDouble();
              final textScale = MediaQuery.textScalerOf(context)
                  .scale(1.0)
                  .clamp(1.0, 1.5)
                  .toDouble();
              final cardHeight = 84.0 * textScale;
              return Wrap(
                spacing: horizontalGap,
                runSpacing: verticalGap,
                children: [
                  for (var index = 0; index < _factoryFamilies.length; index++)
                    SizedBox(
                      width: cardWidth,
                      height: cardHeight,
                      child: Container(
                        key: ValueKey('home-factory-${index + 1}'),
                        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 13),
                        decoration: BoxDecoration(
                          color: Theme.of(context).colorScheme.surfaceContainerLowest,
                          border: Border.all(
                            color: Theme.of(context).colorScheme.outlineVariant,
                          ),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              _factoryFamilies[index].icon,
                              size: 38,
                              color: _factoryFamilies[index].color,
                            ),
                            const SizedBox(width: 18),
                            Expanded(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    _isTurkish
                                        ? _factoryFamilies[index].tr
                                        : _factoryFamilies[index].en,
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(
                                      fontSize: 14.5,
                                      fontWeight: FontWeight.w800,
                                    ),
                                  ),
                                  const SizedBox(height: 5),
                                  Text(
                                    _isTurkish
                                        ? _factoryFamilies[index].trDescription
                                        : _factoryFamilies[index].enDescription,
                                    maxLines: 2,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      fontSize: 12.5,
                                      height: 1.2,
                                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                                    ),
                                  ),
                                ],
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

  @override
  Widget build(BuildContext context) {
    final inlineHome = widget.key == const Key('home-prompt-attachments');
    if (inlineHome) {
      return Column(
        key: const Key('home-progressive-attachments'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _attachmentRow(),
          const SizedBox(height: 38),
          _factoryGrid(),
        ],
      );
    }
    return _attachmentRow();
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
