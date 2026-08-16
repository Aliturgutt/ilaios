import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../app/ilaios_surface_catalog.dart';
import '../../app/ilaios_theme.dart';
import '../../control_plane/operational_snapshot.dart';

class LiveWorkspaceView extends StatelessWidget {
  const LiveWorkspaceView({
    required this.snapshot,
    required this.status,
    super.key,
  });

  final OperationalSnapshot snapshot;
  final String status;

  @override
  Widget build(BuildContext context) => DefaultTabController(
        length: 6,
        child: Padding(
          padding: const EdgeInsets.all(22),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: IlaiosTheme.coreBlue.withValues(alpha: .12),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(
                      Icons.developer_mode_outlined,
                      color: IlaiosTheme.coreBlue,
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _surface(context, 'workspace.title'),
                          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontWeight: FontWeight.w800,
                              ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          _localizedStatus(context, status),
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Container(
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.surfaceContainerLow,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: Theme.of(context).colorScheme.outlineVariant,
                  ),
                ),
                child: TabBar(
                  isScrollable: true,
                  tabAlignment: TabAlignment.start,
                  labelColor: IlaiosTheme.enterpriseCyan,
                  unselectedLabelColor: Theme.of(context).colorScheme.onSurfaceVariant,
                  indicatorColor: IlaiosTheme.enterpriseCyan,
                  indicatorWeight: 3,
                  dividerColor: Colors.transparent,
                  tabs: [
                    _tab(context, Icons.code, 'workspace.liveCode'),
                    _tab(context, Icons.terminal, 'workspace.terminal'),
                    _tab(context, Icons.language, 'workspace.browser'),
                    _tab(context, Icons.folder_outlined, 'workspace.files'),
                    _tab(context, Icons.list_alt, 'workspace.logs'),
                    _tab(context, Icons.bolt_outlined, 'workspace.events'),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.surfaceContainerLow,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: Theme.of(context).colorScheme.outlineVariant,
                    ),
                  ),
                  child: TabBarView(
                    children: [
                      _UnavailableWorkspacePane(
                        icon: Icons.code,
                        accent: IlaiosTheme.enterpriseCyan,
                        title: _surface(context, 'workspace.liveCode'),
                        message: _surface(context, 'workspace.codeUnavailable'),
                      ),
                      _UnavailableWorkspacePane(
                        icon: Icons.terminal,
                        accent: IlaiosTheme.violet,
                        title: _surface(context, 'workspace.terminal'),
                        message: _surface(context, 'workspace.terminalUnavailable'),
                      ),
                      _UnavailableWorkspacePane(
                        icon: Icons.language,
                        accent: IlaiosTheme.coreBlue,
                        title: _surface(context, 'workspace.browser'),
                        message: _surface(context, 'workspace.browserUnavailable'),
                      ),
                      _UnavailableWorkspacePane(
                        icon: Icons.folder_outlined,
                        accent: IlaiosTheme.enterpriseCyan,
                        title: _surface(context, 'workspace.files'),
                        message: _surface(context, 'workspace.filesUnavailable'),
                      ),
                      _LogsPane(events: snapshot.liveEvents),
                      _EventsPane(events: snapshot.liveEvents),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      );

  Tab _tab(BuildContext context, IconData icon, String key) => Tab(
        icon: Icon(icon, size: 18),
        text: _surface(context, key),
      );
}

class _UnavailableWorkspacePane extends StatelessWidget {
  const _UnavailableWorkspacePane({
    required this.icon,
    required this.accent,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final Color accent;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Container(
            margin: const EdgeInsets.all(28),
            padding: const EdgeInsets.all(26),
            decoration: BoxDecoration(
              color: accent.withValues(alpha: .055),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: accent.withValues(alpha: .24)),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 58,
                  height: 58,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: .13),
                    borderRadius: BorderRadius.circular(17),
                  ),
                  child: Icon(icon, size: 30, color: accent),
                ),
                const SizedBox(height: 14),
                Text(
                  title,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.w800,
                      ),
                ),
                const SizedBox(height: 8),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium,
                ),
                const SizedBox(height: 10),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(
                    color: IlaiosTheme.enterpriseCyan.withValues(alpha: .08),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    _surface(context, 'workspace.noFabrication'),
                    textAlign: TextAlign.center,
                    style: const TextStyle(
                      color: IlaiosTheme.enterpriseCyan,
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      );
}

class _LogsPane extends StatelessWidget {
  const _LogsPane({required this.events});

  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) {
    final logs = <Map<String, Object?>>[];
    for (final event in events) {
      if (_firstText(event, const ['message', 'log', 'detail']) != null) logs.add(event);
    }
    if (logs.isEmpty) {
      return _UnavailableWorkspacePane(
        icon: Icons.list_alt,
        accent: IlaiosTheme.violet,
        title: _surface(context, 'workspace.logs'),
        message: _surface(context, 'workspace.logsUnavailable'),
      );
    }
    return _EventList(events: logs, showMessage: true);
  }
}

class _EventsPane extends StatelessWidget {
  const _EventsPane({required this.events});

