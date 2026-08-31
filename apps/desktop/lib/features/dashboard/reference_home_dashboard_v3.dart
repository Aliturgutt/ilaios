import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/client.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../navigation/desktop_section.dart';

/// Final-polish Home surface.
///
/// One governed prompt remains the primary interaction. Supporting content is
/// authority-derived and responsive; compact layouts scroll instead of
/// shrinking typography or overflowing.
class ReferenceHomeDashboardV3 extends StatefulWidget {
  const ReferenceHomeDashboardV3({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.userSession,
    this.onPromptSubmit,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onNavigate;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final VoidCallback? onRefreshRequested;

  @override
  State<ReferenceHomeDashboardV3> createState() =>
      _ReferenceHomeDashboardV3State();
}

class _ReferenceHomeDashboardV3State extends State<ReferenceHomeDashboardV3> {
  final TextEditingController _promptController = TextEditingController();
  bool _submitting = false;

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  Future<void> _startWork() async {
    final objective = _promptController.text.trim();
    if (objective.isEmpty || widget.onPromptSubmit == null) {
      widget.onNavigate(DesktopSection.goals);
      return;
    }
    if (_submitting) return;

    setState(() => _submitting = true);
    try {
      final submission = await widget.onPromptSubmit!(objective);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _t(
              context,
              'Work accepted · ${submission.state}',
              'İş kabul edildi · ${submission.state}',
            ),
          ),
        ),
      );
      _promptController.clear();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(
            _t(
              context,
              'Work could not be started: $error',
              'İş başlatılamadı: $error',
            ),
          ),
        ),
      );
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final model = _HomeModel(
      projection: widget.projection,
      snapshot: widget.snapshot,
      status: widget.status,
      userSession: widget.userSession,
    );

    return LayoutBuilder(
      builder: (context, constraints) {
        // The shell leaves roughly 880 px at the 1320 reference width and
        // roughly 980 px at the standard 1536 width. Keep 1536 in the native
        // one-viewport composition while letting compact clients scroll.
        final compact = constraints.maxWidth < 940;
        final outerPadding = compact ? 14.0 : 20.0;
        final gap = compact ? 12.0 : 16.0;

        if (compact) {
          return SingleChildScrollView(
            key: const Key('command-center-short-viewport-scroll'),
            primary: false,
            padding: EdgeInsets.fromLTRB(outerPadding, 14, outerPadding, 18),
            child: Column(
              key: const Key('command-center-home'),
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _CommandHero(
                  controller: _promptController,
                  submitting: _submitting,
                  model: model,
                  onStartWork: _startWork,
                  onNavigate: widget.onNavigate,
                ),
                SizedBox(height: gap),
                _CompactSupportLayout(
                  model: model,
                  onNavigate: widget.onNavigate,
                  gap: gap,
                ),
              ],
            ),
          );
        }

        return Padding(
          padding: EdgeInsets.fromLTRB(outerPadding, 16, outerPadding, 18),
          child: Column(
            key: const Key('command-center-home'),
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              _CommandHero(
                controller: _promptController,
                submitting: _submitting,
                model: model,
                onStartWork: _startWork,
                onNavigate: widget.onNavigate,
              ),
              SizedBox(height: gap),
              Expanded(
                child: _WideSupportLayout(
                  model: model,
                  onNavigate: widget.onNavigate,
                  gap: gap,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _HomeModel {
  const _HomeModel({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.userSession,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;

  List<Map<String, Object?>> get work =>
      _mapList(snapshot.governanceState['work']);

  List<Map<String, Object?>> get admissions =>
      _mapList(snapshot.governanceState['admissions']);

  List<Map<String, Object?>> get focusItems {
    if (work.isNotEmpty) return work.reversed.take(3).toList(growable: false);
    return snapshot.liveEvents.reversed.take(3).toList(growable: false);
  }

  int? get pendingApprovalCount {
    if (!snapshot.governanceState.containsKey('work') &&
        !snapshot.governanceState.containsKey('admissions')) {
      return null;
    }
    final required = <String>{};
    for (final item in admissions) {
      if (item['human_approval_required'] != true) continue;
      final id = item['request_id'];
      if (id is String && id.isNotEmpty) required.add(id);
    }
    return work.where((item) {
      final state = _normalize(_text(item, const ['status', 'state']) ?? '');
      if (state != 'pending') return false;
      if (admissions.isEmpty) return true;
      final id = item['request_id'];
      return id is String && required.contains(id);
    }).length;
  }

  int get deniedCount => work.where((item) {
        final state = _normalize(_text(item, const ['status', 'state']) ?? '');
        return state == 'denied' || state == 'failed';
      }).length;

  List<_AttentionData> get attentionItems {
    final items = <_AttentionData>[];
    final pending = pendingApprovalCount;
    if (pending != null && pending > 0) {
      items.add(
        _AttentionData(
          title: pending == 1
              ? '1 approval is waiting'
              : '$pending approvals are waiting',
          subtitle:
              'Human approval is required before governed execution can continue.',
          destination: DesktopSection.approvals,
          critical: false,
        ),
      );
    }
    if (deniedCount > 0) {
      items.add(
        _AttentionData(
          title: deniedCount == 1
              ? '1 work item needs review'
              : '$deniedCount work items need review',
          subtitle: 'A governed work item was denied or failed.',
          destination: DesktopSection.workflows,
          critical: false,
        ),
      );
    }
    for (final event in snapshot.liveEvents.reversed) {
      final state = _normalize(
        _text(event, const ['status', 'state', 'event_type', 'type']) ?? '',
      );
      if (!state.contains('error') &&
          !state.contains('failed') &&
          !state.contains('critical')) {
        continue;
      }
      items.add(
        _AttentionData(
          title: _humanEventTitle(event),
          subtitle: _text(event, const ['detail', 'reason']) ??
              'An authoritative runtime event needs review.',
          destination: DesktopSection.workflows,
          critical: true,
        ),
      );
      break;
    }
    return items.take(3).toList(growable: false);
  }

  List<EvidenceRecord> get outputs =>
      snapshot.evidenceRecords.reversed.take(3).toList(growable: false);
}

class _CommandHero extends StatelessWidget {
  const _CommandHero({
    required this.controller,
    required this.submitting,
    required this.model,
    required this.onStartWork,
    required this.onNavigate,
  });

  final TextEditingController controller;
  final bool submitting;
  final _HomeModel model;
  final Future<void> Function() onStartWork;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) => Container(
        key: const Key('command-center-hero'),
        padding: const EdgeInsets.fromLTRB(22, 20, 22, 18),
        decoration: _surface(context, emphasized: true),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            LayoutBuilder(
              builder: (context, constraints) {
                final stacked = constraints.maxWidth < 720;
                final copy = Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      _t(context, 'Start work', 'İş başlat'),
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                            fontSize: 30,
                            height: 1.1,
                            fontWeight: FontWeight.w700,
                          ),
                    ),
                    const SizedBox(height: 7),
                    Text(
                      _t(
                        context,
                        'Describe the finished result. ILAIOS will route the work through the existing governed execution system.',
                        'Bitmiş sonucu tarif et. ILAIOS işi mevcut yönetişimli yürütme sistemi üzerinden yönlendirsin.',
                      ),
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            fontSize: 15,
                            height: 1.4,
                            color: Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                    ),
                  ],
                );
                if (stacked) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      copy,
                      const SizedBox(height: 12),
                      Align(
                        alignment: Alignment.centerLeft,
                        child: _RuntimePill(model: model),
                      ),
                    ],
                  );
                }
                return Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(child: copy),
                    const SizedBox(width: 18),
                    Flexible(child: _RuntimePill(model: model)),
                  ],
                );
              },
            ),
            const SizedBox(height: 16),
            TextField(
              key: const Key('home-command-prompt'),
              controller: controller,
              minLines: 2,
              maxLines: 4,
              style: const TextStyle(fontSize: 15, height: 1.35),
              textInputAction: TextInputAction.newline,
              decoration: InputDecoration(
                hintText: _t(
                  context,
                  'Website, video, software or research — describe the result and constraints…',
                  'Web sitesi, video, yazılım veya araştırma — sonucu ve kısıtları yaz…',
                ),
              ),
            ),
            const SizedBox(height: 12),
            LayoutBuilder(
              builder: (context, constraints) {
                final stacked = constraints.maxWidth < 760;
                final routing = Text(
                  _t(
                    context,
                    'Routing is automatic. Factory selection stays secondary.',
                    'Yönlendirme otomatik. Factory seçimi ikincil kalır.',
                  ),
                  maxLines: stacked ? 2 : 1,
                  overflow: TextOverflow.ellipsis,
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        fontSize: 13,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                );
                final advanced = TextButton(
                  onPressed: () => onNavigate(DesktopSection.goals),
                  child: Text(
                    _t(context, 'Advanced', 'Gelişmiş'),
                    style: const TextStyle(fontSize: 13.5),
                  ),
                );
                final start = FilledButton.icon(
                  key: const Key('home-new-work'),
                  onPressed: submitting ? null : onStartWork,
                  icon: const Icon(Icons.arrow_forward_rounded, size: 18),
                  label: Text(
                    submitting
                        ? _t(context, 'Starting…', 'Başlatılıyor…')
                        : _t(context, 'Start', 'Başlat'),
                    style: const TextStyle(fontSize: 14),
                  ),
                );
                if (stacked) {
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      routing,
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          advanced,
                          const Spacer(),
                          start,
                        ],
                      ),
                    ],
                  );
                }
                return Row(
                  children: [
                    Expanded(child: routing),
                    const SizedBox(width: 8),
                    advanced,
                    const SizedBox(width: 8),
                    start,
                  ],
                );
              },
            ),
          ],
        ),
      );
}

