import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/operational_snapshot.dart';

class ApprovalsView extends StatefulWidget {
  const ApprovalsView({
    required this.snapshot,
    required this.status,
    this.approverId,
    this.onDecision,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;
  final String? approverId;
  final Future<void> Function(String requestId, GovernanceDecision decision)?
      onDecision;

  @override
  State<ApprovalsView> createState() => _ApprovalsViewState();
}

class _ApprovalsViewState extends State<ApprovalsView> {
  final TextEditingController _searchController = TextEditingController();
  String _activeTab = 'all';
  String _riskFilter = 'all';
  String? _selectedRequestId;
  String? _busyRequestId;
  String? _message;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Map<String, Object?>>? get _rawWork {
    final raw = widget.snapshot.governanceState['work'];
    if (raw is! List<Object?>) return null;
    return raw
        .whereType<Map<String, dynamic>>()
        .map((item) => Map<String, Object?>.from(item))
        .toList(growable: false);
  }

  Set<String>? get _approvalRequiredIds {
    final raw = widget.snapshot.governanceState['admissions'];
    if (raw is! List<Object?>) return null;
    final ids = <String>{};
    for (final item in raw) {
      if (item is! Map<String, dynamic> ||
          item['human_approval_required'] != true) {
        continue;
      }
      final id = item['request_id'];
      if (id is String && id.trim().isNotEmpty) ids.add(id.trim());
    }
    return ids;
  }

  List<Map<String, Object?>> get _requests {
    final work = _rawWork;
    if (work == null) return const <Map<String, Object?>>[];
    final required = _approvalRequiredIds;
    if (required == null) return work;
    return work.where((item) {
      final id = _string(item, const ['request_id', 'id']);
      return id != null && required.contains(id);
    }).toList(growable: false);
  }

  List<Map<String, Object?>> get _visibleRequests {
    Iterable<Map<String, Object?>> requests = _requests;
    if (_activeTab != 'all' && _activeTab != 'archive') {
      requests = requests.where((item) {
        final status = _normalizedStatus(item);
        return switch (_activeTab) {
          'pending' => status == 'pending',
          'approved' => status == 'approved',
          'denied' => status == 'denied',
          'high' => _normalizedRisk(item) == 'high',
          _ => true,
        };
      });
    }
    if (_activeTab == 'archive') {
      requests = requests.where((item) => _normalizedStatus(item) != 'pending');
    }
    if (_riskFilter != 'all') {
      requests = requests.where((item) => _normalizedRisk(item) == _riskFilter);
    }
    final query = _searchController.text.trim().toLowerCase();
    if (query.isNotEmpty) {
      requests = requests.where((item) {
        final haystack = <String?>[
          _requestTitle(item),
          _string(item, const ['request_id', 'id']),
          _string(item, const ['request_type', 'type', 'category']),
          _string(item, const ['requester_name', 'requester_id', 'requester']),
          _string(item, const ['reason', 'justification', 'summary', 'objective']),
        ].whereType<String>().join(' ').toLowerCase();
        return haystack.contains(query);
      });
    }
    return requests.take(100).toList(growable: false);
  }

  Map<String, Object?>? get _selected {
    final visible = _visibleRequests;
    final selectedId = _selectedRequestId;
    if (visible.isEmpty || selectedId == null) return null;
    for (final item in visible) {
      if (_requestId(item) == selectedId) return item;
    }
    return null;
  }

  Future<void> _decide(GovernanceDecision decision) async {
    final request = _selected;
    final callback = widget.onDecision;
    if (request == null || callback == null || _busyRequestId != null) return;
    final id = _requestId(request);
    if (id == null || !_decisionAllowed(request)) return;
    setState(() {
      _busyRequestId = id;
      _message = null;
    });
    try {
      await callback(id, decision);
      if (!mounted) return;
      setState(() {
        _message = decision == GovernanceDecision.approved
            ? _copy(context, 'Onay kararı yetkili kontrol düzlemine gönderildi.',
                'Approval decision was sent to the authoritative control plane.')
            : _copy(context, 'Red kararı yetkili kontrol düzlemine gönderildi.',
                'Denial decision was sent to the authoritative control plane.');
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _message = error.toString());
    } finally {
      if (mounted) setState(() => _busyRequestId = null);
    }
  }

  bool _decisionAllowed(Map<String, Object?> request) {
    if (_normalizedStatus(request) != 'pending' || widget.onDecision == null) {
      return false;
    }
    final id = _requestId(request);
    final requester = _string(request, const ['requester_id', 'requester']);
    if (id == null || widget.approverId == null) return false;
    return requester == null || widget.approverId != requester;
  }

  void _clearFilters() {
    _searchController.clear();
    setState(() {
      _activeTab = 'all';
      _riskFilter = 'all';
    });
  }

  @override
  Widget build(BuildContext context) {
    final requests = _requests;
    final available = _rawWork != null;
    final selected = _selected;
    final counts = _Counts.from(requests, available: available);
    final violations = _violationRows(widget.snapshot.governanceState);

    return Container(
      key: const Key('reference-approvals-page'),
      padding: const EdgeInsets.fromLTRB(18, 10, 18, 10),
      color: Theme.of(context).scaffoldBackgroundColor,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _PageHeader(status: widget.status),
          const SizedBox(height: 8),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final showRightRail = constraints.maxWidth >= 1080;
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          _TabsAndActions(
                            counts: counts,
                            activeTab: _activeTab,
                            hasFilters: _activeTab != 'all' ||
                                _riskFilter != 'all' ||
                                _searchController.text.trim().isNotEmpty,
                            onTabChanged: (value) =>
                                setState(() => _activeTab = value),
                            onClear: _clearFilters,
                          ),
                          const SizedBox(height: 6),
                          _Filters(
                            controller: _searchController,
                            riskFilter: _riskFilter,
                            onSearch: (_) => setState(() {}),
                            onRiskChanged: (value) =>
                                setState(() => _riskFilter = value ?? 'all'),
                          ),
                          const SizedBox(height: 6),
                          Expanded(
                            child: _RequestTable(
                              requests: _visibleRequests,
                              authoritativeAvailable: available,
                              selectedRequestId: _requestId(selected),
                              onSelect: (request) => setState(() {
                                _selectedRequestId = _requestId(request);
                              }),
                            ),
                          ),
                          if (requests.isNotEmpty || violations.isNotEmpty) ...[
                            const SizedBox(height: 8),
                            SizedBox(
                              height: 146,
                              child: _BottomCards(
                                requests: requests,
                                violations: violations,
                                available: available,
                              ),
                            ),
                          ],
                        ],
                      ),
                    ),
                    if (showRightRail && selected != null) ...[
                      const SizedBox(width: 14),
                      SizedBox(
                        width: 410,
                        child: _RightRail(
                          request: selected,
                          snapshot: widget.snapshot,
                          decisionAllowed: _decisionAllowed(selected),
                          busy: _busyRequestId == _requestId(selected),
                          message: _message,
                          onApprove: () => _decide(GovernanceDecision.approved),
                          onDeny: () => _decide(GovernanceDecision.denied),
                        ),
                      ),
                    ],
                  ],
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

class _PageHeader extends StatelessWidget {
  const _PageHeader({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) => SizedBox(
        key: const Key('approvals-header'),
        height: 48,
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _copy(context, 'Onaylar', 'Approvals'),
                    style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                          fontSize: 22,
                          fontWeight: FontWeight.w700,
                        ),
                  ),
                  const SizedBox(height: 1),
                  Text(
                    _copy(
                      context,
                      'Bekleyen, onaylanan ve reddedilen talepleri inceleyin ve yönetin.',
                      'Review and manage pending, approved and denied requests.',
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(fontSize: 10.2),
                  ),
                ],
              ),
            ),
            Container(
              constraints: const BoxConstraints(maxWidth: 245),
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
              decoration: BoxDecoration(
                color: _statusConnected(status)
                    ? IlaiosTheme.success.withValues(alpha: .08)
                    : Theme.of(context).colorScheme.surfaceContainerLow,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: _statusConnected(status)
                      ? IlaiosTheme.success.withValues(alpha: .26)
                      : Theme.of(context).colorScheme.outlineVariant,
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.circle,
                    size: 6,
                    color: _statusConnected(status)
                        ? IlaiosTheme.success
                        : Theme.of(context).colorScheme.outline,
                  ),
                  const SizedBox(width: 5),
                  Flexible(
                    child: Text(
                      _localizedStatus(context, status),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 8.7,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _TabsAndActions extends StatelessWidget {
  const _TabsAndActions({
    required this.counts,
    required this.activeTab,
    required this.hasFilters,
    required this.onTabChanged,
    required this.onClear,
  });

  final _Counts counts;
  final String activeTab;
  final bool hasFilters;
  final ValueChanged<String> onTabChanged;
  final VoidCallback onClear;

  @override
  Widget build(BuildContext context) {
    final tabs = <({String code, String label})>[
      (code: 'all', label: _copy(context, 'Tümü', 'All')),
      (code: 'pending', label: '${_copy(context, 'Bekleyen', 'Pending')} (${counts.display(counts.pending)})'),
      (code: 'approved', label: '${_copy(context, 'Onaylanan', 'Approved')} (${counts.display(counts.approved)})'),
      (code: 'denied', label: '${_copy(context, 'Reddedilen', 'Denied')} (${counts.display(counts.denied)})'),
      (code: 'high', label: '${_copy(context, 'Yüksek Risk', 'High Risk')} (${counts.display(counts.highRisk)})'),
      (code: 'archive', label: _copy(context, 'Arşiv', 'Archive')),
    ];
    return SizedBox(
      key: const Key('approvals-tabs'),
      height: 35,
      child: Row(
        children: [
          Expanded(
            child: Container(
              decoration: _cardDecoration(context, radius: 6),
              child: Row(
                children: [
                  for (final tab in tabs)
                    Expanded(
                      child: InkWell(
                        onTap: () => onTabChanged(tab.code),
                        child: Container(
                          alignment: Alignment.center,
                          decoration: BoxDecoration(
                            border: Border(
                              bottom: BorderSide(
                                width: 2,
                                color: activeTab == tab.code
                                    ? IlaiosTheme.coreBlue
                                    : Colors.transparent,
                              ),
                            ),
                          ),
                          child: Text(
                            tab.label,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                            style: TextStyle(
                              fontSize: 8.4,
                              fontWeight: activeTab == tab.code
                                  ? FontWeight.w700
                                  : FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                    ),
                ],
              ),
            ),
          ),
          if (hasFilters) ...[
            const SizedBox(width: 8),
            _TinyAction(
              icon: Icons.filter_alt_off_outlined,
              label: _copy(context, 'Filtreleri Temizle', 'Clear Filters'),
              onTap: onClear,
              prominent: false,
            ),
          ],
        ],
      ),
    );
  }
}

class _TinyAction extends StatelessWidget {
  const _TinyAction({
    required this.icon,
    required this.label,
    this.onTap,
    this.prominent = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final bool prominent;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    final effectiveProminent = prominent && enabled;
    final child = Material(
      color: effectiveProminent
          ? IlaiosTheme.coreBlue
          : Theme.of(context).colorScheme.surfaceContainerLowest,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(5),
        side: BorderSide(
          color: effectiveProminent
              ? IlaiosTheme.coreBlue
              : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Row(
            children: [
              Icon(
                icon,
                size: 14,
                color: effectiveProminent
                    ? Colors.white
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 5),
              Text(
                label,
                style: TextStyle(
                  fontSize: 8.5,
                  fontWeight: FontWeight.w600,
                  color: effectiveProminent ? Colors.white : null,
                ),
              ),
            ],
          ),
        ),
      ),
    );
    return Semantics(
      enabled: enabled,
      button: true,
      child: enabled ? child : Opacity(opacity: .45, child: child),
    );
  }
}

class _Filters extends StatelessWidget {
  const _Filters({
    required this.controller,
    required this.riskFilter,
    required this.onSearch,
    required this.onRiskChanged,
  });

  final TextEditingController controller;
  final String riskFilter;
  final ValueChanged<String> onSearch;
  final ValueChanged<String?> onRiskChanged;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('approvals-filters'),
        height: 44,
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
        decoration: _cardDecoration(context, radius: 6),
        child: Row(
          children: [
            Expanded(
              flex: 2,
              child: _FilterSearch(
                controller: controller,
                onChanged: onSearch,
                hint: _copy(context, 'Talep ara', 'Search requests'),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _StaticFilter(
                label: _copy(context, 'Talep Türü', 'Request Type'),
                value: _copy(context, 'Tümü', 'All'),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: DropdownButtonFormField<String>(
                value: riskFilter,
                isDense: true,
                decoration: InputDecoration(
                  labelText: _copy(context, 'Risk', 'Risk'),
                  contentPadding:
                      const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                ),
                style: TextStyle(
                  fontSize: 8.4,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
                items: <String, String>{
                  'all': _copy(context, 'Tümü', 'All'),
                  'high': _copy(context, 'Yüksek', 'High'),
                  'medium': _copy(context, 'Orta', 'Medium'),
                  'low': _copy(context, 'Düşük', 'Low'),
                }
                    .entries
                    .map((entry) => DropdownMenuItem(
                          value: entry.key,
                          child: Text(entry.value),
                        ))
                    .toList(growable: false),
                onChanged: onRiskChanged,
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _StaticFilter(
                label: _copy(context, 'İsteyen Ajan', 'Requester'),
                value: _copy(context, 'Tümü', 'All'),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _StaticFilter(
                label: _copy(context, 'Sahip', 'Owner'),
                value: _copy(context, 'Tümü', 'All'),
              ),
            ),
            const SizedBox(width: 6),
            Expanded(
              child: _StaticFilter(
                label: _copy(context, 'Tarih Aralığı', 'Date Range'),
                value: _copy(context, 'Son 30 gün', 'Last 30 days'),
                icon: Icons.calendar_today_outlined,
              ),
            ),
          ],
        ),
      );
}

class _FilterSearch extends StatelessWidget {
  const _FilterSearch({
    required this.controller,
    required this.onChanged,
    required this.hint,
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final String hint;

  @override
  Widget build(BuildContext context) => TextField(
        controller: controller,
        onChanged: onChanged,
        style: const TextStyle(fontSize: 8.6),
        decoration: InputDecoration(
          hintText: hint,
          prefixIcon: const Icon(Icons.search, size: 14),
          prefixIconConstraints: const BoxConstraints(minWidth: 28),
          contentPadding: const EdgeInsets.symmetric(horizontal: 7, vertical: 6),
        ),
      );
}

class _StaticFilter extends StatelessWidget {
  const _StaticFilter({
    required this.label,
    required this.value,
    this.icon = Icons.keyboard_arrow_down_rounded,
  });

  final String label;
  final String value;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: const TextStyle(fontSize: 6.8)),
                  Text(
                    value,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
            Icon(icon, size: 12),
          ],
        ),
      );
}

class _RequestTable extends StatelessWidget {
  const _RequestTable({
    required this.requests,
    required this.authoritativeAvailable,
    required this.selectedRequestId,
    required this.onSelect,
  });

  final List<Map<String, Object?>> requests;
  final bool authoritativeAvailable;
  final String? selectedRequestId;
  final ValueChanged<Map<String, Object?>> onSelect;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('approvals-table'),
        decoration: _cardDecoration(context, radius: 6),
        clipBehavior: Clip.antiAlias,
        child: Column(
          children: [
            const _TableHeader(),
            Expanded(
              child: requests.isEmpty
                  ? _TableEmpty(authoritativeAvailable: authoritativeAvailable)
                  : ListView.builder(
                      padding: EdgeInsets.zero,
                      itemCount: math.min(10, requests.length),
                      itemExtent: 31,
                      itemBuilder: (context, index) {
                        final request = requests[index];
                        return _RequestRow(
                          request: request,
                          selected: _requestId(request) == selectedRequestId,
                          onTap: () => onSelect(request),
                        );
                      },
                    ),
            ),
            Container(
              height: 31,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: BoxDecoration(
                border: Border(
                  top: BorderSide(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
              ),
              child: Row(
                children: [
                  Text(
                    requests.isEmpty
                        ? _copy(context, '0 sonuç', '0 results')
                        : '1 – ${math.min(10, requests.length)} / ${requests.length} ${_copy(context, 'sonuç', 'results')}',
                    style: const TextStyle(fontSize: 8),
                  ),
                  const Spacer(),
                  for (final page in const ['‹', '1', '2', '3', '4', '5', '…']) ...[
                    Container(
                      width: 23,
                      height: 22,
                      margin: const EdgeInsets.only(left: 3),
                      alignment: Alignment.center,
                      decoration: BoxDecoration(
                        color: page == '1'
                            ? IlaiosTheme.coreBlue.withValues(alpha: .10)
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: page == '1'
                              ? IlaiosTheme.coreBlue
                              : Theme.of(context).colorScheme.outlineVariant,
                        ),
                      ),
                      child: Text(page, style: const TextStyle(fontSize: 8)),
                    ),
                  ],
                  const SizedBox(width: 8),
                  Text(
                    _copy(context, '10 / sayfa', '10 / page'),
                    style: const TextStyle(fontSize: 8),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _TableHeader extends StatelessWidget {
  const _TableHeader();

  @override
  Widget build(BuildContext context) => Container(
        height: 29,
        padding: const EdgeInsets.symmetric(horizontal: 9),
        color: Theme.of(context).colorScheme.surfaceContainerLow,
        child: const Row(
          children: [
            _Cell(text: 'Talep', flex: 22, header: true),
            _Cell(text: 'Talep Türü', flex: 11, header: true),
            _Cell(text: 'İsteyen Ajan', flex: 12, header: true),
            _Cell(text: 'Risk', flex: 8, header: true),
            _Cell(text: 'Gerekçe', flex: 24, header: true),
            _Cell(text: 'Oluşturma Tarihi', flex: 13, header: true),
            _Cell(text: 'Bekleme Süresi', flex: 10, header: true),
            _Cell(text: 'Durum', flex: 10, header: true),
            SizedBox(width: 18),
          ],
        ),
      );
}

class _RequestRow extends StatelessWidget {
  const _RequestRow({
    required this.request,
    required this.selected,
    required this.onTap,
  });

  final Map<String, Object?> request;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final risk = _normalizedRisk(request);
    final status = _normalizedStatus(request);
    return Material(
      color: selected
          ? IlaiosTheme.coreBlue.withValues(alpha: .06)
          : Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 9),
          decoration: BoxDecoration(
            border: Border(
              bottom: BorderSide(
                color: Theme.of(context)
                    .colorScheme
                    .outlineVariant
                    .withValues(alpha: .65),
              ),
            ),
          ),
          child: Row(
            children: [
              Expanded(
                flex: 22,
                child: Row(
                  children: [
                    Icon(
                      _requestIcon(request),
                      size: 13,
                      color: _statusColor(status),
                    ),
                    const SizedBox(width: 5),
                    Expanded(
                      child: Text(
                        _requestTitle(request),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600),
                      ),
                    ),
                  ],
                ),
              ),
              _Cell(
                text: _string(request, const ['request_type', 'type', 'category']) ?? '—',
                flex: 11,
              ),
              _Cell(
                text: _string(request, const ['requester_name', 'requester_id', 'requester']) ?? '—',
                flex: 12,
              ),
              Expanded(
                flex: 8,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: _Pill(
                    text: _riskLabel(context, risk),
                    color: _riskColor(risk),
                  ),
                ),
              ),
              _Cell(
                text: _string(request, const ['reason', 'justification', 'summary', 'objective']) ?? '—',
                flex: 24,
              ),
              _Cell(
                text: _dateText(_value(request, const ['created_at', 'created', 'timestamp'])),
                flex: 13,
              ),
              _Cell(
                text: _waitText(request),
                flex: 10,
              ),
              Expanded(
                flex: 10,
                child: Align(
                  alignment: Alignment.centerLeft,
                  child: _Pill(
                    text: _statusLabel(context, status),
                    color: _statusColor(status),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Cell extends StatelessWidget {
  const _Cell({required this.text, required this.flex, this.header = false});

  final String text;
  final int flex;
  final bool header;

  @override
  Widget build(BuildContext context) => Expanded(
        flex: flex,
        child: Text(
          text,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: header ? 7.6 : 7.8,
            fontWeight: header ? FontWeight.w700 : FontWeight.w400,
            color: header
                ? Theme.of(context).colorScheme.onSurfaceVariant
                : null,
          ),
        ),
      );
}

class _TableEmpty extends StatelessWidget {
  const _TableEmpty({required this.authoritativeAvailable});

  final bool authoritativeAvailable;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.task_alt_outlined,
              size: 28,
              color: Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(height: 5),
            Text(
              authoritativeAvailable
                  ? _copy(context, 'Eşleşen onay talebi yok.', 'No matching approval request.')
                  : _copy(context, 'Yönetişim verisi kullanılamıyor.', 'Governance data is unavailable.'),
              style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      );
}

class _RightRail extends StatelessWidget {
  const _RightRail({
    required this.request,
    required this.snapshot,
    required this.decisionAllowed,
    required this.busy,
    required this.message,
    required this.onApprove,
    required this.onDeny,
  });

  final Map<String, Object?>? request;
  final OperationalSnapshot snapshot;
  final bool decisionAllowed;
  final bool busy;
  final String? message;
  final VoidCallback onApprove;
  final VoidCallback onDeny;

  @override
  Widget build(BuildContext context) => Column(
        key: const Key('approvals-right-rail'),
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: _SelectedRequestCard(
              request: request,
              snapshot: snapshot,
              decisionAllowed: decisionAllowed,
              busy: busy,
              message: message,
              onApprove: onApprove,
              onDeny: onDeny,
            ),
          ),
          const SizedBox(height: 8),
          SizedBox(height: 90, child: _ReviewNotes(request: request)),
          const SizedBox(height: 8),
          SizedBox(height: 72, child: _AuditHistory(request: request)),
        ],
      );
}

class _SelectedRequestCard extends StatelessWidget {
  const _SelectedRequestCard({
    required this.request,
    required this.snapshot,
    required this.decisionAllowed,
    required this.busy,
    required this.message,
    required this.onApprove,
    required this.onDeny,
  });

  final Map<String, Object?>? request;
  final OperationalSnapshot snapshot;
  final bool decisionAllowed;
  final bool busy;
  final String? message;
  final VoidCallback onApprove;
  final VoidCallback onDeny;

  @override
  Widget build(BuildContext context) {
    final item = request;
    if (item == null) {
      return Container(
        decoration: _cardDecoration(context, radius: 7),
        padding: const EdgeInsets.all(14),
        child: Center(
          child: Text(
            _copy(context, 'Seçili talep yok', 'No request selected'),
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w600),
          ),
        ),
      );
    }
    final id = _requestId(item) ?? '—';
    final risk = _normalizedRisk(item);
    final status = _normalizedStatus(item);
    final requester =
        _string(item, const ['requester_name', 'requester_id', 'requester']) ?? '—';
    final owner = _string(item, const ['owner_name', 'owner', 'approver']) ?? '—';
    final scope = _scopeValues(item);
    final matchingEvidence = snapshot.evidenceRecords
        .where((record) => record.executionId == id)
        .take(5)
        .toList(growable: false);

    return Container(
      key: const Key('approvals-selected-request'),
      decoration: _cardDecoration(context, radius: 7),
      padding: const EdgeInsets.fromLTRB(13, 10, 13, 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(
                _copy(context, 'Seçili Talep', 'Selected Request'),
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              const Icon(Icons.ios_share_outlined, size: 14),
              const SizedBox(width: 12),
              const Icon(Icons.keyboard_arrow_up_rounded, size: 16),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: IlaiosTheme.violet.withValues(alpha: .12),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Icon(
                  _requestIcon(item),
                  color: IlaiosTheme.violet,
                  size: 22,
                ),
              ),
              const SizedBox(width: 9),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _requestTitle(item),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      _string(item, const ['request_type', 'type', 'category']) ??
                          _copy(context, 'Onay Talebi', 'Approval Request'),
                      style: Theme.of(context)
                          .textTheme
                          .bodySmall
                          ?.copyWith(fontSize: 8),
                    ),
                  ],
                ),
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  _Pill(text: _statusLabel(context, status), color: _statusColor(status)),
                  const SizedBox(height: 3),
                  Text('ID: $id', style: const TextStyle(fontSize: 7.1)),
                ],
              ),
            ],
          ),
          const SizedBox(height: 9),
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          const SizedBox(height: 8),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: _DetailsBlock(
                  title: _copy(context, 'Mevcut Durum', 'Current State'),
                  rows: [
                    (_copy(context, 'İsteyen', 'Requester'), requester),
                    (_copy(context, 'Sahip', 'Owner'), owner),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _DetailsBlock(
                  title: _copy(context, 'Kategori', 'Category'),
                  rows: [
                    (_copy(context, 'Risk Seviyesi', 'Risk Level'), _riskLabel(context, risk)),
                    (_copy(context, 'Oluşturma', 'Created'), _dateText(_value(item, const ['created_at', 'created', 'timestamp']))),
                    (_copy(context, 'Son Tarih', 'Due'), _dateText(_value(item, const ['due_at', 'deadline', 'sla_due_at']))),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 7),
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          const SizedBox(height: 7),
          Text(
            _copy(context, 'Gerekçe Özeti', 'Reason Summary'),
            style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 3),
          Text(
            _string(item, const ['reason', 'justification', 'summary', 'objective']) ?? '—',
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 7.8, height: 1.25),
          ),
          const SizedBox(height: 7),
          Text(
            _copy(context, 'Etkilenen Kapsam', 'Affected Scope'),
            style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 4),
          SizedBox(
            height: 22,
            child: ListView(
              scrollDirection: Axis.horizontal,
              children: scope.isEmpty
                  ? [const _ScopeChip(label: '—')]
                  : scope.take(5).map((value) => _ScopeChip(label: value)).toList(),
            ),
          ),
          const SizedBox(height: 7),
          Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
          const SizedBox(height: 7),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _copy(context, 'Kanıtlar', 'Evidence'),
                      style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 4),
                    if (matchingEvidence.isEmpty)
                      Text(
                        _copy(context, 'Eşleşen kanıt kaydı yok', 'No matching evidence record'),
                        style: const TextStyle(fontSize: 7.3),
                      )
                    else
                      for (final record in matchingEvidence)
                        _EvidenceLine(label: record.action),
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: _Workflow(status: status),
              ),
            ],
          ),
          const Spacer(),
          if (message case final text?) ...[
            Text(
              text,
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 7.3),
            ),
            const SizedBox(height: 5),
          ],
          Row(
            children: [
              Expanded(
                child: FilledButton.icon(
                  key: ValueKey('approve-$id'),
                  style: FilledButton.styleFrom(
                    backgroundColor: IlaiosTheme.success,
                    foregroundColor: IlaiosTheme.carbon,
                    minimumSize: const Size(0, 33),
                    padding: EdgeInsets.zero,
                  ),
                  onPressed: decisionAllowed && !busy ? onApprove : null,
                  icon: busy
                      ? const SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(strokeWidth: 1.6),
                        )
                      : const Icon(Icons.check_circle_outline, size: 15),
                  label: Text(_copy(context, 'Onayla', 'Approve')),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: FilledButton.icon(
                  key: ValueKey('deny-$id'),
                  style: FilledButton.styleFrom(
                    backgroundColor: IlaiosTheme.danger,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(0, 33),
                    padding: EdgeInsets.zero,
                  ),
                  onPressed: decisionAllowed && !busy ? onDeny : null,
                  icon: const Icon(Icons.close, size: 15),
                  label: Text(_copy(context, 'Reddet', 'Deny')),
                ),
              ),
              const SizedBox(width: 8),
              Expanded(
                flex: 2,
                child: OutlinedButton(
                  onPressed: () {},
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size(0, 33),
                    padding: EdgeInsets.zero,
                  ),
                  child: Text(_copy(context, 'Detayları Gör', 'View Details')),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _DetailsBlock extends StatelessWidget {
  const _DetailsBlock({required this.title, required this.rows});

  final String title;
  final List<(String, String)> rows;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontSize: 7.4, fontWeight: FontWeight.w700)),
          const SizedBox(height: 4),
          for (final row in rows)
            Padding(
              padding: const EdgeInsets.only(bottom: 3),
              child: Row(
                children: [
                  SizedBox(width: 62, child: Text(row.$1, style: const TextStyle(fontSize: 6.9))),
                  Expanded(
                    child: Text(
                      row.$2,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 7.3, fontWeight: FontWeight.w600),
                    ),
                  ),
                ],
              ),
            ),
        ],
      );
}

class _ScopeChip extends StatelessWidget {
  const _ScopeChip({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Container(
        margin: const EdgeInsets.only(right: 5),
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHigh,
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(label, style: const TextStyle(fontSize: 7)),
      );
}

class _EvidenceLine extends StatelessWidget {
  const _EvidenceLine({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 3),
        child: Row(
          children: [
            const Icon(Icons.check_circle_outline, size: 11, color: IlaiosTheme.success),
            const SizedBox(width: 4),
            Expanded(
              child: Text(
                label,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 7.1),
              ),
            ),
          ],
        ),
      );
}

class _Workflow extends StatelessWidget {
  const _Workflow({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final completed = status == 'approved' || status == 'denied';
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _copy(context, 'İş Akışı', 'Workflow'),
          style: const TextStyle(fontSize: 8.8, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 9),
        Row(
          children: [
            const _StageDot(active: true, done: true),
            const Expanded(child: _StageLine(active: true)),
            _StageDot(active: status == 'pending', done: completed),
            const Expanded(child: _StageLine(active: false)),
            _StageDot(active: false, done: completed),
            const Expanded(child: _StageLine(active: false)),
            _StageDot(active: false, done: completed),
          ],
        ),
        const SizedBox(height: 5),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(_copy(context, 'İstek', 'Request'), style: const TextStyle(fontSize: 6.4)),
            Text(_copy(context, 'İnceleme', 'Review'), style: const TextStyle(fontSize: 6.4)),
            Text(_copy(context, 'Güvenlik', 'Security'), style: const TextStyle(fontSize: 6.4)),
            Text(_copy(context, 'Onay', 'Decision'), style: const TextStyle(fontSize: 6.4)),
          ],
        ),
      ],
    );
  }
}

class _StageDot extends StatelessWidget {
  const _StageDot({required this.active, required this.done});

  final bool active;
  final bool done;

  @override
  Widget build(BuildContext context) => Container(
        width: 17,
        height: 17,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: done
              ? IlaiosTheme.success.withValues(alpha: .12)
              : Colors.transparent,
          border: Border.all(
            width: 1.5,
            color: active
                ? IlaiosTheme.coreBlue
                : done
                    ? IlaiosTheme.success
                    : Theme.of(context).colorScheme.outline,
          ),
        ),
        child: done
            ? const Icon(Icons.check, size: 10, color: IlaiosTheme.success)
            : active
                ? const Center(
                    child: Icon(Icons.circle, size: 5, color: IlaiosTheme.coreBlue),
                  )
                : null,
      );
}

class _StageLine extends StatelessWidget {
  const _StageLine({required this.active});

  final bool active;

  @override
  Widget build(BuildContext context) => Container(
        height: 1,
        color: active
            ? IlaiosTheme.coreBlue
            : Theme.of(context).colorScheme.outlineVariant,
      );
}

class _ReviewNotes extends StatelessWidget {
  const _ReviewNotes({required this.request});

  final Map<String, Object?>? request;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _cardDecoration(context, radius: 7),
        padding: const EdgeInsets.fromLTRB(12, 9, 12, 9),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Text(
                  _copy(context, 'İnceleme Notları', 'Review Notes'),
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                ),
                const Spacer(),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              _string(request, const ['review_note', 'note', 'review_notes']) ??
                  _copy(context, 'Kayıtlı inceleme notu yok.', 'No recorded review note.'),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 7.4),
            ),
          ],
        ),
      );
}

class _AuditHistory extends StatelessWidget {
  const _AuditHistory({required this.request});

  final Map<String, Object?>? request;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _cardDecoration(context, radius: 7),
        padding: const EdgeInsets.fromLTRB(12, 9, 12, 9),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Text(
                  _copy(context, 'Denetim Geçmişi', 'Audit History'),
                  style: const TextStyle(fontSize: 9, fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                Text(_copy(context, 'Tümü ›', 'All ›'), style: const TextStyle(fontSize: 7)),
              ],
            ),
            const Spacer(),
            Row(
              children: [
                Expanded(
                  child: Text(
                    request == null
                        ? '—'
                        : _copy(context, 'Talep kaydı yüklendi', 'Request record loaded'),
                    style: const TextStyle(fontSize: 7.3),
                  ),
                ),
                Text(
                  _dateText(_value(request, const ['created_at', 'created', 'timestamp'])),
                  style: const TextStyle(fontSize: 7.1),
                ),
              ],
            ),
          ],
        ),
      );
}

