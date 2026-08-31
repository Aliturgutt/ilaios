import 'dart:async';
import 'dart:io';

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_surface_catalog.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import 'delivery_identity_scope.dart';
import 'delivery_local_storage.dart';

class DeliveriesView extends StatefulWidget {
  const DeliveriesView({
    required this.snapshot,
    required this.status,
    this.onSaveArtifact,
    this.localStorage,
    this.archiveStoreFactory,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final Future<String> Function(EvidenceRecord record)? onSaveArtifact;
  final DeliveryLocalStorage? localStorage;
  final DeliveryArchiveStore Function(DesktopUserSession session)?
      archiveStoreFactory;

  @override
  State<DeliveriesView> createState() => _DeliveriesViewState();
}

class _DeliveriesViewState extends State<DeliveriesView> {
  final TextEditingController _searchController = TextEditingController();
  late final DeliveryLocalStorage _localStorage =
      widget.localStorage ?? DeliveryLocalStorage();
  String? _activeDigest;
  int? _selectedSequence;
  String? _message;
  String? _archiveError;
  String? _archiveScopeKey;
  String _activeTab = 'all';
  String _typeFilter = 'all';
  Set<String> _archivedDigests = <String>{};
  DeliveryArchiveStore? _archiveStore;
  bool _archiveReady = false;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final session = DeliveryIdentityScope.maybeSessionOf(context);
    final nextKey = session == null
        ? null
        : '${session.providerId}\u0000${session.tenantId}\u0000${session.principalId}';
    if (nextKey == _archiveScopeKey) return;
    _archiveScopeKey = nextKey;
    _archivedDigests = <String>{};
    _archiveStore = null;
    _archiveReady = false;
    _archiveError = null;
    if (session == null) return;
    final store = widget.archiveStoreFactory?.call(session) ??
        DeliveryArchiveStore.forSession(session);
    _archiveStore = store;
    unawaited(_loadArchive(store, nextKey!));
  }

  Future<void> _loadArchive(DeliveryArchiveStore store, String scopeKey) async {
    try {
      final loaded = await store.load();
      if (!mounted || _archiveScopeKey != scopeKey || _archiveStore != store) {
        return;
      }
      setState(() {
        _archivedDigests = loaded;
        _archiveReady = true;
        _archiveError = null;
      });
    } on DeliveryArchiveStateException catch (error) {
      if (!mounted || _archiveScopeKey != scopeKey || _archiveStore != store) {
        return;
      }
      setState(() {
        _archivedDigests = <String>{};
        _archiveReady = false;
        _archiveError = _isTr(context)
            ? 'Arşiv durumu okunamadı; arşivleme ve geri yükleme güvenli biçimde devre dışı bırakıldı. Kanıt kayıtları değişmedi.'
            : 'Archive state is unreadable; archive and restore are safely disabled. Evidence records were unchanged.';
        _message = error.message;
      });
    }
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<EvidenceRecord> get _records => widget.snapshot.evidenceRecords.reversed
      .where(_isFinishedProductEvidence)
      .take(100)
      .toList(growable: false);

  List<EvidenceRecord> get _activeRecords {
    final records = _records;
    if (!_archiveReady) return records;
    return records
        .where((record) => !_archivedDigests.contains(record.artifactDigest))
        .toList(growable: false);
  }

  List<EvidenceRecord> get _archivedRecords {
    if (!_archiveReady) return const <EvidenceRecord>[];
    return _records
        .where((record) => _archivedDigests.contains(record.artifactDigest))
        .toList(growable: false);
  }

  List<EvidenceRecord> get _visibleRecords {
    List<EvidenceRecord> records;
    if (_activeTab == 'archive') {
      records = _archivedRecords;
    } else if (_activeTab == 'all' || _activeTab == 'completed') {
      records = _activeRecords;
    } else {
      return const <EvidenceRecord>[];
    }
    if (_typeFilter != 'all') {
      records = records
          .where((record) => _deliveryTypeCode(record) == _typeFilter)
          .toList(growable: false);
    }
    final query = _searchController.text.trim().toLowerCase();
    if (query.isNotEmpty) {
      records = records
          .where(
            (record) =>
                record.action.toLowerCase().contains(query) ||
                record.executionId.toLowerCase().contains(query) ||
                record.artifactDigest.toLowerCase().contains(query),
          )
          .toList(growable: false);
    }
    return records;
  }

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
      setState(
        () => _message = '${_surface(context, 'deliveries.savedPrefix')} $path',
      );
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _message = error.toString());
    } finally {
      if (mounted) setState(() => _activeDigest = null);
    }
  }

  File _localDeliveryFile(EvidenceRecord record) =>
      _localStorage.resolveArtifactFile(record);

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
                label: Text(
                  _isTr(context) ? 'Yerel kopyayı sil' : 'Delete local copy',
                ),
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

  Future<void> _setArchived(EvidenceRecord record, bool archived) async {
    if (_activeDigest != null) return;
    final store = _archiveStore;
    if (!_archiveReady || store == null) {
      setState(() {
        _message = _isTr(context)
            ? 'Arşivleme için doğrulanmış oturum ve okunabilir arşiv durumu gerekir.'
            : 'Archiving requires a verified session and readable archive state.';
      });
      return;
    }
    final next = Set<String>.of(_archivedDigests);
    if (archived) {
      next.add(record.artifactDigest);
    } else {
      next.remove(record.artifactDigest);
    }
    setState(() {
      _activeDigest = record.artifactDigest;
      _message = null;
    });
    try {
      await store.persist(next);
      if (!mounted) return;
      setState(() {
        _archivedDigests = next;
        _message = archived
            ? (_isTr(context)
                ? 'Çıktı aktif listeden kaldırıldı ve Arşiv’e taşındı. Kanıt kaydı korunuyor.'
                : 'Output removed from the active list and moved to Archive. Evidence is retained.')
            : (_isTr(context)
                ? 'Çıktı Arşiv’den geri yüklendi.'
                : 'Output restored from Archive.');
      });
    } on DeliveryArchiveStateException catch (error) {
      if (!mounted) return;
      setState(() => _message = error.message);
    } finally {
      if (mounted) setState(() => _activeDigest = null);
    }
  }

  void _clearFilters() {
    _searchController.clear();
    setState(() {
      _activeTab = 'all';
      _typeFilter = 'all';
      _selectedSequence = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    final activeRecords = _activeRecords;
    final archivedRecords = _archivedRecords;
    final visibleRecords = _visibleRecords;
    final baseCount = _activeTab == 'archive'
        ? archivedRecords.length
        : activeRecords.length;
    EvidenceRecord? selectedRecord;
    final selectedSequence = _selectedSequence;
    if (selectedSequence != null) {
      for (final record in visibleRecords) {
        if (record.sequence == selectedSequence) {
          selectedRecord = record;
          break;
        }
      }
    }
    final message = _archiveError ?? _message;

    return Container(
      key: const Key('reference-outputs-page'),
      padding: const EdgeInsets.fromLTRB(18, 14, 18, 12),
      color: Theme.of(context).scaffoldBackgroundColor,
      child: LayoutBuilder(
        builder: (context, constraints) {
          final showRightRail =
              selectedRecord != null && constraints.maxWidth >= 1080;
          return Row(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    _Header(status: widget.status, total: activeRecords.length),
                    if (activeRecords.isNotEmpty) ...[
                      const SizedBox(height: 10),
                      _MetricStrip(total: activeRecords.length),
                    ],
                    const SizedBox(height: 10),
                    _Toolbar(
                      activeTab: _activeTab,
                      onTabChanged: (value) => setState(() {
                        _activeTab = value;
                        _selectedSequence = null;
                      }),
                    ),
                    const SizedBox(height: 8),
                    _Filters(
                      controller: _searchController,
                      typeFilter: _typeFilter,
                      onSearchChanged: (_) => setState(() {
                        _selectedSequence = null;
                      }),
                      onTypeChanged: (value) => setState(() {
                        _typeFilter = value ?? 'all';
                        _selectedSequence = null;
                      }),
                      onClear: _clearFilters,
                    ),
                    const SizedBox(height: 8),
                    Expanded(
                      child: _OutputsTable(
                        records: visibleRecords,
                        totalCount: baseCount,
                        activeDigest: _activeDigest,
                        saveEnabled: widget.onSaveArtifact != null,
                        archiveEnabled: _archiveReady,
                        archivedDigests: _archivedDigests,
                        selectedSequence: _selectedSequence,
                        onSelected: (record) =>
                            setState(() => _selectedSequence = record.sequence),
                        localFileFor: _localDeliveryFile,
                        onSave: _save,
                        onDelete: _deleteLocalCopy,
                        onArchive: (record) => _setArchived(record, true),
                        onRestore: (record) => _setArchived(record, false),
                      ),
                    ),
                    if (message != null) ...[
                      const SizedBox(height: 7),
                      _InlineMessage(message: message),
                    ],
                  ],
                ),
              ),
              if (showRightRail) ...[
                const SizedBox(width: 16),
                SizedBox(
                  width: 300,
                  child: _RightRail(
                    record: selectedRecord,
                    archived: _archivedDigests.contains(
                      selectedRecord.artifactDigest,
                    ),
                    localFile: _localDeliveryFile(selectedRecord),
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.status, required this.total});

  final String status;
  final int total;

  @override
  Widget build(BuildContext context) => SizedBox(
        key: const Key('outputs-header'),
        height: 54,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _copy(context, 'Çıktılar', 'Outputs'),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _copy(
                      context,
                      'Projede üretilen doğrulanmış çıktıları görüntüleyin, filtreleyin ve yönetin.',
                      'View, filter and manage verified outputs produced by the project.',
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 10.5),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 10),
            Container(
              constraints: const BoxConstraints(maxWidth: 250),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: total > 0
                    ? IlaiosTheme.success.withValues(alpha: .08)
                    : Theme.of(context).colorScheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(
                  color: total > 0
                      ? IlaiosTheme.success.withValues(alpha: .30)
                      : Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.circle,
                    size: 7,
                    color: widgetStatusAvailable(status)
                        ? IlaiosTheme.success
                        : Theme.of(context).colorScheme.outline,
                  ),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      _localizedStatus(context, status),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _MetricStrip extends StatelessWidget {
  const _MetricStrip({required this.total});

  final int total;

  @override
  Widget build(BuildContext context) => SizedBox(
        key: const Key('outputs-kpis'),
        height: 78,
        child: Row(
          children: [
            Expanded(
              child: _MetricCard(
                icon: Icons.grid_view_rounded,
                accent: IlaiosTheme.coreBlue,
                label: _copy(context, 'Toplam Çıktı', 'Total Outputs'),
                value: '$total',
                note: _copy(context, 'Aktif doğrulanmış çıktılar', 'Active verified outputs'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                icon: Icons.check_circle_outline,
                accent: IlaiosTheme.success,
                label: _copy(context, 'Tamamlanan', 'Completed'),
                value: '$total',
                note: _copy(context, 'Bitmiş ürün kanıtı', 'Finished-product evidence'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                icon: Icons.hourglass_empty_rounded,
                accent: IlaiosTheme.warning,
                label: _copy(context, 'Taslak', 'Draft'),
                value: '—',
                note: _copy(context, 'Yetkili veri yok', 'No authoritative data'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                icon: Icons.rate_review_outlined,
                accent: IlaiosTheme.violet,
                label: _copy(context, 'İncelemede', 'In Review'),
                value: '—',
                note: _copy(context, 'Yetkili veri yok', 'No authoritative data'),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: _MetricCard(
                icon: Icons.cancel_outlined,
                accent: IlaiosTheme.danger,
                label: _copy(context, 'Reddedilen', 'Rejected'),
                value: '—',
                note: _copy(context, 'Yetkili veri yok', 'No authoritative data'),
              ),
            ),
          ],
        ),
      );
}

class _MetricCard extends StatelessWidget {
  const _MetricCard({
    required this.icon,
    required this.accent,
    required this.label,
    required this.value,
    required this.note,
  });

  final IconData icon;
  final Color accent;
  final String label;
  final String value;
  final String note;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
        decoration: _panelDecoration(context, radius: 8),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: .10),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, size: 18, color: accent),
            ),
            const SizedBox(width: 9),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    label,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 9),
                  ),
                  Text(
                    value,
                    style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w700),
                  ),
                  Text(
                    note,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontSize: 7.8,
                          color: accent,
                        ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _Toolbar extends StatelessWidget {
  const _Toolbar({required this.activeTab, required this.onTabChanged});

  final String activeTab;
  final ValueChanged<String> onTabChanged;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('outputs-tabs'),
        height: 44,
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: _panelDecoration(context, radius: 8),
        child: Row(
          children: [
            _Tab(
              label: _copy(context, 'Tümü', 'All'),
              value: 'all',
              selected: activeTab == 'all',
              onTap: onTabChanged,
            ),
            _Tab(
              label: _copy(context, 'Tamamlanan', 'Completed'),
              value: 'completed',
              selected: activeTab == 'completed',
              onTap: onTabChanged,
            ),
            _Tab(
              label: _copy(context, 'Taslak', 'Draft'),
              value: 'draft',
              selected: activeTab == 'draft',
              onTap: onTabChanged,
            ),
            _Tab(
              label: _copy(context, 'İncelemede', 'In Review'),
              value: 'review',
              selected: activeTab == 'review',
              onTap: onTabChanged,
            ),
            _Tab(
              label: _copy(context, 'Reddedilen', 'Rejected'),
              value: 'rejected',
              selected: activeTab == 'rejected',
              onTap: onTabChanged,
            ),
            _Tab(
              label: _copy(context, 'Arşiv', 'Archive'),
              value: 'archive',
              selected: activeTab == 'archive',
              onTap: onTabChanged,
            ),
            const Spacer(),
          ],
        ),
      );
}

class _Tab extends StatelessWidget {
  const _Tab({
    required this.label,
    required this.value,
    required this.selected,
    required this.onTap,
  });

  final String label;
  final String value;
  final bool selected;
  final ValueChanged<String> onTap;

  @override
  Widget build(BuildContext context) => InkWell(
        onTap: () => onTap(value),
        child: Container(
          height: 44,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: selected ? IlaiosTheme.enterpriseCyan : Colors.transparent,
                width: 2,
              ),
            ),
          ),
          alignment: Alignment.center,
          child: Text(
            label,
            style: TextStyle(
              fontSize: 9.5,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected
                  ? IlaiosTheme.enterpriseCyan
                  : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      );
}

class _Filters extends StatelessWidget {
  const _Filters({
    required this.controller,
    required this.typeFilter,
    required this.onSearchChanged,
    required this.onTypeChanged,
    required this.onClear,
  });

  final TextEditingController controller;
  final String typeFilter;
  final ValueChanged<String> onSearchChanged;
  final ValueChanged<String?> onTypeChanged;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) => SizedBox(
        key: const Key('outputs-filters'),
        height: 38,
        child: Row(
          children: [
            SizedBox(
              width: 185,
              child: TextField(
                controller: controller,
                onChanged: onSearchChanged,
                style: const TextStyle(fontSize: 9.5),
                decoration: InputDecoration(
                  hintText: _copy(context, 'Çıktı adı, proje veya kayıt ara…', 'Search output, project or record…'),
                  prefixIcon: const Icon(Icons.search, size: 16),
                  isDense: true,
                ),
              ),
            ),
            const SizedBox(width: 7),
            _FilterDropdown(
              width: 105,
              value: typeFilter,
              onChanged: onTypeChanged,
              items: <String, String>{
                'all': _copy(context, 'Tür', 'Type'),
                'document': _copy(context, 'Doküman', 'Document'),
                'video': _copy(context, 'Video', 'Video'),
                'visual': _copy(context, 'Görsel', 'Visual'),
                'report': _copy(context, 'Rapor', 'Report'),
                'table': _copy(context, 'Tablo', 'Table'),
                'other': _copy(context, 'Diğer', 'Other'),
              },
            ),
            const Spacer(),
            if (controller.text.trim().isNotEmpty || typeFilter != 'all')
              TextButton(
                onPressed: onClear,
                child: Text(
                  _copy(context, 'Filtreleri Temizle', 'Clear Filters'),
                  style: const TextStyle(fontSize: 9),
                ),
              ),
          ],
        ),
      );
}

class _FilterDropdown extends StatelessWidget {
  const _FilterDropdown({
    required this.width,
    required this.value,
    required this.onChanged,
    required this.items,
  });

  final double width;
  final String value;
  final ValueChanged<String?> onChanged;
  final Map<String, String> items;

  @override
  Widget build(BuildContext context) => Container(
        width: width,
        height: 36,
        padding: const EdgeInsets.symmetric(horizontal: 9),
        decoration: _fieldDecoration(context),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: value,
            isExpanded: true,
            iconSize: 16,
            style: TextStyle(
              fontSize: 9.5,
              color: Theme.of(context).colorScheme.onSurface,
            ),
            onChanged: onChanged,
            items: items.entries
                .map(
                  (entry) => DropdownMenuItem<String>(
                    value: entry.key,
                    child: Text(entry.value, overflow: TextOverflow.ellipsis),
                  ),
                )
                .toList(growable: false),
          ),
        ),
      );
}

class _OutputsTable extends StatelessWidget {
  const _OutputsTable({
    required this.records,
    required this.totalCount,
    required this.activeDigest,
    required this.saveEnabled,
    required this.archiveEnabled,
    required this.archivedDigests,
    required this.selectedSequence,
    required this.onSelected,
    required this.localFileFor,
    required this.onSave,
    required this.onDelete,
    required this.onArchive,
    required this.onRestore,
  });

  final List<EvidenceRecord> records;
  final int totalCount;
  final String? activeDigest;
  final bool saveEnabled;
  final bool archiveEnabled;
  final Set<String> archivedDigests;
  final int? selectedSequence;
  final ValueChanged<EvidenceRecord> onSelected;
  final File Function(EvidenceRecord record) localFileFor;
  final Future<void> Function(EvidenceRecord record) onSave;
  final Future<void> Function(EvidenceRecord record) onDelete;
  final Future<void> Function(EvidenceRecord record) onArchive;
  final Future<void> Function(EvidenceRecord record) onRestore;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('outputs-table'),
        decoration: _panelDecoration(context, radius: 8),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            _TableHeader(),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            Expanded(
              child: records.isEmpty
                  ? _OutputsEmptyState(totalCount: totalCount)
                  : Scrollbar(
                      child: ListView.separated(
                        padding: EdgeInsets.zero,
                        itemCount: records.length,
                        separatorBuilder: (_, _) => Divider(
                          height: 1,
                          color: Theme.of(context)
                              .colorScheme
                              .outlineVariant
                              .withValues(alpha: .65),
                        ),
                        itemBuilder: (context, index) {
                          final record = records[index];
                          return _OutputRow(
                            record: record,
                            saving: activeDigest == record.artifactDigest,
                            actionsEnabled: activeDigest == null,
                            saveEnabled: saveEnabled,
                            archiveEnabled: archiveEnabled,
                            archived: archivedDigests.contains(record.artifactDigest),
                            selected: selectedSequence == record.sequence,
                            onSelected: () => onSelected(record),
                            localFile: localFileFor(record),
                            onSave: () => onSave(record),
                            onDelete: () => onDelete(record),
                            onArchive: () => onArchive(record),
                            onRestore: () => onRestore(record),
                          );
                        },
                      ),
                    ),
            ),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            SizedBox(
              height: 34,
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 10),
                child: Row(
                  children: [
                    Text(
                      records.isEmpty
                          ? _copy(context, '0 sonuç', '0 results')
                          : _copy(
                              context,
                              '1–${records.length} / $totalCount sonuç',
                              '1–${records.length} / $totalCount results',
                            ),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 9),
                    ),
                    const Spacer(),
                  ],
                ),
              ),
            ),
          ],
        ),
      );
}

