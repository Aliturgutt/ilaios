import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../create/reference_asset_picker.dart';
import '../navigation/desktop_section.dart';

/// Canonical 7-page Home surface.
///
/// Geometry follows the user-approved 1536x1024 Home reference. Runtime values
/// remain authority-derived; the screenshot's example counts are never copied
/// into application state.
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
  String _objective = '';

  @override
  void dispose() {
    _promptController.dispose();
    super.dispose();
  }

  Future<void> _startWork() async {
    final callback = widget.onPromptSubmit;
    final objective = _promptController.text.trim();
    if (callback == null || objective.isEmpty || _submitting) return;

    setState(() => _submitting = true);
    try {
      final submission = await callback(objective);
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
      setState(() => _objective = '');
    } on Object catch (error) {
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
    final referenceAssets = ReferenceAssetPickerScope.maybeOf(context);
    final groups = _agentGroups(widget.snapshot);

    return ColoredBox(
      color: Theme.of(context).scaffoldBackgroundColor,
      child: SingleChildScrollView(
        key: const Key('command-center-short-viewport-scroll'),
        primary: false,
        child: Column(
          key: const Key('command-center-home'),
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              padding: const EdgeInsets.fromLTRB(24, 20, 27, 14),
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    _t(context, 'Start work', 'İş başlat'),
                    style: const TextStyle(
                      fontSize: 25,
                      height: 1.12,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Expanded(
                        child: SizedBox(
                          height: 60,
                          child: TextField(
                            key: const Key('home-command-prompt'),
                            controller: _promptController,
                            minLines: 1,
                            maxLines: 1,
                            textAlignVertical: TextAlignVertical.center,
                            onChanged: (value) =>
                                setState(() => _objective = value.trim()),
                            decoration: InputDecoration(
                              prefixIcon: const Icon(
                                Icons.attach_file_rounded,
                                size: 22,
                              ),
                              hintText: _t(
                                context,
                                'Website, video, software or research — describe the result and criteria…',
                                'Web sitesi, video, yazılım veya araştırma — sonucu ve kriterleri yaz...',
                              ),
                              hintStyle: const TextStyle(fontSize: 14),
                              contentPadding: const EdgeInsets.symmetric(
                                horizontal: 16,
                                vertical: 18,
                              ),
                              border: OutlineInputBorder(
                                borderRadius: BorderRadius.circular(8),
                              ),
                            ),
                          ),
                        ),
                      ),
                      const SizedBox(width: 16),
                      SizedBox(
                        width: 162,
                        height: 60,
                        child: FilledButton.icon(
                          key: const Key('home-new-work'),
                          onPressed: _objective.isNotEmpty &&
                                  widget.onPromptSubmit != null &&
                                  !_submitting
                              ? _startWork
                              : null,
                          icon: _submitting
                              ? const SizedBox(
                                  width: 18,
                                  height: 18,
                                  child: CircularProgressIndicator(strokeWidth: 2),
                                )
                              : const Icon(Icons.play_arrow_outlined, size: 24),
                          label: Text(
                            _submitting
                                ? _t(context, 'Starting…', 'Başlatılıyor…')
                                : _t(context, 'Start', 'Başlat'),
                            style: const TextStyle(
                              fontSize: 15,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                          style: FilledButton.styleFrom(
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8),
                            ),
                          ),
                        ),
                      ),
                    ],
                  ),
                  if (referenceAssets != null) ...[
                    const SizedBox(height: 13),
                    ReferenceAssetPicker(
                      key: const Key('home-prompt-attachments'),
                      controller: referenceAssets,
                      enabled: widget.userSession != null && !_submitting,
                      compact: true,
                    ),
                  ],
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(24, 20, 27, 22),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Divider(
                    height: 1,
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                  const SizedBox(height: 20),
                  _AgentSection(
                    groups: groups,
                    onShowAll: () => widget.onNavigate(DesktopSection.agents),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AgentSection extends StatelessWidget {
  const _AgentSection({required this.groups, required this.onShowAll});

  final List<_AgentGroup> groups;
  final VoidCallback onShowAll;

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    final subtitle = groups.isEmpty
        ? (tr ? 'Doğrulanmış runtime ajan verisi yok' : 'No verified runtime agent data')
        : (tr
            ? '${groups.length} takım · gerçek zamanlı runtime durumu'
            : '${groups.length} teams · real-time runtime state');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.end,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tr ? 'Ajanlar Çalışıyor' : 'Agents',
                    style: const TextStyle(
                      fontSize: 22,
                      height: 1.1,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    subtitle,
                    style: TextStyle(
                      fontSize: 13.5,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            TextButton.icon(
              onPressed: onShowAll,
              label: Text(
                tr ? 'Tüm Ajanları Görüntüle' : 'View all agents',
                style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700),
              ),
              iconAlignment: IconAlignment.end,
              icon: const Icon(Icons.arrow_forward_rounded, size: 18),
            ),
          ],
        ),
        const SizedBox(height: 14),
        if (groups.isEmpty)
          Container(
            height: 150,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.surfaceContainerLowest,
              border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Text(
              tr
                  ? 'Ajan durumları runtime authority üzerinden geldiğinde burada gösterilir.'
                  : 'Agent state appears here when supplied by the runtime authority.',
              style: TextStyle(
                fontSize: 13,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          )
        else
          LayoutBuilder(
            builder: (context, constraints) {
              final visible = groups.take(8).toList(growable: false);
              const gap = 12.0;
              final width =
                  (constraints.maxWidth - gap * (visible.length - 1)) / visible.length;
              return Wrap(
                spacing: gap,
                runSpacing: gap,
                children: [
                  for (final group in visible)
                    SizedBox(
                      width: width.clamp(132.0, 190.0),
                      child: _AgentGroupCard(group: group),
                    ),
                ],
              );
            },
          ),
      ],
    );
  }
}

class _AgentGroupCard extends StatelessWidget {
  const _AgentGroupCard({required this.group});

  final _AgentGroup group;

  @override
  Widget build(BuildContext context) {
    final tr = IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish;
    return Container(
      height: 212,
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 12),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surfaceContainerLowest,
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _displayTeam(group.team, tr),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800),
          ),
          const Spacer(),
          Center(
            child: Icon(
              Icons.smart_toy_outlined,
              size: 64,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const Spacer(),
          if (group.active != null)
            _StatusLine(
              color: const Color(0xFF16B85A),
              text: tr
                  ? '${group.active} çalışıyor'
                  : '${group.active} active',
            ),
          if (group.busy != null)
            _StatusLine(
              color: const Color(0xFFF0B81C),
              text: tr ? '${group.busy} meşgul' : '${group.busy} busy',
            ),
          if (group.idle != null)
            _StatusLine(
              color: const Color(0xFF94A3B8),
              text: tr ? '${group.idle} boşta' : '${group.idle} idle',
            ),
          if (group.active == null && group.busy == null && group.idle == null)
            Text(
              tr ? 'Durum doğrulanmadı' : 'State unverified',
              style: TextStyle(
                fontSize: 12.5,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
        ],
      ),
    );
  }
}

class _StatusLine extends StatelessWidget {
  const _StatusLine({required this.color, required this.text});
  final Color color;
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Row(
          children: [
            Icon(Icons.circle, size: 8, color: color),
            const SizedBox(width: 7),
            Expanded(
              child: Text(
                text,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5),
              ),
            ),
          ],
        ),
      );
}

class _AgentGroup {
  const _AgentGroup({
    required this.team,
    required this.active,
    required this.busy,
    required this.idle,
  });

  final String team;
  final int? active;
  final int? busy;
  final int? idle;
}

List<_AgentGroup> _agentGroups(OperationalSnapshot snapshot) {
  final registry = <String, Map<String, Object?>>{};
  for (final item in _maps(snapshot.agentState['agents'])) {
    final id = _text(item, const ['agent_id', 'id']);
    if (id == null || !id.startsWith('ilaios.agent.')) continue;
    registry[id] = Map<String, Object?>.of(item);
  }
  if (registry.isEmpty) return const [];

  void mergeTelemetry(Map<String, Object?> item) {
    String? id;
    for (final key in const [
      'agent_id',
      'worker_id',
      'executor_id',
      'agent',
      'worker',
      'id',
    ]) {
      final candidate = _text(item, [key]);
      if (candidate != null && registry.containsKey(candidate)) {
        id = candidate;
        break;
      }
    }
    if (id == null) return;
    final status = _text(item, const [
      'agent_status',
      'worker_status',
      'status',
      'state',
      'lease_state',
    ]);
    if (status != null) registry[id]!['runtime_status'] = status;
  }

  for (final key in const ['agents', 'workers', 'executors', 'leases']) {
    for (final item in _maps(snapshot.schedulerState[key])) {
      mergeTelemetry(item);
    }
  }
  for (final item in snapshot.runtimeRoutes) {
    mergeTelemetry(item);
  }
  for (final item in snapshot.liveEvents) {
    mergeTelemetry(item);
  }

  final buckets = <String, _MutableAgentGroup>{};
  for (final entry in registry.entries) {
    final item = entry.value;
    final team = _text(item, const ['team', 'group', 'domain']) ??
        _teamFromId(entry.key);
    if (team == null) continue;
    final bucket = buckets.putIfAbsent(team, () => _MutableAgentGroup(team));
    final status = _text(item, const ['runtime_status']);
    if (status == null) {
      bucket.unknown++;
      continue;
    }
    final normalized = _normalize(status);
    if (normalized.contains('busy') ||
        normalized.contains('running') ||
        normalized.contains('executing') ||
        normalized.contains('working')) {
      bucket.busy++;
    } else if (normalized.contains('idle') ||
        normalized.contains('available') ||
        normalized.contains('free')) {
      bucket.idle++;
    } else if (normalized.contains('active') ||
        normalized.contains('ready') ||
        normalized.contains('online')) {
      bucket.active++;
    } else {
      bucket.unknown++;
    }
  }

  final groups = buckets.values.toList()
    ..sort((a, b) => a.team.compareTo(b.team));
  return groups
      .map(
        (item) => _AgentGroup(
          team: item.team,
          active: item.active == 0 ? null : item.active,
          busy: item.busy == 0 ? null : item.busy,
          idle: item.idle == 0 ? null : item.idle,
        ),
      )
      .toList(growable: false);
}

class _MutableAgentGroup {
  _MutableAgentGroup(this.team);
  final String team;
  int active = 0;
  int busy = 0;
  int idle = 0;
  int unknown = 0;
}

List<Map<String, Object?>> _maps(Object? raw) {
  if (raw is! List<Object?>) return const [];
  return raw.whereType<Map<String, Object?>>().toList(growable: false);
}

String? _text(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return '$value';
  }
  return null;
}

String? _teamFromId(String id) {
  final parts = id.split('.');
  if (parts.length < 4) return null;
  return parts[2];
}

String _normalize(String value) =>
    value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), '');

String _displayTeam(String raw, bool tr) {
  final value = raw.toLowerCase();
  if (value.contains('core') || value.contains('kernel')) {
    return tr ? 'Çekirdek' : 'Core';
  }
  if (value.contains('engineering')) return tr ? 'Mühendislik' : 'Engineering';
  if (value.contains('security')) return tr ? 'Güvenlik' : 'Security';
  if (value.contains('web')) return 'Web';
  if (value.contains('media') || value.contains('video')) return tr ? 'Medya' : 'Media';
  if (value.contains('research') || value.contains('data')) {
    return tr ? 'Araştırma' : 'Research';
  }
  if (value.contains('operation')) return tr ? 'Operasyon' : 'Operations';
  if (value.contains('meta')) return 'Meta';
  if (raw.isEmpty) return tr ? 'Takım' : 'Team';
  return '${raw[0].toUpperCase()}${raw.substring(1)}';
}

String _t(BuildContext context, String english, String turkish) =>
    IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish
        ? turkish
        : english;
