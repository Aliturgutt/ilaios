import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';

/// Reference-faithful Kanıtlar / Evidence surface.
///
/// The supplied dark/light screenshots define layout and visual hierarchy only.
/// Runtime values are never copied from those screenshots. Every populated row
/// comes from [OperationalSnapshot.evidenceRecords]. Fields that are not part of
/// the authoritative evidence contract are rendered as unavailable rather than
/// fabricated.
class ReferenceEvidenceView extends StatefulWidget {
  const ReferenceEvidenceView({
    required this.snapshot,
    required this.status,
    this.onSaveArtifact,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;

  @override
  State<ReferenceEvidenceView> createState() => _ReferenceEvidenceViewState();
}

class _ReferenceEvidenceViewState extends State<ReferenceEvidenceView> {
  String _activeTab = 'all';
  int? _selectedSequence;
  String? _savingDigest;
  String? _message;

  List<EvidenceRecord> get _records => widget.snapshot.evidenceRecords.reversed
      .take(100)
      .toList(growable: false);

  EvidenceRecord? get _selected {
    final records = _records;
    final sequence = _selectedSequence;
    if (records.isEmpty || sequence == null) return null;
    for (final record in records) {
      if (record.sequence == sequence) return record;
    }
    return null;
  }

  List<EvidenceRecord> get _visibleRecords {
    final records = _records;
    if (_activeTab == 'all' || _activeTab == 'verified') return records;
    return records
        .where((record) => _categoryCode(record) == _activeTab)
        .toList(growable: false);
  }

  void _clearFilters() {
    setState(() => _activeTab = 'all');
  }

  void _select(EvidenceRecord record) {
    if (_selectedSequence == record.sequence) return;
    setState(() => _selectedSequence = record.sequence);
  }

  Future<void> _saveSelected() async {
    final record = _selected;
    final callback = widget.onSaveArtifact;
    if (record == null || callback == null || _savingDigest != null) return;
    setState(() {
      _savingDigest = record.artifactDigest;
      _message = null;
    });
    try {
      final path = await callback(record);
      if (!mounted) return;
      setState(() {
        _message = _copy(
          context,
          'Evidence artifact saved to $path',
          'Kanıt artefaktı $path konumuna kaydedildi',
        );
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _message = error.toString());
    } finally {
      if (mounted) setState(() => _savingDigest = null);
    }
  }

  void _showSelected() {
    final record = _selected;
    if (record == null) return;
    showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(record.action),
        content: SizedBox(
          width: 620,
          child: SelectableText(
            '${_copy(context, 'Sequence', 'Sıra')}: ${record.sequence}\n'
            '${_copy(context, 'Execution', 'Yürütme')}: ${record.executionId}\n'
            '${_copy(context, 'Artifact digest', 'Artefakt özeti')}: ${record.artifactDigest}\n'
            '${_copy(context, 'Previous hash', 'Önceki hash')}: ${record.previousHash.isEmpty ? '—' : record.previousHash}\n'
            '${_copy(context, 'Record hash', 'Kayıt hash')}: ${record.recordHash}',
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: Text(_copy(context, 'Close', 'Kapat')),
          ),
        ],
      ),
    );
  }

  void _confirmVerified() {
    final record = _selected;
    if (record == null) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(
          content: Text(
            _copy(
              context,
              'Record #${record.sequence} is present in the authoritative verified evidence feed.',
              '#${record.sequence} numaralı kayıt yetkili doğrulanmış kanıt akışında mevcut.',
            ),
          ),
        ),
      );
  }