class _BottomCards extends StatelessWidget {
  const _BottomCards({
    required this.requests,
    required this.violations,
    required this.available,
  });

  final List<Map<String, Object?>> requests;
  final List<Map<String, Object?>> violations;
  final bool available;

  @override
  Widget build(BuildContext context) {
    final recent = requests
        .where((item) => _normalizedStatus(item) != 'pending')
        .take(4)
        .toList(growable: false);
    final critical = requests
        .where((item) =>
            _normalizedStatus(item) == 'pending' && _normalizedRisk(item) == 'high')
        .take(4)
        .toList(growable: false);
    return Row(
      children: [
        Expanded(
          child: _MiniListCard(
            title: _copy(context, 'Son Kararlar', 'Recent Decisions'),
            rows: recent
                .map((item) => (_requestTitle(item), _statusLabel(context, _normalizedStatus(item))))
                .toList(growable: false),
            empty: available ? '—' : _copy(context, 'Veri yok', 'Unavailable'),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MiniListCard(
            title: _copy(context, 'Bekleyen Kritik Talepler', 'Critical Pending Requests'),
            rows: critical
                .map((item) => (_requestTitle(item), _waitText(item)))
                .toList(growable: false),
            empty: available ? '—' : _copy(context, 'Veri yok', 'Unavailable'),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _MiniListCard(
            title: _copy(context, 'Politika İhlal Uyarıları', 'Policy Violation Alerts'),
            rows: violations
                .take(4)
                .map((item) => (
                      _string(item, const ['title', 'rule', 'message', 'type']) ?? '—',
                      _dateText(_value(item, const ['created_at', 'timestamp'])),
                    ))
                .toList(growable: false),
            empty: available ? '—' : _copy(context, 'Veri yok', 'Unavailable'),
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: _DistributionCard(requests: requests, available: available),
        ),
      ],
    );
  }
}

class _MiniListCard extends StatelessWidget {
  const _MiniListCard({
    required this.title,
    required this.rows,
    required this.empty,
  });

  final String title;
  final List<(String, String)> rows;
  final String empty;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 7),
        decoration: _cardDecoration(context, radius: 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(title, style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w700)),
                ),
                Text(_copy(context, 'Tümü ›', 'All ›'), style: const TextStyle(fontSize: 6.8)),
              ],
            ),
            const SizedBox(height: 7),
            if (rows.isEmpty)
              Expanded(child: Center(child: Text(empty, style: const TextStyle(fontSize: 8))))
            else
              for (final row in rows)
                Padding(
                  padding: const EdgeInsets.only(bottom: 6),
                  child: Row(
                    children: [
                      const Icon(Icons.circle, size: 6, color: IlaiosTheme.coreBlue),
                      const SizedBox(width: 5),
                      Expanded(
                        child: Text(
                          row.$1,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 7.1),
                        ),
                      ),
                      const SizedBox(width: 5),
                      Text(row.$2, style: const TextStyle(fontSize: 6.8)),
                    ],
                  ),
                ),
          ],
        ),
      );
}