class _RuntimePill extends StatelessWidget {
  const _RuntimePill({required this.model});
  final _HomeModel model;

  @override
  Widget build(BuildContext context) => Container(
        constraints: const BoxConstraints(maxWidth: 250),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              Icons.circle,
              size: 8,
              color: model.projection.connected
                  ? IlaiosTheme.success
                  : Theme.of(context).colorScheme.outline,
            ),
            const SizedBox(width: 8),
            Flexible(
              child: Text(
                model.status,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );
}

class _WideSupportLayout extends StatelessWidget {
  const _WideSupportLayout({
    required this.model,
    required this.onNavigate,
    required this.gap,
  });

  final _HomeModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final double gap;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          Expanded(
            child: Row(
              children: [
                Expanded(child: _FocusPanel(model: model, onNavigate: onNavigate)),
                SizedBox(width: gap),
                Expanded(child: _AttentionPanel(model: model, onNavigate: onNavigate)),
              ],
            ),
          ),
          SizedBox(height: gap),
          Expanded(
            child: Row(
              children: [
                Expanded(child: _OutputsPanel(model: model, onNavigate: onNavigate)),
                SizedBox(width: gap),
                Expanded(child: _CompletedPanel(model: model, onNavigate: onNavigate)),
              ],
            ),
          ),
        ],
      );
}

