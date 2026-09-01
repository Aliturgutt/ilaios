import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_surface_catalog.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/evidence_record.dart';
import '../../control_plane/operational_snapshot.dart';

/// Reference-faithful Live Workspace surface.
///
/// The supplied Dark/Light screenshots define the visual hierarchy only.
/// Runtime values are projected from [OperationalSnapshot]. Source files,
/// terminal output, browser previews, agent identities, timestamps and evidence
/// are never fabricated from the screenshots. Missing authority is rendered as
/// a truthful empty state inside the same reference panel geometry.
class LiveWorkspaceView extends StatefulWidget {
  const LiveWorkspaceView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  State<LiveWorkspaceView> createState() => _LiveWorkspaceViewState();
}

class _LiveWorkspaceViewState extends State<LiveWorkspaceView> {
  int _tab = 0;
  int _selectedFile = 0;

  @override
  Widget build(BuildContext context) {
    final agents = _agents(widget.snapshot);
    final files = _workspaceFiles(widget.snapshot);
    final events = widget.snapshot.liveEvents;
    final evidence = widget.snapshot.evidenceRecords;
    final session = _sessionProjection(widget.snapshot, widget.status);
    final selectedFile = files.isEmpty
        ? null
        : files[_selectedFile.clamp(0, files.length - 1)];

    return Container(
      key: const Key('reference-live-workspace-page'),
      color: Theme.of(context).scaffoldBackgroundColor,
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                _WorkspaceHeader(session: session),
                const SizedBox(height: 6),
                _SummaryStrip(session: session, agents: agents),
                const SizedBox(height: 6),
                _ActiveAgentsStrip(agents: agents),
                const SizedBox(height: 6),
                _WorkspaceTabs(
                  selected: _tab,
                  onSelected: (value) => setState(() => _tab = value),
                ),
                const SizedBox(height: 3),
                Expanded(
                  child: _WorkspaceBody(
                    tab: _tab,
                    files: files,
                    selectedFile: selectedFile,
                    onSelectFile: (index) => setState(() => _selectedFile = index),
                    events: events,
                    session: session,
                  ),
                ),
                const SizedBox(height: 6),
                SizedBox(
                  height: 112,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(
                        flex: 5,
                        child: _OpenFilesPanel(files: files),
                      ),
                      const SizedBox(width: 7),
                      Expanded(
                        flex: 7,
                        child: _EvidencePanel(evidence: evidence),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          SizedBox(
            width: 192,
            child: _WorkspaceRightRail(
              session: session,
              agents: agents,
              events: events,
            ),
          ),
        ],
      ),
    );
  }
}

class _WorkspaceHeader extends StatelessWidget {
  const _WorkspaceHeader({required this.session});

  final _SessionProjection session;

  @override
  Widget build(BuildContext context) => ConstrainedBox(
        key: const Key('live-workspace-header'),
        constraints: const BoxConstraints(minHeight: 38),
        child: Wrap(
          spacing: 10,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            Text(
              _tr(context, 'Canlı Çalışma Alanı', 'Live Workspace'),
              style: const TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                height: 1,
              ),
            ),
            _Pill(
              text: session.connected
                  ? _tr(context, 'AKTİF OTURUM', 'ACTIVE SESSION')
                  : _tr(context, 'BAĞLANTI YOK', 'OFFLINE'),
              color: session.connected ? IlaiosTheme.success : IlaiosTheme.warning,
            ),
            _MetaInline(
              label: _tr(context, 'Başlangıç', 'Started'),
              value: session.startedAt ?? '—',
            ),
            _MetaInline(
              label: _tr(context, 'Proje', 'Project'),
              value: session.project ?? '—',
            ),
            _HeaderAction(
              icon: Icons.fullscreen_rounded,
              label: _tr(context, 'Tam Ekran', 'Full Screen'),
            ),
            _HeaderAction(
              icon: Icons.handshake_outlined,
              label: _tr(context, 'Paylaş', 'Share'),
            ),
            _HeaderAction(
              icon: Icons.save_outlined,
              label: _tr(context, 'Kaydet', 'Save'),
            ),
            SizedBox(
              width: 32,
              height: 28,
              child: OutlinedButton(
                onPressed: () => _showUnavailable(
                  context,
                  _tr(
                    context,
                    'Ek çalışma alanı eylemleri için yetkili bir Desktop API sözleşmesi bulunmuyor.',
                    'No authoritative Desktop API contract is available for additional workspace actions.',
                  ),
                ),
                style: OutlinedButton.styleFrom(padding: EdgeInsets.zero),
                child: const Icon(Icons.more_horiz_rounded, size: 16),
              ),
            ),
          ],
        ),
      );
}

class _HeaderAction extends StatelessWidget {
  const _HeaderAction({required this.icon, required this.label});

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) => SizedBox(
        height: 28,
        child: OutlinedButton.icon(
          onPressed: () => _showUnavailable(
            context,
            _tr(
              context,
              '$label eylemi henüz yetkili çalışma alanı API sözleşmesine bağlı değil.',
              '$label is not yet bound to an authoritative workspace API contract.',
            ),
          ),
          icon: Icon(icon, size: 14),
          label: Text(label),
          style: OutlinedButton.styleFrom(
            padding: const EdgeInsets.symmetric(horizontal: 9),
            textStyle: const TextStyle(fontSize: 8.2, fontWeight: FontWeight.w600),
          ),
        ),
      );
}

class _MetaInline extends StatelessWidget {
  const _MetaInline({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            '$label:',
            style: TextStyle(
              fontSize: 8.4,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(width: 5),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 155),
            child: Text(
              value,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w600),
            ),
          ),
        ],
      );
}

