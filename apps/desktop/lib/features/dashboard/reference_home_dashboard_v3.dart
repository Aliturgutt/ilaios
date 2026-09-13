import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../control_plane/operational_snapshot.dart';
import '../../control_plane/projection.dart';
import '../../identity/identity_client.dart';
import '../create/reference_asset_picker.dart';
import '../navigation/desktop_section.dart';
import 'agent_runtime_status.dart';
import 'pixel_agent_presentation.dart';
import 'pixel_agent_sprite.dart';
import 'prompt_editor_panel.dart';

/// Canonical 7-page Home surface.
///
/// Geometry follows the user-approved 1536x1024 Home reference. Runtime values
/// remain authority-derived; screenshot example counts are never copied into
/// application state.
class ReferenceHomeDashboardV3 extends StatefulWidget {
  const ReferenceHomeDashboardV3({
    required this.projection,
    required this.snapshot,
    required this.status,
    required this.onNavigate,
    this.userSession,
    this.onPromptSubmit,
    this.onPromptRefine,
    this.onRefreshRequested,
    super.key,
  });

  final ControlPlaneProjection projection;
  final OperationalSnapshot snapshot;
  final String status;
  final DesktopUserSession? userSession;
  final ValueChanged<DesktopSection> onNavigate;
  final Future<PromptSubmission> Function(String objective)? onPromptSubmit;
  final Future<PromptRefinementPreview> Function(
    String prompt,
    PromptRefinementMode mode,
  )? onPromptRefine;
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
    final groups = _agentGroups(
      widget.snapshot,
      runtimeConnected: widget.projection.connected,
      authorizedTenantId: widget.userSession?.tenantId,
    );
    final operator = desktopOperatorLabel(widget.userSession);

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
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          _t(context, 'Start work', 'İş başlat'),
                          style: const TextStyle(
                            fontSize: 25,
                            height: 1.12,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                      Text(
                        _t(context, 'Operator · $operator', 'Operatör · $operator'),
                        key: const Key('home-operator-identity'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
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
                  const SizedBox(height: 12),
                  PromptEditorPanel(
                    controller: _promptController,
                    enabled: !_submitting && widget.projection.connected,
                    onRefine: widget.onPromptRefine,
                  ),
                  if (referenceAssets != null) ...[
                    const SizedBox(height: 13),
                    ReferenceAssetPicker(
                      key: const Key('home-prompt-attachments'),
                      controller: referenceAssets,
                      enabled: !_submitting,
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
            ? '${groups.length} takım · aynı canonical runtime görünümü'
            : '${groups.length} teams · same canonical runtime view');

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
                    tr ? 'Ajanlar' : 'Agents',
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
                  (constraints.maxWidth - gap * (visible.length - 1)) /
                      visible.length;
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
            child: PixelAgentSprite(
              key: ValueKey('home-pixel-${group.team}'),
              team: group.team,
              view: PixelAgentView.front,
              motion: group.motion,
            ),
          ),
          const Spacer(),
          if (group.active > 0)
            _StatusLine(
              text: tr ? '${group.active} aktif' : '${group.active} active',
            ),
          if (group.working > 0)
            _StatusLine(
              text: tr ? '${group.working} meşgul' : '${group.working} busy',
            ),
          if (group.waiting > 0)
            _StatusLine(
              text: tr ? '${group.waiting} bekliyor' : '${group.waiting} waiting',
            ),
          if (group.idle > 0)
            _StatusLine(
              text: tr ? '${group.idle} boşta' : '${group.idle} idle',
            ),
          if (group.active == 0 &&
              group.working == 0 &&
              group.waiting == 0 &&
              group.idle == 0)
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
  const _StatusLine({required this.text});
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Row(
          children: [
            Icon(
              Icons.circle,
              size: 8,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
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
    required this.working,
    required this.waiting,
    required this.idle,
    required this.offline,
  });

  final String team;
  final int active;
  final int working;
  final int waiting;
  final int idle;
  final int offline;

  PixelAgentMotion get motion {
    if (working > 0) return PixelAgentMotion.working;
    if (waiting > 0) return PixelAgentMotion.waiting;
    if (idle > 0 || active > 0) return PixelAgentMotion.idle;
    return PixelAgentMotion.offline;
  }
}

List<_AgentGroup> _agentGroups(
  OperationalSnapshot snapshot, {
  required bool runtimeConnected,
  String? authorizedTenantId,
}) {
  final states = resolveCanonicalAgentRuntimeStates(
    snapshot,
    runtimeConnected: runtimeConnected,
    authorizedTenantId: authorizedTenantId,
  );
  if (states.isEmpty) return const [];

  final teamsById = <String, String>{};
  final rawAgents = snapshot.agentState['agents'];
  if (rawAgents is List<Object?>) {
    for (final raw in rawAgents.whereType<Map<String, Object?>>()) {
      final id = _text(raw, const ['agent_id']);
      if (id == null || !states.containsKey(id)) continue;
      final team = _text(raw, const ['team', 'group', 'domain']) ??
          _teamFromId(id);
      if (team != null && pixelAgentTeams.contains(team.toLowerCase())) {
        teamsById[id] = team.toLowerCase();
      }
    }
  }

  final buckets = <String, _MutableAgentGroup>{};
  for (final entry in states.entries) {
    final team = teamsById[entry.key] ?? _teamFromId(entry.key);
    if (team == null || !pixelAgentTeams.contains(team.toLowerCase())) continue;
    final normalizedTeam = team.toLowerCase();
    final bucket = buckets.putIfAbsent(
      normalizedTeam,
      () => _MutableAgentGroup(normalizedTeam),
    );
    switch (entry.value) {
      case AgentRuntimeDisplayState.active:
        bucket.active++;
      case AgentRuntimeDisplayState.working:
        bucket.working++;
      case AgentRuntimeDisplayState.waiting:
        bucket.waiting++;
      case AgentRuntimeDisplayState.idle:
        bucket.idle++;
      case AgentRuntimeDisplayState.offline:
        bucket.offline++;
    }
  }

  const order = <String>[
    'core',
    'engineering',
    'security',
    'web',
    'media',
    'intelligence',
    'operations',
    'meta',
  ];
  final groups = <_AgentGroup>[];
  for (final team in order) {
    final bucket = buckets[team];
    if (bucket == null) continue;
    groups.add(
      _AgentGroup(
        team: team,
        active: bucket.active,
        working: bucket.working,
        waiting: bucket.waiting,
        idle: bucket.idle,
        offline: bucket.offline,
      ),
    );
  }
  return groups;
}

class _MutableAgentGroup {
  _MutableAgentGroup(this.team);
  final String team;
  int active = 0;
  int working = 0;
  int waiting = 0;
  int idle = 0;
  int offline = 0;
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

String _displayTeam(String raw, bool tr) {
  final value = raw.toLowerCase();
  if (value.contains('core') || value.contains('kernel')) {
    return tr ? 'Çekirdek' : 'Core';
  }
  if (value.contains('engineering')) {
    return tr ? 'Mühendislik' : 'Engineering';
  }
  if (value.contains('security')) return tr ? 'Güvenlik' : 'Security';
  if (value.contains('web')) return 'Web';
  if (value.contains('media') || value.contains('video')) {
    return tr ? 'Medya' : 'Media';
  }
  if (value.contains('intelligence') ||
      value.contains('research') ||
      value.contains('data')) {
    return tr ? 'İstihbarat' : 'Intelligence';
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