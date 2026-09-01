import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../reference_assets/reference_asset_draft.dart';

const int maxVideoReferenceAssets = 20;
const int maxVideoReferenceAssetBytes = 10 * 1024 * 1024;
const int maxVideoReferenceTotalBytes = 100 * 1024 * 1024;

class ReferenceAssetPickerController extends ChangeNotifier {
  List<ReferenceAssetDraft> _assets = const <ReferenceAssetDraft>[];

  List<ReferenceAssetDraft> get assets =>
      List<ReferenceAssetDraft>.unmodifiable(_assets);

  int get totalBytes =>
      _assets.fold<int>(0, (sum, asset) => sum + asset.sizeBytes);

  void replace(List<ReferenceAssetDraft> value) {
    _assets = List<ReferenceAssetDraft>.unmodifiable(value);
    ReferenceAssetSubmissionBus.replace(_assets);
    notifyListeners();
  }

  void clear() {
    if (_assets.isEmpty) {
      ReferenceAssetSubmissionBus.clear();
      return;
    }
    _assets = const <ReferenceAssetDraft>[];
    ReferenceAssetSubmissionBus.clear();
    notifyListeners();
  }
}

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
  bool _reading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_changed);
  }

  @override
  void didUpdateWidget(covariant ReferenceAssetPicker oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.controller == widget.controller) return;
    oldWidget.controller.removeListener(_changed);
    widget.controller.addListener(_changed);
  }

  @override
  void dispose() {
    widget.controller.removeListener(_changed);
    super.dispose();
  }

  void _changed() {
    if (mounted) setState(() {});
  }

  String _text(String english, String turkish) =>
      context.ilaiosLocale.locale == IlaiosLocale.turkish ? turkish : english;

  Future<void> _pick() async {
    if (!widget.enabled || _reading) return;
    setState(() {
      _reading = true;
      _error = null;
    });
    try {
      if (!Platform.isWindows) {
        throw _PickerError(
          _text(
            'Reference image selection is currently available in the Windows Desktop build.',
            'Referans görsel seçimi şu anda Windows Desktop sürümünde kullanılabilir.',
          ),
        );
      }
      final dialogTitle = _text(
        'Select Video Factory reference images',
        'Video Factory referans görsellerini seç',
      ).replaceAll("'", "''");
      final script = '''
Add-Type -AssemblyName System.Windows.Forms
\$dialog = New-Object System.Windows.Forms.OpenFileDialog
\$dialog.Filter = 'Images (*.jpg;*.jpeg;*.png;*.webp)|*.jpg;*.jpeg;*.png;*.webp'
\$dialog.Multiselect = \$true
\$dialog.CheckFileExists = \$true
\$dialog.CheckPathExists = \$true
\$dialog.Title = '$dialogTitle'
if (\$dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
  \$dialog.FileNames | ForEach-Object { [Console]::WriteLine(\$_) }
}
''';
      final result = await Process.run(
        'powershell.exe',
        <String>[
          '-NoLogo',
          '-NoProfile',
          '-NonInteractive',
          '-STA',
          '-Command',
          script,
        ],
        runInShell: false,
      );
      if (result.exitCode != 0) {
        throw _PickerError(
          _text(
            'Windows could not open the image selector.',
            'Windows görsel seçiciyi açamadı.',
          ),
        );
      }
      final paths = result.stdout
          .toString()
          .split(RegExp(r'\r?\n'))
          .map((value) => value.trim())
          .where((value) => value.isNotEmpty)
          .toList(growable: false);
      if (paths.isEmpty) return;
      await _addPaths(paths);
    } on _PickerError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on FileSystemException {
      if (mounted) {
        setState(
          () => _error = _text(
            'A selected reference image could not be read.',
            'Seçilen referans görsellerden biri okunamadı.',
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = _text(
            'Reference images could not be loaded safely.',
            'Referans görseller güvenli şekilde yüklenemedi.',
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _reading = false);
    }
  }

  Future<void> _addPaths(List<String> paths) async {
    final current = widget.controller.assets.toList(growable: true);
    var totalBytes =
        current.fold<int>(0, (sum, asset) => sum + asset.sizeBytes);
    final knownDigests = current.map((asset) => asset.sha256Hex).toSet();

    for (final path in paths) {
      if (current.length >= maxVideoReferenceAssets) {
        throw _PickerError(
          _text(
            'A video can use at most 20 reference images.',
            'Bir video en fazla 20 referans görsel kullanabilir.',
          ),
        );
      }
      final file = File(path);
      final stat = await file.stat();
      if (stat.type != FileSystemEntityType.file || stat.size <= 0) {
        throw _PickerError(
          _text(
            '${_basename(path)} is not a readable image file.',
            '${_basename(path)} okunabilir bir görsel dosyası değil.',
          ),
        );
      }
      if (stat.size > maxVideoReferenceAssetBytes) {
        throw _PickerError(
          _text(
            '${_basename(path)} is larger than 10 MiB.',
            '${_basename(path)} 10 MiB sınırını aşıyor.',
          ),
        );
      }
      if (totalBytes + stat.size > maxVideoReferenceTotalBytes) {
        throw _PickerError(
          _text(
            'Reference images exceed the 100 MiB request limit.',
            'Referans görseller toplam 100 MiB istek sınırını aşıyor.',
          ),
        );
      }
      final extension = _extension(path);
      final mimeType = switch (extension) {
        'jpg' || 'jpeg' => 'image/jpeg',
        'png' => 'image/png',
        'webp' => 'image/webp',
        _ => throw _PickerError(
            _text(
              '${_basename(path)} is not JPEG, PNG, or WebP.',
              '${_basename(path)} JPEG, PNG veya WebP değil.',
            ),
          ),
      };
      final bytes = await file.readAsBytes();
      if (bytes.length != stat.size) {
        throw _PickerError(
          _text(
            '${_basename(path)} changed while it was being read.',
            '${_basename(path)} okunurken değişti.',
          ),
        );
      }
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
    widget.controller.replace(current);
  }

  void _remove(int index) {
    final values = widget.controller.assets.toList(growable: true)
      ..removeAt(index);
    widget.controller.replace(values);
  }

  void _move(int index, int delta) {
    final target = index + delta;
    final values = widget.controller.assets.toList(growable: true);
    if (target < 0 || target >= values.length) return;
    final item = values.removeAt(index);
    values.insert(target, item);
    widget.controller.replace(values);
  }

  String _roleLabel(BuildContext context, ReferenceAssetRoleDraft role) =>
      context.tr('videoReferences.role.${role.name}');

  Future<void> _edit(int index) async {
    final asset = widget.controller.assets[index];
    var role = asset.role;
    final instruction = TextEditingController(text: asset.instruction ?? '');
    final result = await showDialog<(ReferenceAssetRoleDraft, String?)>(
      context: context,
      builder: (dialogContext) => StatefulBuilder(
        builder: (dialogContext, setDialogState) => AlertDialog(
          title: Text(dialogContext.tr('videoReferences.dialogTitle')),
          content: SizedBox(
            width: 440,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(asset.filename, maxLines: 1, overflow: TextOverflow.ellipsis),
                const SizedBox(height: 12),
                DropdownButtonFormField<ReferenceAssetRoleDraft>(
                  initialValue: role,
                  decoration: InputDecoration(
                    labelText: dialogContext.tr('videoReferences.role'),
                  ),
                  items: ReferenceAssetRoleDraft.values
                      .map(
                        (value) => DropdownMenuItem<ReferenceAssetRoleDraft>(
                          value: value,
                          child: Text(_roleLabel(dialogContext, value)),
                        ),
                      )
                      .toList(growable: false),
                  onChanged: (value) {
                    if (value != null) setDialogState(() => role = value);
                  },
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: instruction,
                  maxLength: 500,
                  maxLines: 3,
                  decoration: InputDecoration(
                    labelText: dialogContext.tr('videoReferences.howUse'),
                    hintText: dialogContext.tr('videoReferences.hint'),
                  ),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(dialogContext).pop(),
              child: Text(dialogContext.tr('videoReferences.cancel')),
            ),
            FilledButton(
              onPressed: () {
                final text = instruction.text.trim();
                Navigator.of(dialogContext).pop(
                  (role, text.isEmpty ? null : text),
                );
              },
              child: Text(dialogContext.tr('videoReferences.save')),
            ),
          ],
        ),
      ),
    );
    instruction.dispose();
    if (result == null) return;
    final values = widget.controller.assets.toList(growable: true);
    values[index] = asset.copyWith(
      role: result.$1,
      instruction: result.$2,
      clearInstruction: result.$2 == null,
    );
    widget.controller.replace(values);
  }

  @override
  Widget build(BuildContext context) {
    final assets = widget.controller.assets;
    final theme = Theme.of(context);
    return Container(
      key: const Key('video-reference-assets'),
      constraints: BoxConstraints(minHeight: widget.compact ? 84 : 106),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          SizedBox(
            width: widget.compact ? 204 : 244,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    const Icon(Icons.image_outlined, size: 16),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        '${context.tr('videoReferences.title')} ${assets.length}/$maxVideoReferenceAssets',
                        style: theme.textTheme.labelMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  context.tr('videoReferences.formats'),
                  style: theme.textTheme.bodySmall?.copyWith(fontSize: 9),
                ),
                const SizedBox(height: 7),
                OutlinedButton.icon(
                  key: const Key('video-reference-add'),
                  onPressed: widget.enabled && !_reading ? _pick : null,
                  icon: _reading
                      ? const SizedBox(
                          width: 13,
                          height: 13,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Icon(Icons.add_photo_alternate_outlined, size: 16),
                  label: Text(
                    _reading
                        ? context.tr('videoReferences.loading')
                        : context.tr('videoReferences.add'),
                  ),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    _error!,
                    maxLines: 3,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.error,
                      fontSize: 9,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: assets.isEmpty
                ? Column(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        context.tr('videoReferences.optional'),
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodySmall,
                      ),
                      const SizedBox(height: 5),
                      Text(
                        context.tr('videoReferences.privacy'),
                        textAlign: TextAlign.center,
                        style: theme.textTheme.bodySmall?.copyWith(fontSize: 9),
                      ),
                    ],
                  )
                : SizedBox(
                    height: widget.compact ? 70 : 88,
                    child: ListView.separated(
                      scrollDirection: Axis.horizontal,
                      itemCount: assets.length,
                      separatorBuilder: (_, _) => const SizedBox(width: 7),
                      itemBuilder: (context, index) {
                        final asset = assets[index];
                        return SizedBox(
                          width: widget.compact ? 92 : 110,
                          child: Card(
                            margin: EdgeInsets.zero,
                            clipBehavior: Clip.antiAlias,
                            child: Stack(
                              children: [
                                Positioned.fill(
                                  child: Image.memory(
                                    asset.bytes,
                                    fit: BoxFit.cover,
                                    gaplessPlayback: true,
                                    cacheWidth: 256,
                                    cacheHeight: 256,
                                    errorBuilder: (_, _, _) => const ColoredBox(
                                      color: Color(0x11000000),
                                      child: Icon(Icons.broken_image_outlined),
                                    ),
                                  ),
                                ),
                                Positioned(
                                  left: 3,
                                  right: 3,
                                  bottom: 3,
                                  child: DecoratedBox(
                                    decoration: BoxDecoration(
                                      color: theme.colorScheme.surface
                                          .withValues(alpha: .92),
                                      borderRadius: BorderRadius.circular(4),
                                    ),
                                    child: Padding(
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 4,
                                        vertical: 2,
                                      ),
                                      child: Text(
                                        _roleLabel(context, asset.role),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: const TextStyle(
                                          fontSize: 8,
                                          fontWeight: FontWeight.w700,
                                        ),
                                      ),
                                    ),
                                  ),
                                ),
                                Positioned(
                                  top: 2,
                                  right: 2,
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      _MiniButton(
                                        tooltip: context.tr(
                                          'videoReferences.moveLeft',
                                        ),
                                        icon: Icons.chevron_left,
                                        enabled: widget.enabled && index > 0,
                                        onPressed: () => _move(index, -1),
                                      ),
                                      _MiniButton(
                                        tooltip: context.tr(
                                          'videoReferences.instructions',
                                        ),
                                        icon: Icons.tune,
                                        enabled: widget.enabled,
                                        onPressed: () => _edit(index),
                                      ),
                                      _MiniButton(
                                        tooltip: context.tr(
                                          'videoReferences.remove',
                                        ),
                                        icon: Icons.close,
                                        enabled: widget.enabled,
                                        onPressed: () => _remove(index),
                                      ),
                                    ],
                                  ),
                                ),
                              ],
                            ),
                          ),
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _MiniButton extends StatelessWidget {
  const _MiniButton({
    required this.tooltip,
    required this.icon,
    required this.enabled,
    required this.onPressed,
  });

  final String tooltip;
  final IconData icon;
  final bool enabled;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Tooltip(
        message: tooltip,
        child: Material(
          color: Theme.of(context).colorScheme.surface.withValues(alpha: .9),
          borderRadius: BorderRadius.circular(4),
          child: InkWell(
            onTap: enabled ? onPressed : null,
            borderRadius: BorderRadius.circular(4),
            child: SizedBox(
              width: 22,
              height: 22,
              child: Icon(icon, size: 13),
            ),
          ),
        ),
      );
}

String _extension(String path) {
  final filename = _basename(path);
  final index = filename.lastIndexOf('.');
  if (index < 0 || index == filename.length - 1) return '';
  return filename.substring(index + 1).toLowerCase();
}

String _basename(String path) {
  final normalized = path.replaceAll('\\', '/');
  final index = normalized.lastIndexOf('/');
  return index < 0 ? normalized : normalized.substring(index + 1);
}

class _PickerError implements Exception {
  const _PickerError(this.message);
  final String message;
}