class _CompactSupportLayout extends StatelessWidget {
  const _CompactSupportLayout({
    required this.model,
    required this.onNavigate,
    required this.gap,
  });

  final _HomeModel model;
  final ValueChanged<DesktopSection> onNavigate;
  final double gap;

  @override
  Widget build(BuildContext context) => Column(
        children: [
          SizedBox(height: 190, child: _FocusPanel(model: model, onNavigate: onNavigate)),
          SizedBox(height: gap),
          SizedBox(height: 190, child: _AttentionPanel(model: model, onNavigate: onNavigate)),
          SizedBox(height: gap),
          SizedBox(height: 190, child: _OutputsPanel(model: model, onNavigate: onNavigate)),
          SizedBox(height: gap),
          SizedBox(height: 190, child: _CompletedPanel(model: model, onNavigate: onNavigate)),
        ],
      );
}

class _FocusPanel extends StatelessWidget {
  const _FocusPanel({required this.model, required this.onNavigate});
  final _HomeModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final items = model.focusItems;
    return _SectionPanel(
      key: const Key('command-center-focus'),
      title: _t(context, 'FOCUS WORK', 'ODAK İŞLER'),
      actionLabel: _t(context, 'All work', 'Tüm işler'),
      onAction: () => onNavigate(DesktopSection.workflows),
      child: items.isEmpty
          ? _EmptyState(
              icon: Icons.track_changes_rounded,
              title: _t(context, 'Nothing is running yet', 'Henüz çalışan iş yok'),
              detail: _t(
                context,
                'Start from the prompt above. Work appears here only when authoritative runtime state exists.',
                'Yukarıdaki prompttan başlat. İşler yalnızca doğrulanmış runtime durumu oluştuğunda burada görünür.',
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 6),
              itemCount: items.length,
              separatorBuilder: (_, _) => Divider(
                height: 1,
                color: Theme.of(context).colorScheme.outlineVariant,
              ),
              itemBuilder: (context, index) => _WorkRow(item: items[index]),
            ),
    );
  }
}

class _WorkRow extends StatelessWidget {
  const _WorkRow({required this.item});
  final Map<String, Object?> item;

