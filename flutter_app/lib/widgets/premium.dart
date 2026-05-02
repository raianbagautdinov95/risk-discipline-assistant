import 'package:flutter/material.dart';

import '../theme.dart';


class HoverCard extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final BorderRadius radius;
  const HoverCard({
    super.key,
    required this.child,
    this.onTap,
    this.radius = const BorderRadius.all(Radius.circular(14)),
  });

  @override
  State<HoverCard> createState() => _HoverCardState();
}

class _HoverCardState extends State<HoverCard> {
  bool _hover = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      cursor: widget.onTap != null
          ? SystemMouseCursors.click
          : SystemMouseCursors.basic,
      onEnter: (_) => setState(() => _hover = true),
      onExit: (_) => setState(() => _hover = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        curve: Curves.easeOut,
        transform: Matrix4.identity()..translate(0.0, _hover ? -3.0 : 0.0),
        decoration: BoxDecoration(
          borderRadius: widget.radius,
          boxShadow: _hover
              ? [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.18),
                    blurRadius: 22,
                    offset: const Offset(0, 8),
                  ),
                ]
              : [],
        ),
        child: GestureDetector(onTap: widget.onTap, child: widget.child),
      ),
    );
  }
}


class AnimatedCounter extends StatelessWidget {
  final num value;
  final Duration duration;
  final TextStyle? style;
  final String? prefix;
  final String? suffix;
  final int decimals;

  const AnimatedCounter({
    super.key,
    required this.value,
    this.duration = const Duration(milliseconds: 700),
    this.style,
    this.prefix,
    this.suffix,
    this.decimals = 0,
  });

  @override
  Widget build(BuildContext context) {
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: value.toDouble()),
      duration: duration,
      curve: Curves.easeOutCubic,
      builder: (_, v, __) {
        final formatted =
            decimals == 0 ? v.toInt().toString() : v.toStringAsFixed(decimals);
        return Text('${prefix ?? ''}$formatted${suffix ?? ''}', style: style);
      },
    );
  }
}


class StaggeredFadeIn extends StatelessWidget {
  final int index;
  final Widget child;
  final Duration delayPer;
  final Duration duration;

  const StaggeredFadeIn({
    super.key,
    required this.index,
    required this.child,
    this.delayPer = const Duration(milliseconds: 60),
    this.duration = const Duration(milliseconds: 350),
  });

  @override
  Widget build(BuildContext context) {
    final start = (delayPer.inMilliseconds * index).toDouble();
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: duration + Duration(milliseconds: start.toInt()),
      curve: Interval(
        (start / (duration.inMilliseconds + start)).clamp(0.0, 0.99),
        1,
        curve: Curves.easeOutCubic,
      ),
      builder: (_, v, c) => Opacity(
        opacity: v,
        child: Transform.translate(offset: Offset(0, (1 - v) * 12), child: c),
      ),
      child: child,
    );
  }
}


class FadeSlideRoute<T> extends PageRouteBuilder<T> {
  final Widget child;
  FadeSlideRoute({required this.child})
      : super(
          pageBuilder: (_, __, ___) => child,
          transitionDuration: const Duration(milliseconds: 280),
          reverseTransitionDuration: const Duration(milliseconds: 200),
          transitionsBuilder: (_, animation, __, c) {
            final curved =
                CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
            return FadeTransition(
              opacity: curved,
              child: SlideTransition(
                position: Tween<Offset>(
                  begin: const Offset(0, 0.04),
                  end: Offset.zero,
                ).animate(curved),
                child: c,
              ),
            );
          },
        );
}


List<BoxShadow> glow(Color color, {double opacity = 0.35, double blur = 30}) {
  return [
    BoxShadow(
      color: color.withValues(alpha: opacity),
      blurRadius: blur,
      offset: const Offset(0, 8),
    ),
  ];
}