  @override
  Widget build(BuildContext context) {
    final records = _records;
    final selected = _selected;
    final visibleRecords = _visibleRecords;
    final chainIssues = _chainIssueCount(records);

    return Container(
      key: const Key('reference-evidence-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(18, 10, 18, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _Header(total: records.length, status: widget.status),
          if (records.isNotEmpty) ...[
            const SizedBox(height: 8),
            _MetricStrip(
              total: records.length,
              chainIssues: chainIssues,
            ),
          ],
          const SizedBox(height: 8),
          _EvidenceTabs(
            activeTab: _activeTab,
            hasFilters: _activeTab != 'all',
            onChanged: (value) => setState(() => _activeTab = value),
            onClear: _clearFilters,
            onExport: selected != null && widget.onSaveArtifact != null
                ? _saveSelected
                : null,
            exporting: _savingDigest != null,
          ),
          const SizedBox(height: 6),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final showRightRail = constraints.maxWidth >= 1060;
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          Expanded(
                            child: _EvidenceTable(
                              records: visibleRecords,
                              totalCount: records.length,
                              selectedSequence: selected?.sequence,
                              onSelected: _select,
                            ),
                          ),

                        ],
                      ),
                    ),
                    if (showRightRail && selected != null) ...[
                      const SizedBox(width: 12),
                      SizedBox(
                        width: 390,
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            Expanded(
                              child: _SelectedEvidence(
                                record: selected,
                                saving: _savingDigest != null,
                                saveEnabled: widget.onSaveArtifact != null,
                                onView: _showSelected,
                                onSave: _saveSelected,
                                onVerify: _confirmVerified,
                              ),
                            ),
                            const SizedBox(height: 8),
                            SizedBox(
                              height: 164,
                              child: _InfoCard(
                                title: _copy(context, 'Audit Trail', 'Denetim İzi'),
                                child: _AuditTrail(records: records),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ],
                );
              },
            ),
          ),
          if (_message case final message?) ...[
            const SizedBox(height: 6),
            _InlineMessage(message: message),
          ],
        ],
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.total, required this.status});

  final int total;
  final String status;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 50,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _copy(context, 'Evidence', 'Kanıtlar'),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _copy(
                      context,
                      'Inspect authoritative verification records, hashes and audit lineage.',
                      'Yetkili doğrulama kayıtlarını, hash’leri ve denetim zincirini inceleyin.',
                    ),
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(fontSize: 10.2),
                  ),
                ],
              ),
            ),
            _StatusBadge(status: status, total: total),
          ],
        ),
      );
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status, required this.total});

  final String status;
  final int total;

  @override
  Widget build(BuildContext context) {
    final connected = _statusConnected(status);
    final color = connected ? IlaiosTheme.success : IlaiosTheme.warning;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: color.withValues(alpha: .08),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: .22)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            connected ? Icons.verified_outlined : Icons.info_outline_rounded,
            size: 14,
            color: color,
          ),
          const SizedBox(width: 6),
          Text(
            connected
                ? _copy(context, '$total verified records', '$total doğrulanmış kayıt')
                : _copy(context, 'Evidence feed unavailable', 'Kanıt akışı kullanılamıyor'),
            style: TextStyle(fontSize: 8.8, fontWeight: FontWeight.w700, color: color),
          ),
        ],
      ),
    );
  }
}

class _MetricStrip extends StatelessWidget {
  const _MetricStrip({required this.total, required this.chainIssues});

  final int total;
  final int chainIssues;

  @override
  Widget build(BuildContext context) {
    final metrics = <({IconData icon, Color color, String label, String value, String note})>[
      (
        icon: Icons.folder_outlined,
        color: IlaiosTheme.coreBlue,
        label: _copy(context, 'Total Evidence', 'Toplam Kanıt'),
        value: '$total',
        note: _copy(context, 'Authoritative records', 'Yetkili kayıtlar'),
      ),
      (
        icon: Icons.check_circle_outline_rounded,
        color: IlaiosTheme.success,
        label: _copy(context, 'Verified', 'Doğrulandı'),
        value: '$total',
        note: _copy(context, 'Verified evidence feed', 'Doğrulanmış kanıt akışı'),
      ),
      (
        icon: Icons.schedule_outlined,
        color: IlaiosTheme.warning,
        label: _copy(context, 'Reviewed', 'İncelemede'),
        value: '—',
        note: _copy(context, 'Not in evidence contract', 'Kanıt sözleşmesinde yok'),
      ),
      (
        icon: Icons.cancel_outlined,
        color: IlaiosTheme.danger,
        label: _copy(context, 'Failed', 'Başarısız'),
        value: '—',
        note: _copy(context, 'Not in evidence contract', 'Kanıt sözleşmesinde yok'),
      ),
      (
        icon: Icons.shield_outlined,
        color: const Color(0xFF9C5CFF),
        label: _copy(context, 'Chain Integrity', 'Zincir Bütünlüğü'),
        value: total == 0 ? '—' : (chainIssues == 0 ? '100%' : '⚠ $chainIssues'),
        note: total == 0
            ? _copy(context, 'No records', 'Kayıt yok')
            : _copy(context, 'Local linkage check', 'Yerel bağlantı kontrolü'),
      ),
      (
        icon: Icons.speed_outlined,
        color: IlaiosTheme.enterpriseCyan,
        label: _copy(context, 'Average Processing Time', 'Ortalama İşlem Süresi'),
        value: '—',
        note: _copy(context, 'Timing unavailable', 'Süre verisi yok'),
      ),
    ];

    return SizedBox(
      key: const Key('evidence-kpis'),
      height: 82,
      child: Row(
        children: [
          for (var index = 0; index < metrics.length; index++) ...[
            if (index > 0) const SizedBox(width: 8),
            Expanded(child: _MetricCard(metric: metrics[index])),
          ],
        ],
      ),
    );
  }
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({required this.metric});