class _TableHeader extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Container(
        key: const Key('outputs-table-header'),
        height: 32,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        child: Row(
          children: [
            _HeaderCell(_copy(context, 'Çıktı Adı', 'Output'), flex: 28),
            _HeaderCell(_copy(context, 'Tür', 'Type'), flex: 11),
            _HeaderCell(_copy(context, 'Ajan', 'Agent'), flex: 14),
            _HeaderCell(_copy(context, 'Sahip', 'Owner'), flex: 12),
            _HeaderCell(_copy(context, 'Durum', 'Status'), flex: 13),
            _HeaderCell(_copy(context, 'Oluşturulma Tarihi', 'Created'), flex: 15),
            _HeaderCell(_copy(context, 'Boyut', 'Size'), flex: 9),
            const SizedBox(width: 58),
          ],
        ),
      );
}

class _HeaderCell extends StatelessWidget {
  const _HeaderCell(this.label, {required this.flex});

  final String label;
  final int flex;

  @override
  Widget build(BuildContext context) => Expanded(
        flex: flex,
        child: Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),
        ),
      );
}

class _OutputRow extends StatelessWidget {
  const _OutputRow({
    required this.record,
    required this.saving,
    required this.actionsEnabled,
    required this.saveEnabled,
    required this.archiveEnabled,
    required this.archived,
    required this.selected,
    required this.onSelected,
    required this.localFile,
    required this.onSave,
    required this.onDelete,
    required this.onArchive,
    required this.onRestore,
  });

