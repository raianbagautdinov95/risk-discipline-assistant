import 'package:flutter/material.dart';

import '../theme.dart';

class _PulseBox extends StatefulWidget {
  final double? width;
  final double height;
  final double radius;
  const _PulseBox({this.width, required this.height, this.radius = 8});

  @override
  State<_PulseBox> createState() => _PulseBoxState();
}

class _PulseBoxState extends State<_PulseBox>
    with SingleTickerProviderStateMixin {
  late final AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1100),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _c,
      builder: (_, __) => Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(
          color: Color.lerp(
            AppColors.surfaceAlt,
            AppColors.border,
            _c.value,
          ),
          borderRadius: BorderRadius.circular(widget.radius),
        ),
      ),
    );
  }
}

class CardSkeleton extends StatelessWidget {
  const CardSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: const [
            _PulseBox(width: 36, height: 36, radius: 10),
            SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _PulseBox(width: 110, height: 14),
                  SizedBox(height: 6),
                  _PulseBox(width: 70, height: 10),
                ],
              ),
            ),
            _PulseBox(width: 70, height: 22, radius: 12),
          ]),
          const SizedBox(height: 14),
          Row(children: const [
            _PulseBox(width: 70, height: 24, radius: 8),
            SizedBox(width: 6),
            _PulseBox(width: 60, height: 24, radius: 8),
            SizedBox(width: 6),
            _PulseBox(width: 80, height: 24, radius: 8),
          ]),
          const SizedBox(height: 14),
          const _PulseBox(height: 14, width: double.infinity),
          const SizedBox(height: 6),
          const _PulseBox(height: 14, width: 220),
        ],
      ),
    );
  }
}

class JournalSkeleton extends StatelessWidget {
  final int count;
  const JournalSkeleton({super.key, this.count = 4});

  @override
  Widget build(BuildContext context) {
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 32),
      itemCount: count,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, __) => const CardSkeleton(),
    );
  }
}

class StatsSkeleton extends StatelessWidget {
  const StatsSkeleton({super.key});

  @override
  Widget build(BuildContext context) {
    Widget tile() => Expanded(
          child: Container(
            margin: const EdgeInsets.all(4),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surface,
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                _PulseBox(width: 80, height: 12),
                SizedBox(height: 12),
                _PulseBox(width: 60, height: 24),
              ],
            ),
          ),
        );

    Widget chart() => Container(
          margin: const EdgeInsets.symmetric(vertical: 6, horizontal: 12),
          padding: const EdgeInsets.all(16),
          height: 220,
          decoration: BoxDecoration(
            color: AppColors.surface,
            border: Border.all(color: AppColors.border),
            borderRadius: BorderRadius.circular(14),
          ),
          child: const Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _PulseBox(width: 140, height: 14),
              SizedBox(height: 16),
              Expanded(
                  child: _PulseBox(width: double.infinity, height: 0)),
            ],
          ),
        );

    return ListView(
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 32),
      children: [
        Padding(
          padding: const EdgeInsets.all(4),
          child: Row(children: [tile(), tile()]),
        ),
        Padding(
          padding: const EdgeInsets.all(4),
          child: Row(children: [tile(), tile()]),
        ),
        const SizedBox(height: 6),
        chart(),
        chart(),
      ],
    );
  }
}