  final ({IconData icon, Color color, String label, String value, String note}) metric;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
        decoration: _cardDecoration(context, radius: 7),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: metric.color.withValues(alpha: .11),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(metric.icon, color: metric.color, size: 21),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    metric.label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context)
                        .textTheme
                        .labelSmall
                        ?.copyWith(fontSize: 8.2),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    metric.value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w700,
                      height: 1,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    metric.note,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 7.3,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _EvidenceTabs extends StatelessWidget {
  const _EvidenceTabs({
    required this.activeTab,
    required this.hasFilters,
    required this.onChanged,
    required this.onClear,
    required this.onExport,
    required this.exporting,
  });

  final String activeTab;
  final bool hasFilters;
  final ValueChanged<String> onChanged;
  final VoidCallback onClear;
  final VoidCallback? onExport;
  final bool exporting;

  @override
  Widget build(BuildContext context) {
    final tabs = <({String id, String label})>[
      (id: 'all', label: _copy(context, 'All', 'Tümü')),
      (id: 'verified', label: _copy(context, 'Verified', 'Doğrulandı')),
      (id: 'test', label: _copy(context, 'Test', 'Test')),
      (id: 'security', label: _copy(context, 'Security', 'Güvenlik')),
      (id: 'deployment', label: _copy(context, 'Deployment', 'Dağıtım')),
      (id: 'policy', label: _copy(context, 'Policy', 'Politika')),
      (id: 'other', label: _copy(context, 'Other', 'Diğer')),
    ];

    return Container(
      key: const Key('evidence-tabs'),
      height: 38,
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
      ),
      child: Row(
        children: [
          Expanded(
            child: Row(
              children: [
                for (final tab in tabs)
                  InkWell(
                    onTap: () => onChanged(tab.id),
                    child: Container(
                      margin: const EdgeInsets.only(right: 2),
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        border: Border(
                          bottom: BorderSide(
                            color: activeTab == tab.id
                                ? IlaiosTheme.coreBlue
                                : Colors.transparent,
                            width: 2,
                          ),
                        ),
                      ),
                      child: Text(
                        tab.label,
                        style: TextStyle(
                          fontSize: 8.6,
                          fontWeight: activeTab == tab.id
                              ? FontWeight.w700
                              : FontWeight.w500,
                          color: activeTab == tab.id
                              ? IlaiosTheme.coreBlue
                              : Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
          ),
          if (hasFilters) ...[
            _ToolbarButton(
              icon: Icons.filter_alt_off_outlined,
              label: _copy(context, 'Clear Filters', 'Filtreleri Temizle'),
              onPressed: onClear,
            ),
            const SizedBox(width: 7),
          ],
          _ToolbarButton(
            icon: exporting ? Icons.hourglass_top_rounded : Icons.download_outlined,
            label: _copy(context, 'Export', 'Dışa Aktar'),
            onPressed: exporting ? null : onExport,
          ),
        ],
      ),
    );
  }
}

class _ToolbarButton extends StatelessWidget {
  const _ToolbarButton({
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 30,
        child: OutlinedButton.icon(
          onPressed: onPressed,
          icon: Icon(icon, size: 14),
          label: Text(label),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            textStyle: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600),
          ),
        ),
      );
}

class _EvidenceTable extends StatelessWidget {
  const _EvidenceTable({
    required this.records,
    required this.totalCount,
    required this.selectedSequence,
    required this.onSelected,
  });

  final List<EvidenceRecord> records;
  final int totalCount;
  final int? selectedSequence;
  final ValueChanged<EvidenceRecord> onSelected;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('evidence-table'),
        decoration: _cardDecoration(context, radius: 7),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const _EvidenceTableHeader(),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            Expanded(
              child: records.isEmpty
                  ? _EmptyTable()
                  : ListView.builder(
                      padding: EdgeInsets.zero,
                      itemCount: math.min(records.length, 10),
                      itemExtent: 42,
                      itemBuilder: (context, index) {
                        final record = records[index];
                        return _EvidenceTableRow(
                          record: record,
                          selected: record.sequence == selectedSequence,
                          onTap: () => onSelected(record),
                        );
                      },
                    ),
            ),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            SizedBox(
              height: 40,
              child: Row(
                children: [
                  const SizedBox(width: 11),
                  Text(
                    _copy(
                      context,
                      '${records.isEmpty ? 0 : 1} - ${math.min(records.length, 10)} / $totalCount results',
                      '${records.isEmpty ? 0 : 1} - ${math.min(records.length, 10)} / $totalCount sonuç',
                    ),
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 8.1),
                  ),
                  const Spacer(),
                  const _PageBox(label: '‹'),
                  const SizedBox(width: 5),
                  const _PageBox(label: '1', selected: true),
                  const SizedBox(width: 5),
                  const _PageBox(label: '›'),
                  const SizedBox(width: 8),
                  Container(
                    height: 26,
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                      borderRadius: BorderRadius.circular(4),
                    ),
                    child: Text(
                      _copy(context, '10 / page', '10 / sayfa'),
                      style: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600),
                    ),
                  ),
                  const SizedBox(width: 10),
                ],
              ),
            ),
          ],
        ),
      );
}

