import 'dart:convert';

import '../../identity/identity_client_core.dart';

/// Founder-only, credential-free WebView boundary. The authenticated identity
/// adapter remains the sole authority for conversation and memory operations.
class LiWebBridge {
  LiWebBridge({
    required this.session,
    required this.isSessionActive,
    required this.verifyFounder,
    required this.request,
    required this.fetchMemories,
    required this.remember,
  });

  final DesktopUserSession session;
  final bool Function() isSessionActive;
  final Future<DesktopLiState> Function() verifyFounder;
  final Future<Map<String, dynamic>> Function(Map<String, Object?>) request;
  final Future<List<DesktopLiMemory>> Function() fetchMemories;
  final Future<DesktopLiMemory> Function(String, String) remember;

  bool _binding(Object? raw) {
    if (raw is! Map<String, dynamic> || raw.length != 5) return false;
    return raw['user_id'] == session.principalId &&
        raw['tenant_id'] == session.tenantId &&
        raw.containsKey('project_id') &&
        raw['project_id'] == null &&
        raw.containsKey('workload_id') &&
        raw['workload_id'] == null &&
        raw['persona'] == 'li';
  }

  Future<Map<String, Object?>> handle(String raw) async {
    String? id;
    try {
      final input = jsonDecode(raw);
      if (input is! Map<String, dynamic>) throw const FormatException();
      id = input['id'] as String?;
      if (id == null || id.isEmpty || id.length > 80) {
        throw const FormatException();
      }
      final op = input['operation'];
      final rawArgs = input['args'];
      if (rawArgs != null && rawArgs is! Map<String, dynamic>) {
        throw const FormatException();
      }
      final args = rawArgs is Map<String, dynamic>
          ? rawArgs
          : <String, dynamic>{};
      final allowed = switch (op) {
        'list' || 'create' || 'memories' => <String>{},
        'get' => <String>{'conversation_id'},
        'send' => <String>{
          'conversation_id',
          'version',
          'text',
          'message_id',
          'locale',
        },
        'remember' => <String>{'kind', 'content'},
        _ => throw const FormatException(),
      };
      if (args.keys.any((key) => !allowed.contains(key))) {
        throw const FormatException();
      }
      if ((op == 'get' || op == 'send') &&
          (args['conversation_id'] is! String ||
              (args['conversation_id'] as String).isEmpty)) {
        throw const FormatException();
      }
      if (op == 'send' &&
          (args['version'] is! int ||
              args['text'] is! String ||
              (args['text'] as String).trim().isEmpty ||
              args['message_id'] is! String ||
              (args['message_id'] as String).isEmpty ||
              !{'tr', 'en'}.contains(args['locale']))) {
        throw const FormatException();
      }
      if (op == 'remember' &&
          (!{'working', 'episodic', 'semantic'}.contains(args['kind']) ||
              args['content'] is! String ||
              (args['content'] as String).trim().isEmpty ||
              (args['content'] as String).length > 8000)) {
        throw const FormatException();
      }
      if (!session.liFounder || !isSessionActive()) {
        throw const FormatException();
      }
      final founder = await verifyFounder();
      if (!isSessionActive() ||
          !founder.founderOperator ||
          founder.name != 'Li' ||
          founder.userId != session.principalId ||
          founder.tenantId != session.tenantId ||
          founder.source != 'canonical_desktop_session') {
        throw const FormatException();
      }
      if (op == 'memories') {
        final entries = await fetchMemories();
        if (!isSessionActive()) throw const FormatException();
        return {
          'id': id,
          'ok': true,
          'data': {'memories': entries.map(_memory).toList()},
        };
      }
      if (op == 'remember') {
        final entry = await remember(
          args['kind'] as String,
          args['content'] as String,
        );
        if (!isSessionActive()) throw const FormatException();
        return {
          'id': id,
          'ok': true,
          'data': {'memory': _memory(entry)},
        };
      }
      final response = await request({'operation': op, ...args});
      if (!isSessionActive() || !_binding(response['binding'])) {
        throw const FormatException();
      }
      if (op == 'list') {
        final entries = response['conversations'];
        if (entries is! List ||
            entries.any(
              (item) =>
                  item is! Map<String, dynamic> ||
                  item['conversation_id'] is! String ||
                  !_binding(item['binding']),
            )) {
          throw const FormatException();
        }
      } else {
        final conversation = response['conversation'];
        if (conversation is! Map<String, dynamic> ||
            conversation['conversation_id'] is! String ||
            conversation['version'] is! int ||
            conversation['messages'] is! List ||
            !_binding(conversation['binding']) ||
            ((op == 'get' || op == 'send') &&
                conversation['conversation_id'] != args['conversation_id'])) {
          throw const FormatException();
        }
      }
      return {'id': id, 'ok': true, 'data': response};
    } catch (_) {
      return {
        'id': id,
        'ok': false,
        'error': 'Li request rejected or unavailable',
      };
    }
  }

  Map<String, Object?> _memory(DesktopLiMemory memory) => {
    'memory_id': memory.memoryId,
    'kind': memory.kind,
    'content': memory.content,
    'source': memory.source,
    'confidence': memory.confidence,
    'sensitivity': memory.sensitivity,
    'created_at': memory.createdAt.toUtc().toIso8601String(),
  };
}
