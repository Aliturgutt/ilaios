import 'dart:io';

import 'package:crypto/crypto.dart';
import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../company_knowledge/company_knowledge_draft.dart';

const int maxCompanyKnowledgeDocuments = 10;
const int maxCompanyKnowledgeDocumentBytes = 25 * 1024 * 1024;

class CompanyKnowledgePickerController extends ChangeNotifier {
  List<CompanyKnowledgeDraft> _documents = const <CompanyKnowledgeDraft>[];

  List<CompanyKnowledgeDraft> get documents =>
      List<CompanyKnowledgeDraft>.unmodifiable(_documents);

  void replace(List<CompanyKnowledgeDraft> documents) {
    _documents = List<CompanyKnowledgeDraft>.unmodifiable(documents);
    CompanyKnowledgeSubmissionBus.replace(_documents);
    notifyListeners();
  }

  void clear() {
    final hadDocuments = _documents.isNotEmpty;
    _documents = const <CompanyKnowledgeDraft>[];
    CompanyKnowledgeSubmissionBus.clear();
    if (hadDocuments) notifyListeners();
  }
}

class CompanyKnowledgePicker extends StatefulWidget {
  const CompanyKnowledgePicker({
    required this.controller,
    required this.enabled,
    this.compact = false,
    super.key,
  });

  final CompanyKnowledgePickerController controller;
  final bool enabled;
  final bool compact;

  @override
  State<CompanyKnowledgePicker> createState() => _CompanyKnowledgePickerState();
}