class _EvidenceTableHeader extends StatelessWidget {
  const _EvidenceTableHeader();

  @override
  Widget build(BuildContext context) => Container(
        height: 34,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        child: const Row(
          children: [
            Expanded(flex: 28, child: _HeaderCell('Kanıt Adı')),
            Expanded(flex: 15, child: _HeaderCell('Kategori')),
            Expanded(flex: 20, child: _HeaderCell('Kaynak')),
            Expanded(flex: 16, child: _HeaderCell('Durum')),
            Expanded(flex: 14, child: _HeaderCell('Güven')),
            Expanded(flex: 13, child: _HeaderCell('Sıra')),
            SizedBox(width: 26),
          ],
        ),
      );
}

class _HeaderCell extends StatelessWidget {
  const _HeaderCell(this.label);
  final String label;

  @override
  Widget build(BuildContext context) => Text(
        label,
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(fontSize: 7.8),
      );
}

class _EvidenceTableRow extends StatelessWidget {
  const _EvidenceTableRow({
    required this.record,
    required this.selected,
    required this.onTap,
  });

  final EvidenceRecord record;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final category = _categoryCode(record);
    final categoryColor = _categoryColor(category);
    return Material(
      color: selected
          ? IlaiosTheme.coreBlue.withValues(alpha: .08)
          : Colors.transparent,
      child: InkWell(
        key: ValueKey('evidence-row-${record.sequence}'),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: Theme.of(context).colorScheme.outlineVariant.withValues(alpha: .65),
              ),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                flex: 28,
                child: Row(
                  children: [
                    Icon(Icons.description_outlined, size: 15, color: IlaiosTheme.coreBlue),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        record.action,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 8.7, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                flex: 15,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: _Pill(
                    label: _categoryLabel(context, category),
                    color: categoryColor,
                  ),
                ),
              ),
              Expanded(
                flex: 20,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _short(record.executionId, 18),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 8.2),
                    ),
                    Text(
                      _short(record.artifactDigest, 18),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        fontSize: 7.1,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                flex: 16,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: _Pill(
                    label: _copy(context, 'Verified', 'Doğrulandı'),
                    color: IlaiosTheme.success,
                  ),
                ),
              ),
              Expanded(
                flex: 14,
                child: Row(
                  children: [
                    const Icon(Icons.verified_user_outlined, size: 13, color: IlaiosTheme.success),
                    const SizedBox(width: 4),
                    Text(
                      _copy(context, 'verified', 'doğrulandı'),
                      style: const TextStyle(fontSize: 7.9, fontWeight: FontWeight.w600),
                    ),
                  ],
                ),
              ),
              Expanded(
                flex: 13,
                child: Text(
                  '#${record.sequence}',
                  style: const TextStyle(fontSize: 8.1),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EmptyTable extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.fact_check_outlined,
              size: 34,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 8),
            Text(
              _copy(context, 'No verified evidence records', 'Doğrulanmış kanıt kaydı yok'),
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 3),
            Text(
              _copy(
                context,
                'Records appear here only after the authoritative runtime returns verified evidence.',
                'Kayıtlar yalnızca yetkili çalışma zamanı doğrulanmış kanıt döndürdüğünde burada görünür.',
              ),
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 8.2),
            ),
          ],
        ),
      );
}