  @override
  Widget build(BuildContext context) {
    final title = _humanWorkTitle(item);
    final state = _humanState(_text(item, const ['status', 'state', 'phase']) ?? '');
    final detail = _text(item, const ['description', 'message', 'task', 'phase', 'stage']);
    final id = _text(item, const ['request_id', 'job_id', 'execution_id']);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      child: Row(
        children: [
          const Icon(Icons.work_outline_rounded, size: 20, color: IlaiosTheme.enterpriseCyan),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                if (detail != null) ...[
                  const SizedBox(height: 3),
                  Text(detail, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 13, color: Theme.of(context).colorScheme.onSurfaceVariant)),
                ],
              ],
            ),
          ),
          const SizedBox(width: 12),
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(state, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
              if (id != null) ...[
                const SizedBox(height: 3),
                Text('ID ${_short(id, 12)}', style: TextStyle(fontSize: 12.5, color: Theme.of(context).colorScheme.onSurfaceVariant)),
              ],
            ],
          ),
        ],
      ),
    );
  }
}

class _AttentionData {
  const _AttentionData({required this.title, required this.subtitle, required this.destination, required this.critical});
  final String title;
  final String subtitle;
  final DesktopSection destination;
  final bool critical;
}

class _AttentionPanel extends StatelessWidget {
  const _AttentionPanel({required this.model, required this.onNavigate});
  final _HomeModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final items = model.attentionItems;
    return _SectionPanel(
      key: const Key('command-center-attention'),
      title: _t(context, 'NEEDS ATTENTION', 'DİKKAT GEREKTİRENLER'),
      actionLabel: _t(context, 'Approvals', 'Onaylar'),
      onAction: () => onNavigate(DesktopSection.approvals),
      child: items.isEmpty
          ? _EmptyState(
              icon: Icons.verified_outlined,
              title: _t(context, 'No action is required', 'İşlem gerekmiyor'),
              detail: _t(
                context,
                'Only authoritative approvals, failures, or runtime issues appear here.',
                'Burada yalnızca doğrulanmış onay, hata veya runtime sorunları görünür.',
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 6),
              itemCount: items.length,
              separatorBuilder: (_, _) => Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
              itemBuilder: (context, index) {
                final data = items[index];
                final color = data.critical ? IlaiosTheme.danger : IlaiosTheme.warning;
                return ListTile(
                  dense: true,
                  leading: Icon(Icons.error_outline_rounded, color: color),
                  title: Text(data.title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
                  subtitle: Text(data.subtitle, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)),
                  trailing: const Icon(Icons.chevron_right_rounded),
                  onTap: () => onNavigate(data.destination),
                );
              },
            ),
    );
  }
}

class _OutputsPanel extends StatelessWidget {
  const _OutputsPanel({required this.model, required this.onNavigate});
  final _HomeModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final records = model.outputs;
    return _SectionPanel(
      key: const Key('command-center-artifacts'),
      title: _t(context, 'LATEST OUTPUTS', 'SON ÇIKTILAR'),
      actionLabel: _t(context, 'Outputs', 'Çıktılar'),
      onAction: () => onNavigate(DesktopSection.artifacts),
      child: records.isEmpty
          ? _EmptyState(
              icon: Icons.inventory_2_outlined,
              title: _t(context, 'No output yet', 'Henüz çıktı yok'),
              detail: _t(
                context,
                'Verified files and finished products appear here after governed execution produces evidence.',
                'Doğrulanmış dosyalar ve bitmiş ürünler, yönetişimli yürütme evidence ürettiğinde burada görünür.',
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 6),
              itemCount: records.length,
              separatorBuilder: (_, _) => Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
              itemBuilder: (context, index) => _OutputRow(record: records[index]),
            ),
    );
  }
}

class _OutputRow extends StatelessWidget {
  const _OutputRow({required this.record});
  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Row(
          children: [
            const Icon(Icons.description_outlined, size: 20, color: IlaiosTheme.enterpriseCyan),
            const SizedBox(width: 12),
            Expanded(
              child: Text(_humanAction(record.action), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
            ),
            const SizedBox(width: 12),
            Text('ID ${_short(record.executionId, 12)}', style: TextStyle(fontSize: 12.5, color: Theme.of(context).colorScheme.onSurfaceVariant)),
          ],
        ),
      );
}

class _CompletedPanel extends StatelessWidget {
  const _CompletedPanel({required this.model, required this.onNavigate});
  final _HomeModel model;
  final ValueChanged<DesktopSection> onNavigate;

