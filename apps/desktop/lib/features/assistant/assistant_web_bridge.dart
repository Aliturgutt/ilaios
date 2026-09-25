import 'dart:convert';

/// Narrow, credential-free boundary for the bundled Assistant WebView.
/// Authentication and server-side scope enforcement remain in IdentityClient.
class AssistantWebBridge {
  AssistantWebBridge({
    required this.request,
    required this.isSessionActive,
    required this.userId,
    required this.tenantId,
  });
  final bool Function() isSessionActive;
  final String userId;
  final String tenantId;
  final Future<Map<String, dynamic>> Function(Map<String, Object?>) request;
  static const operations = {'list', 'get', 'create', 'send'};

  Future<Map<String, Object?>> handle(String raw) async {
    Object? id;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is! Map<String, dynamic>) {
        throw const FormatException();
      }
      id = decoded['id'];
      if (id is! String || id.isEmpty || id.length > 80) {
        throw const FormatException();
      }
      final operation = decoded['operation'];
      if (operation is! String || !operations.contains(operation)) {
        throw const FormatException();
      }
      final args = decoded['args'];
      if (args != null && args is! Map<String, dynamic>) {
        throw const FormatException();
      }
      final params = args is Map<String, dynamic> ? args : <String, dynamic>{};
      final allowed = switch (operation) {
        'list' || 'create' => <String>{},
        'get' => {'conversation_id'},
        'send' => {
          'conversation_id',
          'version',
          'text',
          'message_id',
          'locale',
        },
        _ => <String>{},
      };
      if (params.keys.any((key) => !allowed.contains(key))) {
        throw const FormatException();
      }
      if ((operation == 'get' || operation == 'send') &&
          (params['conversation_id'] is! String ||
              (params['conversation_id'] as String).isEmpty)) {
        throw const FormatException();
      }
      if (operation == 'send' &&
          (params['version'] is! int ||
              params['text'] is! String ||
              (params['text'] as String).trim().isEmpty ||
              params['message_id'] is! String ||
              !{'tr', 'en'}.contains(params['locale']))) {
        throw const FormatException();
      }
      if (!isSessionActive()) throw const FormatException();
      final response = await request({'operation': operation, ...params});
      if (!isSessionActive()) throw const FormatException();
      bool validBinding(Object? candidate) {
        if (candidate is! Map<String, dynamic> || candidate.length != 5) {
          return false;
        }
        return candidate['user_id'] == userId &&
            candidate['tenant_id'] == tenantId &&
            candidate.containsKey('project_id') &&
            candidate['project_id'] == null &&
            candidate.containsKey('workload_id') &&
            candidate['workload_id'] == null &&
            candidate['persona'] == 'assistant';
      }

      if (!validBinding(response['binding'])) throw const FormatException();
      if (operation == 'list') {
        if (response['conversations'] is! List) throw const FormatException();
      } else {
        final conversation = response['conversation'];
        if (conversation is! Map<String, dynamic> ||
            conversation['conversation_id'] is! String ||
            conversation['version'] is! int ||
            conversation['messages'] is! List ||
            !validBinding(conversation['binding'])) {
          throw const FormatException();
        }
      }
      return {'id': id, 'ok': true, 'data': response};
    } catch (_) {
      return {
        'id': id is String ? id : null,
        'ok': false,
        'error': 'Request rejected or service unavailable',
      };
    }
  }
}