class _SelectedEvidence extends StatelessWidget {
  const _SelectedEvidence({
    required this.record,
    required this.saving,
    required this.saveEnabled,
    required this.onView,
    required this.onSave,
    required this.onVerify,
  });

  final EvidenceRecord? record;
  final bool saving;
  final bool saveEnabled;
  final VoidCallback onView;
  final VoidCallback onSave;
  final VoidCallback onVerify;

  @override
  Widget build(BuildContext context) {
    final record = this.record;
    return Container(
      key: const Key('selected-evidence-panel'),
      decoration: _cardDecoration(context, radius: 7),
      child: record == null
          ? _EmptySelected()
          : Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(12, 11, 12, 8),
                  child: Text(
                    _copy(context, 'Selected Evidence', 'Seçili Kanıt'),
                    style: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w700),
                  ),
                ),
                Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.all(12),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Container(
                              width: 42,
                              height: 42,
                              decoration: BoxDecoration(
                                color: IlaiosTheme.coreBlue.withValues(alpha: .10),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Icon(
                                Icons.description_outlined,
                                color: IlaiosTheme.coreBlue,
                                size: 23,
                              ),
                            ),
                            const SizedBox(width: 9),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Row(
                                    children: [
                                      Expanded(
                                        child: Text(
                                          record.action,
                                          maxLines: 2,
                                          overflow: TextOverflow.ellipsis,
                                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
                                        ),
                                      ),
                                      const SizedBox(width: 7),
                                      _Pill(
                                        label: _copy(context, 'Verified', 'Doğrulandı'),
                                        color: IlaiosTheme.success,
                                      ),
                                    ],
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'ID: ${_short(record.recordHash, 24)}',
                                    maxLines: 1,
                                    overflow: TextOverflow.ellipsis,
                                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 7.8),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        _DetailGrid(record: record),
                        const SizedBox(height: 12),
                        Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                        const SizedBox(height: 10),
                        Text(
                          _copy(context, 'Summary', 'Özet'),
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 5),
                        Text(
                          _copy(
                            context,
                            'This record is returned by the authoritative verified evidence feed. Its artifact digest and lineage hashes are shown exactly as supplied by the control plane.',
                            'Bu kayıt yetkili doğrulanmış kanıt akışından döndürülür. Artefakt özeti ve zincir hash’leri kontrol düzleminin sağladığı biçimde gösterilir.',
                          ),
                          style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 8),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          _copy(context, 'Evidence Chain', 'Kanıt Zinciri'),
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 7),
                        _ChainView(record: record),
                        const SizedBox(height: 12),
                        Text(
                          _copy(context, 'Evidence Items', 'Eklenen Kanıt Öğeleri'),
                          style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                        ),
                        const SizedBox(height: 6),
                        _EvidenceItem(
                          icon: Icons.fingerprint_rounded,
                          name: _copy(context, 'Artifact digest', 'Artefakt özeti'),
                          value: _short(record.artifactDigest, 30),
                        ),
                        _EvidenceItem(
                          icon: Icons.link_rounded,
                          name: _copy(context, 'Record hash', 'Kayıt hash'),
                          value: _short(record.recordHash, 30),
                        ),
                        _EvidenceItem(
                          icon: Icons.account_tree_outlined,
                          name: _copy(context, 'Execution ID', 'Yürütme ID'),
                          value: _short(record.executionId, 30),
                        ),
                      ],
                    ),
                  ),
                ),
                Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
                Padding(
                  padding: const EdgeInsets.all(10),
                  child: Row(
                    children: [
                      Expanded(
                        child: _ActionButton(
                          icon: Icons.visibility_outlined,
                          label: _copy(context, 'View', 'Görüntüle'),
                          filled: true,
                          onPressed: onView,
                        ),
                      ),
                      const SizedBox(width: 7),
                      Expanded(
                        child: _ActionButton(
                          icon: saving ? Icons.hourglass_top_rounded : Icons.download_outlined,
                          label: _copy(context, 'Download', 'İndir'),
                          onPressed: saveEnabled && !saving ? onSave : null,
                        ),
                      ),
                      const SizedBox(width: 7),
                      Expanded(
                        child: _ActionButton(
                          icon: Icons.verified_outlined,
                          label: _copy(context, 'Verify', 'Doğrula'),
                          success: true,
                          onPressed: onVerify,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
    );
  }
}

class _EmptySelected extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.fact_check_outlined, size: 34, color: Theme.of(context).colorScheme.outline),
              const SizedBox(height: 8),
              Text(
                _copy(context, 'No evidence selected', 'Seçili kanıt yok'),
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ],
          ),
        ),
      );
}

