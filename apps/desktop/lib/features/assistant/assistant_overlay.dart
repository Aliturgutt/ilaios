import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_locale.dart';
import '../../control_plane/client.dart';
import '../../identity/identity_client.dart';
import '../li/li_view.dart';
import 'assistant_symbol.dart';

/// Presentation only: all durable conversation operations go through the
/// existing authenticated Desktop identity adapter. No provider/tool dispatch.
class AssistantOverlay extends StatefulWidget {
  const AssistantOverlay({
    required this.session,
    required this.onClose,
    this.onRequest,
    this.onFetchLiState,
    this.onFetchLiMemories,
    this.onRememberLiMemory,
    this.onSubmitWork,
    super.key,
  });

  final DesktopUserSession session;
  final VoidCallback onClose;
  final Future<Map<String, dynamic>> Function(Map<String, Object?>)? onRequest;
  final Future<DesktopLiState> Function()? onFetchLiState;
  final Future<List<DesktopLiMemory>> Function()? onFetchLiMemories;
  final Future<DesktopLiMemory> Function(String, String)? onRememberLiMemory;
  final Future<PromptSubmission> Function(String)? onSubmitWork;

  @override
  State<AssistantOverlay> createState() => _AssistantOverlayState();
}

class _AssistantOverlayState extends State<AssistantOverlay> {
  final _composer = TextEditingController();
  List<Map<String, dynamic>> _history = [];
  Map<String, dynamic>? _conversation;
  bool _founder = false;
  bool _busy = true;
  bool _memory = false;
  bool _error = false;
  String? _workState;
  String? _pendingMessageId;