  final EvidenceRecord record;
  final bool saving;
  final bool actionsEnabled;
  final bool saveEnabled;
  final bool archiveEnabled;
  final bool archived;
  final bool selected;
  final VoidCallback onSelected;
  final File localFile;
  final VoidCallback onSave;
  final VoidCallback onDelete;
  final VoidCallback onArchive;
  final VoidCallback onRestore;

  @override
  Widget build(BuildContext context) {
    final type = _deliveryTypeCode(record);
    final accent = _typeColor(type);
    final exists = _safeExists(localFile);
    final size = exists ? _safeFileSize(localFile) : '—';

    return Material(
      color: selected
          ? Theme.of(context).colorScheme.primary.withValues(alpha: .06)
          : Colors.transparent,
      child: InkWell(
        onTap: onSelected,
        child: SizedBox(
          height: 48,
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 10),
            child: Row(
              children: [
            Expanded(
              flex: 28,
              child: Row(
                children: [
                  Container(
                    width: 27,
                    height: 27,
                    decoration: BoxDecoration(
                      color: accent.withValues(alpha: .10),
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Icon(_typeIcon(type), size: 15, color: accent),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Text(
                          _outputName(record),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700),
                        ),
                        Text(
                          record.action,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(fontSize: 7.3),
                        ),
                        Text(
                          record.executionId,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(fontSize: 6.6),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            Expanded(
              flex: 11,
              child: Align(
                alignment: Alignment.centerLeft,
                child: _Pill(text: _typeLabel(context, type), color: accent),
              ),
            ),
            Expanded(flex: 14, child: _UnavailableCell()),
            Expanded(flex: 12, child: _UnavailableCell()),
            Expanded(
              flex: 13,
              child: Align(
                alignment: Alignment.centerLeft,
                child: _Pill(
                  text: archived
                      ? _copy(context, 'Arşivde', 'Archived')
                      : _copy(context, 'Tamamlandı', 'Completed'),
                  color: archived ? IlaiosTheme.violet : IlaiosTheme.success,
                ),
              ),
            ),
            Expanded(flex: 15, child: _UnavailableCell()),
            Expanded(
              flex: 9,
              child: Text(size, style: const TextStyle(fontSize: 8.5)),
            ),
            SizedBox(
              width: 58,
              child: Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  SizedBox(
                    width: 27,
                    height: 30,
                    child: IconButton(
                      key: ValueKey('save-artifact-${record.sequence}'),
                      tooltip: _surface(context, 'deliveries.save'),
                      padding: EdgeInsets.zero,
                      visualDensity: VisualDensity.compact,
                      iconSize: 15,
                      onPressed: actionsEnabled && saveEnabled ? onSave : null,
                      icon: saving
                          ? const SizedBox(
                              width: 12,
                              height: 12,
                              child: CircularProgressIndicator(strokeWidth: 1.5),
                            )
                          : const Icon(Icons.download_outlined),
                    ),
                  ),
                  SizedBox(
                    width: 27,
                    height: 30,
                    child: PopupMenuButton<String>(
                      key: ValueKey('delete-local-artifact-${record.sequence}'),
                      tooltip: _copy(context, 'Çıktı işlemleri', 'Output actions'),
                      padding: EdgeInsets.zero,
                      enabled: actionsEnabled,
                      iconSize: 15,
                      icon: const Icon(Icons.more_vert),
                      onSelected: (value) {
                        switch (value) {
                          case 'delete-local':
                            onDelete();
                          case 'archive':
                            onArchive();
                          case 'restore':
                            onRestore();
                        }
                      },
                      itemBuilder: (context) => <PopupMenuEntry<String>>[
                        PopupMenuItem<String>(
                          value: 'delete-local',
                          child: Row(
                            children: [
                              const Icon(Icons.delete_outline, size: 16),
                              const SizedBox(width: 8),
                              Text(_copy(context, 'Yerel kopyayı sil', 'Delete local copy')),
                            ],
                          ),
                        ),
                        PopupMenuItem<String>(
                          value: archived ? 'restore' : 'archive',
                          enabled: archiveEnabled,
                          child: Row(
                            children: [
                              Icon(
                                archived ? Icons.unarchive_outlined : Icons.archive_outlined,
                                size: 16,
                              ),
                              const SizedBox(width: 8),
                              Text(
                                archived
                                    ? _copy(context, 'Geri yükle', 'Restore')
                                    : _copy(context, 'Listeden kaldır', 'Remove from list'),
                              ),
                            ],
                          ),
                        ),
                        PopupMenuItem<String>(
                          enabled: false,
                          child: Tooltip(
                            message: _copy(
                              context,
                              'Yetkili remote-delete sözleşmesi yok; kalıcı silme güvenli biçimde devre dışı.',
                              'No authoritative remote-delete contract exists; permanent purge is safely disabled.',
                            ),
                            child: Row(
                              children: [
                                const Icon(Icons.delete_forever_outlined, size: 16),
                                const SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    _copy(
                                      context,
                                      'Kalıcı olarak sil — kullanılamıyor',
                                      'Permanently delete — unavailable',
                                    ),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _UnavailableCell extends StatelessWidget {
  @override
  Widget build(BuildContext context) => Text(
        '—',
        style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 9),
      );
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .10),
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: color.withValues(alpha: .18)),
        ),
        child: Text(
          text,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 7.8, fontWeight: FontWeight.w600, color: color),
        ),
      );
}

class _OutputsEmptyState extends StatelessWidget {
  const _OutputsEmptyState({required this.totalCount});

  final int totalCount;

  @override
  Widget build(BuildContext context) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                totalCount == 0 ? Icons.inventory_2_outlined : Icons.filter_alt_off_outlined,
                size: 32,
                color: IlaiosTheme.enterpriseCyan,
              ),
              const SizedBox(height: 9),
              Text(
                totalCount == 0
                    ? _surface(context, 'deliveries.empty')
                    : _copy(
                        context,
                        'Seçili filtrelerle eşleşen doğrulanmış çıktı yok.',
                        'No verified outputs match the selected filters.',
                      ),
                textAlign: TextAlign.center,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 5),
              Text(
                _copy(
                  context,
                  'Tamamlanan ve doğrulanan işler burada çıktı olarak görünür. İlk çıktıyı almak için yeni bir iş başlat.',
                  'Completed and verified work appears here as output. Start a new task to create the first output.',
                ),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 9),
              ),
            ],
          ),
        ),
      );
}

class _RightRail extends StatelessWidget {
  const _RightRail({
    required this.record,
    required this.archived,
    required this.localFile,
  });

  final EvidenceRecord record;
  final bool archived;
  final File localFile;

  @override
  Widget build(BuildContext context) {
    final exists = _safeExists(localFile);
    return Container(
      key: const Key('outputs-right-rail'),
      padding: const EdgeInsets.all(14),
      decoration: _panelDecoration(context, radius: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            _copy(context, 'Çıktı ayrıntıları', 'Output details'),
            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 12),
          Text(
            _outputName(record),
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          Align(
            alignment: Alignment.centerLeft,
            child: _Pill(
              text: archived
                  ? _copy(context, 'Arşivde', 'Archived')
                  : _copy(context, 'Tamamlandı', 'Completed'),
              color: archived ? IlaiosTheme.violet : IlaiosTheme.success,
            ),
          ),
          const SizedBox(height: 14),
          _OutputDetailRow(
            label: _copy(context, 'Tür', 'Type'),
            value: _typeLabel(context, _deliveryTypeCode(record)),
          ),
          _OutputDetailRow(
            label: _copy(context, 'Yürütme', 'Execution'),
            value: record.executionId,
          ),
          _OutputDetailRow(
            label: _copy(context, 'Kanıt kaydı', 'Evidence record'),
            value: '#${record.sequence}',
          ),
          _OutputDetailRow(
            label: _copy(context, 'Yerel kopya', 'Local copy'),
            value: exists
                ? _copy(context, 'Mevcut', 'Available')
                : _copy(context, 'Kaydedilmemiş', 'Not saved'),
          ),
          if (exists)
            _OutputDetailRow(
              label: _copy(context, 'Boyut', 'Size'),
              value: _safeFileSize(localFile),
            ),
          const SizedBox(height: 14),
          Text(
            _copy(context, 'Kanıt özeti', 'Evidence digest'),
            style: TextStyle(
              fontSize: 8,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 4),
          SelectableText(
            record.artifactDigest,
            maxLines: 4,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  fontSize: 8,
                  fontFamily: 'monospace',
                ),
          ),
          const Spacer(),
          Text(
            record.action,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 8),
          ),
        ],
      ),
    );
  }
}

class _OutputDetailRow extends StatelessWidget {
  const _OutputDetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 9),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 82,
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 8,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: SelectableText(
                value,
                maxLines: 3,
                style: const TextStyle(
                  fontSize: 8.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
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
        key: const Key('delivery-message'),
        height: 30,
        padding: const EdgeInsets.symmetric(horizontal: 10),
        alignment: Alignment.centerLeft,
        decoration: BoxDecoration(
          color: IlaiosTheme.enterpriseCyan.withValues(alpha: .07),
          borderRadius: BorderRadius.circular(7),
          border: Border.all(
            color: IlaiosTheme.enterpriseCyan.withValues(alpha: .28),
          ),
        ),
        child: SelectableText(
          message,
          maxLines: 1,
          style: Theme.of(context).textTheme.bodySmall?.copyWith(fontSize: 8.5),
        ),
      );
}

bool _safeExists(File file) {
  try {
    return file.existsSync();
  } on FileSystemException {
    return false;
  }
}

String _safeFileSize(File file) {
  try {
    return _formatBytes(file.lengthSync());
  } on FileSystemException {
    return '—';
  }
}

String _formatBytes(int bytes) {
  if (bytes < 1024) return '$bytes B';
  if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
  if (bytes < 1024 * 1024 * 1024) {
    return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
  return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
}

String _deliveryTypeCode(EvidenceRecord record) {
  final value = record.action.toLowerCase();
  if (value.contains('video') || value.contains('media')) return 'video';
  if (value.contains('image') ||
      value.contains('visual') ||
      value.contains('design')) {
    return 'visual';
  }
  if (value.contains('report') || value.contains('research')) return 'report';
  if (value.contains('table') ||
      value.contains('sheet') ||
      value.contains('csv')) {
    return 'table';
  }
  if (value.contains('document') ||
      value.contains('doc') ||
      value.contains('pdf') ||
      value.contains('web')) {
    return 'document';
  }
  return 'other';
}

String _typeLabel(BuildContext context, String code) => switch (code) {
      'document' => _copy(context, 'Doküman', 'Document'),
      'video' => _copy(context, 'Video', 'Video'),
      'visual' => _copy(context, 'Görsel', 'Visual'),
      'report' => _copy(context, 'Rapor', 'Report'),
      'table' => _copy(context, 'Tablo', 'Table'),
      _ => _copy(context, 'Diğer', 'Other'),
    };

Color _typeColor(String code) => switch (code) {
      'document' => IlaiosTheme.coreBlue,
      'video' => IlaiosTheme.violet,
      'visual' => const Color(0xFFEB5D91),
      'report' => IlaiosTheme.warning,
      'table' => IlaiosTheme.success,
      _ => const Color(0xFF91A7C0),
    };

IconData _typeIcon(String code) => switch (code) {
      'document' => Icons.description_outlined,
      'video' => Icons.videocam_outlined,
      'visual' => Icons.image_outlined,
      'report' => Icons.analytics_outlined,
      'table' => Icons.table_chart_outlined,
      _ => Icons.inventory_2_outlined,
    };

String _outputName(EvidenceRecord record) {
  var value = record.action;
  const suffix = '.finished_product';
  if (value.endsWith(suffix)) {
    value = value.substring(0, value.length - suffix.length);
  }
  value = value.replaceAll(RegExp(r'[._-]+'), ' ').trim();
  if (value.isEmpty) return record.executionId;
  return value
      .split(' ')
      .where((part) => part.isNotEmpty)
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');
}

BoxDecoration _panelDecoration(BuildContext context, {required double radius}) =>
    BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

BoxDecoration _fieldDecoration(BuildContext context) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(7),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

bool _isFinishedProductEvidence(EvidenceRecord record) =>
    record.action.endsWith('.finished_product');

bool widgetStatusAvailable(String value) {
  final lower = value.toLowerCase();
  return lower.contains('connected') ||
      lower.contains('operational') ||
      lower.contains('bağlı');
}

String _localizedStatus(BuildContext context, String value) {
  if (!_isTr(context)) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    'Operational APIs not connected' => 'Operasyon API’leri bağlı değil',
    _ => value,
  };
}

bool _isTr(BuildContext context) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish;

String _copy(BuildContext context, String tr, String en) =>
    _isTr(context) ? tr : en;

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;
