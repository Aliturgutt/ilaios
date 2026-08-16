import 'package:flutter/material.dart';

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
              const Row(
                children: [
                  Icon(Icons.developer_mode_outlined, color: IlaiosTheme.cyan),
                  SizedBox(width: 10),
                  Text(
                    'Live Workspace',
                    style: TextStyle(fontSize: 20, fontWeight: FontWeight.w700),
                  ),
                ],
              ),
              const SizedBox(height: 5),
              Text(status, style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12)),
              const SizedBox(height: 16),
              Container(
                decoration: BoxDecoration(
                  color: IlaiosTheme.surface,
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(color: IlaiosTheme.border),
                ),
                child: const TabBar(
                  isScrollable: true,
                  tabAlignment: TabAlignment.start,
                  tabs: [
                    Tab(icon: Icon(Icons.code, size: 17), text: 'Live Code'),
                    Tab(icon: Icon(Icons.terminal, size: 17), text: 'Terminal'),
                    Tab(icon: Icon(Icons.language, size: 17), text: 'Browser'),
                    Tab(icon: Icon(Icons.folder_outlined, size: 17), text: 'Files'),
                    Tab(icon: Icon(Icons.list_alt, size: 17), text: 'Logs'),
                    Tab(icon: Icon(Icons.bolt_outlined, size: 17), text: 'Events'),
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
                      const _UnavailableWorkspacePane(
                        icon: Icons.code,
                        title: 'Live Code',
                        message:
                            'The current Desktop API does not expose a safe working-file projection.',
                      ),
                      const _UnavailableWorkspacePane(
                        icon: Icons.terminal,
                        title: 'Terminal',
                        message:
                            'No authorized terminal output stream is exposed by the current Desktop API.',
                      ),
                      const _UnavailableWorkspacePane(
                        icon: Icons.language,
                        title: 'Browser',
                        message:
                            'No authoritative browser-session preview is exposed by the current Desktop API.',
                      ),
                      const _UnavailableWorkspacePane(
                        icon: Icons.folder_outlined,
                        title: 'Files',
                        message:
                            'Workspace files are not exposed to Desktop by the current safe projection.',
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
                const Text(
                  'Unavailable — no data is fabricated.',
                  style: TextStyle(color: IlaiosTheme.cyan, fontSize: 11),
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
      if (_firstText(event, const <String>['message', 'log', 'detail']) != null) {
        logs.add(event);
      }
    }
    if (logs.isEmpty) {
      return const _UnavailableWorkspacePane(
        icon: Icons.list_alt,
        title: 'Logs',
        message: 'No authoritative log-message stream is present in live events.',
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
      ? const _UnavailableWorkspacePane(
          icon: Icons.bolt_outlined,
          title: 'Events',
          message: 'No authoritative runtime events are currently available.',
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
          final type = _firstText(event, const <String>['event_type', 'type']) ?? 'event';
          final message = _firstText(event, const <String>['message', 'log', 'detail']);
          final timestamp = _firstText(
            event,
            const <String>['timestamp', 'created_at', 'occurred_at'],
          );
          return Semantics(
            label: 'Runtime event $type',
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 10),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Padding(
                    padding: EdgeInsets.only(top: 5),
                    child: Icon(Icons.circle, size: 7, color: IlaiosTheme.success),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(type, style: const TextStyle(fontWeight: FontWeight.w600)),
                        if (showMessage && message != null) ...[
                          const SizedBox(height: 4),
                          Text(
                            message,
                            style: const TextStyle(color: IlaiosTheme.muted, fontSize: 12),
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
                        style: const TextStyle(color: IlaiosTheme.muted, fontSize: 11),
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
