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
      final id = _requestId(item);
      return id != null && required.contains(id);
    }).toList(growable: false);
  }

  List<Map<String, Object?>> get _visibleRequests {
    Iterable<Map<String, Object?>> requests = _requests;

    if (_activeTab == 'archive') {
      requests = requests.where((item) => _normalizedStatus(item) != 'pending');
    } else if (_activeTab != 'all') {
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

    if (_riskFilter != 'all') {
      requests = requests.where((item) => _normalizedRisk(item) == _riskFilter);
    }

    final query = _searchController.text.trim().toLowerCase();
    if (query.isNotEmpty) {
      requests = requests.where((item) {
        final haystack = <String?>[
          _requestTitle(item),
          _requestId(item),
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
    final selectedId = _selectedRequestId;
    if (selectedId == null) return null;
    for (final item in _visibleRequests) {
      if (_requestId(item) == selectedId) return item;
    }
    return null;
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
            ? _copy(
                context,
                'Onay kararı yetkili kontrol düzlemine gönderildi.',
                'Approval decision was sent to the authoritative control plane.',
              )
            : _copy(
                context,
                'Red kararı yetkili kontrol düzlemine gönderildi.',
                'Denial decision was sent to the authoritative control plane.',
              );
      });
    } on Object catch (error) {
      if (!mounted) return;
      setState(() => _message = error.toString());
    } finally {
      if (mounted) setState(() => _busyRequestId = null);
    }
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
    final visible = _visibleRequests;
    final available = _rawWork != null;
    final selected = _selected;
    final counts = _Counts.from(requests, available: available);

    return Container(
      key: const Key('reference-approvals-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(24, 18, 24, 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _PageHeader(status: widget.status),
          const SizedBox(height: 18),
          _TabsAndActions(
            counts: counts,
            activeTab: _activeTab,
            hasFilters: _activeTab != 'all' ||
                _riskFilter != 'all' ||
                _searchController.text.trim().isNotEmpty,
            onTabChanged: (value) => setState(() => _activeTab = value),
            onClear: _clearFilters,
          ),
          const SizedBox(height: 12),
          _Filters(
            controller: _searchController,
            riskFilter: _riskFilter,
            onSearch: (_) => setState(() {}),
            onRiskChanged: (value) =>
                setState(() => _riskFilter = value ?? 'all'),
          ),
          const SizedBox(height: 14),
          Expanded(
            child: LayoutBuilder(
              builder: (context, constraints) {
                final showDetail = constraints.maxWidth >= 1120;
                final table = _RequestTable(
                  requests: visible,
                  authoritativeAvailable: available,
                  selectedRequestId: _requestId(selected),
                  onSelect: (request) {
                    setState(() => _selectedRequestId = _requestId(request));
                  },
                );

                final detail = _RightRail(
                  request: selected,
                  snapshot: widget.snapshot,
                  decisionAllowed: selected != null && _decisionAllowed(selected),
                  busy: selected != null && _busyRequestId == _requestId(selected),
                  message: _message,
                  onApprove: () => _decide(GovernanceDecision.approved),
                  onDeny: () => _decide(GovernanceDecision.denied),
                );
                if (!showDetail) {
                  if (selected == null) return table;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton.icon(
                          key: const Key('approvals-back-to-queue'),
                          autofocus: true,
                          onPressed: () => setState(() => _selectedRequestId = null),
                          icon: const Icon(Icons.arrow_back),
                          label: Text(_copy(context, 'Karar Kuyruğu', 'Decision Queue')),
                        ),
                      ),
                      Expanded(child: detail),
                    ],
                  );
                }

                return Row(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Expanded(child: table),
                    const SizedBox(width: 16),
                    SizedBox(
                      width: 390,
                      child: detail,
                    ),
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
  Widget build(BuildContext context) => Row(
        key: const Key('approvals-header'),
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _copy(context, 'Onaylar', 'Approvals'),
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontSize: 28,
                        fontWeight: FontWeight.w700,
                        height: 1.15,
                      ),
                ),
                const SizedBox(height: 6),
                Text(
                  _copy(
                    context,
                    'Bekleyen kararları inceleyin; sonuçlanan talepleri ve kanıt bağlamını takip edin.',
                    'Review pending decisions and track completed requests with their evidence context.',
                  ),
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        fontSize: 14,
                        height: 1.4,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 16),
          _StatusBadge(status: status),
        ],
      );
}

class _StatusBadge extends StatelessWidget {
  const _StatusBadge({required this.status});

  final String status;

  @override
  Widget build(BuildContext context) {
    final connected = _statusConnected(status);
    final color = connected
        ? IlaiosTheme.success
        : Theme.of(context).colorScheme.onSurfaceVariant;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      decoration: BoxDecoration(
        color: connected
            ? IlaiosTheme.success.withValues(alpha: .10)
            : Theme.of(context).colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(999),
        border: Border.all(
          color: connected
              ? IlaiosTheme.success.withValues(alpha: .32)
              : Theme.of(context).colorScheme.outlineVariant,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(Icons.circle, size: 8, color: color),
          const SizedBox(width: 7),
          Text(
            _localizedStatus(context, status),
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
        ],
      ),
    );
  }
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
      (
        code: 'pending',
        label:
            '${_copy(context, 'Bekleyen', 'Pending')} (${counts.display(counts.pending)})',
      ),
      (
        code: 'approved',
        label:
            '${_copy(context, 'Onaylanan', 'Approved')} (${counts.display(counts.approved)})',
      ),
      (
        code: 'denied',
        label:
            '${_copy(context, 'Reddedilen', 'Denied')} (${counts.display(counts.denied)})',
      ),
      (
        code: 'high',
        label:
            '${_copy(context, 'Yüksek Risk', 'High Risk')} (${counts.display(counts.highRisk)})',
      ),
      (code: 'archive', label: _copy(context, 'Arşiv', 'Archive')),
    ];

    return Row(
      key: const Key('approvals-tabs'),
      children: [
        Expanded(
          child: SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(
              children: [
                for (final tab in tabs) ...[
                  _TabButton(
                    label: tab.label,
                    selected: activeTab == tab.code,
                    onPressed: () => onTabChanged(tab.code),
                  ),
                  const SizedBox(width: 6),
                ],
              ],
            ),
          ),
        ),
        if (hasFilters) ...[
          const SizedBox(width: 12),
          TextButton.icon(
            onPressed: onClear,
            icon: const Icon(Icons.filter_alt_off_outlined, size: 18),
            label: Text(_copy(context, 'Filtreleri Temizle', 'Clear Filters')),
          ),
        ],
      ],
    );
  }
}