  String _copy(String en, String tr) =>
      IlaiosLocaleScope.of(context).locale == IlaiosLocale.turkish ? tr : en;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _composer.dispose();
    super.dispose();
  }

  Future<Map<String, dynamic>> _request(Map<String, Object?> body) async {
    final request = widget.onRequest;
    if (request == null) throw const IdentityClientException('Assistant unavailable');
    final response = await request(body);
    final binding = response['binding'];
    if (binding is! Map<String, dynamic> ||
        binding.length != 5 || !binding.containsKey('project_id') || !binding.containsKey('workload_id') ||
        binding['user_id'] != widget.session.principalId ||
        binding['tenant_id'] != widget.session.tenantId ||
        binding['project_id'] != null || binding['workload_id'] != null ||
        !const ['assistant', 'li'].contains(binding['persona'])) {
      throw const IdentityClientException('Assistant scope invalid');
    }
    if (binding['persona'] == 'li') {
      final verify = widget.onFetchLiState;
      if (!widget.session.liFounder || verify == null) {
        throw const IdentityClientException('Access unavailable');
      }
      final state = await verify();
      if (!state.founderOperator || state.name != 'Li' ||
          state.userId != widget.session.principalId ||
          state.tenantId != widget.session.tenantId ||
          state.source != 'canonical_desktop_session') {
        throw const IdentityClientException('Access unavailable');
      }
      if (mounted) _founder = true;
    } else if (mounted) {
      if (_founder) {
        _conversation = null;
        _history = [];
        _composer.clear();
        _pendingMessageId = null;
      }
      _founder = false;
      _memory = false;
    }
    return response;
  }

  List<Map<String, dynamic>> _maps(Object? value) {
    if (value is! List || value.any((item) => item is! Map<String, dynamic>)) {
      throw const IdentityClientException('Assistant response invalid');
    }
    return value.cast<Map<String, dynamic>>();
  }

  void _accept(Map<String, dynamic> response) {
    final document = response['conversation'];
    if (document is! Map<String, dynamic> ||
        document['conversation_id'] is! String || document['version'] is! int) {
      throw const IdentityClientException('Conversation invalid');
    }
    final binding = document['binding'];
    if (binding is! Map<String, dynamic> || binding.length != 5 ||
        !binding.containsKey('project_id') || !binding.containsKey('workload_id') ||
        binding['user_id'] != widget.session.principalId ||
        binding['tenant_id'] != widget.session.tenantId ||
        binding['project_id'] != null || binding['workload_id'] != null ||
        binding['persona'] != (_founder ? 'li' : 'assistant')) {
      throw const IdentityClientException('Conversation scope invalid');
    }
    _maps(document['messages']);
    _conversation = document;
  }

  Future<void> _load() async {
    try {
      _conversation = null;
      final response = await _request({'operation': 'list'});
      if (!mounted) return;
      _history = _maps(response['conversations']);
      if (_history.isNotEmpty) {
        final response = await _request({'operation': 'get',
          'conversation_id': _history.first['conversation_id']});
        if (!mounted) return;
        _accept(response);
      }
      setState(() { _busy = false; _error = false; });
    } on Object {
      if (mounted) setState(() {
        _busy = false; _error = true; _founder = false;
        _conversation = null; _history = []; _memory = false;
      });
    }
  }

  Future<void> _select(String? id) async {
    if (_busy) return;
    setState(() { _busy = true; _memory = false; });
    try {
      final result = await _request(id == null
          ? {'operation': 'create'}
          : {'operation': 'get', 'conversation_id': id});
      if (!mounted) return;
      _accept(result);
      _composer.clear();
      _pendingMessageId = null;
      final listed = await _request({'operation': 'list'});
      if (!mounted) return;
      _history = _maps(listed['conversations']);
      setState(() { _busy = false; _error = false; });
    } on Object {
      if (mounted) setState(() {
        _busy = false; _error = true; _founder = false;
        _conversation = null; _memory = false;
      });
    }
  }

  Future<void> _send() async {
    final text = _composer.text.trim();
    if (_busy || text.isEmpty || widget.onRequest == null) return;
    setState(() { _busy = true; _error = false; });
    try {
      if (_conversation == null) {
        final response = await _request({'operation': 'create'});
        if (!mounted) return;
        _accept(response);
      }
      _pendingMessageId ??= '${DateTime.now().microsecondsSinceEpoch}-${math.Random.secure().nextInt(1 << 32)}';
      final response = await _request({
        'operation': 'send',
        'conversation_id': _conversation!['conversation_id'],
        'version': _conversation!['version'],
        'text': text,
        'message_id': _pendingMessageId,
        'locale': IlaiosLocaleScope.of(context).locale.code,
      });
      if (!mounted) return;
      _accept(response);
      _composer.clear();
      _pendingMessageId = null;
      final listed = await _request({'operation': 'list'});
      if (!mounted) return;
      _history = _maps(listed['conversations']);
      setState(() { _busy = false; _error = false; });
    } on Object {
      if (mounted) setState(() {
        _busy = false; _error = true; _founder = false;
        _conversation = null; _memory = false;
      });
    }
  }

  Future<void> _submitWork() async {
    final submit = widget.onSubmitWork;
    final text = _composer.text.trim();
    if (submit == null || text.isEmpty || _busy) return;
    final approved = await showDialog<bool>(context: context, builder: (context) => AlertDialog(
      title: Text(_copy('Submit work?', 'İş gönderilsin mi?')),
      content: Text(_copy('This submits your draft to the existing work flow. Required policy, approval and cost checks still apply.',
          'Taslağınız mevcut iş akışına gönderilir. Gerekli politika, onay ve maliyet kontrolleri geçerlidir.')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(_copy('Cancel', 'Vazgeç'))),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(_copy('Submit', 'Gönder'))),
      ],
    ));
    if (!mounted || approved != true) return;
    setState(() { _busy = true; _workState = null; });
    try {
      final result = await submit(text);
      if (!mounted) return;
      setState(() { _workState = '${result.goalId} · ${result.state}'; });
    } on Object {
      if (mounted) setState(() => _error = true);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _surface(Key key, Widget child) => Material(
    key: key,
    color: Theme.of(context).colorScheme.surface,
    shape: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
    child: child,
  );

  @override
  Widget build(BuildContext context) => LayoutBuilder(builder: (context, constraints) {
    final width = constraints.maxWidth;
    final height = constraints.maxHeight;
    final leftWidth = math.min(290.0, width * .38);
    final bottom = math.min(29.0, height * .03);
    // Anchor to the shell viewport, independently of sidebar item spacing.
    final leftTop = (height * 482 / 1024)
        .clamp(0.0, math.max(0.0, height - 260)).toDouble();
    final chatTop = math.max(leftTop + 40, height * 637 / 1024)
        .clamp(0.0, math.max(0.0, height - 220)).toDouble();
    final messages = _conversation?['messages'] as List? ?? const [];
    return Stack(children: [
      Positioned(left: 0, top: math.min(leftTop, chatTop - 32), bottom: bottom, width: leftWidth,
        child: _surface(const Key('assistant-history-arm'), Column(children: [
          Padding(padding: const EdgeInsets.all(12), child: Row(children: [
            const AssistantSymbol(), const SizedBox(width: 8),
            Expanded(child: Text(_copy('Assistant', 'Asistan'), style: const TextStyle(fontWeight: FontWeight.w600))),
            IconButton(key: const Key('assistant-close'), tooltip: _copy('Close', 'Kapat'),
                onPressed: widget.onClose, icon: const Icon(Icons.close)),
          ])),
          TextButton(key: const Key('assistant-new'), onPressed: _busy ? null : () => _select(null),
              child: Text(_copy('New conversation', 'Yeni sohbet'))),
          Expanded(child: ListView(children: [
            for (var i = 0; i < _history.length; i++)
              ListTile(dense: true, selected: _conversation?['conversation_id'] == _history[i]['conversation_id'],
                title: Text('${_copy('Conversation', 'Sohbet')} ${_history.length - i}'),
                onTap: _busy ? null : () => _select(_history[i]['conversation_id'] as String)),
            if (_founder)
              TextButton(key: const Key('assistant-memory'), onPressed: () => setState(() => _memory = !_memory),
                child: Text(_copy('Authorized memory', 'Yetkili hafıza'))),
          ])),
        ]))),
      Positioned(left: leftWidth, right: math.min(12.0, width * .01), top: chatTop, bottom: bottom,
        child: _surface(const Key('assistant-conversation-arm'), Column(children: [
          Padding(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), child: Row(children: [
            const AssistantSymbol(), const SizedBox(width: 10),
            Expanded(child: Text(_founder ? 'Li — Founder Intelligence' : 'ILAIOS Assistant',
                key: const Key('assistant-panel-identity'), style: const TextStyle(fontWeight: FontWeight.w600))),
            if (_busy) const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
          ])),
          Expanded(child: _memory && _founder
              ? LiView(userSession: widget.session, onFetchState: widget.onFetchLiState,
                  onFetchMemories: widget.onFetchLiMemories, onRemember: widget.onRememberLiMemory)
              : ListView(padding: const EdgeInsets.symmetric(horizontal: 16), children: [
                  if (messages.isEmpty) Text(_copy('Ask about ILAIOS or describe your next task.', 'ILAIOS hakkında sorun veya sonraki işinizi anlatın.')),
                  if (messages.isNotEmpty) Text(_copy('Past responses are history, not current-state evidence.',
                      'Geçmiş yanıtlar güncel durum kanıtı değildir.'), style: Theme.of(context).textTheme.bodySmall),
                  for (final raw in messages)
                    if (raw is Map)
                      Padding(padding: const EdgeInsets.only(bottom: 10), child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start, children: [
                          SelectableText(raw['text'] is String ? raw['text'] as String : 'UNVERIFIED'),
                          if (raw['provenance'] is List)
                            for (final source in raw['provenance'] as List)
                              if (source is Map) Text('${_copy('Source', 'Kaynak')}: ${source['source_id']}',
                                  style: Theme.of(context).textTheme.bodySmall),
                        ])),
                  if (_error) Text(_copy('UNVERIFIED — Could not load or save. Your draft is retained; reload before retrying.',
                      'UNVERIFIED — Yüklenemedi veya kaydedilemedi. Taslağınız duruyor; yeniden denemeden önce yükleyin.'), key: const Key('assistant-error')),
                  if (_workState != null) Text(_workState!),
                ])),
          if (!_memory) Padding(padding: const EdgeInsets.all(10), child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Expanded(child: TextField(key: const Key('assistant-composer'), controller: _composer,
              enabled: !_busy, minLines: 1, maxLines: 3, maxLength: 8000,
              onChanged: (_) { _pendingMessageId = null; },
              decoration: InputDecoration(hintText: _copy('Message', 'Mesaj'), counterText: ''))),
            const SizedBox(width: 8),
            FilledButton(key: const Key('assistant-send'), onPressed: _busy || _error || widget.onRequest == null ? null : _send,
                child: Text(_copy('Send', 'Gönder'))),
          ])),
          if (!_memory) Wrap(spacing: 8, children: [
            TextButton(key: const Key('assistant-submit-work'), onPressed: _busy || widget.onSubmitWork == null ? null : _submitWork,
                child: Text(_copy('Submit draft as work', 'Taslağı iş olarak gönder'))),
            TextButton(onPressed: _busy ? null : () { setState(() => _busy = true); _load(); },
                child: Text(_copy('Reload history', 'Geçmişi yenile'))),
          ]),
        ]))),
    ]);
  });
}
