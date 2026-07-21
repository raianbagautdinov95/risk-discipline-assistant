import 'package:flutter/material.dart';

import '../models/trade.dart';
import '../theme.dart';

class _Achievement {
  final IconData icon;
  final String label;
  final String value;
  final Color color;
  final bool unlocked;
  const _Achievement({
    required this.icon,
    required this.label,
    required this.value,
    required this.color,
    this.unlocked = true,
  });
}

class StreaksStrip extends StatelessWidget {
  final List<Trade> trades;
  const StreaksStrip({super.key, required this.trades});

  int _disciplineStreak() {
    if (trades.isEmpty) return 0;
    final byDay = <DateTime, _DayAcc>{};
    for (final t in trades) {
      final d = DateTime(t.createdAt.year, t.createdAt.month, t.createdAt.day);
      final acc = byDay.putIfAbsent(d, _DayAcc.new);
      acc.total++;
      if (t.isForbidden) acc.forbidden++;
    }
    var streak = 0;
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day);
    for (var i = 0; i < 365; i++) {
      final d = start.subtract(Duration(days: i));
      final acc = byDay[d];
      if (acc == null) continue;
      if (acc.forbidden > 0) break;
      streak++;
    }
    return streak;
  }

  int _winStreak() {
    final closed = trades.where((t) => t.isWin || t.isLoss).toList()
      ..sort((a, b) => a.createdAt.compareTo(b.createdAt));
    var best = 0, cur = 0;
    for (final t in closed) {
      if (t.isWin) {
        cur++;
        if (cur > best) best = cur;
      } else {
        cur = 0;
      }
    }
    return best;
  }

  double _allowedRate() {
    if (trades.isEmpty) return 0;
    final allowed = trades.where((t) => t.isAllowed).length;
    return allowed * 100 / trades.length;
  }

  List<_Achievement> _badges() {
    final allowedCount = trades.where((t) => t.isAllowed).length;
    final winsCount = trades.where((t) => t.isWin).length;
    final cleanWeek = _disciplineStreak() >= 7;
    final winStreak3 = _winStreak() >= 3;
    final winStreak5 = _winStreak() >= 5;
    return [
      _Achievement(
        icon: Icons.flag,
        label: 'First trade',
        value: trades.isNotEmpty ? 'unlocked' : 'locked',
        color: AppColors.info,
        unlocked: trades.isNotEmpty,
      ),
      _Achievement(
        icon: Icons.shield,
        label: 'Clean week',
        value: cleanWeek ? '7 days' : 'locked',
        color: AppColors.success,
        unlocked: cleanWeek,
      ),
      _Achievement(
        icon: Icons.local_fire_department,
        label: '3 WINs in a row',
        value: winStreak3 ? 'unlocked' : 'locked',
        color: AppColors.warn,
        unlocked: winStreak3,
      ),
      _Achievement(
        icon: Icons.workspace_premium,
        label: '5 WINs in a row',
        value: winStreak5 ? 'unlocked' : 'locked',
        color: AppColors.warn,
        unlocked: winStreak5,
      ),
      _Achievement(
        icon: Icons.school,
        label: '10 ALLOWED',
        value: allowedCount >= 10 ? 'unlocked' : '$allowedCount/10',
        color: AppColors.primary,
        unlocked: allowedCount >= 10,
      ),
      _Achievement(
        icon: Icons.emoji_events,
        label: '20 WINs',
        value: winsCount >= 20 ? 'unlocked' : '$winsCount/20',
        color: AppColors.primary,
        unlocked: winsCount >= 20,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final discipline = _disciplineStreak();
    final winStreak = _winStreak();
    final allowedRate = _allowedRate();
    final badges = _badges();
    final unlocked = badges.where((b) => b.unlocked).length;

    return Container(
      margin: const EdgeInsets.fromLTRB(12, 4, 12, 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [AppColors.primary, AppColors.primaryDeep],
        ),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: AppColors.primary.withValues(alpha: 0.25),
            blurRadius: 24,
            offset: const Offset(0, 8),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            const Icon(Icons.local_fire_department,
                color: Colors.white, size: 22),
            const SizedBox(width: 8),
            const Text('Achievements',
                style: TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.w700,
                    fontSize: 15)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text('$unlocked / ${badges.length}',
                  style: const TextStyle(
                      color: Colors.white,
                      fontSize: 11,
                      fontWeight: FontWeight.w700)),
            ),
          ]),
          const SizedBox(height: 14),
          Row(
            children: [
              _bigStat(
                icon: Icons.shield,
                value: '$discipline',
                label: 'days without violations',
              ),
              _divider(),
              _bigStat(
                icon: Icons.local_fire_department,
                value: '$winStreak',
                label: 'WIN streak',
              ),
              _divider(),
              _bigStat(
                icon: Icons.percent,
                value: '${allowedRate.toStringAsFixed(0)}%',
                label: 'allowed rate',
              ),
            ],
          ),
          const SizedBox(height: 14),
          SizedBox(
            height: 70,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              itemCount: badges.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) => _badge(badges[i]),
            ),
          ),
        ],
      ),
    );
  }

  Widget _bigStat({
    required IconData icon,
    required String value,
    required String label,
  }) {
    return Expanded(
      child: Column(
        children: [
          Icon(icon, color: Colors.white.withValues(alpha: 0.85), size: 20),
          const SizedBox(height: 4),
          Text(value,
              style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w900,
                  fontSize: 22)),
          Text(label,
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.75),
                  fontSize: 10)),
        ],
      ),
    );
  }

  Widget _divider() => Container(
        width: 1,
        height: 36,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        color: Colors.white.withValues(alpha: 0.18),
      );

  Widget _badge(_Achievement a) {
    return Container(
      width: 92,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: a.unlocked
            ? Colors.white.withValues(alpha: 0.15)
            : Colors.black.withValues(alpha: 0.20),
        border: Border.all(
            color: a.unlocked
                ? Colors.white.withValues(alpha: 0.3)
                : Colors.white.withValues(alpha: 0.10)),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(
            a.icon,
            color: a.unlocked ? Colors.white : Colors.white.withValues(alpha: 0.35),
            size: 20,
          ),
          const SizedBox(height: 2),
          Text(
            a.label,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 9,
              fontWeight: FontWeight.w700,
              color: a.unlocked ? Colors.white : Colors.white.withValues(alpha: 0.55),
            ),
          ),
          Text(
            a.value,
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              fontSize: 8,
              color: a.unlocked
                  ? Colors.white.withValues(alpha: 0.85)
                  : Colors.white.withValues(alpha: 0.4),
            ),
          ),
        ],
      ),
    );
  }
}

class _DayAcc {
  int total = 0;
  int forbidden = 0;
}
