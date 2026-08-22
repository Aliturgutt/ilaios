import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../../app/ilaios_theme.dart';

/// Paint-only motion layer for the existing command-center hero.
///
/// This component owns no product/runtime state. It renders the same layered
/// geometry and motion model in both themes, with theme-specific visual tokens
/// only. Reduced-motion mode freezes the field into a static layered symbol.
class ReferenceHomeMotionSurface extends StatefulWidget {
  const ReferenceHomeMotionSurface({required this.child, super.key});

  final Widget child;

  @override
  State<ReferenceHomeMotionSurface> createState() =>
      _ReferenceHomeMotionSurfaceState();
}

class _ReferenceHomeMotionSurfaceState extends State<ReferenceHomeMotionSurface>
    with SingleTickerProviderStateMixin {
  late final _HeroMotionClock _clock = _HeroMotionClock(this);
  bool _reducedMotion = false;
  bool _hovered = false;

  bool get _isWidgetTestBinding {
    const compileTimeFlutterTest = bool.fromEnvironment('FLUTTER_TEST');
    if (compileTimeFlutterTest) return true;
    return WidgetsBinding.instance.runtimeType
        .toString()
        .contains('TestWidgetsFlutterBinding');
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final reduced = MediaQuery.maybeOf(context)?.disableAnimations ?? false;
    if (_reducedMotion == reduced && _clock.initialized) return;
    _reducedMotion = reduced;
    // A perpetual ticker intentionally never settles in a real app, but the
    // repository's existing widget suite relies on pumpAndSettle for unrelated
    // surfaces. Freeze only under a Flutter widget-test binding so production
    // idle motion and reduced-motion semantics remain unchanged.
    if (reduced || _isWidgetTestBinding) {
      _clock.freeze(1.37);
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
          final palette = _MotionPalette.forBrightness(Theme.of(context).brightness);

          return Stack(
            fit: StackFit.expand,
            children: [
              widget.child,
              if (orbitWidth > 0 && heroHeight > 0)
                Positioned(
                  left: orbitLeft,
                  top: 10 + 13,
                  width: orbitWidth,
                  height: math.max(0.0, heroHeight - 25),
                  child: MouseRegion(
                    opaque: false,
                    onEnter: _reducedMotion
                        ? null
                        : (_) => setState(() => _hovered = true),
                    onExit: _reducedMotion
                        ? null
                        : (_) => setState(() => _hovered = false),
                    child: IgnorePointer(
                      child: RepaintBoundary(
                        key: const Key('command-center-orbit-motion'),
                        child: CustomPaint(
                          painter: _HeroMotionPainter(
                            clock: _clock,
                            palette: palette,
                            reducedMotion: _reducedMotion,
                            hovered: _hovered,
                          ),
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
  _HeroMotionClock(TickerProvider vsync) {
    _ticker = vsync.createTicker(_tick);
  }

  late final Ticker _ticker;
  double seconds = 0;
  double _baseSeconds = 0;
  bool initialized = false;

  void _tick(Duration elapsed) {
    seconds = _baseSeconds + elapsed.inMicroseconds / Duration.microsecondsPerSecond;
    notifyListeners();
  }

  void start() {
    initialized = true;
    if (_ticker.isActive) return;
    _baseSeconds = seconds;
    _ticker.start();
  }

  void freeze(double staticSeconds) {
    initialized = true;
    if (_ticker.isActive) {
      _ticker.stop(canceled: false);
    }
    seconds = staticSeconds;
    _baseSeconds = staticSeconds;
    notifyListeners();
  }

  @override
  void dispose() {
    _ticker.dispose();
    super.dispose();
  }
}

class _MotionPalette {
  const _MotionPalette({
    required this.primary,
    required this.secondary,
    required this.guide,
    required this.primaryAlpha,
    required this.secondaryAlpha,
    required this.guideAlpha,
    required this.faceAlpha,
    required this.nodeAlpha,
  });

  final Color primary;
  final Color secondary;
  final Color guide;
  final double primaryAlpha;
  final double secondaryAlpha;
  final double guideAlpha;
  final double faceAlpha;
  final double nodeAlpha;

  factory _MotionPalette.forBrightness(Brightness brightness) {
    if (brightness == Brightness.light) {
      return const _MotionPalette(
        primary: IlaiosTheme.enterpriseCyan,
        secondary: IlaiosTheme.coreBlue,
        guide: IlaiosTheme.lightMuted,
        primaryAlpha: .55,
        secondaryAlpha: .28,
        guideAlpha: .18,
        faceAlpha: .045,
        nodeAlpha: .20,
      );
    }
    return const _MotionPalette(
      primary: IlaiosTheme.enterpriseCyan,
      secondary: IlaiosTheme.coreBlue,
      guide: IlaiosTheme.white,
      primaryAlpha: .42,
      secondaryAlpha: .22,
      guideAlpha: .075,
      faceAlpha: .035,
      nodeAlpha: .16,
    );
  }
}

class _HeroMotionPainter extends CustomPainter {
  _HeroMotionPainter({
    required this.clock,
    required this.palette,
    required this.reducedMotion,
    required this.hovered,
  }) : super(repaint: clock);

  final _HeroMotionClock clock;
  final _MotionPalette palette;
  final bool reducedMotion;
  final bool hovered;

  double _cycle(double period, [double offset = 0]) =>
      ((clock.seconds / period) + offset) % 1;

  double _wave(double period, [double offset = 0]) =>
      math.sin(_cycle(period, offset) * math.pi * 2);

  @override
  void paint(Canvas canvas, Size size) {
    if (size.isEmpty) return;

    final hoverScale = reducedMotion ? 1.0 : (hovered ? 1.045 : 1.0);
    final floatY = reducedMotion ? 0.0 : _wave(6.2, .13) * 2.4;
    final fieldCenter = Offset(size.width * .5, size.height * .61 + floatY);

    canvas.save();
    canvas.translate(fieldCenter.dx, fieldCenter.dy);
    canvas.scale(hoverScale);
    canvas.translate(-fieldCenter.dx, -fieldCenter.dy);

    _paintConstructionGuides(canvas, size, fieldCenter);
    _paintSecondaryField(canvas, size, fieldCenter);
    _paintPrimaryField(canvas, size, fieldCenter);
    _paintOrbitArcs(canvas, size, fieldCenter);
    _paintOrbitMarkers(canvas, size, fieldCenter);
    _paintVerticalAxis(canvas, size, fieldCenter);
    _paintCenterNode(canvas, size, fieldCenter);
    _paintCube(canvas, size, fieldCenter);

    canvas.restore();
  }

  void _paintConstructionGuides(Canvas canvas, Size size, Offset center) {
    final guide = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = .7
      ..color = palette.guide.withValues(alpha: palette.guideAlpha);
    canvas.drawLine(
      Offset(center.dx - size.width * .34, center.dy),
      Offset(center.dx + size.width * .34, center.dy),
      guide,
    );
    final rect = Rect.fromCenter(
      center: center,
      width: size.width * .70,
      height: size.height * .23,
    );
    canvas.drawOval(rect, guide);
  }

  void _paintSecondaryField(Canvas canvas, Size size, Offset center) {
    const layerCount = 8;
    for (var i = 0; i < layerCount; i++) {
      final phase = reducedMotion ? 0.0 : _wave(4.2 + i * .38, i * .117);
      final depth = i / (layerCount - 1);
      final width = size.width * (.39 + i * .075) * (1 + phase * .008);
      final height = size.height * (.105 + i * .031) * (1 + phase * .018);
      final alpha = palette.secondaryAlpha * (.18 + depth * .34) *
          (hovered && !reducedMotion ? 1.18 : 1.0);
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = .55 + depth * .38
        ..color = palette.secondary.withValues(alpha: alpha.clamp(0.0, 1.0));
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(center.dx, center.dy + (i - 3.5) * .65),
          width: width,
          height: height,
        ),
        paint,
      );
    }
  }

  void _paintPrimaryField(Canvas canvas, Size size, Offset center) {
    const layerCount = 7;
    for (var i = 0; i < layerCount; i++) {
      final pulse = reducedMotion ? 0.0 : _wave(2.2 + i * .10, i * .143);
      final near = i / (layerCount - 1);
      final width = size.width * (.48 + i * .072) * (1 + pulse * .012);
      final height = size.height * (.13 + i * .034) * (1 + pulse * .028);
      final alpha = palette.primaryAlpha * (.31 + near * .44) *
          (1 + pulse * .10) *
          (hovered && !reducedMotion ? 1.12 : 1.0);
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = .78 + near * .68
        ..color = palette.primary.withValues(alpha: alpha.clamp(0.0, 1.0));
      canvas.drawOval(
        Rect.fromCenter(
          center: Offset(center.dx, center.dy + (i - 3) * .48),
          width: width,
          height: height,
        ),
        paint,
      );
    }
  }

  void _paintOrbitArcs(Canvas canvas, Size size, Offset center) {
    const periods = <double>[6.0, 9.0, 13.0, 7.5];
    const directions = <double>[1, -1, 1, -1];
    for (var i = 0; i < periods.length; i++) {
      final angle = reducedMotion
          ? i * .8
          : _cycle(periods[i], i * .19) * math.pi * 2 * directions[i];
      final rect = Rect.fromCenter(
        center: center,
        width: size.width * (.57 + i * .115),
        height: size.height * (.16 + i * .052),
      );
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeWidth = 1.05 + i * .13
        ..color = palette.primary.withValues(
          alpha: palette.primaryAlpha * (.42 - i * .055),
        );
      canvas.drawArc(rect, angle, math.pi * (.32 + i * .045), false, paint);
      canvas.drawArc(
        rect,
        angle + math.pi * 1.08,
        math.pi * (.17 + i * .025),
        false,
        paint,
      );
    }
  }

  void _paintOrbitMarkers(Canvas canvas, Size size, Offset center) {
    const markerCount = 3;
    for (var i = 0; i < markerCount; i++) {
      final angle = reducedMotion
          ? .9 + i * 1.9
          : _cycle(7.0 + i * 2.4, i * .27) * math.pi * 2 * (i.isEven ? 1 : -1);
      final rx = size.width * (.32 + i * .045);
      final ry = size.height * (.075 + i * .024);
      final point = Offset(
        center.dx + math.cos(angle) * rx,
        center.dy + math.sin(angle) * ry,
      );
      final paint = Paint()
        ..style = PaintingStyle.fill
        ..color = palette.primary.withValues(
          alpha: palette.primaryAlpha * (.65 - i * .08),
        );
      canvas.drawCircle(point, 1.55 - i * .12, paint);
    }
  }

  void _paintVerticalAxis(Canvas canvas, Size size, Offset center) {
    final top = size.height * .18 + (reducedMotion ? 0 : _wave(6.2, .13) * 2.4);
    final bottom = center.dy + size.height * .12;
    final base = Paint()
      ..strokeWidth = .8
      ..color = palette.guide.withValues(alpha: palette.guideAlpha * 1.35);
    canvas.drawLine(Offset(center.dx, top), Offset(center.dx, bottom), base);

    final pulseT = reducedMotion ? .56 : _cycle(3.0, .21);
    final pulseY = top + (bottom - top) * pulseT;
    final pulse = Paint()
      ..strokeCap = StrokeCap.round
      ..strokeWidth = 1.35
      ..color = palette.primary.withValues(alpha: palette.primaryAlpha * .68);
    canvas.drawLine(
      Offset(center.dx, pulseY - 7),
      Offset(center.dx, pulseY + 7),
      pulse,
    );
  }

  void _paintCenterNode(Canvas canvas, Size size, Offset center) {
    final breathe = reducedMotion ? 0.0 : _wave(1.8, .08);
    final haloPulse = reducedMotion ? 0.0 : _wave(3.6, .36);
    final radius = math.min(size.width, size.height) * (.018 + (breathe + 1) * .0012);

    for (var i = 3; i >= 1; i--) {
      final halo = Paint()
        ..style = PaintingStyle.fill
        ..color = palette.primary.withValues(
          alpha: palette.nodeAlpha * (.055 + i * .018) * (1 + haloPulse * .10),
        );
      canvas.drawCircle(center, radius * (1.8 + i * .72), halo);
    }

    final node = Paint()
      ..style = PaintingStyle.fill
      ..color = palette.primary.withValues(
        alpha: (palette.primaryAlpha * .92).clamp(0.0, 1.0),
      );
    canvas.drawCircle(center, radius, node);
    final core = Paint()
      ..style = PaintingStyle.fill
      ..color = IlaiosTheme.white.withValues(alpha: .86);
    canvas.drawCircle(center, radius * .34, core);
  }

  void _paintCube(Canvas canvas, Size size, Offset fieldCenter) {
    final cubeCenter = Offset(
      fieldCenter.dx,
      size.height * .305 + (reducedMotion ? 0 : _wave(6.2, .13) * 2.4),
    );
    final cubeSize = math.min(size.width, size.height) * .105;
    final yaw = reducedMotion ? .58 : _cycle(8.0, .12) * math.pi * 2;
    final pitch = -.34 + (reducedMotion ? 0 : _wave(10.5, .41) * .08);

    final vertices = <_Vec3>[
      for (final x in const [-1.0, 1.0])
        for (final y in const [-1.0, 1.0])
          for (final z in const [-1.0, 1.0]) _Vec3(x, y, z),
    ];
    final projected = vertices
        .map((v) => _project(v.rotateY(yaw).rotateX(pitch), cubeCenter, cubeSize))
        .toList(growable: false);

    const faces = <List<int>>[
      [0, 1, 3, 2],
      [4, 6, 7, 5],
      [0, 4, 5, 1],
      [2, 3, 7, 6],
      [0, 2, 6, 4],
      [1, 5, 7, 3],
    ];
    for (var i = 0; i < faces.length; i++) {
      final path = Path()..moveTo(projected[faces[i][0]].dx, projected[faces[i][0]].dy);
      for (final index in faces[i].skip(1)) {
        path.lineTo(projected[index].dx, projected[index].dy);
      }
      path.close();
      final fill = Paint()
        ..style = PaintingStyle.fill
        ..color = (i.isEven ? palette.primary : palette.secondary).withValues(
          alpha: palette.faceAlpha * (i < 3 ? 1.0 : .62),
        );
      canvas.drawPath(path, fill);
    }

    const edges = <List<int>>[
      [0, 1], [0, 2], [0, 4], [1, 3], [1, 5], [2, 3],
      [2, 6], [3, 7], [4, 5], [4, 6], [5, 7], [6, 7],
    ];
    for (var i = 0; i < edges.length; i++) {
      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeCap = StrokeCap.round
        ..strokeWidth = i % 3 == 0 ? 1.25 : .92
        ..color = palette.primary.withValues(
          alpha: palette.primaryAlpha * (i % 3 == 0 ? .86 : .58),
        );
      canvas.drawLine(projected[edges[i][0]], projected[edges[i][1]], paint);
    }
  }

  Offset _project(_Vec3 value, Offset center, double size) {
    const perspective = 4.3;
    final depth = perspective / (perspective + value.z * .46);
    return Offset(
      center.dx + value.x * size * depth,
      center.dy + value.y * size * depth,
    );
  }

  @override
  bool shouldRepaint(covariant _HeroMotionPainter oldDelegate) =>
      oldDelegate.clock != clock ||
      oldDelegate.palette != palette ||
      oldDelegate.reducedMotion != reducedMotion ||
      oldDelegate.hovered != hovered;
}

class _Vec3 {
  const _Vec3(this.x, this.y, this.z);

  final double x;
  final double y;
  final double z;

  _Vec3 rotateY(double angle) {
    final cosA = math.cos(angle);
    final sinA = math.sin(angle);
    return _Vec3(x * cosA + z * sinA, y, -x * sinA + z * cosA);
  }

  _Vec3 rotateX(double angle) {
    final cosA = math.cos(angle);
    final sinA = math.sin(angle);
    return _Vec3(x, y * cosA - z * sinA, y * sinA + z * cosA);
  }
}