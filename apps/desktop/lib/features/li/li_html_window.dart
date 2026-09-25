import 'dart:async';
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_windows/webview_windows.dart';

import '../../identity/identity_client_core.dart';
import 'li_web_bridge.dart';

/// The approved Li design supplies styling, not prototype state or scripts.
class LiHtmlWindow extends StatefulWidget {
  const LiHtmlWindow({
    super.key,
    required this.session,
    required this.dark,
    required this.english,
    required this.verifyFounder,
    required this.request,
    required this.fetchMemories,
    required this.remember,
  });
  final DesktopUserSession session;
  final bool dark;
  final bool english;
  final Future<DesktopLiState> Function() verifyFounder;
  final Future<Map<String, dynamic>> Function(Map<String, Object?>) request;
  final Future<List<DesktopLiMemory>> Function() fetchMemories;
  final Future<DesktopLiMemory> Function(String, String) remember;

  @override
  State<LiHtmlWindow> createState() => _LiHtmlWindowState();
}

class _LiHtmlWindowState extends State<LiHtmlWindow> {
  final _controller = WebviewController();
  StreamSubscription<dynamic>? _messages;
  bool _initialized = false;
  bool _ready = false;
  String? _error;
  int _generation = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      if (!widget.session.liFounder) {
        throw StateError('Founder session required');
      }
      final state = await widget.verifyFounder();
      if (!mounted ||
          !state.founderOperator ||
          state.name != 'Li' ||
          state.userId != widget.session.principalId ||
          state.tenantId != widget.session.tenantId ||
          state.source != 'canonical_desktop_session') {
        throw StateError('Founder verification failed');
      }
      final approved = await rootBundle.loadString(
        'assets/li_design_reference.html',
      );
      final headEnd = approved.indexOf('<body');
      if (headEnd < 0) throw StateError('Approved design unavailable');
      final logo =
          RegExp(
            r'<img[^>]*class="canonical horizontal light-logo"[^>]*>',
          ).firstMatch(approved)?.group(0) ??
          '';
      final script = await rootBundle.loadString('assets/li_production.js');
      final html =
          '${approved.substring(0, headEnd)}<body class="${widget.dark ? 'dark' : ''}">'
          '<header class="toolbar"><div><h1>Li - Founder Intelligence</h1>'
          '<small id="status" role="status">Verifying founder session</small></div></header>'
          '<div class="window"><aside><div class="brand">$logo</div>'
          '<button id="new-chat" type="button">New conversation</button>'
          '<button id="show-memory" type="button">Founder memory</button>'
          '<nav id="history" aria-label="Li conversation history"></nav></aside>'
          '<main class="main"><div class="titlebar"><strong>Li - Founder Intelligence</strong>'
          '<span class="pill">Authenticated founder</span></div>'
          '<section id="content" class="content" aria-live="polite">'
          '<div id="messages"></div><div id="memories" hidden></div></section>'
          '<form id="composer" class="composer"><textarea id="message" required '
          'aria-label="Message"></textarea><button id="send" type="submit">Send</button></form>'
          '<form id="memory-form" hidden><select id="memory-kind" aria-label="Memory kind">'
          '<option value="working">Working</option><option value="episodic">Episodic</option>'
          '<option value="semantic">Semantic</option></select>'
          '<textarea id="memory-content" aria-label="Memory content"></textarea>'
          '<button id="remember" type="submit">Save memory</button></form>'
          '<p>Factory execution and approvals require separate governed services.</p>'
          '</main></div><script>$script</script>'
          '<script>document.documentElement.lang="${widget.english ? 'en' : 'tr'}";</script>'
          '</body></html>';
      if (!mounted) return;
      await _controller.initialize();
      _initialized = true;
      await _controller.setPopupWindowPolicy(WebviewPopupWindowPolicy.deny);
      final generation = ++_generation;
      final bridge = LiWebBridge(
        session: widget.session,
        isSessionActive: () => mounted && generation == _generation,
        verifyFounder: widget.verifyFounder,
        request: widget.request,
        fetchMemories: widget.fetchMemories,
        remember: widget.remember,
      );
      _messages = _controller.webMessage.listen((message) async {
        if (message is! String || !mounted || generation != _generation) return;
        final response = await bridge.handle(message);
        if (mounted && generation == _generation) {
          await _controller.postWebMessage(jsonEncode(response));
        }
      });
      await _controller.loadStringContent(html);
      if (mounted) setState(() => _ready = true);
    } catch (_) {
      if (mounted) {
        setState(
          () =>
              _error = 'Li unavailable: founder verification or service failed',
        );
      }
    }
  }

  @override
  void dispose() {
    _generation++;
    _messages?.cancel();
    if (_initialized) _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: _error != null
        ? Center(child: SelectableText(_error!))
        : _ready
        ? Webview(_controller)
        : const Center(child: CircularProgressIndicator()),
  );
}
