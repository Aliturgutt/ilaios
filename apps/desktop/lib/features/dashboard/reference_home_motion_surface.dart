import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../app/ilaios_theme.dart';

/// Paint-only motion layer for the existing command-center hero.
///
/// This deliberately does not own any product state or execution authority. It
/// only adds low-frequency visual energy over the existing central orbit visual
/// while preserving the approved Home geometry. When platform reduced-motion
/// is enabled the overlay is disabled and the underlying static hero remains.
class ReferenceHomeMotionSurface extends StatefulWidget {
  const ReferenceHomeMotionSurface({required this.child, super.key});

  final Widget child;

  @override
  State<ReferenceHomeMotionSurface> createState() =>
      _ReferenceHomeMotionSurfaceState();
}

class _ReferenceHomeMotionSurfaceState extends State<ReferenceHomeMotionSurface> {
  final _HeroMotionClock _clock = _HeroMotionClock();
  bool? _reducedMotion;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reduced = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (_reducedMotion == reduced) return;
    _reducedMotion = reduced;
    if (reduced) {
      _clock.stop();
    } else {
      _clock.start();
    }
  }

  @override
  void dispose() {
    _clock.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => LayoutBuilder(
        builder: (context, constraints) {
          final railWidth = constraints.maxWidth >= 1500 ? 282.0 : 258.0;
          final mainWidth = math.max(0.0, constraints.maxWidth - 20 - 10 - railWidth);
          final heroHeight =
              (constraints.maxHeight - 20).clamp(620.0, 1200.0).toDouble() * .225;
          final heroInnerWidth = math.max(0.0, mainWidth - 28);
          final flexWidth = math.max(0.0, heroInnerWidth - 22);
          final orbitLeft = 10 + 16 + (flexWidth * 58 / 104) + 12;
          final orbitWidth = flexWidth * 20 / 104;

          return Stack(
            fit: StackFit.expand,
            children: [
              widget.child,
              if (_reducedMotion == false && orbitWidth > 0 && heroHeight > 0)
                Positioned(
                  left: orbitLeft,
                  top: 10 + 13,
                  width: orbitWidth,
                  height: math.max(0.0, heroHeight - 25),
                  child: IgnorePointer(
                    child: RepaintBoundary(
                      key: const Key('command-center-orbit-motion'),
                      child: CustomPaint(
                        painter: _HeroMotionPainter(
                          clock: _clock,
                          accent: IlaiosTheme.enterpriseCyan,
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      );
}

class _HeroMotionClock extends ChangeNotifier {
  Timer? _timer;
  double phase = 0;

  void start() {
    if (_timer != null) return;
    _timer = Timer.periodic(const Duration(milliseconds: 125), (_) {
      phase = (phase + 1 / 144) % 1;
      notifyListeners();
    });
  }

  void stop() {
    _timer?.cancel();
    _timer = null;
    phase = 0;
    notifyListeners();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }
}

class _HeroMotionPainter extends CustomPainter {
  _HeroMotionPainter({required this.clock, required this.accent})
      : super(repaint: clock);

  final _HeroMotionClock clock;
  final Color accent;

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;
    final phase = clock.phase;
    final angle = phase * math.pi * 2;
    final center = Offset(size.width / 2, size.height * .57);
    final breathe = .5 + .5 * math.sin(angle);

    final glow = Paint()
      ..style = PaintingStyle.fill
      ..color = accent.withValues(alpha: .018 + breathe * .028)
      ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 12);
    canvas.drawCircle(center, math.min(size.width, size.height) * (.12 + breathe * .025), glow);

    final ring = Paint()
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 1.45
      ..color = accent.withValues(alpha: .34 + breathe * .20);
    final ringRect = Rect.fromCenter(
      center: center,
      width: size.width * .82,
      height: size.height * .31,
    );
    canvas.drawArc(ringRect, angle, math.pi * .62, false, ring);
    canvas.drawArc(ringRect, angle + math.pi, math.pi * .34, false, ring);

    final cubeCenter = Offset(
      center.dx + math.sin(angle) * 1.8,
      size.height * .31 + math.cos(angle) * 1.6,
    );
    final r = math.min(size.width, size.height) * .105;
    canvas.save();
    canvas.translate(cubeCenter.dx, cubeCenter.dy);
    canvas.rotate(math.sin(angle) * .045);
    final cubePaint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.15
      ..color = accent.withValues(alpha: .20 + breathe * .20);
    final path = Path()
      ..moveTo(0, -r)
      ..lineTo(-r * .86, -r * .5)
      ..lineTo(0, 0)
      ..lineTo(r * .86, -r * .5)
      ..close()
      ..moveTo(0, 0)
      ..lineTo(0, r)
      ..moveTo(-r * .86, -r * .5)
      ..lineTo(-r * .86, r * .5)
      ..lineTo(0, r)
      ..moveTo(r * .86, -r * .5)
      ..lineTo(r * .86, r * .5)
      ..lineTo(0, r);
    canvas.drawPath(path, cubePaint);
    canvas.restore();
  }

  @override
  bool shouldRepaint(covariant _HeroMotionPainter oldDelegate) =>
      oldDelegate.clock != clock || oldDelegate.accent != accent;
}