class _TabButton extends StatelessWidget {
  const _TabButton({
    required this.label,
    required this.selected,
    required this.onPressed,
  });

  final String label;
  final bool selected;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) => Semantics(
        button: true,
        selected: selected,
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(8),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
            decoration: BoxDecoration(
              color: selected
                  ? IlaiosTheme.enterpriseCyan.withValues(alpha: .10)
                  : Colors.transparent,
              borderRadius: BorderRadius.circular(8),
              border: Border.all(
                color: selected
                    ? IlaiosTheme.enterpriseCyan
                    : Theme.of(context).colorScheme.outlineVariant,
              ),
            ),
            child: Text(
              label,
              style: TextStyle(
                fontSize: 13.5,
                fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                color: selected ? IlaiosTheme.enterpriseCyan : null,
              ),
            ),
          ),
        ),
      );
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
        padding: const EdgeInsets.all(12),
        decoration: _cardDecoration(context),
        child: LayoutBuilder(
          builder: (context, constraints) {
            final stacked = constraints.maxWidth < 760;
            final search = TextField(
              controller: controller,
              onChanged: onSearch,
              style: const TextStyle(fontSize: 14),
              decoration: InputDecoration(
                hintText: _copy(context, 'Talep ara', 'Search requests'),
                prefixIcon: const Icon(Icons.search, size: 20),
              ),
            );
            final risk = DropdownButtonFormField<String>(
              value: riskFilter,
              decoration: InputDecoration(
                labelText: _copy(context, 'Risk', 'Risk'),
              ),
              style: TextStyle(
                fontSize: 14,
                color: Theme.of(context).colorScheme.onSurface,
              ),
              items: <String, String>{
                'all': _copy(context, 'Tümü', 'All'),
                'high': _copy(context, 'Yüksek', 'High'),
                'medium': _copy(context, 'Orta', 'Medium'),
                'low': _copy(context, 'Düşük', 'Low'),
              }
                  .entries
                  .map(
                    (entry) => DropdownMenuItem(
                      value: entry.key,
                      child: Text(entry.value),
                    ),
                  )
                  .toList(growable: false),
              onChanged: onRiskChanged,
            );

            if (stacked) {
              return Column(
                children: [
                  search,
                  const SizedBox(height: 10),
                  risk,
                ],
              );
            }

            return Row(
              children: [
                Expanded(flex: 3, child: search),
                const SizedBox(width: 12),
                Expanded(child: risk),
              ],
            );
          },
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
        decoration: _cardDecoration(context),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 12),
              child: Text(
                _copy(context, 'Karar Kuyruğu', 'Decision Queue'),
                style: const TextStyle(
                  fontSize: 17,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Divider(
              height: 1,
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
            Expanded(
              child: requests.isEmpty
                  ? _TableEmpty(
                      authoritativeAvailable: authoritativeAvailable,
                    )
                  : ListView.separated(
                      itemCount: requests.length,
                      separatorBuilder: (_, _) => Divider(
                        height: 1,
                        color: Theme.of(context)
                            .colorScheme
                            .outlineVariant
                            .withValues(alpha: .7),
                      ),
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
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLow,
                border: Border(
                  top: BorderSide(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
              ),
              child: Text(
                requests.isEmpty
                    ? _copy(context, '0 sonuç', '0 results')
                    : '${requests.length} ${_copy(context, 'sonuç', 'results')}',
                style: TextStyle(
                  fontSize: 13,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
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
    final requester =
        _string(request, const ['requester_name', 'requester_id', 'requester']);
    final reason = _string(
      request,
      const ['reason', 'justification', 'summary', 'objective'],
    );

    return Material(
      color: selected
          ? IlaiosTheme.enterpriseCyan.withValues(alpha: .07)
          : Colors.transparent,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Icon(
                _requestIcon(request),
                size: 20,
                color: selected
                    ? IlaiosTheme.enterpriseCyan
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(width: 12),
              Expanded(
                flex: 3,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _requestTitle(request),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (reason != null) ...[
                      const SizedBox(height: 4),
                      Text(
                        reason,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 13,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Text(
                  requester ?? '—',
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 13.5),
                ),
              ),
              const SizedBox(width: 12),
              _Pill(text: _riskLabel(context, risk), color: _riskColor(risk)),
              const SizedBox(width: 8),
              _Pill(
                text: _statusLabel(context, status),
                color: _statusColor(status),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _TableEmpty extends StatelessWidget {
  const _TableEmpty({required this.authoritativeAvailable});

  final bool authoritativeAvailable;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                authoritativeAvailable
                    ? Icons.task_alt_outlined
                    : Icons.cloud_off_outlined,
                size: 36,
                color: Theme.of(context).colorScheme.outline,
              ),
              const SizedBox(height: 12),
              Text(
                authoritativeAvailable
                    ? _copy(
                        context,
                        'Şu anda eşleşen bir onay talebi yok.',
                        'There are no matching approval requests right now.',
                      )
                    : _copy(
                        context,
                        'Yönetişim verisi şu anda kullanılamıyor.',
                        'Governance data is currently unavailable.',
                      ),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
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
  Widget build(BuildContext context) => Container(
        key: const Key('approvals-right-rail'),
        decoration: _cardDecoration(context),
        padding: const EdgeInsets.all(16),
        child: SingleChildScrollView(
          primary: false,
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
      return Center(
        child: Text(
          _copy(
            context,
            'Ayrıntıları görmek için bir talep seçin.',
            'Select a request to review its details.',
          ),
          textAlign: TextAlign.center,
          style: TextStyle(
            fontSize: 14,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      );
    }

    final id = _requestId(item) ?? '—';
    final risk = _normalizedRisk(item);
    final status = _normalizedStatus(item);
    final requester =
        _string(item, const ['requester_name', 'requester_id', 'requester']) ??
            '—';
    final reason = _string(
          item,
          const ['reason', 'justification', 'summary', 'objective'],
        ) ??
        '—';
    final matchingEvidence = snapshot.evidenceRecords
        .where((record) => record.executionId == id)
        .take(4)
        .toList(growable: false);

    return Column(
      key: const Key('approvals-selected-request'),
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text(
          _copy(context, 'Talep Ayrıntıları', 'Request Details'),
          style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 14),
        Text(
          _requestTitle(item),
          style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            _Pill(text: _riskLabel(context, risk), color: _riskColor(risk)),
            _Pill(
              text: _statusLabel(context, status),
              color: _statusColor(status),
            ),
          ],
        ),
        const SizedBox(height: 18),
        _DetailRow(
          label: _copy(context, 'İsteyen', 'Requester'),
          value: requester,
        ),
        _DetailRow(
          label: _copy(context, 'Oluşturma', 'Created'),
          value: _dateText(
            _value(item, const ['created_at', 'created', 'timestamp']),
          ),
        ),
        const SizedBox(height: 12),
        Text(
          _copy(context, 'Gerekçe', 'Reason'),
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 6),
        Text(reason, style: const TextStyle(fontSize: 13.5, height: 1.4)),
        const SizedBox(height: 16),
        Text(
          _copy(context, 'Kanıt', 'Evidence'),
          style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 6),
        if (matchingEvidence.isEmpty)
          Text(
            _copy(
              context,
              'Bu talep için eşleşen kanıt kaydı yok.',
              'No matching evidence record is available for this request.',
            ),
            style: TextStyle(
              fontSize: 13,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          )
        else
          for (final record in matchingEvidence)
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Row(
                children: [
                  const Icon(
                    Icons.check_circle_outline,
                    size: 17,
                    color: IlaiosTheme.success,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      record.action,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
        const SizedBox(height: 20),
        if (message case final text?) ...[
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerLow,
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(text, style: const TextStyle(fontSize: 13)),
          ),
          const SizedBox(height: 10),
        ],
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                key: ValueKey('approve-$id'),
                onPressed: decisionAllowed && !busy ? onApprove : null,
                style: FilledButton.styleFrom(
                  backgroundColor: IlaiosTheme.success,
                  foregroundColor: IlaiosTheme.carbon,
                  minimumSize: const Size(0, 44),
                ),
                icon: busy
                    ? const SizedBox(
                        width: 16,
                        height: 16,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Icon(Icons.check_circle_outline, size: 18),
                label: Text(_copy(context, 'Onayla', 'Approve')),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton.icon(
                key: ValueKey('deny-$id'),
                onPressed: decisionAllowed && !busy ? onDeny : null,
                style: FilledButton.styleFrom(
                  backgroundColor: IlaiosTheme.danger,
                  foregroundColor: Colors.white,
                  minimumSize: const Size(0, 44),
                ),
                icon: const Icon(Icons.close, size: 18),
                label: Text(_copy(context, 'Reddet', 'Deny')),
              ),
            ),
          ],
        ),
        const SizedBox(height: 12),
        Text(
          '${_copy(context, 'Teknik kimlik', 'Technical ID')}: $id',
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 12.5,
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            SizedBox(
              width: 92,
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 13,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                value,
                style: const TextStyle(
                  fontSize: 13.5,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ],
        ),
      );
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .12),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: color.withValues(alpha: .28)),
        ),
        child: Text(
          text,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: FontWeight.w700,
            color: color,
          ),
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

BoxDecoration _cardDecoration(BuildContext context) => BoxDecoration(
      color: Theme.of(context).colorScheme.surfaceContainerLowest,
      borderRadius: BorderRadius.circular(10),
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
  if (_statusConnected(status)) return _copy(context, 'Bağlı', 'Connected');
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
    _string(
      request,
      const ['title', 'request_name', 'name', 'action', 'operation'],
    ) ??
    _copyFallbackId(_requestId(request));

String _copyFallbackId(String? id) =>
    id == null || id.isEmpty ? '—' : 'Request ${id.length > 8 ? id.substring(0, 8) : id}';

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
  if (raw.contains('high') ||
      raw.contains('critical') ||
      raw.contains('yüksek')) {
    return 'high';
  }
  if (raw.contains('medium') ||
      raw.contains('moderate') ||
      raw.contains('orta')) {
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
      _ => IlaiosTheme.enterpriseCyan,
    };

String _riskLabel(BuildContext context, String risk) => switch (risk) {
      'high' => _copy(context, 'Yüksek', 'High'),
      'medium' => _copy(context, 'Orta', 'Medium'),
      'low' => _copy(context, 'Düşük', 'Low'),
      _ => _copy(context, 'Belirsiz', 'Unknown'),
    };

Color _riskColor(String risk) => switch (risk) {
      'high' => IlaiosTheme.danger,
      'medium' => IlaiosTheme.warning,
      'low' => IlaiosTheme.success,
      _ => ThemeData.fallback().colorScheme.outline,
    };

IconData _requestIcon(Map<String, Object?> request) {
  final text =
      '${_requestTitle(request)} ${_string(request, const ['type', 'category']) ?? ''}'
          .toLowerCase();
  if (text.contains('deploy') || text.contains('release')) {
    return Icons.rocket_launch_outlined;
  }
  if (text.contains('api') || text.contains('network')) {
    return Icons.key_outlined;
  }
  if (text.contains('budget') || text.contains('finance')) {
    return Icons.paid_outlined;
  }
  if (text.contains('data') || text.contains('export')) {
    return Icons.storage_outlined;
  }
  if (text.contains('policy')) return Icons.policy_outlined;
  return Icons.task_alt_outlined;
}

String _dateText(Object? value) {
  if (value == null) return '—';
  if (value is int) {
    final date = DateTime.fromMillisecondsSinceEpoch(
      value < 1000000000000 ? value * 1000 : value,
    ).toLocal();
    return '${date.day.toString().padLeft(2, '0')}.${date.month.toString().padLeft(2, '0')}.${date.year} ${date.hour.toString().padLeft(2, '0')}:${date.minute.toString().padLeft(2, '0')}';
  }
  final text = value.toString().trim();
  if (text.isEmpty) return '—';
  final parsed = DateTime.tryParse(text);
  if (parsed == null) return text.length <= 22 ? text : '${text.substring(0, 22)}…';
  final local = parsed.toLocal();
  return '${local.day.toString().padLeft(2, '0')}.${local.month.toString().padLeft(2, '0')}.${local.year} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
}