class _DistributionCard extends StatelessWidget {
  const _DistributionCard({required this.requests, required this.available});

  final List<Map<String, Object?>> requests;
  final bool available;

  @override
  Widget build(BuildContext context) {
    final buckets = <String, int>{};
    for (final item in requests) {
      final category =
          _string(item, const ['request_type', 'type', 'category']) ??
              _copy(context, 'Diğer', 'Other');
      buckets[category] = (buckets[category] ?? 0) + 1;
    }
    final entries = buckets.entries.toList(growable: false)
      ..sort((a, b) => b.value.compareTo(a.value));
    return Container(
      key: const Key('approvals-distribution'),
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 7),
      decoration: _cardDecoration(context, radius: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  _copy(context, 'Talep Dağılımı', 'Request Distribution'),
                  style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w700),
                ),
              ),
              Text(_copy(context, 'Tümü ›', 'All ›'), style: const TextStyle(fontSize: 6.8)),
            ],
          ),
          const SizedBox(height: 6),
          Expanded(
            child: Row(
              children: [
                SizedBox(
                  width: 76,
                  height: 76,
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      CustomPaint(
                        size: const Size.square(76),
                        painter: _DonutPainter(
                          values: entries.take(6).map((entry) => entry.value).toList(growable: false),
                        ),
                      ),
                      Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            available ? '${requests.length}' : '—',
                            style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
                          ),
                          Text(_copy(context, 'Toplam', 'Total'), style: const TextStyle(fontSize: 6.3)),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: entries.isEmpty
                        ? [Text('—', style: const TextStyle(fontSize: 7))]
                        : entries.take(5).map((entry) {
                            return Padding(
                              padding: const EdgeInsets.only(bottom: 3),
                              child: Row(
                                children: [
                                  const Icon(Icons.circle, size: 5, color: IlaiosTheme.coreBlue),
                                  const SizedBox(width: 4),
                                  Expanded(
                                    child: Text(
                                      entry.key,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 6.7),
                                    ),
                                  ),
                                  Text('${entry.value}', style: const TextStyle(fontSize: 6.7)),
                                ],
                              ),
                            );
                          }).toList(growable: false),
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

class _DonutPainter extends CustomPainter {
  const _DonutPainter({required this.values});

  final List<int> values;

  static const colors = <Color>[
    IlaiosTheme.coreBlue,
    IlaiosTheme.violet,
    IlaiosTheme.warning,
    IlaiosTheme.success,
    IlaiosTheme.danger,
    IlaiosTheme.enterpriseCyan,
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final total = values.fold<int>(0, (sum, value) => sum + value);
    final rect = Offset.zero & size;
    final background = Paint()
      ..color = const Color(0x335F6B7A)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 9;
    canvas.drawArc(rect.deflate(7), 0, math.pi * 2, false, background);
    if (total <= 0) return;
    var start = -math.pi / 2;
    for (var index = 0; index < values.length; index++) {
      final sweep = math.pi * 2 * values[index] / total;
      final paint = Paint()
        ..color = colors[index % colors.length]
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.butt
        ..strokeWidth = 9;
      canvas.drawArc(rect.deflate(7), start, math.max(0, sweep - .025), false, paint);
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(covariant _DonutPainter oldDelegate) =>
      oldDelegate.values != values;
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .13),
          borderRadius: BorderRadius.circular(4),
        ),
        child: Text(
          text,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 6.9, fontWeight: FontWeight.w700, color: color),
        ),
      );
}

