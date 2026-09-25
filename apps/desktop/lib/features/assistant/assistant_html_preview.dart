import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:webview_windows/webview_windows.dart';

class AssistantHtmlPreview extends StatefulWidget {
  const AssistantHtmlPreview({
    super.key,
    this.assetPath = 'assets/assistant_design_reference.html',
    required this.dark,
    required this.english,
  });
  final String assetPath;
  final bool dark;
  final bool english;

  @override
  State<AssistantHtmlPreview> createState() => _AssistantHtmlPreviewState();
}

class _AssistantHtmlPreviewState extends State<AssistantHtmlPreview> {
  final controller = WebviewController();
  String? error;
  bool ready = false;
  @override
  void initState() {
    super.initState();
    load();
  }

  Future<void> load() async {
    try {
      final source = await rootBundle.loadString(widget.assetPath);
      final html = source.replaceFirst(
        '</body>',
        '<script>document.body.classList.toggle("dark", ${widget.dark});'
            'document.documentElement.lang="${widget.english ? 'en' : 'tr'}";'
            'document.querySelectorAll("#light,#dark").forEach(e=>e.remove());'
            '</script></body>',
      );
      await controller.initialize();
      await controller.setPopupWindowPolicy(WebviewPopupWindowPolicy.deny);
      await controller.loadStringContent(html);
      if (mounted) setState(() => ready = true);
    } catch (e) {
      if (mounted) setState(() => error = e.toString());
    }
  }

  @override
  void dispose() {
    controller.dispose();
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