class _SummaryStrip extends StatelessWidget {
  const _SummaryStrip({required this.session, required this.agents});

  final _SessionProjection session;
  final List<_AgentProjection> agents;

  @override
  Widget build(BuildContext context) {
    final active = agents.where((agent) => agent.active).length;
    return SizedBox(
      key: const Key('live-workspace-summary'),
      height: 56,
      child: Row(
        children: [
          Expanded(
            child: _SummaryCard(
              icon: Icons.code_rounded,
              accent: IlaiosTheme.coreBlue,
              label: _tr(context, 'Çalışma Modu', 'Workspace Mode'),
              value: session.mode ?? '—',
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _SummaryCard(
              icon: Icons.groups_2_outlined,
              accent: IlaiosTheme.violet,
              label: _tr(context, 'Aktif Ajanlar', 'Active Agents'),
              value: agents.isEmpty ? '—' : '$active / ${agents.length}',
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _SummaryCard(
              icon: Icons.flag_outlined,
              accent: IlaiosTheme.coreBlue,
              label: _tr(context, 'Dal / Ortam', 'Branch / Environment'),
              value: session.branch ?? session.environment ?? '—',
              chip: session.environment,
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _SummaryCard(
              icon: Icons.signal_cellular_alt_rounded,
              accent: IlaiosTheme.success,
              label: _tr(context, 'Bağlantı', 'Connection'),
              value: session.connected
                  ? _tr(context, 'Gerçek Zamanlı', 'Real Time')
                  : _tr(context, 'Çevrimdışı', 'Offline'),
              chip: session.connected ? 'real-time' : null,
            ),
          ),
          const SizedBox(width: 6),
          Expanded(
            child: _SummaryCard(
              icon: Icons.sync_rounded,
              accent: IlaiosTheme.enterpriseCyan,
              label: _tr(context, 'Senkronizasyon', 'Synchronization'),
              value: session.syncState ?? '—',
              chip: session.syncState,
            ),
          ),
        ],
      ),
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    required this.icon,
    required this.accent,
    required this.label,
    required this.value,
    this.chip,
  });

  final IconData icon;
  final Color accent;
  final String label;
  final String value;
  final String? chip;

  @override
  Widget build(BuildContext context) => _Card(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        child: Row(
          children: [
            Icon(icon, size: 20, color: accent),
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
                    style: TextStyle(
                      fontSize: 7.2,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Flexible(
                        child: Text(
                          value,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 10.2, fontWeight: FontWeight.w600),
                        ),
                      ),
                      if (chip != null && chip!.trim().isNotEmpty) ...[
                        const SizedBox(width: 6),
                        _TinyTag(text: chip!, color: accent),
                      ],
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _ActiveAgentsStrip extends StatelessWidget {
  const _ActiveAgentsStrip({required this.agents});

  final List<_AgentProjection> agents;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('live-workspace-active-agents'),
        padding: const EdgeInsets.fromLTRB(8, 4, 8, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _tr(context, 'Aktif Ajanlar', 'Active Agents'),
              style: const TextStyle(fontSize: 8.4, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 3),
            SizedBox(
              height: 34,
              child: agents.isEmpty
                  ? Align(
                      alignment: Alignment.centerLeft,
                      child: Text(
                        _tr(
                          context,
                          'Yetkili ajan oturumu bulunmuyor.',
                          'No authoritative agent session is available.',
                        ),
                        style: TextStyle(
                          fontSize: 8,
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                    )
                  : Row(
                      children: [
                        for (final agent in agents.take(5)) ...[
                          Expanded(child: _AgentChip(agent: agent)),
                          const SizedBox(width: 5),
                        ],
                        Expanded(
                          child: OutlinedButton.icon(
                            onPressed: () => _showUnavailable(
                              context,
                              _tr(
                                context,
                                'Ajan daveti için yetkili bir Desktop API sözleşmesi bulunmuyor.',
                                'No authoritative Desktop API contract is available for inviting agents.',
                              ),
                            ),
                            icon: const Icon(Icons.add, size: 13),
                            label: Text(_tr(context, 'Ajan Davet Et', 'Invite Agent')),
                            style: OutlinedButton.styleFrom(
                              minimumSize: const Size.fromHeight(34),
                              padding: const EdgeInsets.symmetric(horizontal: 6),
                              textStyle: const TextStyle(fontSize: 7.5),
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

class _AgentChip extends StatelessWidget {
  const _AgentChip({required this.agent});

  final _AgentProjection agent;

  @override
  Widget build(BuildContext context) => Container(
        height: 34,
        padding: const EdgeInsets.symmetric(horizontal: 6),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            CircleAvatar(
              radius: 10,
              backgroundColor: agent.active
                  ? IlaiosTheme.success.withValues(alpha: .12)
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
              child: Icon(
                Icons.person_outline_rounded,
                size: 12,
                color: agent.active
                    ? IlaiosTheme.success
                    : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(width: 5),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    agent.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 7.6, fontWeight: FontWeight.w600),
                  ),
                  Text(
                    agent.owner ?? agent.id,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 6.7,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
            if (agent.state != null)
              _TinyTag(
                text: agent.state!,
                color: agent.active ? IlaiosTheme.success : IlaiosTheme.coreBlue,
              ),
          ],
        ),
      );
}

class _WorkspaceTabs extends StatelessWidget {
  const _WorkspaceTabs({required this.selected, required this.onSelected});

  final int selected;
  final ValueChanged<int> onSelected;

  @override
  Widget build(BuildContext context) {
    final tabs = <(IconData, String, String)>[
      (Icons.code_rounded, 'Canlı Kod', 'Live Code'),
      (Icons.terminal_rounded, 'Terminal', 'Terminal'),
      (Icons.chat_bubble_outline_rounded, 'Tartışma', 'Discussion'),
      (Icons.folder_outlined, 'Dosyalar', 'Files'),
      (Icons.list_alt_rounded, 'Günlükler', 'Logs'),
      (Icons.info_outline_rounded, 'Olaylar', 'Events'),
    ];
    return Container(
      key: const Key('live-workspace-tabs'),
      height: 31,
      decoration: BoxDecoration(
        border: Border(
          bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
        ),
      ),
      child: Row(
        children: [
          for (final entry in tabs.indexed)
            InkWell(
              key: ValueKey('workspace-tab-${entry.$1}'),
              onTap: () => onSelected(entry.$1),
              child: Container(
                height: 31,
                padding: const EdgeInsets.symmetric(horizontal: 11),
                decoration: BoxDecoration(
                  border: Border(
                    bottom: BorderSide(
                      color: selected == entry.$1
                          ? IlaiosTheme.enterpriseCyan
                          : Colors.transparent,
                      width: 2,
                    ),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      entry.$2.$1,
                      size: 13,
                      color: selected == entry.$1
                          ? IlaiosTheme.enterpriseCyan
                          : Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 5),
                    Text(
                      _tr(context, entry.$2.$2, entry.$2.$3),
                      style: TextStyle(
                        fontSize: 8.2,
                        fontWeight: selected == entry.$1 ? FontWeight.w600 : FontWeight.w500,
                        color: selected == entry.$1
                            ? IlaiosTheme.enterpriseCyan
                            : Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class _WorkspaceBody extends StatelessWidget {
  const _WorkspaceBody({
    required this.tab,
    required this.files,
    required this.selectedFile,
    required this.onSelectFile,
    required this.events,
    required this.session,
  });

  final int tab;
  final List<_WorkspaceFile> files;
  final _WorkspaceFile? selectedFile;
  final ValueChanged<int> onSelectFile;
  final List<Map<String, Object?>> events;
  final _SessionProjection session;

  @override
  Widget build(BuildContext context) {
    if (tab == 0) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 142,
            child: _FilesPane(files: files, onSelect: onSelectFile),
          ),
          const SizedBox(width: 4),
          Expanded(
            flex: 5,
            child: _CodePane(file: selectedFile),
          ),
          const SizedBox(width: 4),
          Expanded(
            flex: 4,
            child: _TerminalPane(events: events),
          ),
          const SizedBox(width: 4),
          Expanded(
            flex: 7,
            child: _BrowserPane(session: session),
          ),
        ],
      );
    }
    if (tab == 1) return _LargeTerminalPane(events: events);
    if (tab == 2) return _DiscussionPane(events: events);
    if (tab == 3) return _LargeFilesPane(files: files);
    if (tab == 4) return _EventPane(events: events, showMessages: true);
    return _EventPane(events: events, showMessages: false);
  }
}

class _FilesPane extends StatelessWidget {
  const _FilesPane({required this.files, required this.onSelect});

  final List<_WorkspaceFile> files;
  final ValueChanged<int> onSelect;

  @override
  Widget build(BuildContext context) => _PanelShell(
        key: const Key('live-workspace-files-pane'),
        title: _tr(context, 'Dosyalar', 'Files'),
        child: files.isEmpty
            ? _MiniEmpty(
                icon: Icons.folder_off_outlined,
                message: _tr(
                  context,
                  'Yetkili dosya ağacı yok.',
                  'No authoritative file tree.',
                ),
              )
            : ListView.builder(
                padding: const EdgeInsets.symmetric(vertical: 4),
                itemCount: files.length,
                itemBuilder: (context, index) {
                  final file = files[index];
                  return InkWell(
                    onTap: () => onSelect(index),
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 4),
                      child: Row(
                        children: [
                          Icon(
                            file.directory ? Icons.folder_outlined : Icons.code_rounded,
                            size: 12,
                            color: file.directory
                                ? IlaiosTheme.warning
                                : IlaiosTheme.coreBlue,
                          ),
                          const SizedBox(width: 5),
                          Expanded(
                            child: Text(
                              file.path,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontSize: 7.2),
                            ),
                          ),
                          if (file.state != null)
                            Text(
                              file.state!,
                              style: const TextStyle(
                                fontSize: 6.5,
                                color: IlaiosTheme.warning,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                        ],
                      ),
                    ),
                  );
                },
              ),
      );
}

class _CodePane extends StatelessWidget {
  const _CodePane({required this.file});

  final _WorkspaceFile? file;

  @override
  Widget build(BuildContext context) => _PanelShell(
        key: const Key('live-workspace-code-pane'),
        title: file?.name ?? _tr(context, 'Canlı Kod', 'Live Code'),
        trailing: file?.language,
        child: file?.content == null
            ? _MiniEmpty(
                icon: Icons.code_off_rounded,
                message: _tr(
                  context,
                  'Yetkili kaynak dosya içeriği yayınlanmıyor.',
                  'Authoritative source-file content is not being published.',
                ),
              )
            : _CodeText(content: file!.content!),
      );
}

class _CodeText extends StatelessWidget {
  const _CodeText({required this.content});

  final String content;

  @override
  Widget build(BuildContext context) {
    final lines = content.split('\n');
    return ListView.builder(
      padding: const EdgeInsets.fromLTRB(7, 5, 7, 5),
      itemCount: lines.length,
      itemBuilder: (context, index) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 20,
            child: Text(
              '${index + 1}',
              textAlign: TextAlign.right,
              style: TextStyle(
                fontFamily: 'monospace',
                fontSize: 6.8,
                color: Theme.of(context).colorScheme.outline,
              ),
            ),
          ),
          const SizedBox(width: 7),
          Expanded(
            child: Text(
              lines[index],
              style: TextStyle(
                fontFamily: 'monospace',
                fontSize: 6.8,
                height: 1.45,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TerminalPane extends StatelessWidget {
  const _TerminalPane({required this.events});

  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) {
    final messages = _eventMessages(events);
    return _PanelShell(
      key: const Key('live-workspace-terminal-pane'),
      title: _tr(context, 'Terminal', 'Terminal'),
      child: messages.isEmpty
          ? _MiniEmpty(
              icon: Icons.terminal_rounded,
              message: _tr(
                context,
                'Yetkili terminal çıktısı yok.',
                'No authoritative terminal output.',
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(7),
              itemCount: messages.length.clamp(0, 24),
              itemBuilder: (context, index) => Padding(
                padding: const EdgeInsets.only(bottom: 3),
                child: Text(
                  messages[messages.length - 1 - index],
                  style: TextStyle(
                    fontFamily: 'monospace',
                    fontSize: 6.8,
                    height: 1.3,
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ),
    );
  }
}

class _BrowserPane extends StatelessWidget {
  const _BrowserPane({required this.session});

  final _SessionProjection session;

  @override
  Widget build(BuildContext context) => _PanelShell(
        key: const Key('live-workspace-browser-pane'),
        title: _tr(context, 'Tarayıcı', 'Browser'),
        trailing: session.previewUrl,
        child: Column(
          children: [
            Container(
              height: 27,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.surfaceContainerLowest,
                border: Border(
                  bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
                ),
              ),
              child: Row(
                children: [
                  const Icon(Icons.arrow_back_rounded, size: 12),
                  const SizedBox(width: 6),
                  const Icon(Icons.arrow_forward_rounded, size: 12),
                  const SizedBox(width: 6),
                  const Icon(Icons.refresh_rounded, size: 12),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Container(
                      height: 19,
                      padding: const EdgeInsets.symmetric(horizontal: 7),
                      alignment: Alignment.centerLeft,
                      decoration: BoxDecoration(
                        color: Theme.of(context).colorScheme.surfaceContainerLow,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
                      ),
                      child: Text(
                        session.previewUrl ?? _tr(context, 'Önizleme kullanılamıyor', 'Preview unavailable'),
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontSize: 6.8),
                      ),
                    ),
                  ),
                  const SizedBox(width: 6),
                  const Icon(Icons.open_in_new_rounded, size: 12),
                ],
              ),
            ),
            Expanded(
              child: _MiniEmpty(
                icon: Icons.language_rounded,
                message: session.previewUrl == null
                    ? _tr(
                        context,
                        'Yetkili tarayıcı önizlemesi bağlı değil.',
                        'No authoritative browser preview is connected.',
                      )
                    : _tr(
                        context,
                        'Önizleme URL’si mevcut; gömülü web görünümü Desktop sözleşmesine bağlı değil.',
                        'A preview URL is available; embedded web rendering is not bound to the Desktop contract.',
                      ),
              ),
            ),
          ],
        ),
      );
}

class _LargeTerminalPane extends StatelessWidget {
  const _LargeTerminalPane({required this.events});

  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) => _PanelShell(
        title: _tr(context, 'Terminal', 'Terminal'),
        child: _TerminalPane(events: events),
      );
}

class _DiscussionPane extends StatelessWidget {
  const _DiscussionPane({required this.events});

  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) {
    final discussions = events.where((event) {
      final type = _firstText(event, const ['event_type', 'type'])?.toLowerCase() ?? '';
      return type.contains('comment') || type.contains('discussion') || type.contains('message');
    }).toList(growable: false);
    return _PanelShell(
      title: _tr(context, 'Tartışma', 'Discussion'),
      child: discussions.isEmpty
          ? _MiniEmpty(
              icon: Icons.chat_bubble_outline_rounded,
              message: _tr(
                context,
                'Yetkili tartışma kaydı yok.',
                'No authoritative discussion records are available.',
              ),
            )
          : _EventList(events: discussions, showMessage: true),
    );
  }
}

class _LargeFilesPane extends StatelessWidget {
  const _LargeFilesPane({required this.files});

  final List<_WorkspaceFile> files;

  @override
  Widget build(BuildContext context) => _PanelShell(
        title: _tr(context, 'Dosyalar', 'Files'),
        child: files.isEmpty
            ? _MiniEmpty(
                icon: Icons.folder_off_outlined,
                message: _tr(
                  context,
                  'Yetkili çalışma alanı dosyaları yayınlanmıyor.',
                  'Authoritative workspace files are not being published.',
                ),
              )
            : ListView.separated(
                padding: const EdgeInsets.all(8),
                itemCount: files.length,
                separatorBuilder: (_, _) => const Divider(height: 1),
                itemBuilder: (context, index) {
                  final file = files[index];
                  return ListTile(
                    dense: true,
                    visualDensity: VisualDensity.compact,
                    leading: Icon(file.directory ? Icons.folder_outlined : Icons.code_rounded, size: 16),
                    title: Text(file.path, style: const TextStyle(fontSize: 9)),
                    subtitle: file.language == null ? null : Text(file.language!, style: const TextStyle(fontSize: 7.5)),
                    trailing: file.state == null ? null : Text(file.state!, style: const TextStyle(fontSize: 7.5)),
                  );
                },
              ),
      );
}

class _EventPane extends StatelessWidget {
  const _EventPane({required this.events, required this.showMessages});

  final List<Map<String, Object?>> events;
  final bool showMessages;

  @override
  Widget build(BuildContext context) => _PanelShell(
        title: showMessages ? _tr(context, 'Günlükler', 'Logs') : _tr(context, 'Olaylar', 'Events'),
        child: events.isEmpty
            ? _MiniEmpty(
                icon: showMessages ? Icons.list_alt_rounded : Icons.info_outline_rounded,
                message: _tr(
                  context,
                  'Yetkili çalışma alanı olayı yok.',
                  'No authoritative workspace events are available.',
                ),
              )
            : _EventList(events: events, showMessage: showMessages),
      );
}

class _OpenFilesPanel extends StatelessWidget {
  const _OpenFilesPanel({required this.files});

  final List<_WorkspaceFile> files;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('live-workspace-open-files'),
        padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Text(
                  _tr(context, 'AÇIK DOSYALAR & SON DEĞİŞİKLİKLER', 'OPEN FILES & RECENT CHANGES'),
                  style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                Text(
                  _tr(context, 'Tümünü Gör', 'View All'),
                  style: const TextStyle(fontSize: 7.4, color: IlaiosTheme.coreBlue),
                ),
                const Icon(Icons.chevron_right_rounded, size: 12, color: IlaiosTheme.coreBlue),
              ],
            ),
            const SizedBox(height: 6),
            Expanded(
              child: files.isEmpty
                  ? _MiniEmpty(
                      icon: Icons.description_outlined,
                      message: _tr(context, 'Açık dosya kaydı yok.', 'No open-file records.'),
                    )
                  : Row(
                      children: [
                        for (final file in files.take(5)) ...[
                          Expanded(child: _FileCard(file: file)),
                          const SizedBox(width: 5),
                        ],
                      ],
                    ),
            ),
          ],
        ),
      );
}

class _FileCard extends StatelessWidget {
  const _FileCard({required this.file});

  final _WorkspaceFile file;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                const Icon(Icons.code_rounded, size: 13, color: IlaiosTheme.coreBlue),
                const SizedBox(width: 5),
                Expanded(
                  child: Text(
                    file.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w600),
                  ),
                ),
                if (file.state != null)
                  Text(
                    file.state!,
                    style: const TextStyle(fontSize: 6.6, color: IlaiosTheme.warning),
                  ),
              ],
            ),
            const SizedBox(height: 5),
            Text(
              file.path,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 6.6, color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
            const Spacer(),
            Text(
              file.updatedAt ?? '—',
              style: TextStyle(fontSize: 6.6, color: Theme.of(context).colorScheme.onSurfaceVariant),
            ),
          ],
        ),
      );
}

class _EvidencePanel extends StatelessWidget {
  const _EvidencePanel({required this.evidence});

  final List<EvidenceRecord> evidence;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('live-workspace-evidence'),
        padding: const EdgeInsets.fromLTRB(8, 6, 8, 6),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Text(
                  _tr(context, 'KANIT & DOĞRULAMA', 'EVIDENCE & VERIFICATION'),
                  style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w700),
                ),
                const Spacer(),
                Text(
                  _tr(context, 'Tümünü Gör', 'View All'),
                  style: const TextStyle(fontSize: 7.4, color: IlaiosTheme.coreBlue),
                ),
                const Icon(Icons.chevron_right_rounded, size: 12, color: IlaiosTheme.coreBlue),
              ],
            ),
            const SizedBox(height: 6),
            Expanded(
              child: evidence.isEmpty
                  ? _MiniEmpty(
                      icon: Icons.verified_user_outlined,
                      message: _tr(
                        context,
                        'Doğrulanmış kanıt kaydı yok.',
                        'No verified evidence records are available.',
                      ),
                    )
                  : Row(
                      children: [
                        for (final record in evidence.reversed.take(4)) ...[
                          Expanded(child: _EvidenceCard(record: record)),
                          const SizedBox(width: 5),
                        ],
                      ],
                    ),
            ),
          ],
        ),
      );
}

class _EvidenceCard extends StatelessWidget {
  const _EvidenceCard({required this.record});

  final EvidenceRecord record;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(7),
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(5),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              width: 27,
              height: 27,
              decoration: BoxDecoration(
                color: IlaiosTheme.success.withValues(alpha: .09),
                shape: BoxShape.circle,
              ),
              child: const Icon(Icons.verified_user_outlined, size: 17, color: IlaiosTheme.success),
            ),
            const SizedBox(width: 7),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    record.action,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 7.3, fontWeight: FontWeight.w700),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    record.executionId,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 6.4, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _tr(context, 'Geçti', 'Verified'),
                    style: const TextStyle(fontSize: 6.8, color: IlaiosTheme.success, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
}

class _WorkspaceRightRail extends StatelessWidget {
  const _WorkspaceRightRail({
    required this.session,
    required this.agents,
    required this.events,
  });

  final _SessionProjection session;
  final List<_AgentProjection> agents;
  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _SessionPanel(session: session, agents: agents),
          const SizedBox(height: 7),
          Expanded(
            child: _ActivityPanel(events: events),
          ),
          const SizedBox(height: 7),
          SizedBox(
            height: 154,
            child: _ReviewNotesPanel(events: events),
          ),
        ],
      );
}

class _SessionPanel extends StatelessWidget {
  const _SessionPanel({required this.session, required this.agents});

  final _SessionProjection session;
  final List<_AgentProjection> agents;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('live-workspace-session-panel'),
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              _tr(context, 'OTURUM DURUMU', 'SESSION STATUS'),
              style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 9),
            _RailValue(label: _tr(context, 'Oturum ID', 'Session ID'), value: session.id ?? '—'),
            _RailValue(label: _tr(context, 'Süre', 'Elapsed'), value: session.elapsed ?? '—'),
            _RailValue(label: _tr(context, 'Sahip', 'Owner'), value: session.owner ?? '—'),
            _RailValue(label: _tr(context, 'Mod', 'Mode'), value: session.mode ?? '—'),
            _RailValue(
              label: _tr(context, 'Bağlı Ajanlar', 'Connected Agents'),
              value: agents.isEmpty ? '—' : '${agents.where((a) => a.active).length} / ${agents.length}',
            ),
            _RailValue(label: _tr(context, 'Son Kaydetme', 'Last Save'), value: session.lastSave ?? '—'),
            const SizedBox(height: 5),
            Row(
              children: [
                Icon(
                  Icons.circle,
                  size: 6,
                  color: session.connected ? IlaiosTheme.success : Theme.of(context).colorScheme.outline,
                ),
                const SizedBox(width: 5),
                Text(
                  session.connected ? _tr(context, 'Aktif', 'Active') : _tr(context, 'Çevrimdışı', 'Offline'),
                  style: TextStyle(
                    fontSize: 7.2,
                    color: session.connected ? IlaiosTheme.success : Theme.of(context).colorScheme.onSurfaceVariant,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),
          ],
        ),
      );
}

class _RailValue extends StatelessWidget {
  const _RailValue({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 7),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Text(
                label,
                style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
            ),
            const SizedBox(width: 6),
            Flexible(
              child: Text(
                value,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                textAlign: TextAlign.right,
                style: const TextStyle(fontSize: 7, fontWeight: FontWeight.w600),
              ),
            ),
          ],
        ),
      );
}

class _ActivityPanel extends StatelessWidget {
  const _ActivityPanel({required this.events});

  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) => _Card(
        key: const Key('live-workspace-activity-panel'),
        padding: const EdgeInsets.fromLTRB(9, 8, 9, 7),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Text(
                  _tr(context, 'CANLI ETKİNLİK', 'LIVE ACTIVITY'),
                  style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w700),
                ),
                const Spacer(),
              ],
            ),
            const SizedBox(height: 7),
            Expanded(
              child: events.isEmpty
                  ? _MiniEmpty(
                      icon: Icons.history_toggle_off_rounded,
                      message: _tr(context, 'Canlı etkinlik yok.', 'No live activity.'),
                    )
                  : ListView.builder(
                      padding: EdgeInsets.zero,
                      itemCount: events.length.clamp(0, 7),
                      itemBuilder: (context, index) {
                        final event = events[events.length - 1 - index];
                        final type = _firstText(event, const ['event_type', 'type']) ?? 'event';
                        final message = _firstText(event, const ['message', 'detail', 'path']);
                        final time = _firstText(event, const ['timestamp', 'created_at', 'occurred_at']) ?? '—';
                        return Padding(
                          padding: const EdgeInsets.only(bottom: 8),
                          child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              SizedBox(
                                width: 37,
                                child: Text(
                                  _shortTime(time),
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(fontSize: 6.5, color: Theme.of(context).colorScheme.onSurfaceVariant),
                                ),
                              ),
                              Container(
                                margin: const EdgeInsets.only(top: 3),
                                width: 6,
                                height: 6,
                                decoration: const BoxDecoration(
                                  color: IlaiosTheme.coreBlue,
                                  shape: BoxShape.circle,
                                ),
                              ),
                              const SizedBox(width: 5),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      type,
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 6.8, fontWeight: FontWeight.w600),
                                    ),
                                    if (message != null)
                                      Text(
                                        message,
                                        maxLines: 2,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(fontSize: 6.2, color: Theme.of(context).colorScheme.onSurfaceVariant),
                                      ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),
            ),
            Align(
              alignment: Alignment.centerRight,
              child: Text(
                _tr(context, 'Tüm etkinlikleri görüntüle  ›', 'View all activity  ›'),
                style: const TextStyle(fontSize: 6.8, color: IlaiosTheme.coreBlue),
              ),
            ),
          ],
        ),
      );
}