class _Counts {
  const _Counts({
    required this.available,
    required this.total,
    required this.pending,
    required this.approved,
    required this.denied,
    required this.highRisk,
  });

  factory _Counts.from(
    List<Map<String, Object?>> requests, {
    required bool available,
  }) {
    var pending = 0;
    var approved = 0;
    var denied = 0;
    var high = 0;
    for (final item in requests) {
      switch (_normalizedStatus(item)) {
        case 'pending':
          pending += 1;
        case 'approved':
          approved += 1;
        case 'denied':
          denied += 1;
      }
      if (_normalizedRisk(item) == 'high') high += 1;
    }
    return _Counts(
      available: available,
      total: requests.length,
      pending: pending,
      approved: approved,
      denied: denied,
      highRisk: high,
    );
  }

  final bool available;
  final int total;
  final int pending;
  final int approved;
  final int denied;
  final int highRisk;

  String display(int value) => available ? '$value' : '—';
}

BoxDecoration _cardDecoration(BuildContext context, {double radius = 8}) =>
    BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(radius),
      border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    );

String _copy(BuildContext context, String tr, String en) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish ? tr : en;

bool _statusConnected(String status) {
  final normalized = status.toLowerCase();
  return normalized.contains('connected') ||
      normalized.contains('accepted') ||
      normalized.contains('started') ||
      normalized.contains('saved');
}