class _DetailGrid extends StatelessWidget {
  const _DetailGrid({required this.record});
  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              children: [
                _DetailLine(
                  label: _copy(context, 'Source', 'Kaynak'),
                  value: _short(record.executionId, 22),
                ),
                _DetailLine(
                  label: _copy(context, 'Owner', 'Sahip'),
                  value: '—',
                ),
                _DetailLine(
                  label: _copy(context, 'Related Agent', 'İlgili Ajan'),
                  value: '—',
                ),
              ],
            ),
          ),
          Container(
            width: 1,
            height: 70,
            margin: const EdgeInsets.symmetric(horizontal: 10),
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          Expanded(
            child: Column(
              children: [
                _DetailLine(
                  label: _copy(context, 'Created', 'Oluşturulma'),
                  value: '—',
                ),
                _DetailLine(
                  label: _copy(context, 'Verification Result', 'Doğrulama Sonucu'),
                  value: _copy(context, 'Verified', 'Başarılı'),
                  valueColor: IlaiosTheme.success,
                ),
                _DetailLine(
                  label: _copy(context, 'Trust Score', 'Güven Skoru'),
                  value: '—',
                ),
              ],
            ),
          ),
        ],
      );
}

class _DetailLine extends StatelessWidget {
  const _DetailLine({required this.label, required this.value, this.valueColor});
  final String label;
  final String value;
  final Color? valueColor;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 6),
        child: Row(
          children: [
            SizedBox(
              width: 72,
              child: Text(
                label,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 7.5),
              ),
            ),
            Expanded(
              child: Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(
                  fontSize: 8,
                  fontWeight: FontWeight.w600,
                  color: valueColor,
                ),
              ),
            ),
          ],
        ),
      );
}