class _ReviewNotesPanel extends StatelessWidget {
  const _ReviewNotesPanel({required this.events});

  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) {
    final reviews = events.where((event) {
      final type = (_firstText(event, const ['event_type', 'type', 'state']) ?? '').toLowerCase();
      return type.contains('review') || type.contains('check') || type.contains('approval');
    }).toList(growable: false);
    return _Card(
      key: const Key('live-workspace-review-panel'),
      padding: const EdgeInsets.fromLTRB(9, 8, 9, 7),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Text(
                _tr(context, 'İNCELEME & NOTLAR', 'REVIEW & NOTES'),
                style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w700),
              ),
              const Spacer(),
              const Icon(Icons.more_horiz_rounded, size: 13),
            ],
          ),
          const SizedBox(height: 7),
          Expanded(
            child: reviews.isEmpty
                ? _MiniEmpty(
                    icon: Icons.fact_check_outlined,
                    message: _tr(context, 'İnceleme kaydı yok.', 'No review records.'),
                  )
                : ListView.builder(
                    padding: EdgeInsets.zero,
                    itemCount: reviews.length.clamp(0, 4),
                    itemBuilder: (context, index) {
                      final event = reviews[reviews.length - 1 - index];
                      final message = _firstText(event, const ['message', 'detail', 'event_type', 'type']) ?? '—';
                      final owner = _firstText(event, const ['owner', 'agent_name', 'agent_id', 'actor']);
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Row(
                          children: [
                            const Icon(Icons.check_box_outlined, size: 11, color: IlaiosTheme.success),
                            const SizedBox(width: 5),
                            Expanded(
                              child: Text(
                                message,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontSize: 6.7),
                              ),
                            ),
                            if (owner != null) ...[
                              const SizedBox(width: 4),
                              Text(
                                owner,
                                maxLines: 1,
                                overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontSize: 6.2, color: Theme.of(context).colorScheme.onSurfaceVariant),
                              ),
                            ],
                          ],
                        ),
                      );
                    },
                  ),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: Text(
              _tr(context, 'Tüm görevleri görüntüle  ›', 'View all tasks  ›'),
              style: const TextStyle(fontSize: 6.8, color: IlaiosTheme.coreBlue),
            ),
          ),
        ],
      ),
    );
  }
}