String _localizedStatus(BuildContext context, String status) {
  if (_statusConnected(status)) {
    return _copy(context, 'Bağlı', 'Connected');
  }
  if (status.trim().isEmpty) return '—';
  return status;
}

Object? _value(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value != null) return value;
  }
  return null;
}

String? _string(Map<String, Object?>? source, List<String> keys) {
  final value = _value(source, keys);
  if (value == null) return null;
  final text = value.toString().trim();
  return text.isEmpty ? null : text;
}

String? _requestId(Map<String, Object?>? request) =>
    _string(request, const ['request_id', 'id']);

String _requestTitle(Map<String, Object?> request) =>
    _string(request, const ['title', 'request_name', 'name', 'action', 'operation']) ??
    _requestId(request) ??
    '—';

String _normalizedStatus(Map<String, Object?> request) {
  final raw = (_string(request, const ['status', 'decision', 'state']) ?? '')
      .toLowerCase();
  if (raw.contains('approv') || raw == 'allow' || raw == 'accepted') {
    return 'approved';
  }
  if (raw.contains('deny') || raw.contains('reject') || raw == 'blocked') {
    return 'denied';
  }
  if (raw.contains('pend') || raw.contains('wait') || raw.contains('review')) {
    return 'pending';
  }
  return raw.isEmpty ? 'unknown' : raw;
}

