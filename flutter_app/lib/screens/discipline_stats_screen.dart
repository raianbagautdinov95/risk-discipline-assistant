import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';

import '../models/trade.dart';
import '../services/api_service.dart';
import '../services/demo_data.dart';
import '../services/user_store.dart';
import '../theme.dart';
import '../widgets/calendar_heatmap.dart';
import '../widgets/premium.dart';
import '../widgets/share_card.dart';
import '../widgets/skeletons.dart';
import '../widgets/streaks.dart';

class DisciplineStatsScreen extends StatefulWidget {
  const DisciplineStatsScreen({super.key});

  @override
  State<DisciplineStatsScreen> createState() => _DisciplineStatsScreenState();
}

class _DisciplineStatsScreenState extends State<DisciplineStatsScreen> {
  final _api = ApiService();
  bool _loading = true;
  bool _demo = false;
  String? _error;
  int? _tid;
  DisciplineStats? _stats;
  List<Trade> _trades = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    if (_demo) {
      _trades = DemoData.trades(count: 30);
      _stats = DemoData.stats(from: _trades);
      _tid = -1;
      if (mounted) setState(() => _loading = false);
      return;
    }
    try {
      _tid = await UserStore.getTelegramId();
      if (_tid == null) return;
      _stats = await _api.getStats(_tid!);
      _trades = await _api.getJournal(_tid!, limit: 200);
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _toggleDemo(bool value) {
    setState(() => _demo = value);
    _load();
  }

  Future<void> _openShareCard(BuildContext context) async {
    if (_stats == null) return;
    await showDialog(
      context: context,
      builder: (_) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: const EdgeInsets.all(16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 600),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: ShareCard(stats: _stats!, trades: _trades),
              ),
            ),
            const SizedBox(height: 12),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Text(
                'Правый клик по картинке → "Сохранить изображение".\n'
                'Постни в Twitter / Telegram-канал — продвигаешь продукт + мотивируешь себя.',
                textAlign: TextAlign.center,
                style: TextStyle(color: AppColors.textSecondary, fontSize: 12),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _bigTile(
    String label,
    num numericValue,
    Color color,
    IconData icon, {
    String prefix = '',
    String suffix = '',
    int decimals = 0,
  }) {
    return Expanded(
      child: HoverCard(
        radius: BorderRadius.circular(12),
        child: Container(
          margin: const EdgeInsets.all(4),
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 12),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            border: Border.all(color: Theme.of(context).dividerTheme.color ?? AppColors.border),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(icon, size: 14, color: color),
                ),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(label,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textSecondary)),
                ),
              ]),
              const SizedBox(height: 8),
              AnimatedCounter(
                value: numericValue,
                prefix: prefix,
                suffix: suffix,
                decimals: decimals,
                style: TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w800,
                    height: 1.1,
                    letterSpacing: -0.5,
                    color: color),
              ),
            ],
          ),
        ),
      ),
    );
  }

  /// Compute cumulative P&L curve from closed trades sorted by date.
  List<FlSpot> _equityCurve() {
    final closed = _trades
        .where((t) => t.isClosed && t.pnlPercent != null && t.closedAt != null)
        .toList()
      ..sort((a, b) => a.closedAt!.compareTo(b.closedAt!));
    final spots = <FlSpot>[const FlSpot(0, 0)];
    double cum = 0;
    for (var i = 0; i < closed.length; i++) {
      cum += closed[i].pnlPercent!;
      spots.add(FlSpot((i + 1).toDouble(), cum));
    }
    return spots;
  }

  /// Win-rate per day for the last N days.
  List<MapEntry<DateTime, double>> _winRateByDay() {
    final now = DateTime.now();
    final byDay = <DateTime, _DayAcc>{};
    for (final t in _trades) {
      if (!t.isClosed) continue;
      if (t.outcome != 'WIN' && t.outcome != 'LOSS') continue;
      final d = DateTime(
          t.closedAt!.year, t.closedAt!.month, t.closedAt!.day);
      final acc = byDay.putIfAbsent(d, _DayAcc.new);
      if (t.isWin) acc.wins++;
      if (t.isLoss) acc.losses++;
    }
    final last = <MapEntry<DateTime, double>>[];
    for (var i = 6; i >= 0; i--) {
      final d = DateTime(now.year, now.month, now.day - i);
      final acc = byDay[d];
      if (acc == null || acc.total == 0) {
        last.add(MapEntry(d, 0));
      } else {
        last.add(MapEntry(d, acc.winRate));
      }
    }
    return last;
  }

  Widget _equityChart() {
    final spots = _equityCurve();
    if (spots.length <= 1) {
      return _emptyChart(
          'Закрой хотя бы одну сделку с P&L,\nчтобы появилась кривая капитала.');
    }
    final last = spots.last.y;
    final color = last >= 0 ? AppColors.success : AppColors.danger;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(6),
                  decoration: BoxDecoration(
                    color: color.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Icon(Icons.show_chart, size: 16, color: color),
                ),
                const SizedBox(width: 10),
                const Text('Equity curve',
                    style: TextStyle(
                        fontWeight: FontWeight.w600, fontSize: 14)),
                const SizedBox(width: 8),
                const Text('накопленный P&L',
                    style: TextStyle(
                        color: AppColors.textMuted, fontSize: 11)),
                const Spacer(),
                Text(
                  '${last >= 0 ? '+' : ''}${last.toStringAsFixed(2)}%',
                  style: TextStyle(
                      color: color,
                      fontWeight: FontWeight.w700,
                      fontSize: 20),
                ),
              ],
            ),
            const SizedBox(height: 16),
            SizedBox(
              height: 200,
              child: LineChart(
                LineChartData(
                  gridData: FlGridData(
                    show: true,
                    drawVerticalLine: false,
                    horizontalInterval:
                        (last.abs() < 5) ? 1 : (last.abs() / 4).ceilToDouble(),
                    getDrawingHorizontalLine: (_) => const FlLine(
                      color: AppColors.border,
                      strokeWidth: 1,
                      dashArray: [4, 4],
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  titlesData: const FlTitlesData(
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 36,
                      ),
                    ),
                    bottomTitles:
                        AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles:
                        AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles:
                        AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  lineTouchData: LineTouchData(
                    touchTooltipData: LineTouchTooltipData(
                      getTooltipColor: (_) => AppColors.surfaceAlt,
                      tooltipRoundedRadius: 8,
                    ),
                  ),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      isCurved: true,
                      curveSmoothness: 0.25,
                      color: color,
                      barWidth: 3,
                      dotData: const FlDotData(show: false),
                      belowBarData: BarAreaData(
                        show: true,
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            color.withValues(alpha: 0.35),
                            color.withValues(alpha: 0.0),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _winRateChart() {
    final data = _winRateByDay();
    final hasAny = data.any((e) => e.value > 0);
    if (!hasAny) {
      return _emptyChart('Закрытых сделок за неделю нет — график пуст.');
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
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
                child: const Icon(Icons.bar_chart,
                    size: 16, color: AppColors.primary),
              ),
              const SizedBox(width: 10),
              const Text('Win-rate по дням',
                  style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
              const SizedBox(width: 8),
              const Text('последние 7 дней',
                  style: TextStyle(color: AppColors.textMuted, fontSize: 11)),
            ]),
            const SizedBox(height: 16),
            SizedBox(
              height: 180,
              child: BarChart(
                BarChartData(
                  alignment: BarChartAlignment.spaceAround,
                  maxY: 100,
                  gridData: const FlGridData(show: true),
                  borderData: FlBorderData(show: false),
                  titlesData: FlTitlesData(
                    leftTitles: const AxisTitles(
                        sideTitles: SideTitles(showTitles: true, reservedSize: 30)),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        getTitlesWidget: (value, meta) {
                          final i = value.toInt();
                          if (i < 0 || i >= data.length) {
                            return const SizedBox.shrink();
                          }
                          final d = data[i].key;
                          return Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Text(
                              '${d.day}.${d.month.toString().padLeft(2, '0')}',
                              style: const TextStyle(fontSize: 10),
                            ),
                          );
                        },
                      ),
                    ),
                    rightTitles:
                        const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    topTitles:
                        const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                  ),
                  barGroups: [
                    for (var i = 0; i < data.length; i++)
                      BarChartGroupData(x: i, barRods: [
                        BarChartRodData(
                          toY: data[i].value,
                          width: 18,
                          borderRadius:
                              const BorderRadius.vertical(top: Radius.circular(4)),
                          color: data[i].value >= 50
                              ? Colors.green
                              : Colors.red,
                        ),
                      ]),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _miniMetric(IconData icon, String label, String value, Color color) {
    return Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(icon, size: 14, color: color),
      const SizedBox(width: 4),
      Text(
        '$label: ',
        style: const TextStyle(fontSize: 12, color: AppColors.textSecondary),
      ),
      Text(
        value,
        style: TextStyle(
            fontSize: 12, fontWeight: FontWeight.w600, color: color),
      ),
    ]);
  }

  Widget _emptyChart(String text) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const Icon(Icons.show_chart, size: 36, color: Colors.grey),
            const SizedBox(height: 6),
            Text(text,
                style: const TextStyle(color: Colors.grey),
                textAlign: TextAlign.center),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final demoSwitch = Container(
      margin: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
      decoration: BoxDecoration(
        color: _demo ? Colors.indigo.shade50 : Colors.white,
        border: Border.all(
            color: _demo ? Colors.indigo : Colors.grey.shade300, width: 1.2),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(
            _demo ? Icons.science : Icons.cloud,
            color: _demo ? Colors.indigo : Colors.grey,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _demo ? 'Демо-режим включён' : 'Реальные данные',
                  style: TextStyle(
                    fontWeight: FontWeight.bold,
                    color: _demo ? Colors.indigo : null,
                  ),
                ),
                Text(
                  _demo
                      ? '30 фейковых сделок — посмотреть как выглядит готовый продукт'
                      : 'Из твоего журнала. Включи демо чтобы увидеть полный экран',
                  style: const TextStyle(fontSize: 11, color: Colors.grey),
                ),
              ],
            ),
          ),
          Switch(value: _demo, onChanged: _toggleDemo),
        ],
      ),
    );

    if (_loading) {
      return Column(children: [
        demoSwitch,
        const Expanded(child: StatsSkeleton()),
      ]);
    }
    if (_error != null && !_demo) {
      return Column(children: [
        demoSwitch,
        Expanded(
          child: Center(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error, color: Colors.red, size: 48),
                  const SizedBox(height: 8),
                  Text(_error!, textAlign: TextAlign.center),
                  const SizedBox(height: 12),
                  FilledButton(onPressed: _load, child: const Text('Повторить')),
                ],
              ),
            ),
          ),
        ),
      ]);
    }
    if (_tid == null && !_demo) {
      return Column(children: [
        demoSwitch,
        const Expanded(
          child: Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Перейди во вкладку "Настройки" и укажи Telegram ID.\n'
                'Или включи "Демо" сверху, чтобы увидеть как выглядит экран.',
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
      ]);
    }
    final s = _stats!;
    if (s.total == 0) {
      return Column(children: [
        demoSwitch,
        const Expanded(
          child: Center(
            child: Padding(
              padding: EdgeInsets.all(24),
              child: Text(
                'Нет данных. Сначала проверь хотя бы одну сделку.\n'
                'Или включи "Демо" сверху.',
                textAlign: TextAlign.center,
              ),
            ),
          ),
        ),
      ]);
    }
    final allowedPct = s.total > 0 ? (s.allowed * 100 / s.total) : 0.0;
    final forbiddenPct = s.total > 0 ? (s.forbidden * 100 / s.total) : 0.0;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          demoSwitch,
          if (_demo)
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: Colors.amber.shade100,
                borderRadius: BorderRadius.circular(8),
              ),
              child: const Row(children: [
                Icon(Icons.info_outline, size: 18),
                SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Это синтетические данные. Выключи Демо чтобы вернуться к реальным.',
                    style: TextStyle(fontSize: 12),
                  ),
                ),
              ]),
            ),
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 0),
            child: OutlinedButton.icon(
              onPressed: () => _openShareCard(context),
              icon: const Icon(Icons.ios_share),
              label: const Text('Поделиться equity curve'),
            ),
          ),
          const SizedBox(height: 4),
          StreaksStrip(trades: _trades),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Column(children: [
          Row(children: [
            _bigTile('Всего проверок', s.total, AppColors.info,
                Icons.format_list_numbered),
            _bigTile('Разрешено', s.allowed, AppColors.success,
                Icons.check_circle_outline),
          ]),
          Row(children: [
            _bigTile('Запрещено', s.forbidden, AppColors.danger, Icons.block),
            _bigTile(
              'Win-rate',
              s.winRatePct,
              s.winRatePct >= 50 ? AppColors.success : AppColors.danger,
              Icons.percent,
              suffix: '%',
              decimals: 0,
            ),
          ]),
          Row(children: [
            _bigTile('Закрытых', s.closed, AppColors.textSecondary,
                Icons.task_alt),
            _bigTile(
              'P&L total',
              s.totalPnlPercent,
              s.totalPnlPercent >= 0 ? AppColors.success : AppColors.danger,
              Icons.trending_up,
              prefix: s.totalPnlPercent >= 0 ? '+' : '',
              suffix: '%',
              decimals: 2,
            ),
          ]),
          const SizedBox(height: 8),

          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: AppColors.success.withValues(alpha: 0.16),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(Icons.shield,
                          size: 16, color: AppColors.success),
                    ),
                    const SizedBox(width: 10),
                    const Text('Дисциплина',
                        style: TextStyle(
                            fontWeight: FontWeight.w600, fontSize: 14)),
                    const Spacer(),
                    Text('${allowedPct.toStringAsFixed(0)}% allowed',
                        style: const TextStyle(
                            color: AppColors.textSecondary, fontSize: 12)),
                  ]),
                  const SizedBox(height: 12),
                  ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: LinearProgressIndicator(
                      value: s.total > 0 ? s.allowed / s.total : 0,
                      color: AppColors.success,
                      backgroundColor: AppColors.danger.withValues(alpha: 0.4),
                      minHeight: 10,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Wrap(
                    spacing: 16,
                    runSpacing: 4,
                    children: [
                      _miniMetric(Icons.trending_up, 'Средний R:R',
                          s.avgRr.toString(), AppColors.info),
                      _miniMetric(Icons.percent, 'Средний риск',
                          '${s.avgRisk}%', AppColors.warn),
                      _miniMetric(
                          Icons.show_chart,
                          'Avg P&L закрытых',
                          '${s.avgPnlPercent >= 0 ? '+' : ''}'
                              '${s.avgPnlPercent.toStringAsFixed(2)}%',
                          s.avgPnlPercent >= 0
                              ? AppColors.success
                              : AppColors.danger),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 8),

          _equityChart(),
          const SizedBox(height: 8),
          _winRateChart(),
          const SizedBox(height: 8),
          CalendarHeatmap(trades: _trades, weeks: 12),
          const SizedBox(height: 8),

          if (s.commonForbidReasons.isNotEmpty)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(children: [
                      Container(
                        padding: const EdgeInsets.all(6),
                        decoration: BoxDecoration(
                          color: AppColors.danger.withValues(alpha: 0.16),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Icon(Icons.warning_rounded,
                            size: 16, color: AppColors.danger),
                      ),
                      const SizedBox(width: 10),
                      const Text('Частые причины запрета',
                          style: TextStyle(
                              fontWeight: FontWeight.w600, fontSize: 14)),
                    ]),
                    const SizedBox(height: 12),
                    ...s.commonForbidReasons.map((e) {
                      final maxCount = s.commonForbidReasons.first.value;
                      final ratio = maxCount == 0 ? 0.0 : e.value / maxCount;
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(children: [
                              Expanded(
                                child: Text(e.key,
                                    style: const TextStyle(fontSize: 13)),
                              ),
                              Container(
                                padding: const EdgeInsets.symmetric(
                                    horizontal: 8, vertical: 2),
                                decoration: BoxDecoration(
                                  color: AppColors.danger.withValues(alpha: 0.16),
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: Text('${e.value}',
                                    style: const TextStyle(
                                        color: AppColors.danger,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600)),
                              ),
                            ]),
                            const SizedBox(height: 4),
                            ClipRRect(
                              borderRadius: BorderRadius.circular(4),
                              child: LinearProgressIndicator(
                                value: ratio,
                                minHeight: 4,
                                color: AppColors.danger,
                                backgroundColor:
                                    AppColors.danger.withValues(alpha: 0.15),
                              ),
                            ),
                          ],
                        ),
                      );
                    }),
                  ],
                ),
              ),
            ),
          const SizedBox(height: 16),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Text(
              '⚠️ Это не финансовая рекомендация. Бот помогает контролировать '
              'риск и дисциплину.',
              style: TextStyle(
                  fontSize: 12,
                  fontStyle: FontStyle.italic,
                  color: Colors.grey),
            ),
          ),
            ]),
          ),
        ],
      ),
    );
  }
}

class _DayAcc {
  int wins = 0;
  int losses = 0;
  int get total => wins + losses;
  double get winRate => total == 0 ? 0 : wins * 100 / total;
}
