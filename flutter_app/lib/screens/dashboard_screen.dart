import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/market_signal.dart';
import '../models/trade.dart';
import '../services/api_service.dart';
import '../services/user_store.dart';
import '../theme.dart';
import '../widgets/common.dart';
import 'discipline_stats_screen.dart';
import 'trade_detail_screen.dart';

class DashboardScreen extends StatefulWidget {
  final ValueChanged<int> onSwitchTab;
  const DashboardScreen({super.key, required this.onSwitchTab});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  final _api = ApiService();
  final _signalApi = SignalApiService();
  final _df = DateFormat('EEEE, dd MMMM', 'ru_RU');

  bool _loading = true;
  int? _tid;
  DisciplineStats? _stats;
  List<Trade> _journal = [];
  List<MarketSignal> _signals = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    _tid = await UserStore.getTelegramId();

    final futures = await Future.wait([
      if (_tid != null) _api.getStats(_tid!).then((s) => s).catchError((_) => null)
      else Future.value(null),
      if (_tid != null) _api.getJournal(_tid!, limit: 100).then((s) => s).catchError((_) => <Trade>[])
      else Future.value(<Trade>[]),
      _signalApi.getActive().catchError((_) => <MarketSignal>[]),
    ]);

    _stats = futures[0] as DisciplineStats?;
    _journal = futures[1] as List<Trade>;
    _signals = futures[2] as List<MarketSignal>;

