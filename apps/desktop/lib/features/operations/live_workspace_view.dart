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
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  const Icon(Icons.developer_mode_outlined, color: IlaiosTheme.cyan),
                  const SizedBox(width: 10),
                  Text(
                    _surface(context, 'workspace.title'),
                    style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
              const SizedBox(height: 5),
              Text(
                status,
                style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
              ),
              const SizedBox(height: 16),
              Container(
                decoration: BoxDecoration(
                  color: IlaiosTheme.surface,
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(color: IlaiosTheme.border),
                ),
                child: TabBar(
                  isScrollable: true,
                  tabAlignment: TabAlignment.start,
                  tabs: [
                    Tab(
                      icon: const Icon(Icons.code, size: 17),
                      text: _surface(context, 'workspace.liveCode'),
                    ),
                    Tab(
                      icon: const Icon(Icons.terminal, size: 17),
                      text: _surface(context, 'workspace.terminal'),
                    ),
                    Tab(
                      icon: const Icon(Icons.language, size: 17),
                      text: _surface(context, 'workspace.browser'),
                    ),
                    Tab(
                      icon: const Icon(Icons.folder_outlined, size: 17),
                      text: _surface(context, 'workspace.files'),
                    ),
                    Tab(
                      icon: const Icon(Icons.list_alt, size: 17),
                      text: _surface(context, 'workspace.logs'),
                    ),
                    Tab(
                      icon: const Icon(Icons.bolt_outlined, size: 17),
                      text: _surface(context, 'workspace.events'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              Expanded(
                child: Container(
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: IlaiosTheme.surface,
                    borderRadius: BorderRadius.circular(11),
                    border: Border.all(color: IlaiosTheme.border),
                  ),
                  child: TabBarView(
                    children: [
                      _UnavailableWorkspacePane(
                        icon: Icons.code,
                        title: _surface(context, 'workspace.liveCode'),
                        message: _surface(context, 'workspace.codeUnavailable'),
                      ),
                      _UnavailableWorkspacePane(
                        icon: Icons.terminal,
                        title: _surface(context, 'workspace.terminal'),
                        message: _surface(context, 'workspace.terminalUnavailable'),
                      ),
                      _UnavailableWorkspacePane(
                        icon: Icons.language,
                        title: _surface(context, 'workspace.browser'),
                        message: _surface(context, 'workspace.browserUnavailable'),
                      ),
                      _UnavailableWorkspacePane(
                        icon: Icons.folder_outlined,
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
}

class _UnavailableWorkspacePane extends StatelessWidget {
  const _UnavailableWorkspacePane({
    required this.icon,
    required this.title,
    required this.message,
  });

  final IconData icon;
  final String title;
  final String message;

  @override
  Widget build(BuildContext context) => Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 480),
          child: Padding(
            padding: const EdgeInsets.all(28),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(icon, size: 34, color: IlaiosTheme.muted),
                const SizedBox(height: 12),
                Text(title, style: const TextStyle(fontWeight: FontWeight.w700)),
                const SizedBox(height: 8),
                Text(
                  message,
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: IlaiosTheme.muted, height: 1.5),
                ),
                const SizedBox(height: 8),
                Text(
                  _surface(context, 'workspace.noFabrication'),
                  style: const TextStyle(color: IlaiosTheme.cyan, fontSize: 11),
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
      if (_firstText(event, const ['message', 'log', 'detail']) != null) {
        logs.add(event);
      }
    }
    if (logs.isEmpty) {
      return _UnavailableWorkspacePane(
        icon: Icons.list_alt,
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
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(top: 5),
                    child: Icon(
                      Icons.circle,
                      size: 7,
                      color: state == null ? IlaiosTheme.muted : _stateColor(state),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          state == null ? type : '$type · $state',
                          style: const TextStyle(fontWeight: FontWeight.w600),
                        ),
                        if (showMessage && message != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            message,
                            style: const TextStyle(
                              color: IlaiosTheme.muted,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                  if (timestamp != null) ...[
                    const SizedBox(width: 12),
                    ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 180),
                      child: Text(
                        timestamp,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(
                          color: IlaiosTheme.muted,
                          fontSize: 11,
                        ),
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
    return IlaiosTheme.cyan;
  }
  return IlaiosTheme.muted;
}

String _surface(BuildContext context, String key) =>
    IlaiosSurfaceCatalog.text(context.ilaiosLocale.locale.code, key) ?? key;
