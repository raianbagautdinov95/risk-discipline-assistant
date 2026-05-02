class MarketSignal {
  final String symbol;
  final String action;
  final double confidence;
  final double entry;
  final double stopLoss;
  final double takeProfit;
  final double riskReward;
  final String trendOneHour;
  final List<String> reasons;
  final int timestamp;
  final String status;
  final String? closedAt;
  final double? pnlR;
  final String? closeReason;

  MarketSignal({
    required this.symbol,
    required this.action,
    required this.confidence,
    required this.entry,
    required this.stopLoss,
    required this.takeProfit,
    required this.riskReward,
    required this.trendOneHour,
    required this.reasons,
    required this.timestamp,
    this.status = 'NEW',
    this.closedAt,
    this.pnlR,
    this.closeReason,
  });

  factory MarketSignal.fromJson(Map<String, dynamic> j) => MarketSignal(
        symbol: j['symbol'] ?? '',
        action: j['action'] ?? 'HOLD',
        confidence: (j['confidence'] ?? 0).toDouble(),
        entry: (j['entry'] ?? 0).toDouble(),
        stopLoss: (j['stop_loss'] ?? 0).toDouble(),
        takeProfit: (j['take_profit'] ?? 0).toDouble(),
        riskReward: (j['risk_reward'] ?? 0).toDouble(),
        trendOneHour: j['trend_1h'] ?? 'UNKNOWN',
        reasons: List<String>.from(j['reasons'] ?? const []),
        timestamp: (j['timestamp'] is int)
            ? j['timestamp']
            : ((j['signal_timestamp'] ?? 0) as num).toInt(),
        status: j['status'] ?? 'NEW',
        closedAt: j['closed_at'],
        pnlR: (j['pnl_r'] as num?)?.toDouble(),
        closeReason: j['close_reason'],
      );

  bool get isLong => action == 'BUY';
  bool get isShort => action == 'SELL';
  bool get isHold => action == 'HOLD';

  String get directionForDiscipline => isLong ? 'long' : 'short';
  String get pairForDiscipline => symbol.replaceAll('-', '/');
}
