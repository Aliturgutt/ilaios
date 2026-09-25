import 'package:flutter/material.dart';

/// Shared Assistant/Li identity, using the existing canonical asset bundle.
/// Theme.of is the Desktop surface authority; artwork is scaled only.
class AssistantSymbol extends StatelessWidget {
  const AssistantSymbol({this.size = 24, super.key});

  final double size;

  @override
  Widget build(BuildContext context) => Image.asset(
    Theme.of(context).brightness == Brightness.dark
        ? '../../brand/assets/05-ilaios-app-icon.jpg'
        : '../../brand/assets/04-ilaios-symbol-light.jpg',
    width: size,
    height: size,
    fit: BoxFit.contain,
    filterQuality: FilterQuality.high,
    excludeFromSemantics: true,
    errorBuilder: (context, error, stackTrace) => Icon(
      Icons.auto_awesome_rounded,
      size: size,
      color: Theme.of(context).colorScheme.onSurface,
    ),
  );
}
