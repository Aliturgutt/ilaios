import 'dart:async';

import 'package:flutter/material.dart';

import 'pixel_agent_presentation.dart';

/// Presentation-only sprite renderer backed by the user-approved repo assets.
/// It never mutates runtime state or fabricates missing frames.
class PixelAgentSprite extends StatefulWidget {
  const PixelAgentSprite({
    required this.team,
    required this.view,
    required this.motion,
    this.size = const Size(64, 80),
    this.frameDuration = const Duration(milliseconds: 280),
    super.key,
  });

  final String team;
  final PixelAgentView view;
  final PixelAgentMotion motion;
  final Size size;
  final Duration frameDuration;

  @override
  State<PixelAgentSprite> createState() => _PixelAgentSpriteState();
}

class _PixelAgentSpriteState extends State<PixelAgentSprite> {
  Timer? _timer;
  int _frame = 1;

  @override
  void initState() {
    super.initState();
    _syncTimer();
  }

  @override
  void didUpdateWidget(covariant PixelAgentSprite oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.motion != widget.motion ||
        oldWidget.team != widget.team ||
        oldWidget.view != widget.view ||
        oldWidget.frameDuration != widget.frameDuration) {
      _frame = 1;
      _syncTimer();
    }
  }

  void _syncTimer() {
    _timer?.cancel();
    _timer = null;
    final count = pixelFrameCount(widget.motion);
    if (count <= 1 || widget.frameDuration <= Duration.zero) return;
    _timer = Timer.periodic(widget.frameDuration, (_) {
      if (!mounted) return;
      setState(() => _frame = _frame % count + 1);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _timer = null;
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final path = pixelAgentAssetPath(
      team: widget.team,
      view: widget.view,
      motion: widget.motion,
      frame: _frame,
    );
    if (path == null) {
      return SizedBox(
        key: const Key('pixel-agent-missing-frame'),
        width: widget.size.width,
        height: widget.size.height,
      );
    }
    return Image.asset(
      path,
      key: ValueKey('pixel-agent-${widget.team}-${widget.view.name}-${widget.motion.name}-$_frame'),
      width: widget.size.width,
      height: widget.size.height,
      fit: BoxFit.contain,
      filterQuality: FilterQuality.none,
      gaplessPlayback: true,
      errorBuilder: (_, _, _) => SizedBox(
        key: const Key('pixel-agent-missing-frame'),
        width: widget.size.width,
        height: widget.size.height,
      ),
    );
  }
}