String _normalizedRisk(Map<String, Object?> request) {
  final raw = (_string(request, const ['risk', 'risk_level', 'severity']) ?? '')
      .toLowerCase();
  if (raw.contains('high') || raw.contains('critical') || raw.contains('yüksek')) {
    return 'high';
  }
  if (raw.contains('medium') || raw.contains('moderate') || raw.contains('orta')) {
    return 'medium';
  }
  if (raw.contains('low') || raw.contains('düşük')) return 'low';
  return 'unknown';
}

String _statusLabel(BuildContext context, String status) => switch (status) {
      'pending' => _copy(context, 'Bekliyor', 'Pending'),
      'approved' => _copy(context, 'Onaylandı', 'Approved'),
      'denied' => _copy(context, 'Reddedildi', 'Denied'),
      _ => _copy(context, 'Bilinmiyor', 'Unknown'),
    };

Color _statusColor(String status) => switch (status) {
      'pending' => IlaiosTheme.warning,
      'approved' => IlaiosTheme.success,
      'denied' => IlaiosTheme.danger,
      _ => IlaiosTheme.coreBlue,
    };

String _riskLabel(BuildContext context, String risk) => switch (risk) {
      'high' => _copy(context, 'Yüksek', 'High'),
      'medium' => _copy(context, 'Orta', 'Medium'),
      'low' => _copy(context, 'Düşük', 'Low'),
      _ => '—',
    };