  @override
  Widget build(BuildContext context) {
    final records = model.outputs;
    return _SectionPanel(
      key: const Key('command-center-completed'),
      title: _t(context, 'RECENTLY COMPLETED', 'SON TAMAMLANANLAR'),
      actionLabel: _t(context, 'Evidence', 'Evidence'),
      onAction: () => onNavigate(DesktopSection.evidence),
      child: records.isEmpty
          ? _EmptyState(
              icon: Icons.task_alt_rounded,
              title: _t(context, 'No verified completion yet', 'Henüz doğrulanmış tamamlanma yok'),
              detail: _t(
                context,
                'Completed work appears here only when the evidence chain contains a real record.',
                'Tamamlanan işler yalnızca evidence zincirinde gerçek kayıt bulunduğunda burada görünür.',
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.symmetric(vertical: 6),
              itemCount: records.length,
              separatorBuilder: (_, _) => Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
              itemBuilder: (context, index) => _OutputRow(record: records[index]),
            ),
    );
  }
}

class _SectionPanel extends StatelessWidget {
  const _SectionPanel({required this.title, required this.child, this.actionLabel, this.onAction, super.key});
  final String title;
  final Widget child;
  final String? actionLabel;
  final VoidCallback? onAction;

  @override
  Widget build(BuildContext context) => Container(
        decoration: _surface(context),
        clipBehavior: Clip.antiAlias,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 13, 10, 11),
              child: Row(
                children: [
                  Expanded(child: Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, letterSpacing: .1, fontWeight: FontWeight.w700))),
                  if (actionLabel != null)
                    TextButton(onPressed: onAction, child: Text(actionLabel!, style: const TextStyle(fontSize: 13.5))),
                ],
              ),
            ),
            Divider(height: 1, color: Theme.of(context).colorScheme.outlineVariant),
            Expanded(child: child),
          ],
        ),
      );
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.icon, required this.title, required this.detail});
  final IconData icon;
  final String title;
  final String detail;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 24, color: Theme.of(context).colorScheme.onSurfaceVariant),
              const SizedBox(height: 5),
              Text(title, textAlign: TextAlign.center, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w700)),
              const SizedBox(height: 3),
              Text(detail, textAlign: TextAlign.center, maxLines: 3, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 13, height: 1.35, color: Theme.of(context).colorScheme.onSurfaceVariant)),
            ],
          ),
        ),
      );
}

BoxDecoration _surface(BuildContext context, {bool emphasized = false}) {
  final dark = Theme.of(context).brightness == Brightness.dark;
  return BoxDecoration(
    color: Theme.of(context).colorScheme.surfaceContainerLow,
    borderRadius: BorderRadius.circular(emphasized ? 12 : 10),
    border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    boxShadow: !emphasized || dark
        ? const []
        : const [BoxShadow(color: Color(0x080B0F14), blurRadius: 12, offset: Offset(0, 4))],
  );
}

String _t(BuildContext context, String english, String turkish) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish ? turkish : english;

String _normalize(String value) => value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();

String? _text(Map<String, Object?>? source, List<String> keys) {
  if (source == null) return null;
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return '$value';
  }
  return null;
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return value.whereType<Map<String, Object?>>().toList(growable: false);
}

String _humanWorkTitle(Map<String, Object?> item) =>
    _text(item, const ['project_name', 'title', 'objective', 'goal', 'task', 'description']) ?? 'Work item';

String _humanEventTitle(Map<String, Object?> event) {
  final message = _text(event, const ['message', 'title', 'event_type', 'type']);
  return message == null ? 'Runtime issue' : _humanAction(message);
}

String _humanAction(String value) {
  final cleaned = value.replaceAll(RegExp(r'[_\-.]+'), ' ').replaceAll(RegExp(r'\s+'), ' ').trim();
  if (cleaned.isEmpty) return 'Verified output';
  return cleaned[0].toUpperCase() + cleaned.substring(1);
}

String _humanState(String value) {
  final normalized = _normalize(value);
  if (normalized.isEmpty) return 'Status unavailable';
  return switch (normalized) {
    'in progress' || 'running' || 'active' => 'In progress',
    'pending' || 'queued' => 'Waiting',
    'completed' || 'complete' || 'succeeded' || 'success' => 'Completed',
    'failed' || 'denied' => 'Needs review',
    _ => _humanAction(value),
  };
}

String _short(String value, int maxLength) =>
    value.length <= maxLength ? value : '${value.substring(0, maxLength)}…';