    if (mounted) setState(() => _loading = false);
  }

  String get _greeting {
    final h = DateTime.now().hour;
    if (h < 6) return 'Доброй ночи';
    if (h < 12) return 'Доброе утро';
    if (h < 18) return 'Добрый день';
    return 'Добрый вечер';
  }

  int _disciplineStreak() {
    if (_journal.isEmpty) return 0;
    final byDay = <DateTime, int>{};
    for (final t in _journal) {
      final d = DateTime(t.createdAt.year, t.createdAt.month, t.createdAt.day);
      if (t.isForbidden) byDay[d] = (byDay[d] ?? 0) + 1;
      byDay.putIfAbsent(d, () => 0);
    }
    var streak = 0;
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day);
    for (var i = 0; i < 365; i++) {
      final d = start.subtract(Duration(days: i));
      final forbidden = byDay[d];
      if (forbidden == null) continue;
      if (forbidden > 0) break;
      streak++;
    }
    return streak;
  }

  int _todayCount() {
    final now = DateTime.now();
    final start = DateTime(now.year, now.month, now.day);
    return _journal.where((t) => t.createdAt.isAfter(start)).length;
  }

  List<Trade> _pendingTrades() => _journal
      .where((t) => t.isAllowed && !t.isClosed)
      .take(5)
      .toList();

  Color _decisionColor(String d) => switch (d) {
        'ALLOWED' => AppColors.success,
        'FORBIDDEN' => AppColors.danger,
        _ => AppColors.warn,
      };

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_tid == null) {
      return HintState(
        icon: Icons.account_circle_outlined,
        title: 'Привет!',
        subtitle: 'Перейди в "Настройки" и укажи свой Telegram ID, '
            'чтобы открыть весь функционал.',
        action: FilledButton.icon(
          onPressed: () => widget.onSwitchTab(5),
          icon: const Icon(Icons.settings),
          label: const Text('В настройки'),
        ),
      );
    }

    final streak = _disciplineStreak();
    final winRate = _stats?.winRatePct ?? 0;
    final pending = _pendingTrades();
    final todayCount = _todayCount();

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
        children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 22),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [AppColors.primary, AppColors.primaryDeep],
              ),
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(
                  color: AppColors.primary.withValues(alpha: 0.3),
                  blurRadius: 24,
                  offset: const Offset(0, 8),
                ),
              ],
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(_greeting,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.w700,
                    )),
                Text(
                  _df.format(DateTime.now()),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.75),
                    fontSize: 13,
                  ),
                ),
                const SizedBox(height: 16),
                Row(children: [
                  Expanded(
                    child: _heroStat(
                      icon: Icons.local_fire_department,
                      value: '$streak',
                      label: 'дней\nбез нарушений',
                    ),
                  ),
                  Container(
                      width: 1,
                      height: 40,
                      color: Colors.white.withValues(alpha: 0.2)),
                  Expanded(
                    child: _heroStat(
                      icon: Icons.percent,
                      value: '${winRate.toStringAsFixed(0)}%',
                      label: 'win-rate',
                    ),
                  ),
                  Container(
                      width: 1,
                      height: 40,
                      color: Colors.white.withValues(alpha: 0.2)),
                  Expanded(
                    child: _heroStat(
                      icon: Icons.today,
                      value: '$todayCount',
                      label: 'сделок\nсегодня',
                    ),
                  ),
                ]),
              ],
            ),
          ),
          const SizedBox(height: 14),

          FilledButton.icon(
            style: FilledButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 18),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
              ),
            ),
            onPressed: () => widget.onSwitchTab(2),
            icon: const Icon(Icons.shield, size: 20),
            label: const Text(
              'Проверить новую сделку',
              style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  letterSpacing: 0.3),
            ),
          ),
          const SizedBox(height: 18),

          _SectionTitle(
            icon: Icons.satellite_alt,
            title: 'Сигналы рынка',
            color: AppColors.info,
            counter: _signals.length,
            onSeeAll: () => widget.onSwitchTab(1),
          ),
          const SizedBox(height: 8),
          if (_signals.isEmpty)
            _emptyMini('Сейчас активных сигналов нет.\nСканер ищет каждые 15 минут.'),
          for (final s in _signals.take(3))
            _miniSignalCard(s, onTap: () => widget.onSwitchTab(1)),

          const SizedBox(height: 18),

          _SectionTitle(
            icon: Icons.hourglass_empty,
            title: 'Незакрытые сделки',
            color: AppColors.warn,
            counter: pending.length,
            onSeeAll: () => widget.onSwitchTab(3),
          ),
          const SizedBox(height: 8),
          if (pending.isEmpty)
            _emptyMini('🎉 Все сделки закрыты — журнал актуален.'),
          for (final t in pending) _miniPendingCard(t),

          const SizedBox(height: 18),

          _SectionTitle(
            icon: Icons.bar_chart,
            title: 'Дисциплина',
            color: AppColors.success,
            onSeeAll: () => Navigator.of(context).push(
              MaterialPageRoute(
                builder: (_) => Scaffold(
                  appBar: AppBar(title: const Text('Дисциплина')),
                  body: const DisciplineStatsScreen(),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          if (_stats == null || _stats!.total == 0)
            _emptyMini('Сделай первую проверку — статистика появится.')
          else
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surface,
                border: Border.all(color: AppColors.border),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Row(children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        '${_stats!.allowed}/${_stats!.total} ALLOWED',
                        style: const TextStyle(
                            fontWeight: FontWeight.w700, fontSize: 16),
                      ),
                      const SizedBox(height: 6),
                      ClipRRect(
                        borderRadius: BorderRadius.circular(8),
                        child: LinearProgressIndicator(
                          value: _stats!.total == 0
                              ? 0
                              : _stats!.allowed / _stats!.total,
                          color: AppColors.success,
                          backgroundColor: AppColors.danger.withValues(alpha: 0.3),
                          minHeight: 8,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'P&L total: ${_stats!.totalPnlPercent >= 0 ? '+' : ''}'
                        '${_stats!.totalPnlPercent.toStringAsFixed(2)}%   '
                        '•   Avg R:R: ${_stats!.avgRr}',
                        style: const TextStyle(
                            color: AppColors.textMuted, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ]),
            ),
        ],
      ),
    );
  }

  Widget _heroStat(
      {required IconData icon, required String value, required String label}) {
    return Column(
      children: [
        Icon(icon, color: Colors.white.withValues(alpha: 0.85), size: 20),
        const SizedBox(height: 4),
        Text(value,
            style: const TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w900,
                fontSize: 24)),
        Text(label,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.75),
              fontSize: 10,
              height: 1.2,
            )),
      ],
    );
  }

  Widget _emptyMini(String text) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: AppColors.surface,
          border: Border.all(color: AppColors.border),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Text(text,
            textAlign: TextAlign.center,
            style: const TextStyle(color: AppColors.textMuted, fontSize: 13)),
      );

  Widget _miniSignalCard(MarketSignal s, {required VoidCallback onTap}) {
    final color = s.isLong ? AppColors.success : AppColors.danger;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: color.withValues(alpha: 0.4)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Row(children: [
          Icon(
              s.isLong ? Icons.trending_up : Icons.trending_down,
              color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${s.symbol} • ${s.action}',
                  style: TextStyle(
                      fontWeight: FontWeight.w700, color: color, fontSize: 14),
                ),
                Text(
                  'entry ${s.entry}  •  R:R ${s.riskReward.toStringAsFixed(2)}',
                  style: const TextStyle(
                      color: AppColors.textMuted, fontSize: 11),
                ),
              ],
            ),
          ),
          const Icon(Icons.chevron_right, color: AppColors.textMuted),
        ]),
      ),
    );
  }

  Widget _miniPendingCard(Trade t) {
    final age = DateTime.now().difference(t.createdAt);
    final ageStr = age.inDays > 0
        ? '${age.inDays} дн.'
        : age.inHours > 0
            ? '${age.inHours}ч'
            : '${age.inMinutes}мин';
    final color = _decisionColor(t.decision);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.warn.withValues(alpha: 0.3)),
        borderRadius: BorderRadius.circular(12),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => Navigator.of(context).push(
          MaterialPageRoute(
            builder: (_) => TradeDetailScreen(
              trade: t,
              telegramId: _tid!,
              onClosed: _load,
              onRepeat: () => widget.onSwitchTab(2),
            ),
          ),
        ),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            const Icon(Icons.hourglass_top, color: AppColors.warn),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '#${t.id}  ${t.pair}  ${t.direction.toUpperCase()}',
                    style:
                        TextStyle(fontWeight: FontWeight.w700, color: color),
                  ),
                  Text(
                    'открыта $ageStr назад  •  risk ${t.riskPercent}%',
                    style: const TextStyle(
                        color: AppColors.textMuted, fontSize: 11),
                  ),
                ],
              ),
            ),
            const Icon(Icons.chevron_right, color: AppColors.textMuted),
          ]),
        ),
      ),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  final IconData icon;
  final String title;
  final Color color;
  final int? counter;
  final VoidCallback? onSeeAll;

  const _SectionTitle({
    required this.icon,
    required this.title,
    required this.color,
    this.counter,
    this.onSeeAll,
  });

  @override
  Widget build(BuildContext context) {
    return Row(children: [
      Container(
        padding: const EdgeInsets.all(6),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.16),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(icon, size: 16, color: color),
      ),
      const SizedBox(width: 10),
      Text(title,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
      if (counter != null) ...[
        const SizedBox(width: 6),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
          decoration: BoxDecoration(
            color: color.withValues(alpha: 0.18),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Text('$counter',
              style: TextStyle(
                  color: color, fontSize: 11, fontWeight: FontWeight.w700)),
        ),
      ],
      const Spacer(),
      if (onSeeAll != null)
        TextButton(
          onPressed: onSeeAll,
          style: TextButton.styleFrom(visualDensity: VisualDensity.compact),
          child: const Text('Открыть',
              style: TextStyle(fontSize: 12)),
        ),
    ]);
  }
}