class _ChainView extends StatelessWidget {
  const _ChainView({required this.record});
  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) {
    final nodes = <({IconData icon, String label, String value, bool success})>[
      (
        icon: Icons.play_circle_outline,
        label: _copy(context, 'Execution', 'Yürütme'),
        value: _short(record.executionId, 12),
        success: true,
      ),
      (
        icon: Icons.fingerprint_rounded,
        label: _copy(context, 'Artifact', 'Artefakt'),
        value: _short(record.artifactDigest, 12),
        success: true,
      ),
      (
        icon: Icons.link_rounded,
        label: _copy(context, 'Previous', 'Önceki'),
        value: record.previousHash.isEmpty ? 'GENESIS' : _short(record.previousHash, 12),
        success: true,
      ),
      (
        icon: Icons.verified_outlined,
        label: _copy(context, 'Record', 'Kayıt'),
        value: _short(record.recordHash, 12),
        success: true,
      ),
    ];
    return Row(
      children: [
        for (var i = 0; i < nodes.length; i++) ...[
          Expanded(child: _ChainNode(node: nodes[i])),
          if (i < nodes.length - 1)
            Expanded(
              child: Container(
                height: 1,
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
        ],
      ],
    );
  }
}

class _ChainNode extends StatelessWidget {
  const _ChainNode({required this.node});
  final ({IconData icon, String label, String value, bool success}) node;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Container(
            width: 28,
            height: 28,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              border: Border.all(
                color: node.success ? IlaiosTheme.coreBlue : Theme.of(context).colorScheme.outline,
              ),
            ),
            child: Icon(node.icon, size: 14, color: node.success ? IlaiosTheme.coreBlue : null),
          ),
          const SizedBox(height: 4),
          Text(
            node.label,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 6.9, fontWeight: FontWeight.w600),
          ),
          Text(
            node.value,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 6.2, color: Theme.of(context).colorScheme.onSurfaceVariant),
          ),
        ],
      );
}

class _EvidenceItem extends StatelessWidget {
  const _EvidenceItem({required this.icon, required this.name, required this.value});
  final IconData icon;
  final String name;
  final String value;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 28,
        child: Row(
          children: [
            const Icon(Icons.check_circle_outline_rounded, size: 13, color: IlaiosTheme.success),
            const SizedBox(width: 7),
            Icon(icon, size: 13, color: Theme.of(context).colorScheme.onSurfaceVariant),
            const SizedBox(width: 6),
            Expanded(
              child: Text(
                name,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 7.8, fontWeight: FontWeight.w600),
              ),
            ),
            const SizedBox(width: 8),
            SizedBox(
              width: 122,
              child: Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.right,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 7.2),
              ),
            ),
          ],
        ),
      );
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.icon,
    required this.label,
    required this.onPressed,
    this.filled = false,
    this.success = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onPressed;
  final bool filled;
  final bool success;

  @override
  Widget build(BuildContext context) {
    if (success) {
      return SizedBox(
        height: 34,
        child: FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: IlaiosTheme.success),
          onPressed: onPressed,
          icon: Icon(icon, size: 14),
          label: Text(label),
        ),
      );
    }
    if (filled) {
      return SizedBox(
        height: 34,
        child: FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: IlaiosTheme.coreBlue),
          onPressed: onPressed,
          icon: Icon(icon, size: 14),
          label: Text(label),
        ),
      );
    }
    return SizedBox(
      height: 34,
      child: OutlinedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon, size: 14),
        label: Text(label),
      ),
    );
  }
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _cardDecoration(context, radius: 7),
        padding: const EdgeInsets.fromLTRB(10, 9, 10, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 9.2, fontWeight: FontWeight.w700),
                  ),
                ),
                Text(
                  _copy(context, 'All ›', 'Tümü ›'),
                  style: const TextStyle(fontSize: 7.5, color: IlaiosTheme.coreBlue),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Expanded(child: child),
          ],
        ),
      );
}

class _AuditTrail extends StatelessWidget {
  const _AuditTrail({required this.records});
  final List<EvidenceRecord> records;

  @override
  Widget build(BuildContext context) {
    if (records.isEmpty) return const _Unavailable(icon: Icons.history_outlined);
    return Column(
      children: [
        for (final record in records.take(5))
          Expanded(
            child: Row(
              children: [
                Container(
                  width: 17,
                  height: 17,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(color: IlaiosTheme.coreBlue),
                  ),
                  child: const Icon(Icons.check_rounded, size: 10, color: IlaiosTheme.coreBlue),
                ),
                const SizedBox(width: 7),
                SizedBox(
                  width: 42,
                  child: Text(
                    '#${record.sequence}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 6.9),
                  ),
                ),
                Expanded(
                  child: Text(
                    record.action,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 7.4, fontWeight: FontWeight.w600),
                  ),
                ),
                const SizedBox(width: 6),
                SizedBox(
                  width: 78,
                  child: Text(
                    _short(record.recordHash, 12),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.right,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 6.5),
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _Unavailable extends StatelessWidget {
  const _Unavailable({required this.icon});
  final IconData icon;

  @override
  Widget build(BuildContext context) => Center(
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 17, color: Theme.of(context).colorScheme.outline),
            const SizedBox(width: 7),
            Text(
              _copy(context, 'No authoritative data', 'Yetkili veri yok'),
              style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 7.8),
            ),
          ],
        ),
      );
}

class _InlineMessage extends StatelessWidget {
  const _InlineMessage({required this.message});
  final String message;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('evidence-action-message'),
        height: 30,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        alignment: Alignment.centerLeft,
        decoration: BoxDecoration(
          color: IlaiosTheme.coreBlue.withValues(alpha: .07),
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: IlaiosTheme.coreBlue.withValues(alpha: .18)),
        ),
        child: Text(
          message,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 8.1, fontWeight: FontWeight.w600),
        ),
      );
}