class _PanelShell extends StatelessWidget {
  const _PanelShell({
    required this.title,
    required this.child,
    this.trailing,
    super.key,
  });

  final String title;
  final Widget child;
  final String? trailing;

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(4),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              height: 27,
              padding: const EdgeInsets.symmetric(horizontal: 7),
              decoration: BoxDecoration(
                border: Border(
                  bottom: BorderSide(color: Theme.of(context).colorScheme.outlineVariant),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 7.2, fontWeight: FontWeight.w600),
                    ),
                  ),
                  if (trailing != null)
                    Flexible(
                      child: Text(
                        trailing!,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 6.2, color: Theme.of(context).colorScheme.onSurfaceVariant),
                      ),
                    ),
                  const SizedBox(width: 4),
                  const Icon(Icons.more_horiz_rounded, size: 12),
                ],
              ),
            ),
            Expanded(child: child),
          ],
        ),
      );
}

class _Card extends StatelessWidget {
  const _Card({required this.child, this.padding = const EdgeInsets.all(8), super.key});

  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) => Container(
        padding: padding,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(6),
          border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        ),
        child: child,
      );
}

class _Pill extends StatelessWidget {
  const _Pill({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .09),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: color.withValues(alpha: .18)),
        ),
        child: Text(
          text,
          style: TextStyle(fontSize: 6.9, color: color, fontWeight: FontWeight.w700),
        ),
      );
}

