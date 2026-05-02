import 'dart:math';

import '../models/trade.dart';

class DemoData {
  static List<Trade> trades({int count = 30}) {
    final rng = Random(42);
    final now = DateTime.now();
    final pairs = const [
      'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT',
      'AVAX/USDT', 'LINK/USDT',
    ];
    final reasons = const [
      'Сделка без stop-loss запрещена.',
      'Риск 2.5% превышает лимит 1.0% на сделку.',
      'R:R = 1.4 ниже минимума 1:2.',
      'Плечо x10 превышает лимит x5.',
      'FOMO в эмоциях.',
    ];

    final list = <Trade>[];
    for (var i = 0; i < count; i++) {
      final days = count - i;
      final created = now.subtract(Duration(days: days, hours: rng.nextInt(8)));

      final r = rng.nextDouble();
      final decision = r < 0.6 ? 'ALLOWED' : (r < 0.9 ? 'FORBIDDEN' : 'WAIT');

      final pair = pairs[rng.nextInt(pairs.length)];
      final isLong = rng.nextBool();
      final entry = 100.0 + rng.nextDouble() * 100; // synthetic price

      double? sl, tp, rr;
      if (decision != 'FORBIDDEN' || rng.nextBool()) {
        // Most allowed/wait have SL/TP
        final slDist = entry * 0.01 * (0.5 + rng.nextDouble() * 1.5);
        final tpDist = slDist * (1.5 + rng.nextDouble() * 2.5);
        sl = isLong ? entry - slDist : entry + slDist;
        tp = isLong ? entry + tpDist : entry - tpDist;
        rr = double.parse((tpDist / slDist).toStringAsFixed(2));
      }

      final risk = double.parse((0.5 + rng.nextDouble() * 1.5).toStringAsFixed(2));
      final score = decision == 'ALLOWED'
          ? 5.5 + rng.nextDouble() * 4
          : (decision == 'WAIT' ? 4.0 + rng.nextDouble() * 2 : rng.nextDouble() * 3);

      // Outcome only for allowed older than 1 day; ~58% win-rate.
      String outcome = 'NONE';
      double? pnl;
      DateTime? closedAt;
      if (decision == 'ALLOWED' && days > 1) {
        final win = rng.nextDouble() < 0.58;
        outcome = win ? 'WIN' : 'LOSS';
        // P&L is a function of R: win earns ~rr*risk, loss = -risk
        pnl = win
            ? double.parse(((rr ?? 2) * risk * (0.85 + rng.nextDouble() * 0.3))
                .toStringAsFixed(2))
            : double.parse((-risk * (0.85 + rng.nextDouble() * 0.3))
                .toStringAsFixed(2));
        closedAt = created.add(Duration(hours: 4 + rng.nextInt(12)));
      }

      list.add(Trade(
        id: i + 1,
        pair: pair,
        direction: isLong ? 'long' : 'short',
        entryPrice: double.parse(entry.toStringAsFixed(2)),
        stopLoss: sl == null ? null : double.parse(sl.toStringAsFixed(2)),
        takeProfit: tp == null ? null : double.parse(tp.toStringAsFixed(2)),
        leverage: 1 + rng.nextInt(5),
        riskPercent: risk,
        decision: decision,
        score: double.parse(score.toStringAsFixed(1)),
        rrRatio: rr,
        outcome: outcome,
        pnlPercent: pnl,
        exitPrice: null,
        closedAt: closedAt,
        notes: null,
        deposit: 1000,
        reason: 'demo trade',
        setup: 'breakout',
        emotion: 'спокоен',
        forbidReasons: decision == 'FORBIDDEN'
            ? reasons[rng.nextInt(reasons.length)]
            : null,
        coachSummary: null,
        officerSummary: null,
        createdAt: created,
      ));
    }

    // Sort by created_at desc to mimic API ordering.
    list.sort((a, b) => b.createdAt.compareTo(a.createdAt));
    return list;
  }

  /// Aggregate stats matching the trades() above.
  static DisciplineStats stats({List<Trade>? from}) {
    final t = from ?? trades();
    final allowed = t.where((x) => x.isAllowed).length;
    final forbidden = t.where((x) => x.isForbidden).length;
    final wait = t.where((x) => x.isWait).length;
    final closed = t.where((x) => x.isClosed).toList();
    final wins = closed.where((x) => x.isWin).length;
    final losses = closed.where((x) => x.isLoss).length;
    final breakevens = closed.where((x) => x.outcome == 'BREAKEVEN').length;

    final pnlValues =
        closed.map((x) => x.pnlPercent ?? 0).toList(growable: false);
    final totalPnl = pnlValues.fold<double>(0, (a, b) => a + b);
    final avgPnl = pnlValues.isEmpty ? 0.0 : totalPnl / pnlValues.length;
    final rr = t
        .where((x) => x.rrRatio != null)
        .map((x) => x.rrRatio!)
        .toList(growable: false);
    final avgRr = rr.isEmpty
        ? 0.0
        : double.parse((rr.fold<double>(0, (a, b) => a + b) / rr.length)
            .toStringAsFixed(2));
    final avgRisk = t.isEmpty
        ? 0.0
        : double.parse((t.fold<double>(0, (a, x) => a + x.riskPercent) / t.length)
            .toStringAsFixed(2));

    return DisciplineStats(
      total: t.length,
      allowed: allowed,
      forbidden: forbidden,
      wait: wait,
      avgRr: avgRr,
      avgRisk: avgRisk,
      commonForbidReasons: const [
        MapEntry('Риск выше лимита', 4),
        MapEntry('Нет stop-loss', 3),
        MapEntry('R:R ниже минимума', 2),
        MapEntry('FOMO в эмоциях', 1),
      ],
      closed: closed.length,
      wins: wins,
      losses: losses,
      breakevens: breakevens,
      winRatePct: (wins + losses) == 0
          ? 0
          : double.parse((wins * 100 / (wins + losses)).toStringAsFixed(1)),
      avgPnlPercent: double.parse(avgPnl.toStringAsFixed(2)),
      totalPnlPercent: double.parse(totalPnl.toStringAsFixed(2)),
    );
  }
}
