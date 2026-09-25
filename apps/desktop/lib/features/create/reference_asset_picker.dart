import '../../app/ilaios_icon_palette.dart';
export 'reference_asset_picker_core.dart'
    hide ReferenceAssetPicker, ReferenceAssetPickerController;

import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';
import '../../app/desktop_page_heading.dart';
import 'package:flutter/services.dart';

import '../../app/ilaios_locale.dart';
import '../../reference_assets/reference_asset_draft.dart';
import 'company_knowledge_picker.dart';
import 'reference_asset_picker_core.dart' as core;
import 'source_video_picker.dart';

const MethodChannel _referenceDropChannel = MethodChannel(
  'ilaios/reference-assets-drop',
);

class ReferenceAssetPickerController
    extends core.ReferenceAssetPickerController {
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
    var totalBytes = current.fold<int>(
      0,
      (sum, asset) => sum + asset.sizeBytes,
    );
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
      context
          .dependOnInheritedWidgetOfExactType<ReferenceAssetPickerScope>()
          ?.controller;

  @override
  bool updateShouldNotify(ReferenceAssetPickerScope oldWidget) =>
      controller != oldWidget.controller;
}

enum _AttachmentPane { documents, images, video }

const _factoryFamilies =
    <
      ({
        String en,
        String tr,
        String enDescription,
        String trDescription,
        IconData icon,
        Color color,
      })
    >[
      (
        en: 'Web Factory',
        tr: 'Web Fabrikası',
        enDescription:
            'Creates business sites, landing pages and web apps. Shapes page layouts and web interfaces.',
        trDescription:
            'Kurumsal siteler, açılış sayfaları ve web uygulamaları oluşturur. Sayfa düzeni ve web arayüzlerine odaklanır.',
        icon: Icons.travel_explore_rounded,
        color: IlaiosIconPalette.web,
      ),
      (
        en: 'Video and Media Factory',
        tr: 'Video ve Medya Fabrikası',
        enDescription:
            'Creates promotional videos, animation and visual content. Develops visual stories for presentations and campaigns.',
        trDescription:
            'Tanıtım videoları, animasyonlar ve görsel içerikler hazırlar. Sunum ve kampanyalar için görsel anlatımlar geliştirir.',
        icon: Icons.movie_creation_rounded,
        color: IlaiosIconPalette.media,
      ),
      (
        en: 'Software Factory',
        tr: 'Yazılım Fabrikası',
        enDescription:
            'Develops custom software, automation and integrations. Handles service logic and connected systems.',
        trDescription:
            'Özel yazılımlar, otomasyonlar ve sistem entegrasyonları geliştirir. Servis mantığı ve bağlı sistemlere odaklanır.',
        icon: Icons.integration_instructions_rounded,
        color: IlaiosIconPalette.software,
      ),
      (
        en: 'App Factory',
        tr: 'Uygulama Fabrikası',
        enDescription:
            'Develops user-focused mobile and desktop apps. Designs app screens and interaction flows.',
        trDescription:
            'Mobil ve masaüstü için kullanıcı odaklı uygulamalar geliştirir. Uygulama ekranları ve etkileşim akışları tasarlar.',
        icon: Icons.devices_rounded,
        color: IlaiosIconPalette.application,
      ),
      (
        en: 'Security Factory',
        tr: 'Güvenlik Fabrikası',
        enDescription:
            'Analyzes systems, tests security and improves resilience. Reviews risks and recommends hardening steps.',
        trDescription:
            'Sistemleri analiz eder, güvenlik testleri ve sağlamlaştırma yapar. Riskleri inceler ve koruma adımları önerir.',
        icon: Icons.verified_user_rounded,
        color: IlaiosIconPalette.security,
      ),
      (
        en: 'Research and Data Factory',
        tr: 'Araştırma ve Veri Fabrikası',
        enDescription:
            'Researches sources, analyzes data and prepares reports. Turns findings into structured insights.',
        trDescription:
            'Kaynakları araştırır, verileri analiz eder ve raporlar hazırlar. Bulguları düzenli içgörülere dönüştürür.',
        icon: Icons.analytics_rounded,
        color: IlaiosIconPalette.research,
      ),
      (
        en: 'Creative Factory',
        tr: 'Yaratıcı Fabrika',
        enDescription:
            'Develops brand identity, designs and creative content. Explores visual concepts and brand materials.',
        trDescription:
            'Marka kimliği, tasarım ve yaratıcı içerikler geliştirir. Görsel konseptler ve marka materyalleri hazırlar.',
        icon: Icons.auto_awesome_rounded,
        color: IlaiosIconPalette.creative,
      ),
      (
        en: 'Marketing Factory',
        tr: 'Pazarlama Fabrikası',
        enDescription:
            'Creates campaign content and marketing workflows. Plans audience messages and promotion materials.',
        trDescription:
            'Kampanya içerikleri ve pazarlama iş akışları hazırlar. Hedef kitle mesajları ve tanıtım materyalleri planlar.',
        icon: Icons.campaign_rounded,
        color: IlaiosIconPalette.marketing,
      ),
      (
        en: 'Operations Factory',
        tr: 'Operasyon Fabrikası',
        enDescription:
            'Organizes workflows and develops operational automation. Streamlines recurring tasks and handoffs.',
        trDescription:
            'İş süreçlerini düzenler ve operasyonel otomasyonlar geliştirir. Tekrarlanan görevleri ve iş devrini kolaylaştırır.',
        icon: Icons.precision_manufacturing_rounded,
        color: IlaiosIconPalette.operations,
      ),
    ];