class _TinyTag extends StatelessWidget {
  const _TinyTag({required this.text, required this.color});

  final String text;
  final Color color;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 2),
        decoration: BoxDecoration(
          color: color.withValues(alpha: .10),
          borderRadius: BorderRadius.circular(3),
        ),
        child: Text(
          text,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(fontSize: 5.9, color: color, fontWeight: FontWeight.w600),
        ),
      );
}

class _MiniEmpty extends StatelessWidget {
  const _MiniEmpty({required this.icon, required this.message});

  final IconData icon;
  final String message;

  @override
  Widget build(BuildContext context) => Center(
        child: Padding(
          padding: const EdgeInsets.all(7),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 18, color: Theme.of(context).colorScheme.outline),
              const SizedBox(height: 5),
              Text(
                message,
                textAlign: TextAlign.center,
                style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant),
              ),
            ],
          ),
        ),
      );
}

class _EventList extends StatelessWidget {
  const _EventList({required this.events, required this.showMessage});

  final List<Map<String, Object?>> events;
  final bool showMessage;

  @override
  Widget build(BuildContext context) => ListView.separated(
        padding: const EdgeInsets.all(8),
        itemCount: events.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final event = events[events.length - 1 - index];
          final type = _firstText(event, const ['event_type', 'type']) ?? 'event';
          final message = _firstText(event, const ['message', 'log', 'detail']);
          final timestamp = _firstText(event, const ['timestamp', 'created_at', 'occurred_at']);
          final state = _firstText(event, const ['state', 'status']);
          return Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  margin: const EdgeInsets.only(top: 4),
                  width: 6,
                  height: 6,
                  decoration: BoxDecoration(
                    color: state == null ? Theme.of(context).colorScheme.outline : _stateColor(state),
                    shape: BoxShape.circle,
                  ),
                ),
                const SizedBox(width: 7),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        state == null ? type : '$type · $state',
                        style: const TextStyle(fontSize: 8, fontWeight: FontWeight.w600),
                      ),
                      if (showMessage && message != null) ...[
                        const SizedBox(height: 3),
                        Text(message, style: const TextStyle(fontSize: 7.2)),
                      ],
                    ],
                  ),
                ),
                if (timestamp != null)
                  Text(
                    _shortTime(timestamp),
                    style: TextStyle(fontSize: 6.8, color: Theme.of(context).colorScheme.onSurfaceVariant),
                  ),
              ],
            ),
          );
        },
      );
}

