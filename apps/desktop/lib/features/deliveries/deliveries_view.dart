import 'package:flutter/material.dart';

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
      setState(() => _message = 'Saved verified artifact to $path');
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _message = error.toString());
    } finally {
      if (mounted) setState(() => _activeDigest = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final records = widget.snapshot.evidenceRecords.reversed.take(100).toList();
    return SingleChildScrollView(
      padding: const EdgeInsets.all(28),
      child: Align(
        alignment: Alignment.topLeft,
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1200),
          child: Card(
            child: Padding(
              padding: const EdgeInsets.all(26),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(Icons.inventory_2_outlined, color: IlaiosTheme.cyan),
                      SizedBox(width: 10),
                      Text(
                        'Deliveries',
                        style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(widget.status,
                      style: const TextStyle(color: IlaiosTheme.muted)),
                  const SizedBox(height: 12),
                  const Text(
                    'Only artifacts present in the verified evidence chain are offered here. Saving is an explicit user action; Desktop retrieves bytes from the authoritative evidence store and never fabricates a finished product.',
                    style: TextStyle(color: IlaiosTheme.muted, height: 1.5),
                  ),
                  const SizedBox(height: 22),
                  if (records.isEmpty)
                    const Text(
                      'No verified deliverable artifacts are available yet.',
                      style: TextStyle(color: IlaiosTheme.muted),
                    )
                  else
                    for (final record in records)
                      _DeliveryRow(
                        record: record,
                        saving: _activeDigest == record.artifactDigest,
                        enabled: widget.onSaveArtifact != null && _activeDigest == null,
                        onSave: () => _save(record),
                      ),
                  if (_message case final message?) ...[
                    const SizedBox(height: 18),
                    SelectableText(
                      message,
                      key: const Key('delivery-message'),
                      style: const TextStyle(color: IlaiosTheme.muted),
                    ),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _DeliveryRow extends StatelessWidget {
  const _DeliveryRow({
    required this.record,
    required this.saving,
    required this.enabled,
    required this.onSave,
  });

  final EvidenceRecord record;
  final bool saving;
  final bool enabled;
  final VoidCallback onSave;

  String _short(String value) =>
      value.length <= 20 ? value : '${value.substring(0, 20)}…';

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: IlaiosTheme.canvas,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: IlaiosTheme.border),
        ),
        child: Row(
          children: [
            const Icon(Icons.verified_outlined, color: IlaiosTheme.success),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(record.action,
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(
                    'Execution ${record.executionId} • SHA-256 ${_short(record.artifactDigest)}',
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      color: IlaiosTheme.muted,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 12),
            FilledButton.icon(
              key: ValueKey('save-artifact-${record.sequence}'),
              onPressed: enabled ? onSave : null,
              icon: saving
                  ? const SizedBox(
                      width: 15,
                      height: 15,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.download_outlined),
              label: Text(saving ? 'Saving…' : 'Save'),
            ),
          ],
        ),
      );
}
