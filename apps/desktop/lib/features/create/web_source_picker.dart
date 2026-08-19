import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../web_source/web_source_draft.dart';

const int maxWebSourceArchiveBytes = 64 * 1024 * 1024;

class WebSourcePickerController extends ChangeNotifier {
  WebSourceDraft? _source;

  WebSourceDraft? get source => _source;

  void replace(WebSourceDraft source) {
    _source = source;
    WebSourceSubmissionBus.replace(source);
    notifyListeners();
  }

  void clear() {
    final hadSource = _source != null;
    _source = null;
    WebSourceSubmissionBus.clear();
    if (hadSource) notifyListeners();
  }
}

class WebSourcePicker extends StatefulWidget {
  const WebSourcePicker({
    required this.controller,
    required this.enabled,
    super.key,
  });

  final WebSourcePickerController controller;
  final bool enabled;

  @override
  State<WebSourcePicker> createState() => _WebSourcePickerState();
}

class _WebSourcePickerState extends State<WebSourcePicker> {
  bool _reading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_changed);
  }

  @override
  void didUpdateWidget(covariant WebSourcePicker oldWidget) {
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
        throw _WebSourcePickerError(
          _text(
            'Existing Web source selection is currently available in the Windows Desktop build.',
            'Mevcut Web kaynak seçimi şu anda Windows Desktop sürümünde kullanılabilir.',
          ),
        );
      }
      final dialogTitle = _text(
        'Select an existing Next.js source ZIP',
        'Mevcut Next.js kaynak ZIP dosyasını seç',
      ).replaceAll("'", "''");
      final script = '''
Add-Type -AssemblyName System.Windows.Forms
\$dialog = New-Object System.Windows.Forms.OpenFileDialog
\$dialog.Filter = 'ZIP archive (*.zip)|*.zip'
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
        throw _WebSourcePickerError(
          _text(
            'Windows could not open the Web source selector.',
            'Windows Web kaynak seçiciyi açamadı.',
          ),
        );
      }
      final path = result.stdout.toString().trim();
      if (path.isEmpty) return;
      await _loadPath(path);
    } on _WebSourcePickerError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on FileSystemException {
      if (mounted) {
        setState(
          () => _error = _text(
            'The selected Web source archive could not be read.',
            'Seçilen Web kaynak arşivi okunamadı.',
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = _text(
            'The Web source archive could not be loaded safely.',
            'Web kaynak arşivi güvenli şekilde yüklenemedi.',
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
      throw _WebSourcePickerError(
        _text(
          '$filename is not a readable file.',
          '$filename okunabilir bir dosya değil.',
        ),
      );
    }
    if (_extension(path) != 'zip') {
      throw _WebSourcePickerError(
        _text(
          'Existing Web source must be a ZIP archive.',
          'Mevcut Web kaynağı ZIP arşivi olmalıdır.',
        ),
      );
    }
    if (stat.size > maxWebSourceArchiveBytes) {
      throw _WebSourcePickerError(
        _text(
          'Web source ZIP is larger than 64 MiB.',
          'Web kaynak ZIP dosyası 64 MiB sınırını aşıyor.',
        ),
      );
    }
    final bytes = await file.readAsBytes();
    if (bytes.length != stat.size) {
      throw _WebSourcePickerError(
        _text(
          'The Web source archive changed while it was being read.',
          'Web kaynak arşivi okunurken değişti.',
        ),
      );
    }
    if (!_hasZipSignature(bytes)) {
      throw _WebSourcePickerError(
        _text(
          'The selected bytes do not contain a ZIP signature.',
          'Seçilen dosya ZIP imzası içermiyor.',
        ),
      );
    }
    widget.controller.replace(
      WebSourceDraft(
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
    return Container(
      key: const Key('web-source-picker'),
      width: 430,
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHigh,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              const Icon(Icons.folder_zip_outlined, size: 17),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  _text('Existing Web Source', 'Mevcut Web Kaynağı'),
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (source != null)
                IconButton(
                  key: const Key('web-source-remove'),
                  tooltip: _text('Remove Web source', 'Web kaynağını kaldır'),
                  onPressed: widget.enabled ? widget.controller.clear : null,
                  icon: const Icon(Icons.close_rounded, size: 17),
                ),
            ],
          ),
          const SizedBox(height: 4),
          if (source == null) ...[
            Text(
              _text(
                'Optional. Attach one Next.js/React source ZIP when you want Web Factory to upgrade an existing site or Web App. Imported code is validated server-side before it can enter the governed revision chain.',
                'İsteğe bağlı. Web Factory ile mevcut bir siteyi veya Web uygulamasını yükseltmek için bir Next.js/React kaynak ZIP dosyası ekleyin. İçeri aktarılan kod, yönetilen revizyon zincirine girmeden önce sunucu tarafında doğrulanır.',
              ),
              style: theme.textTheme.bodySmall?.copyWith(fontSize: 9.5),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerLeft,
              child: OutlinedButton.icon(
                key: const Key('web-source-add'),
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
                      : _text('Choose ZIP', 'ZIP Seç'),
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
              _text(
                'The ZIP remains local until submission; only its authenticated wsrc-* ID is placed in the execution intent.',
                'ZIP dosyası gönderime kadar yerelde kalır; yürütme isteğine yalnızca doğrulanmış wsrc-* kimliği eklenir.',
              ),
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

bool _hasZipSignature(List<int> bytes) =>
    bytes.length >= 4 &&
    bytes[0] == 0x50 &&
    bytes[1] == 0x4b &&
    ((bytes[2] == 0x03 && bytes[3] == 0x04) ||
        (bytes[2] == 0x05 && bytes[3] == 0x06) ||
        (bytes[2] == 0x07 && bytes[3] == 0x08));

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

class _WebSourcePickerError implements Exception {
  const _WebSourcePickerError(this.message);

  final String message;
}