class _CompanyKnowledgePickerState extends State<CompanyKnowledgePicker> {
  bool _reading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    widget.controller.addListener(_changed);
  }

  @override
  void didUpdateWidget(covariant CompanyKnowledgePicker oldWidget) {
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
        throw _CompanyKnowledgePickerError(
          _text(
            'Company-document selection is currently available in the Windows Desktop build.',
            'Şirket belgesi seçimi şu anda Windows Desktop sürümünde kullanılabilir.',
          ),
        );
      }
      final dialogTitle = _text(
        'Select company PDF, DOCX, or ZIP files',
        'Şirket PDF, DOCX veya ZIP dosyalarını seç',
      ).replaceAll("'", "''");
      final script = '''
Add-Type -AssemblyName System.Windows.Forms
\$dialog = New-Object System.Windows.Forms.OpenFileDialog
\$dialog.Filter = 'Company documents (*.pdf;*.docx;*.zip)|*.pdf;*.docx;*.zip'
\$dialog.Multiselect = \$true
\$dialog.CheckFileExists = \$true
\$dialog.CheckPathExists = \$true
\$dialog.Title = '$dialogTitle'
if (\$dialog.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) {
  foreach (\$path in \$dialog.FileNames) { [Console]::WriteLine(\$path) }
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
        throw _CompanyKnowledgePickerError(
          _text(
            'Windows could not open the company-document selector.',
            'Windows şirket belgesi seçiciyi açamadı.',
          ),
        );
      }
      final paths = result.stdout
          .toString()
          .split(RegExp(r'[\r\n]+'))
          .map((value) => value.trim())
          .where((value) => value.isNotEmpty)
          .toList(growable: false);
      if (paths.isEmpty) return;
      await _loadPaths(paths);
    } on _CompanyKnowledgePickerError catch (error) {
      if (mounted) setState(() => _error = error.message);
    } on FileSystemException {
      if (mounted) {
        setState(
          () => _error = _text(
            'A selected company document could not be read.',
            'Seçilen şirket belgelerinden biri okunamadı.',
          ),
        );
      }
    } catch (_) {
      if (mounted) {
        setState(
          () => _error = _text(
            'The company documents could not be loaded safely.',
            'Şirket belgeleri güvenli şekilde yüklenemedi.',
          ),
        );
      }
    } finally {
      if (mounted) setState(() => _reading = false);
    }
  }

  Future<void> _loadPaths(List<String> paths) async {
    final loaded = <CompanyKnowledgeDraft>[];
    final seenDigests = <String>{};
    for (final path in paths.take(maxCompanyKnowledgeDocuments)) {
      final file = File(path);
      final stat = await file.stat();
      final filename = _basename(path);
      if (stat.type != FileSystemEntityType.file || stat.size <= 0) {
        throw _CompanyKnowledgePickerError(
          _text(
            '$filename is not a readable document.',
            '$filename okunabilir bir belge değil.',
          ),
        );
      }
      if (stat.size > maxCompanyKnowledgeDocumentBytes) {
        throw _CompanyKnowledgePickerError(
          _text(
            '$filename is larger than 25 MiB.',
            '$filename 25 MiB sınırını aşıyor.',
          ),
        );
      }
      final extension = _extension(path);
      final mimeType = switch (extension) {
        'pdf' => 'application/pdf',
        'docx' =>
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'zip' => 'application/zip',
        _ => null,
      };
      if (mimeType == null) {
        throw _CompanyKnowledgePickerError(
          _text(
            '$filename must be PDF, DOCX, or ZIP.',
            '$filename PDF, DOCX veya ZIP olmalıdır.',
          ),
        );
      }
      final bytes = await file.readAsBytes();
      if (bytes.length != stat.size) {
        throw _CompanyKnowledgePickerError(
          _text(
            '$filename changed while it was being read.',
            '$filename okunurken değişti.',
          ),
        );
      }
      if (extension == 'pdf' && !_hasPdfSignature(bytes)) {
        throw _CompanyKnowledgePickerError(
          _text(
            '$filename does not contain a PDF signature.',
            '$filename PDF imzası içermiyor.',
          ),
        );
      }
      if ((extension == 'docx' || extension == 'zip') && !_hasZipSignature(bytes)) {
        throw _CompanyKnowledgePickerError(
          _text(
            '$filename does not contain a ZIP signature.',
            '$filename ZIP imzası içermiyor.',
          ),
        );
      }
      final digest = sha256.convert(bytes).toString();
      if (!seenDigests.add(digest)) continue;
      loaded.add(
        CompanyKnowledgeDraft(
          filename: filename,
          mimeType: mimeType,
          bytes: bytes,
          sha256Hex: digest,
        ),
      );
    }
    widget.controller.replace(loaded);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final documents = widget.controller.documents;
    final detail = documents.isEmpty
        ? _text(
            'Persistent company Knowledge · PDF/DOCX/ZIP · up to 10 files · 25 MiB each',
            'Kalıcı şirket Bilgisi · PDF/DOCX/ZIP · en fazla 10 dosya · dosya başına 25 MiB',
          )
        : _text(
            '${documents.length} file(s) staged locally; upload occurs on Start and persists in authenticated company Knowledge.',
            '${documents.length} dosya yerelde hazır; Başlat ile doğrulanmış şirket Bilgisine kalıcı yüklenir.',
          );

    return Container(
      key: const Key('company-knowledge-picker'),
      padding: EdgeInsets.all(widget.compact ? 7 : 10),
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
              const Icon(Icons.description_outlined, size: 16),
              const SizedBox(width: 6),
              Expanded(
                child: Text(
                  _text('Company Knowledge', 'Şirket Bilgisi'),
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: theme.textTheme.labelMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
              if (documents.isNotEmpty)
                IconButton(
                  key: const Key('company-knowledge-clear'),
                  tooltip: _text('Remove staged documents', 'Hazır belgeleri kaldır'),
                  onPressed: widget.enabled ? widget.controller.clear : null,
                  visualDensity: VisualDensity.compact,
                  icon: const Icon(Icons.close_rounded, size: 16),
                ),
              SizedBox(
                height: 30,
                child: OutlinedButton.icon(
                  key: const Key('company-knowledge-add'),
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
                        : _text('PDF / DOCX / ZIP', 'PDF / DOCX / ZIP'),
                    style: const TextStyle(fontSize: 9),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 3),
          Text(
            detail,
            maxLines: widget.compact ? 1 : 2,
            overflow: TextOverflow.ellipsis,
            style: theme.textTheme.bodySmall?.copyWith(fontSize: 8.8),
          ),
          if (documents.isNotEmpty) ...[
            const SizedBox(height: 3),
            Text(
              documents.map((document) => document.filename).join(' · '),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall?.copyWith(
                fontSize: 8.8,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
          if (_error != null) ...[
            const SizedBox(height: 3),
            Text(
              _error!,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.error,
                fontSize: 8.5,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

bool _hasPdfSignature(List<int> bytes) =>
    bytes.length >= 5 &&
    bytes[0] == 0x25 &&
    bytes[1] == 0x50 &&
    bytes[2] == 0x44 &&
    bytes[3] == 0x46 &&
    bytes[4] == 0x2d;

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

class _CompanyKnowledgePickerError implements Exception {
  const _CompanyKnowledgePickerError(this.message);

  final String message;
}