class ReferenceAssetPicker extends StatefulWidget {
  const ReferenceAssetPicker({
    required this.controller,
    required this.enabled,
    this.compact = false,
    this.factoryCardHeight,
    super.key,
  });

  final ReferenceAssetPickerController controller;
  final bool enabled;
  final bool compact;
  final double? factoryCardHeight;

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
    _AttachmentPane.documents =>
      widget.controller.companyKnowledge.documents.length,
    _AttachmentPane.images => widget.controller.assets.length,
    _AttachmentPane.video =>
      widget.controller.sourceVideo.source == null ? 0 : 1,
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
        minimumSize: const Size(132, 38),
        padding: const EdgeInsets.symmetric(horizontal: 14),
        foregroundColor: Theme.of(context).colorScheme.onSurface,
        backgroundColor: Theme.of(context).colorScheme.surfaceContainerLowest,
        side: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
        textStyle: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
      ),
      icon: Icon(icon, size: 20, color: IlaiosIconPalette.attachment(context)),
      label: Text(count == 0 ? label : '$label ($count)'),
    );
  }

  Widget _attachmentRow() => Wrap(
    spacing: 10,
    runSpacing: 6,
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
        style: DesktopPageHeading.style(context).copyWith(fontSize: 19),
      ),
      const SizedBox(height: 7),
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
      const SizedBox(height: 12),
      LayoutBuilder(
        builder: (context, constraints) {
          final columns = constraints.maxWidth >= 980
              ? 3
              : constraints.maxWidth >= 560
              ? 2
              : 1;
          const horizontalGap = 12.0;
          const verticalGap = 8.0;
          final cardWidth =
              ((constraints.maxWidth - horizontalGap * (columns - 1)) / columns)
                  .floorToDouble();
          final textScale = MediaQuery.textScalerOf(
            context,
          ).scale(1.0).clamp(1.0, 1.5).toDouble();
          final cardHeight = (widget.factoryCardHeight ?? 82.0) * textScale;
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
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 7,
                    ),
                    decoration: BoxDecoration(
                      color: Theme.of(
                        context,
                      ).colorScheme.surfaceContainerLowest,
                      border: Border.all(
                        color: Theme.of(context).colorScheme.outlineVariant,
                      ),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 46,
                          height: 46,
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            color: IlaiosIconPalette.factory(
                              context,
                              _factoryFamilies[index].color,
                            ).withValues(alpha: 0.10),
                            borderRadius: BorderRadius.circular(13),
                            border: Border.all(
                              color: IlaiosIconPalette.factory(
                                context,
                                _factoryFamilies[index].color,
                              ).withValues(alpha: 0.18),
                            ),
                          ),
                          child: Icon(
                            _factoryFamilies[index].icon,
                            size: 26,
                            color: IlaiosIconPalette.factory(
                              context,
                              _factoryFamilies[index].color,
                            ),
                          ),
                        ),
                        const SizedBox(width: 12),
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
                                style: TextStyle(
                                  fontSize: 14.5,
                                  fontWeight: FontWeight.w700,
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.onSurface,
                                ),
                              ),
                              const SizedBox(height: 3),
                              Text(
                                _isTurkish
                                    ? _factoryFamilies[index].trDescription
                                    : _factoryFamilies[index].enDescription,
                                maxLines: 4,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(
                                  fontSize: 13,
                                  height: 1.3,
                                  fontWeight: FontWeight.w400,
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.onSurfaceVariant,
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
          const SizedBox(height: 14),
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
