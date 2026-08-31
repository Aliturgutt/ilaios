import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../source_media/source_media_draft.dart';

const int maxSourceVideoBytes = 128 * 1024 * 1024;

class SourceVideoPickerController extends ChangeNotifier {
  SourceMediaDraft? _source;

  SourceMediaDraft? get source => _source;

  void replace(SourceMediaDraft source) {
    _source = source;
    SourceMediaSubmissionBus.replace(source);
    notifyListeners();
  }

  void clear() {
    final hadSource = _source != null;
    _source = null;
    SourceMediaSubmissionBus.clear();
    if (hadSource) notifyListeners();
  }
}

class SourceVideoPicker extends StatefulWidget {
  const SourceVideoPicker({
    required this.controller,
    required this.enabled,
    this.compact = false,
    super.key,
  });

  final SourceVideoPickerController controller;
  final bool enabled;
  final bool compact;

  @override
  State<SourceVideoPicker> createState() => _SourceVideoPickerState();
}

class _SourceVideoPickerState extends State<SourceVideoPicker> {
  bool _reading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_changed);
  }

  @override
  void didUpdateWidget(covariant SourceVideoPicker oldWidget) {
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
        throw _SourcePickerError(
          _text(
            'Source-video selection is currently available in the Windows Desktop build.',
            'Kaynak video seçimi şu anda Windows Desktop sürümünde kullanılabilir.',
          ),
        );
      }
      final dialogTitle = _text(
        'Select an MP4 source video',
        'MP4 kaynak video seç',
      ).replaceAll("'", "''");
      final script = '''
Add-Type -AssemblyName System.Windows.Forms
\$dialog = New-Object System.Windows.Forms.OpenFileDialog
\$dialog.Filter = 'MP4 video (*.mp4)|*.mp4'
\$dialog.Multiselect = \$false
\$dialog.CheckFileExists = \$true
\$dialog.CheckPathExists = \$true
\$dialog.Title = '$dialogTitle'
if (\$dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
  [Console]::WriteLine(\$dialog.FileName)
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
        throw _SourcePickerError(
          _text(
            'Windows could not open the source-video selector.',
            'Windows kaynak video seçiciyi açamadı.',
          ),
        );
      }
      final path = result.stdout.toString().trim();
      if (path.isEmpty) return;
      await _loadPath(path);
    } on _SourcePickerError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on FileSystemException {
      if (mounted) {
        setState(
          () => _error = _text(
            'The selected source video could not be read.',
            'Seçilen kaynak video okunamadı.',
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = _text(
            'The source video could not be loaded safely.',
            'Kaynak video güvenli şekilde yüklenemedi.',
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _reading = false);
    }
  }

  Future<void> _loadPath(String path) async {
    final file = File(path);
    final stat = await file.stat();
    final filename = _basename(path);
    if (stat.type != FileSystemEntityType.file || stat.size <= 0) {
      throw _SourcePickerError(
        _text(
          '$filename is not a readable video file.',
          '$filename okunabilir bir video dosyası değil.',
        ),
      );
    }
    if (_extension(path) != 'mp4') {
      throw _SourcePickerError(
        _text(
          'Source video must be an MP4 file.',
          'Kaynak video MP4 dosyası olmalıdır.',
        ),
      );
    }
    if (stat.size > maxSourceVideoBytes) {
      throw _SourcePickerError(
        _text(
          'Source video is larger than 128 MiB.',
          'Kaynak video 128 MiB sınırını aşıyor.',
        ),
      );
    }
    final bytes = await file.readAsBytes();
    if (bytes.length != stat.size) {
      throw _SourcePickerError(
        _text(
          'The source video changed while it was being read.',
          'Kaynak video okunurken değişti.',
        ),
      );
    }
    if (!_hasMp4Ftyp(bytes)) {
      throw _SourcePickerError(
        _text(
          'The selected bytes do not contain an MP4 signature.',
          'Seçilen dosya MP4 imzası içermiyor.',
        ),
      );
    }
    widget.controller.replace(
      SourceMediaDraft(
        filename: filename,
        bytes: bytes,
        sha256Hex: sha256.convert(bytes).toString(),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final source = widget.controller.source;
    final theme = Theme.of(context);
    final explanation = _text(
      'Optional. Attach one authenticated MP4 when you want Video Factory to revise or localize an existing video. Server-side ffprobe remains authoritative.',
      'İsteğe bağlı. Video Factory ile mevcut videoyu düzenlemek veya yerelleştirmek için bir doğrulanmış MP4 ekleyin. Sunucu tarafındaki ffprobe nihai doğrulamadır.',
    );
    final localDetail = _text(
      'The file remains local until submission; only its authenticated src-* ID is placed in the execution intent.',
      'Dosya gönderime kadar yerelde kalır; yürütme isteğine yalnızca doğrulanmış src-* kimliği eklenir.',
    );

    return Container(
      key: const Key('source-video-picker'),
      width: 430,
      padding: EdgeInsets.all(widget.compact ? 7 : 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: widget.compact
          ? Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    const Icon(Icons.video_file_outlined, size: 16),
                    const SizedBox(width: 6),
                    Expanded(
                      child: Text(
                        _text('Source Video', 'Kaynak Video'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: theme.textTheme.labelMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (source == null)
                      SizedBox(
                        height: 30,
                        child: OutlinedButton.icon(
                          key: const Key('source-video-add'),
                          onPressed: widget.enabled && !_reading ? _pick : null,
                          icon: _reading
                              ? const SizedBox(
                                  width: 12,
                                  height: 12,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.upload_file_outlined, size: 14),
                          label: Text(
                            _reading
                                ? _text('Reading…', 'Okunuyor…')
                                : _text('Choose MP4', 'MP4 Seç'),
                            style: const TextStyle(fontSize: 9),
                          ),
                        ),
                      )
                    else
                      IconButton(
                        key: const Key('source-video-remove'),
                        tooltip: _text(
                          'Remove source video',
                          'Kaynak videoyu kaldır',
                        ),
                        onPressed: widget.enabled ? widget.controller.clear : null,
                        visualDensity: VisualDensity.compact,
                        icon: const Icon(Icons.close_rounded, size: 16),
                      ),
                  ],
                ),
                const SizedBox(height: 3),
                if (source == null)
                  Tooltip(
                    message: explanation,
                    child: Text(
                      _text(
                        'Optional authenticated MP4 · ffprobe verified',
                        'İsteğe bağlı doğrulanmış MP4 · ffprobe denetimli',
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(fontSize: 8.8),
                    ),
                  )
                else ...[
                  Text(
                    source.filename,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall?.copyWith(
                      fontSize: 9,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Tooltip(
                    message: localDetail,
                    child: Text(
                      '${_formatBytes(source.sizeBytes)} • SHA-256 ${source.sha256Hex.substring(0, 12)}…',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(fontSize: 8.5),
                    ),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 3),
                  Text(
                    _error!,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.error,
                      fontSize: 8.5,
                    ),
                  ),
                ],
              ],
            )
          : Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    const Icon(Icons.video_file_outlined, size: 17),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        _text('Source Video', 'Kaynak Video'),
                        style: theme.textTheme.labelMedium?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    if (source != null)
                      IconButton(
                        key: const Key('source-video-remove'),
                        tooltip: _text(
                          'Remove source video',
                          'Kaynak videoyu kaldır',
                        ),
                        onPressed: widget.enabled ? widget.controller.clear : null,
                        icon: const Icon(Icons.close_rounded, size: 17),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                if (source == null) ...[
                  Text(
                    explanation,
                    style: theme.textTheme.bodySmall?.copyWith(fontSize: 9.5),
                  ),
                  const SizedBox(height: 8),
                  Align(
                    alignment: Alignment.centerLeft,
                    child: OutlinedButton.icon(
                      key: const Key('source-video-add'),
                      onPressed: widget.enabled && !_reading ? _pick : null,
                      icon: _reading
                          ? const SizedBox(
                              width: 13,
                              height: 13,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.upload_file_outlined, size: 16),
                      label: Text(
                        _reading
                            ? _text('Reading…', 'Okunuyor…')
                            : _text('Choose MP4', 'MP4 Seç'),
                      ),
                    ),
                  ),
                ] else ...[
                  Text(
                    source.filename,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    '${_formatBytes(source.sizeBytes)} • SHA-256 ${source.sha256Hex.substring(0, 12)}…',
                    style: theme.textTheme.bodySmall?.copyWith(fontSize: 9),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    localDetail,
                    style: theme.textTheme.bodySmall?.copyWith(fontSize: 9),
                  ),
                ],
                if (_error != null) ...[
                  const SizedBox(height: 6),
                  Text(
                    _error!,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.error,
                      fontSize: 9,
                    ),
                  ),
                ],
              ],
            ),
    );
  }
}

bool _hasMp4Ftyp(List<int> bytes) =>
    bytes.length >= 12 &&
    bytes[4] == 0x66 &&
    bytes[5] == 0x74 &&
    bytes[6] == 0x79 &&
    bytes[7] == 0x70;

String _basename(String path) {
  final normalized = path.replaceAll('\\', '/');
  final index = normalized.lastIndexOf('/');
  return index < 0 ? normalized : normalized.substring(index + 1);
}

String _extension(String path) {
  final name = _basename(path).toLowerCase();
  final index = name.lastIndexOf('.');
  return index < 0 ? '' : name.substring(index + 1);
}

String _formatBytes(int bytes) {
  if (bytes >= 1024 * 1024) {
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MiB';
  }
  if (bytes >= 1024) return '${(bytes / 1024).toStringAsFixed(1)} KiB';
  return '$bytes B';
}

class _SourcePickerError implements Exception {
  const _SourcePickerError(this.message);

  final String message;
}