class _SessionProjection {
  const _SessionProjection({
    required this.connected,
    this.id,
    this.startedAt,
    this.elapsed,
    this.owner,
    this.mode,
    this.project,
    this.branch,
    this.environment,
    this.syncState,
    this.previewUrl,
    this.lastSave,
  });

  final bool connected;
  final String? id;
  final String? startedAt;
  final String? elapsed;
  final String? owner;
  final String? mode;
  final String? project;
  final String? branch;
  final String? environment;
  final String? syncState;
  final String? previewUrl;
  final String? lastSave;
}

class _AgentProjection {
  const _AgentProjection({
    required this.id,
    required this.name,
    required this.active,
    this.owner,
    this.state,
  });

  final String id;
  final String name;
  final bool active;
  final String? owner;
  final String? state;
}

class _WorkspaceFile {
  const _WorkspaceFile({
    required this.path,
    required this.name,
    required this.directory,
    this.content,
    this.language,
    this.state,
    this.updatedAt,
  });

  final String path;
  final String name;
  final bool directory;
  final String? content;
  final String? language;
  final String? state;
  final String? updatedAt;
}

_SessionProjection _sessionProjection(OperationalSnapshot snapshot, String status) {
  final sources = <Map<String, Object?>>[
    snapshot.schedulerState,
    snapshot.governanceState,
    if (snapshot.liveEvents.isNotEmpty) snapshot.liveEvents.last,
  ];
  String? read(List<String> keys) {
    for (final source in sources) {
      final value = _firstText(source, keys);
      if (value != null) return value;
    }
    return null;
  }

  final statusLower = status.toLowerCase();
  final connected = statusLower.contains('connected') ||
      statusLower.contains('bağlı') ||
      statusLower.contains('operational');
  return _SessionProjection(
    connected: connected,
    id: read(const ['session_id', 'workspace_session_id', 'run_id', 'execution_id']),
    startedAt: read(const ['started_at', 'start_time', 'session_started_at']),
    elapsed: read(const ['elapsed', 'duration', 'session_duration']),
    owner: read(const ['owner', 'principal_id', 'user', 'created_by']),
    mode: read(const ['workspace_mode', 'mode', 'execution_mode']),
    project: read(const ['project_name', 'project', 'workspace', 'goal', 'objective']),
    branch: read(const ['branch', 'git_branch', 'source_branch']),
    environment: read(const ['environment', 'env', 'runtime_environment']),
    syncState: read(const ['sync_state', 'synchronization', 'sync_status']),
    previewUrl: read(const ['preview_url', 'browser_url', 'url', 'localhost_url']),
    lastSave: read(const ['last_save', 'saved_at', 'last_saved_at']),
  );
}