class _Pill extends StatelessWidget {
  const _Pill({required this.label, required this.color});
  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 7.2,
            fontWeight: FontWeight.w700,
            color: color,
          ),
        ),
      );
}

class _PageBox extends StatelessWidget {
  const _PageBox({required this.label, this.selected = false});
  final String label;
  final bool selected;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(minWidth: 26),
        height: 26,
        alignment: Alignment.center,
        padding: const EdgeInsets.symmetric(horizontal: 7),
        decoration: BoxDecoration(
          color: selected ? IlaiosTheme.coreBlue.withValues(alpha: .10) : Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(
            color: selected ? IlaiosTheme.coreBlue : Theme.of(context).colorScheme.outlineVariant,
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w600),
        ),
      );
}

BoxDecoration _cardDecoration(BuildContext context, {double radius = 8}) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

String _categoryCode(EvidenceRecord record) {
  final value = record.action.toLowerCase();
  if (value.contains('test') ||
      value.contains('qa') ||
      value.contains('verify') ||
      value.contains('validation')) {
    return 'test';
  }
  if (value.contains('security') ||
      value.contains('scan') ||
      value.contains('auth') ||
      value.contains('threat')) {
    return 'security';
  }
  if (value.contains('deploy') ||
      value.contains('release') ||
      value.contains('build') ||
      value.contains('artifact')) {
    return 'deployment';
  }
  if (value.contains('policy') ||
      value.contains('govern') ||
      value.contains('approval') ||
      value.contains('compliance')) {
    return 'policy';
  }
  return 'other';
}

String _categoryLabel(BuildContext context, String code) => switch (code) {
      'test' => _copy(context, 'Test', 'Test'),
      'security' => _copy(context, 'Security', 'Güvenlik'),
      'deployment' => _copy(context, 'Deployment', 'Dağıtım'),
      'policy' => _copy(context, 'Policy', 'Politika'),
      _ => _copy(context, 'Other', 'Diğer'),
    };

Color _categoryColor(String code) => switch (code) {
      'test' => IlaiosTheme.coreBlue,
      'security' => const Color(0xFF8B5CF6),
      'deployment' => IlaiosTheme.enterpriseCyan,
      'policy' => IlaiosTheme.success,
      _ => Colors.grey,
    };

int _chainIssueCount(List<EvidenceRecord> records) {
  if (records.length < 2) return 0;
  final ordered = records.toList(growable: false)
    ..sort((a, b) => a.sequence.compareTo(b.sequence));
  var issues = 0;
  for (var index = 1; index < ordered.length; index++) {
    final current = ordered[index];
    final previous = ordered[index - 1];
    if (current.previousHash.isNotEmpty && current.previousHash != previous.recordHash) {
      issues += 1;
    }
  }
  return issues;
}

bool _statusConnected(String status) {
  final normalized = status.trim().toLowerCase();
  if (normalized.contains('unavailable') ||
      normalized.contains('offline') ||
      normalized.contains('error')) {
    return false;
  }
  return normalized.contains('connected') || normalized.contains('operational');
}

String _short(String value, int max) =>
    value.length <= max ? value : '${value.substring(0, max)}…';

bool _isTr(BuildContext context) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;

String _copy(BuildContext context, String en, String tr) => _isTr(context) ? tr : en;