Color _riskColor(String risk) => switch (risk) {
      'high' => IlaiosTheme.danger,
      'medium' => IlaiosTheme.warning,
      'low' => IlaiosTheme.success,
      _ => IlaiosTheme.coreBlue,
    };

IconData _requestIcon(Map<String, Object?> request) {
  final text = '${_requestTitle(request)} ${_string(request, const ['type', 'category']) ?? ''}'
      .toLowerCase();
  if (text.contains('deploy') || text.contains('release')) {
    return Icons.rocket_launch_outlined;
  }
  if (text.contains('api') || text.contains('network')) return Icons.key_outlined;
  if (text.contains('budget') || text.contains('finance')) return Icons.paid_outlined;
  if (text.contains('data') || text.contains('export')) return Icons.storage_outlined;
  if (text.contains('policy')) return Icons.policy_outlined;
  return Icons.task_alt_outlined;
}

String _dateText(Object? value) {
  if (value == null) return '—';
  if (value is int) {
    final date = DateTime.fromMillisecondsSinceEpoch(
      value < 1000000000000 ? value * 1000 : value,
    ).toLocal();
    return '${date.day.toString().padLeft(2, '0')}.${date.month.toString().padLeft(2, '0')} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
  final text = value.toString().trim();
  if (text.isEmpty) return '—';
  final parsed = DateTime.tryParse(text);
  if (parsed == null) return text.length <= 18 ? text : '${text.substring(0, 18)}…';
  final local = parsed.toLocal();
  return '${local.day.toString().padLeft(2, '0')}.${local.month.toString().padLeft(2, '0')}.${local.year} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
}

String _waitText(Map<String, Object?> request) {
  final raw = _value(
    request,
    const ['wait_seconds', 'waiting_seconds', 'age_seconds', 'wait_time_seconds'],
  );
  if (raw is num) {
    final seconds = raw.round().clamp(0, 315360000);
    final days = seconds ~/ 86400;
    final hours = (seconds % 86400) ~/ 3600;
    final minutes = (seconds % 3600) ~/ 60;
    if (days > 0) return '${days}g ${hours}s';
    if (hours > 0) return '${hours}s ${minutes}dk';
    return '${minutes}dk';
  }
  return '—';
}

List<String> _scopeValues(Map<String, Object?> request) {
  final raw = _value(
    request,
    const ['affected_scope', 'scope', 'resources', 'affected_resources'],
  );
  if (raw is List<Object?>) {
    return raw
        .map((item) => item.toString().trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }
  if (raw is String && raw.trim().isNotEmpty) {
    return raw
        .split(',')
        .map((item) => item.trim())
        .where((item) => item.isNotEmpty)
        .toList(growable: false);
  }
  return const <String>[];
}

List<Map<String, Object?>> _violationRows(Map<String, Object?> state) {
  for (final key in const ['violations', 'policy_violations', 'alerts']) {
    final raw = state[key];
    if (raw is List<Object?>) {
      return raw
          .whereType<Map<String, dynamic>>()
          .map((item) => Map<String, Object?>.from(item))
          .toList(growable: false);
    }
  }
  return const <Map<String, Object?>>[];
}