List<_AgentProjection> _agents(OperationalSnapshot snapshot) {
  final raw = _mapList(snapshot.schedulerState['agents']).isNotEmpty
      ? _mapList(snapshot.schedulerState['agents'])
      : _mapList(snapshot.schedulerState['workers']);
  return raw.map((item) {
    final id = _firstText(item, const ['agent_id', 'worker_id', 'id']) ?? '—';
    final name = _firstText(item, const ['agent_name', 'name', 'role']) ?? id;
    final state = _firstText(item, const ['status', 'state', 'activity']);
    final normalized = state?.toLowerCase() ?? '';
    final active = normalized.contains('active') ||
        normalized.contains('running') ||
        normalized.contains('busy') ||
        normalized.contains('working') ||
        normalized.contains('coding') ||
        normalized.contains('testing');
    return _AgentProjection(
      id: id,
      name: name,
      active: active,
      owner: _firstText(item, const ['owner', 'assignee', 'principal_id']),
      state: state,
    );
  }).toList(growable: false);
}

List<_WorkspaceFile> _workspaceFiles(OperationalSnapshot snapshot) {
  final candidates = <Object?>[
    snapshot.schedulerState['workspace_files'],
    snapshot.schedulerState['files'],
    snapshot.schedulerState['open_files'],
  ];
  List<Map<String, Object?>> raw = const <Map<String, Object?>>[];
  for (final candidate in candidates) {
    final parsed = _mapList(candidate);
    if (parsed.isNotEmpty) {
      raw = parsed;
      break;
    }
  }
  return raw.map((item) {
    final path = _firstText(item, const ['path', 'file_path', 'name']) ?? '—';
    final slash = path.replaceAll('\\', '/').split('/');
    final name = _firstText(item, const ['name', 'file_name']) ?? slash.last;
    final type = _firstText(item, const ['type', 'kind']);
    final directory = type?.toLowerCase().contains('dir') ?? false;
    return _WorkspaceFile(
      path: path,
      name: name,
      directory: directory,
      content: _firstText(item, const ['content', 'text', 'source']),
      language: _firstText(item, const ['language', 'lang', 'syntax']),
      state: _firstText(item, const ['state', 'status', 'change']),
      updatedAt: _firstText(item, const ['updated_at', 'timestamp', 'modified_at']),
    );
  }).toList(growable: false);
}

