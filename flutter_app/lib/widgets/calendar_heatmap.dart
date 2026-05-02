import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/trade.dart';
import '../theme.dart';

class _DayBucket {
  int wins = 0;
  int losses = 0;
  int allowed = 0;
  int forbidden = 0;
  int wait = 0;

  int get total => allowed + forbidden + wait;
  bool get hasFor => forbidden > 0;
  bool get hasWin => wins > 0;
  bool get hasLoss => losses > 0;
}

class CalendarHeatmap extends StatelessWidget {
  final List<Trade> trades;
  final int weeks;
  final void Function(DateTime day, _DayBucket bucket)? onDayTap;

  const CalendarHeatmap({
    super.key,
    required this.trades,
    this.weeks = 12,
    this.onDayTap,
  });

  Map<DateTime, _DayBucket> _buildIndex() {
    final map = <DateTime, _DayBucket>{};
    for (final t in trades) {
      final d = DateTime(t.createdAt.year, t.createdAt.month, t.createdAt.day);
      final b = map.putIfAbsent(d, _DayBucket.new);
      if (t.isAllowed) b.allowed++;
      if (t.isForbidden) b.forbidden++;
      if (t.isWait) b.wait++;
      if (t.isWin) b.wins++;
      if (t.isLoss) b.losses++;
    }
    return map;
  }

  Color _cellColor(_DayBucket? b, BuildContext ctx) {
    final isDark = Theme.of(ctx).brightness == Brightness.dark;
    final empty = isDark
        ? AppColors.surfaceAlt.withValues(alpha: 0.6)
        : AppColors.lSurfaceAlt;
    if (b == null || b.total == 0) return empty;
    if (b.hasFor) return AppColors.danger.withValues(alpha: 0.55);
    if (b.hasWin && !b.hasLoss) return AppColors.success;
    if (b.hasLoss && !b.hasWin) return AppColors.danger.withValues(alpha: 0.7);
    if (b.hasWin && b.hasLoss) return AppColors.warn;
    return AppColors.success.withValues(alpha: 0.4); // ALLOWED but not closed
  }

  @override
  Widget build(BuildContext context) {
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day)
        .subtract(Duration(days: today.weekday - 1 + (weeks - 1) * 7));
    final index = _buildIndex();
    final dayLabels = const ['Пн', '', 'Ср', '', 'Пт', '', 'Вс'];
    final monthDf = DateFormat('LLL', 'ru_RU');

    final monthCols = <int, String>{};
    for (var w = 0; w < weeks; w++) {
      final colStart = start.add(Duration(days: w * 7));
      final prevColStart = w == 0 ? null : start.add(Duration(days: (w - 1) * 7));
      if (prevColStart == null || colStart.month != prevColStart.month) {
        monthCols[w] = monthDf.format(colStart);
      }
    }

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border.all(
            color: Theme.of(context).dividerTheme.color ?? AppColors.border),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: AppColors.primary.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Icon(Icons.calendar_view_month,
                  size: 16, color: AppColors.primary),
            ),
            const SizedBox(width: 10),
            const Text('Активность по дням',
                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
            const SizedBox(width: 8),
            Text('последние ${weeks} недель',
                style: const TextStyle(
                    color: AppColors.textMuted, fontSize: 11)),
          ]),
          const SizedBox(height: 14),

          LayoutBuilder(builder: (_, constraints) {
            const labelW = 26.0;
            const gap = 3.0;
            final cell =
                ((constraints.maxWidth - labelW) / weeks - gap).clamp(8, 22);

            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Padding(
                  padding: const EdgeInsets.only(left: labelW),
                  child: SizedBox(
                    height: 14,
                    child: Row(
                      children: [
                        for (var w = 0; w < weeks; w++)
                          SizedBox(
                            width: cell + gap,
                            child: Text(
                              monthCols[w] ?? '',
                              style: const TextStyle(
                                  fontSize: 10,
                                  color: AppColors.textMuted),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 4),
                // 7 rows × weeks cols
                for (var row = 0; row < 7; row++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: gap),
                    child: Row(children: [
                      SizedBox(
                        width: labelW,
                        child: Text(
                          dayLabels[row],
                          style: const TextStyle(
                              fontSize: 10, color: AppColors.textMuted),
                        ),
                      ),
                      for (var w = 0; w < weeks; w++)
                        Padding(
                          padding: const EdgeInsets.only(right: gap),
                          child: _Cell(
                            day: start.add(Duration(days: w * 7 + row)),
                            bucket: index[start.add(Duration(days: w * 7 + row))],
                            color: _cellColor(
                                index[start.add(Duration(days: w * 7 + row))],
                                context),
                            size: cell.toDouble(),
                            onTap: onDayTap,
                            isFuture: start
                                .add(Duration(days: w * 7 + row))
                                .isAfter(today),
                          ),
                        ),
                    ]),
                  ),
                const SizedBox(height: 10),
                Wrap(spacing: 12, runSpacing: 6, children: [
                  _legend(AppColors.success, 'WIN'),
                  _legend(AppColors.danger.withValues(alpha: 0.7), 'LOSS'),
                  _legend(AppColors.warn, 'смешанный'),
                  _legend(AppColors.danger.withValues(alpha: 0.55), 'нарушение'),
                  _legend(
                      Theme.of(context).brightness == Brightness.dark
                          ? AppColors.surfaceAlt
                          : AppColors.lSurfaceAlt,
                      'нет данных'),
                ]),
              ],
            );
          }),
        ],
      ),
    );
  }

  Widget _legend(Color color, String label) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Container(
        width: 10,
        height: 10,
        decoration: BoxDecoration(
          color: color,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
      const SizedBox(width: 4),
      Text(label,
          style:
              const TextStyle(fontSize: 10, color: AppColors.textMuted)),
    ]);
  }
}

class _Cell extends StatelessWidget {
  final DateTime day;
  final _DayBucket? bucket;
  final Color color;
  final double size;
  final bool isFuture;
  final void Function(DateTime, _DayBucket)? onTap;

  const _Cell({
    required this.day,
    required this.bucket,
    required this.color,
    required this.size,
    this.isFuture = false,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd.MM');
    final tooltip = bucket == null || bucket!.total == 0
        ? '${df.format(day)} — нет проверок'
        : '${df.format(day)}: '
            'WIN ${bucket!.wins}  LOSS ${bucket!.losses}  '
            'ALLOWED ${bucket!.allowed}  FORB ${bucket!.forbidden}';
    return Tooltip(
      message: tooltip,
      child: GestureDetector(
        onTap: bucket == null || onTap == null
            ? null
            : () => onTap!(day, bucket!),
        child: Container(
          width: size,
          height: size,
          decoration: BoxDecoration(
            color: isFuture ? color.withValues(alpha: 0.15) : color,
            borderRadius: BorderRadius.circular(3),
          ),
        ),
      ),
    );
  }
}
