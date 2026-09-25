import 'dart:async';
import 'dart:convert';
import 'assistant_web_bridge.dart';
import '../../identity/identity_client_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_windows/webview_windows.dart';

class AssistantHtmlPreview extends StatefulWidget {
  const AssistantHtmlPreview({
    super.key,
    this.assetPath = 'assets/assistant_design_reference.html',
    required this.dark,
    required this.english,
    this.onRequest,
    this.session,
  });
  final DesktopUserSession? session;
  final String assetPath;
  final bool dark;
  final bool english;
  final Future<Map<String, dynamic>> Function(Map<String, Object?>)? onRequest;

  @override
  State<AssistantHtmlPreview> createState() => _AssistantHtmlPreviewState();
}

class _AssistantHtmlPreviewState extends State<AssistantHtmlPreview> {
  final controller = WebviewController();
  String? error;
  bool ready = false;
  bool _initialized = false;
  StreamSubscription<dynamic>? _messages;
  int _generation = 0;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<String> _productionHtml(String approved) async {
    // Retain the approved stylesheet and canonical embedded logo, never execute
    // prototype scripts or display its fake conversations/actions.
    final head = approved.substring(0, approved.indexOf('<body'));
    final logo =
        RegExp(
          r'<img class="canonical horizontal light-logo"[^>]*>',
        ).firstMatch(approved)?.group(0) ??
        '';
    final script = await rootBundle.loadString(
      'assets/assistant_production.js',
    );
    return '$head<body><header class="toolbar"><div><h1>ILAIOS Assistant</h1>'
        '<small id="status" role="status">Connecting to authenticated Assistant...</small>'
        '</div></header><div class="window"><aside><div class="brand">$logo</div>'
        '<button id="new-chat" type="button">New conversation</button>'
        '<nav id="history" aria-label="Conversation history"></nav>'
        '</aside><main><h2 id="heading">Assistant</h2>'
        '<section id="content" aria-label="Authenticated conversation">'
        '<div id="messages" aria-live="polite"></div></section>'
        '<form id="composer"><textarea id="message" aria-label="Message" '
        'placeholder="Write a message" required></textarea>'
        '<button id="send" type="submit">Send</button></form>'
        '<p>Work approval, factory execution, file upload and downloads are '
        'unavailable until their governed services are connected.</p>'
        '</main></div><script>$script</script></body></html>';
  }

  Future<void> load() async {
    try {
      final source = await rootBundle.loadString(widget.assetPath);
      if (!mounted) return;
      if (widget.onRequest != null && widget.session == null) {
        throw StateError('Authenticated session required');
      }
      final runtime = widget.onRequest == null
          ? source
          : await _productionHtml(source);
      final html = runtime.replaceFirst(
        '</body>',
        '<script>document.body.classList.toggle("dark", ${widget.dark});'
            'document.documentElement.lang="${widget.english ? 'en' : 'tr'}";'
            'document.querySelectorAll("#light,#dark").forEach(e=>e.remove());'
            '</script></body>',
      );
      if (!mounted) return;
      await controller.initialize();
      _initialized = true;
      await controller.setPopupWindowPolicy(WebviewPopupWindowPolicy.deny);
      if (widget.onRequest != null) {
        final generation = ++_generation;
        final bridge = AssistantWebBridge(
          request: widget.onRequest!,
          userId: widget.session!.principalId,
          tenantId: widget.session!.tenantId,
          isSessionActive: () => mounted && generation == _generation,
        );
        _messages = controller.webMessage.listen((message) async {
          if (message is! String || !mounted || generation != _generation) {
            return;
          }
          final result = await bridge.handle(message);
          if (mounted && generation == _generation) {
            await controller.postWebMessage(jsonEncode(result));
          }
        });
      }
      await controller.loadStringContent(html);
      if (mounted) setState(() => ready = true);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  @override
  void dispose() {
    _generation++;
    _messages?.cancel();
    if (_initialized) controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    body: error != null
        ? Center(child: SelectableText('Assistant preview error: $error'))
        : ready
        ? Webview(controller)
        : const Center(child: CircularProgressIndicator()),
  );
}