List<String> _eventMessages(List<Map<String, Object?>> events) {
  final output = <String>[];
  for (final event in events) {
    final message = _firstText(event, const ['message', 'log', 'detail', 'event_type', 'type']);
    if (message != null) output.add(message);
  }
  return output;
}

String? _firstText(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return value.toString();
  }
  return null;
}

List<Map<String, Object?>> _mapList(Object? value) {
  if (value is! List<Object?>) return const <Map<String, Object?>>[];
  return value.whereType<Map<String, Object?>>().toList(growable: false);
}

Color _stateColor(String value) {
  final normalized = value.toLowerCase();
  if (normalized.contains('fail') ||
      normalized.contains('error') ||
      normalized.contains('unhealthy') ||
      normalized.contains('denied')) {
    return IlaiosTheme.danger;
  }
  if (normalized.contains('block') ||
      normalized.contains('warn') ||
      normalized.contains('pending') ||
      normalized.contains('review')) {
    return IlaiosTheme.warning;
  }
  if (normalized.contains('complete') ||
      normalized.contains('success') ||
      normalized.contains('healthy') ||
      normalized.contains('passed')) {
    return IlaiosTheme.success;
  }
  if (normalized.contains('running') ||
      normalized.contains('active') ||
      normalized.contains('working')) {
    return IlaiosTheme.enterpriseCyan;
  }
  return IlaiosTheme.coreBlue;
}

String _shortTime(String value) {
  if (value.length <= 8) return value;
  final match = RegExp(r'(\d{2}:\d{2})(?::\d{2})?').firstMatch(value);
  return match?.group(1) ?? value;
}

String _tr(BuildContext context, String tr, String en) =>
    context.ilaiosLocale.locale == IlaiosLocale.turkish ? tr : en;

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;

void _showUnavailable(BuildContext context, String message) {
  final title = _surface(context, 'workspace.title');
  showDialog<void>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: const Text('OK')),
      ],
    ),
  );
}