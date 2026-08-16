import 'dart:io';

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_surface_catalog.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';

class DeliveriesView extends StatefulWidget {
  const DeliveriesView({
    required this.snapshot,
    required this.status,
    this.onSaveArtifact,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;

  @override
  State<DeliveriesView> createState() => _DeliveriesViewState();
}

class _DeliveriesViewState extends State<DeliveriesView> {
  String? _activeDigest;
  String? _message;

  Future<void> _save(EvidenceRecord record) async {
    final callback = widget.onSaveArtifact;
    if (callback == null || _activeDigest != null) return;
    setState(() {
      _activeDigest = record.artifactDigest;
      _message = null;
    });
    try {
      final path = await callback(record);
      if (!mounted) return;
      setState(() => _message = '${_surface(context, 'deliveries.savedPrefix')} $path');
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _message = error.toString());
    } finally {
      if (mounted) setState(() => _activeDigest = null);
    }
  }

  File _localDeliveryFile(EvidenceRecord record) {
    final userProfile = Platform.environment['USERPROFILE']?.trim();
    final localAppData = Platform.environment['LOCALAPPDATA']?.trim();
    final separator = Platform.pathSeparator;
    final rootPath = userProfile?.isNotEmpty == true
        ? '$userProfile${separator}Downloads${separator}ILAIOS'
        : (localAppData?.isNotEmpty == true
            ? '$localAppData${separator}ILAIOS${separator}Deliveries'
            : '${Directory.systemTemp.path}${separator}ILAIOS${separator}Deliveries');
    final safeExecution =
        record.executionId.replaceAll(RegExp(r'[^A-Za-z0-9._-]'), '_');
    final extension =
        record.action.toLowerCase().contains('video') ? '.mp4' : '.bin';
    final digestPrefix = record.artifactDigest.length <= 16
        ? record.artifactDigest
        : record.artifactDigest.substring(0, 16);
    return File('$rootPath$separator${'ILAIOS-$safeExecution-$digestPrefix$extension'}');
  }

  Future<void> _deleteLocalCopy(EvidenceRecord record) async {
    if (_activeDigest != null) return;
    final confirmed = await showDialog<bool>(
          context: context,
          builder: (dialogContext) => AlertDialog(
            icon: const Icon(Icons.delete_outline, color: IlaiosTheme.danger),
            title: Text(
              _isTr(context) ? 'Yerel kopya silinsin mi?' : 'Delete local copy?',
            ),
            content: Text(
              _isTr(context)
                  ? 'Yalnızca bilgisayarına kaydedilmiş çıktı dosyası silinir. ILAIOS kanıt kaydı, SHA-256 ve provenance zinciri korunur.'
                  : 'Only the delivery file saved on this computer is deleted. The ILAIOS evidence record, SHA-256 and provenance chain are retained.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(dialogContext).pop(false),
                child: Text(_isTr(context) ? 'Vazgeç' : 'Cancel'),
              ),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: IlaiosTheme.danger),
                onPressed: () => Navigator.of(dialogContext).pop(true),
                icon: const Icon(Icons.delete_outline),
                label: Text(_isTr(context) ? 'Yerel kopyayı sil' : 'Delete local copy'),
              ),
            ],
          ),
        ) ??
        false;
    if (!confirmed || !mounted) return;

    setState(() {
      _activeDigest = record.artifactDigest;
      _message = null;
    });
    try {
      final file = _localDeliveryFile(record);
      if (await file.exists()) {
        await file.delete();
        if (!mounted) return;
        setState(() {
          _message = _isTr(context)
              ? 'Yerel çıktı silindi. Doğrulanmış kanıt kaydı korunuyor.'
              : 'Local delivery deleted. Verified evidence is retained.';
        });
      } else if (mounted) {
        setState(() {
          _message = _isTr(context)
              ? 'Bu çıktı için kaydedilmiş yerel dosya bulunamadı. Kanıt kaydı değişmedi.'
              : 'No saved local file was found for this delivery. The evidence record was unchanged.';
        });
      }
    } on FileSystemException catch (error) {
      if (!mounted) return;
      setState(() {
        _message = _isTr(context)
            ? 'Yerel dosya silinemedi: ${error.message}'
            : 'The local file could not be deleted: ${error.message}';
      });
    } finally {
      if (mounted) setState(() => _activeDigest = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final records = widget.snapshot.evidenceRecords.reversed.take(100).toList();
    final scheme = Theme.of(context).colorScheme;
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1240),
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: scheme.surfaceContainerLow,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: scheme.outlineVariant),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Row(
                  children: [
                    Container(
                      width: 44,
                      height: 44,
                      decoration: BoxDecoration(
                        color: IlaiosTheme.enterpriseCyan.withValues(alpha: .12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: const Icon(
                        Icons.inventory_2_outlined,
                        color: IlaiosTheme.enterpriseCyan,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _surface(context, 'deliveries.title'),
                            style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                  fontWeight: FontWeight.w800,
                                ),
                          ),
                          const SizedBox(height: 3),
                          Text(
                            _localizedStatus(context, widget.status),
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ],
                      ),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: IlaiosTheme.coreBlue.withValues(alpha: .08),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(
                          color: IlaiosTheme.coreBlue.withValues(alpha: .25),
                        ),
                      ),
                      child: Text(
                        '${records.length} ${_isTr(context) ? 'doğrulanmış' : 'verified'}',
                        style: const TextStyle(
                          color: IlaiosTheme.coreBlue,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 14),
                Text(
                  _surface(context, 'deliveries.note'),
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 20),
                if (records.isEmpty)
                  _DeliveryEmptyState(enabled: widget.onSaveArtifact != null)
                else
                  for (final record in records)
                    _DeliveryRow(
                      record: record,
                      saving: _activeDigest == record.artifactDigest,
                      enabled: widget.onSaveArtifact != null && _activeDigest == null,
                      deleteEnabled: _activeDigest == null,
                      onSave: () => _save(record),
                      onDelete: () => _deleteLocalCopy(record),
                    ),
                if (_message case final message?) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(13),
                    decoration: BoxDecoration(
                      color: IlaiosTheme.enterpriseCyan.withValues(alpha: .07),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(
                        color: IlaiosTheme.enterpriseCyan.withValues(alpha: .28),
                      ),
                    ),
                    child: SelectableText(
                      message,
                      key: const Key('delivery-message'),
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _DeliveryEmptyState extends StatelessWidget {
  const _DeliveryEmptyState({required this.enabled});

  final bool enabled;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(24),
        decoration: BoxDecoration(
          color: IlaiosTheme.coreBlue.withValues(alpha: .045),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: IlaiosTheme.coreBlue.withValues(alpha: .20)),
        ),
        child: Row(
          children: [
            Container(
              width: 54,
              height: 54,
              decoration: BoxDecoration(
                color: IlaiosTheme.coreBlue.withValues(alpha: .12),
                borderRadius: BorderRadius.circular(15),
              ),
              child: const Icon(
                Icons.inventory_2_outlined,
                color: IlaiosTheme.coreBlue,
                size: 28,
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _surface(context, 'deliveries.empty'),
                    style: const TextStyle(fontWeight: FontWeight.w800),
                  ),
                  const SizedBox(height: 5),
                  Text(
                    _isTr(context)
                        ? 'Bir yürütme doğrulanmış çıktı ürettiğinde dosya, SHA-256 kimliği ve açık kaydetme eylemi burada görünür.'
                        : 'When an execution produces a verified artifact, its file identity, SHA-256 digest and explicit save action appear here.',
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            Icon(
              enabled ? Icons.verified_outlined : Icons.lock_outline,
              color: enabled ? IlaiosTheme.enterpriseCyan : Theme.of(context).colorScheme.outline,
            ),
          ],
        ),
      );
}

class _DeliveryRow extends StatefulWidget {
  const _DeliveryRow({
    required this.record,
    required this.saving,
    required this.enabled,
    required this.deleteEnabled,
    required this.onSave,
    required this.onDelete,
  });

  final EvidenceRecord record;
  final bool saving;
  final bool enabled;
  final bool deleteEnabled;
  final VoidCallback onSave;
  final VoidCallback onDelete;

  @override
  State<_DeliveryRow> createState() => _DeliveryRowState();
}

class _DeliveryRowState extends State<_DeliveryRow> {
  bool hovered = false;

  String _short(String value) =>
      value.length <= 20 ? value : '${value.substring(0, 20)}…';

  @override
  Widget build(BuildContext context) => MouseRegion(
        onEnter: (_) => setState(() => hovered = true),
        onExit: (_) => setState(() => hovered = false),
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          padding: const EdgeInsets.all(15),
          decoration: BoxDecoration(
            color: hovered
                ? IlaiosTheme.enterpriseCyan.withValues(alpha: .055)
                : Theme.of(context).colorScheme.surfaceContainerLowest,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: hovered
                  ? IlaiosTheme.enterpriseCyan.withValues(alpha: .42)
                  : Theme.of(context).colorScheme.outlineVariant,
            ),
          ),
          child: Row(
            children: [
              Container(
                width: 42,
                height: 42,
                decoration: BoxDecoration(
                  color: IlaiosTheme.success.withValues(alpha: .10),
                  borderRadius: BorderRadius.circular(11),
                ),
                child: const Icon(Icons.verified_outlined, color: IlaiosTheme.success),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.record.action,
                      style: const TextStyle(fontWeight: FontWeight.w800),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_surface(context, 'deliveries.execution')} ${widget.record.executionId} • SHA-256 ${_short(widget.record.artifactDigest)}',
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  FilledButton.icon(
                    key: ValueKey('save-artifact-${widget.record.sequence}'),
                    onPressed: widget.enabled ? widget.onSave : null,
                    icon: widget.saving
                        ? const SizedBox(
                            width: 15,
                            height: 15,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.download_outlined),
                    label: Text(
                      widget.saving
                          ? _surface(context, 'deliveries.saving')
                          : _surface(context, 'deliveries.save'),
                    ),
                  ),
                  OutlinedButton.icon(
                    key: ValueKey('delete-local-artifact-${widget.record.sequence}'),
                    style: OutlinedButton.styleFrom(
                      foregroundColor: IlaiosTheme.danger,
                      side: BorderSide(
                        color: IlaiosTheme.danger.withValues(alpha: .55),
                      ),
                    ),
                    onPressed: widget.deleteEnabled ? widget.onDelete : null,
                    icon: const Icon(Icons.delete_outline),
                    label: Text(_isTr(context) ? 'Yerel kopyayı sil' : 'Delete local copy'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
}

String _localizedStatus(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    _ => value,
  };
}

bool _isTr(BuildContext context) => context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;