  final List<Map<String, Object?>> events;

  @override
  Widget build(BuildContext context) => events.isEmpty
      ? _UnavailableWorkspacePane(
          icon: Icons.bolt_outlined,
          accent: IlaiosTheme.coreBlue,
          title: _surface(context, 'workspace.events'),
          message: _surface(context, 'workspace.eventsUnavailable'),
        )
      : _EventList(events: events, showMessage: false);
}

class _EventList extends StatelessWidget {
  const _EventList({required this.events, required this.showMessage});

  final List<Map<String, Object?>> events;
  final bool showMessage;

  @override
  Widget build(BuildContext context) => ListView.separated(
        padding: const EdgeInsets.all(14),
        itemCount: events.length,
        separatorBuilder: (_, _) => const Divider(height: 1),
        itemBuilder: (context, index) {
          final event = events[events.length - 1 - index];
          final type = _firstText(event, const ['event_type', 'type']) ?? 'event';
          final message = _firstText(event, const ['message', 'log', 'detail']);
          final timestamp = _firstText(
            event,
            const ['timestamp', 'created_at', 'occurred_at'],
          );
          final state = _firstText(event, const ['state', 'status']);
          final semantics = state == null
              ? '${_surface(context, 'workspace.runtimeEvent')} $type'
              : '${_surface(context, 'workspace.runtimeEvent')} $type, ${_surface(context, 'workspace.state')} $state';
          return Semantics(
            label: semantics,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 5),
                    width: 8,
                    height: 8,
                    decoration: BoxDecoration(
                      color: state == null
                          ? Theme.of(context).colorScheme.outline
                          : _stateColor(state),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          state == null ? type : '$type · $state',
                          style: const TextStyle(fontWeight: FontWeight.w700),
                        ),
                        if (showMessage && message != null) ...[
                          const SizedBox(height: 4),
                          Text(message, style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ],
                    ),
                  ),
                  if (timestamp != null) ...[
                    const SizedBox(width: 12),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 190),
                      child: Text(
                        timestamp,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          );
        },
      );
}

String? _firstText(Map<String, Object?> source, List<String> keys) {
  for (final key in keys) {
    final value = source[key];
    if (value is String && value.trim().isNotEmpty) return value.trim();
    if (value is num || value is bool) return value.toString();
  }
  return null;
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
      normalized.contains('pending')) {
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

String _localizedStatus(BuildContext context, String value) {
  if (context.ilaiosLocale.locale != IlaiosLocale.turkish) return value;
  return switch (value) {
    'Operational APIs connected' => 'Operasyon API’leri bağlı',
    'Connected to authoritative control plane' => 'Yetkili kontrol düzlemine bağlı',
    _ => value,
  };
}

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;
