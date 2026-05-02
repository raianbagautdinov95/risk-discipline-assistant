class Trade {
  final int id;
  final String pair;
  final String direction;
  final double entryPrice;
  final double? stopLoss;
  final double? takeProfit;
  final int leverage;
  final double riskPercent;
  final String decision;
  final double score;
  final double? rrRatio;
  final String outcome;
  final double? pnlPercent;
  final double? exitPrice;
  final DateTime? closedAt;
  final String? notes;
  final double deposit;
  final String? reason;
  final String? setup;
  final String? emotion;
  final String? forbidReasons;
  final String? coachSummary;
  final String? officerSummary;
  final DateTime createdAt;

  Trade({
    required this.id,
    required this.pair,
    required this.direction,
    required this.entryPrice,
    required this.stopLoss,
    required this.takeProfit,
    required this.leverage,
    required this.riskPercent,
    required this.decision,
    required this.score,
    required this.rrRatio,
    required this.outcome,
    required this.pnlPercent,
    required this.exitPrice,
    required this.closedAt,
    required this.notes,
    required this.deposit,
    required this.reason,
    required this.setup,
    required this.emotion,
    required this.forbidReasons,
    required this.coachSummary,
    required this.officerSummary,
    required this.createdAt,
  });

  factory Trade.fromJson(Map<String, dynamic> j) => Trade(
        id: j['id'] ?? 0,
        pair: j['pair'] ?? '',
        direction: j['direction'] ?? 'long',
        entryPrice: (j['entry_price'] ?? 0).toDouble(),
        stopLoss: (j['stop_loss'] as num?)?.toDouble(),
        takeProfit: (j['take_profit'] as num?)?.toDouble(),
        leverage: j['leverage'] ?? 1,
        riskPercent: (j['risk_percent'] ?? 0).toDouble(),
        decision: j['decision'] ?? 'WAIT',
        score: (j['score'] ?? 0).toDouble(),
        rrRatio: (j['rr_ratio'] as num?)?.toDouble(),
        outcome: j['outcome'] ?? 'NONE',
        pnlPercent: (j['pnl_percent'] as num?)?.toDouble(),
        exitPrice: (j['exit_price'] as num?)?.toDouble(),
        closedAt:
            j['closed_at'] == null ? null : DateTime.tryParse(j['closed_at']),
        notes: j['notes'],
        deposit: (j['deposit'] ?? 0).toDouble(),
        reason: j['reason'],
        setup: j['setup'],
        emotion: j['emotion'],
        forbidReasons: j['forbid_reasons'],
        coachSummary: j['coach_summary'],
        officerSummary: j['officer_summary'],
        createdAt: DateTime.tryParse(j['created_at'] ?? '') ?? DateTime.now(),
      );

  bool get isLong => direction == 'long';
  bool get isAllowed => decision == 'ALLOWED';
  bool get isForbidden => decision == 'FORBIDDEN';
  bool get isWait => decision == 'WAIT';
  bool get isClosed => outcome != 'NONE';
  bool get isWin => outcome == 'WIN';
  bool get isLoss => outcome == 'LOSS';

  String get decisionRu {
    switch (decision) {
      case 'ALLOWED':
        return 'РАЗРЕШЕНО';
      case 'FORBIDDEN':
        return 'ЗАПРЕЩЕНО';
      case 'WAIT':
        return 'ЖДАТЬ';
      default:
        return decision;
    }
  }
}

class TradeRequest {
  final String pair;
  final String direction;
  final double entryPrice;
  final double? stopLoss;
  final double? takeProfit;
  final double deposit;
  final double riskPercent;
  final int leverage;
  final String? reason;
  final String? setup;
  final String? emotion;
  final double lossesToday;
  final int consecutiveLosses;

  TradeRequest({
    required this.pair,
    required this.direction,
    required this.entryPrice,
    this.stopLoss,
    this.takeProfit,
    required this.deposit,
    required this.riskPercent,
    this.leverage = 1,
    this.reason,
    this.setup,
    this.emotion,
    this.lossesToday = 0,
    this.consecutiveLosses = 0,
  });

  Map<String, dynamic> toJson() => {
        'pair': pair,
        'direction': direction,
        'entry_price': entryPrice,
        if (stopLoss != null) 'stop_loss': stopLoss,
        if (takeProfit != null) 'take_profit': takeProfit,
        'deposit': deposit,
        'risk_percent': riskPercent,
        'leverage': leverage,
        if (reason != null) 'reason': reason,
        if (setup != null) 'setup': setup,
        if (emotion != null) 'emotion': emotion,
        'losses_today': lossesToday,
        'consecutive_losses': consecutiveLosses,
      };
}

class TradeResponse {
  final String decision;
  final double score;
  final RiskCalc calc;
  final List<RuleViolation> violations;
  final CoachReport? coach;
  final OfficerReport? officer;
  final String recommendation;
  final String formattedMessage;
  final String disclaimer;

  TradeResponse({
    required this.decision,
    required this.score,
    required this.calc,
    required this.violations,
    required this.coach,
    required this.officer,
    required this.recommendation,
    required this.formattedMessage,
    required this.disclaimer,
  });

  factory TradeResponse.fromJson(Map<String, dynamic> j) => TradeResponse(
        decision: j['decision'] ?? 'WAIT',
        score: (j['score'] ?? 0).toDouble(),
        calc: RiskCalc.fromJson(j['calc'] ?? const {}),
        violations: ((j['violations'] ?? []) as List)
            .map((v) => RuleViolation.fromJson(v))
            .toList(),
        coach: j['coach'] == null ? null : CoachReport.fromJson(j['coach']),
        officer:
            j['officer'] == null ? null : OfficerReport.fromJson(j['officer']),
        recommendation: j['recommendation'] ?? '',
        formattedMessage: j['formatted_message'] ?? '',
        disclaimer: j['disclaimer'] ?? '',
      );

  String get decisionRu {
    switch (decision) {
      case 'ALLOWED':
        return 'РАЗРЕШЕНО';
      case 'FORBIDDEN':
        return 'ЗАПРЕЩЕНО';
      case 'WAIT':
        return 'ЖДАТЬ';
      default:
        return decision;
    }
  }
}

class RiskCalc {
  final double riskMoney;
  final double? slDistance;
  final double? tpDistance;
  final double? rrRatio;
  final double? positionSize;
  final double leveragedRisk;
  final bool leverageCritical;

  RiskCalc({
    required this.riskMoney,
    required this.slDistance,
    required this.tpDistance,
    required this.rrRatio,
    required this.positionSize,
    required this.leveragedRisk,
    required this.leverageCritical,
  });

  factory RiskCalc.fromJson(Map<String, dynamic> j) => RiskCalc(
        riskMoney: (j['risk_money'] ?? 0).toDouble(),
        slDistance: (j['sl_distance'] as num?)?.toDouble(),
        tpDistance: (j['tp_distance'] as num?)?.toDouble(),
        rrRatio: (j['rr_ratio'] as num?)?.toDouble(),
        positionSize: (j['position_size'] as num?)?.toDouble(),
        leveragedRisk: (j['leveraged_risk'] ?? 0).toDouble(),
        leverageCritical: j['leverage_critical'] ?? false,
      );
}

class RuleViolation {
  final String code;
  final String message;
  final bool blocking;

  RuleViolation({
    required this.code,
    required this.message,
    required this.blocking,
  });

  factory RuleViolation.fromJson(Map<String, dynamic> j) => RuleViolation(
        code: j['code'] ?? '',
        message: j['message'] ?? '',
        blocking: j['blocking'] ?? true,
      );
}

class CoachReport {
  final String summary;
  final List<String> pros;
  final List<String> cons;
  final String recommendation;

  CoachReport({
    required this.summary,
    required this.pros,
    required this.cons,
    required this.recommendation,
  });

  factory CoachReport.fromJson(Map<String, dynamic> j) => CoachReport(
        summary: j['summary'] ?? '',
        pros: List<String>.from(j['pros'] ?? const []),
        cons: List<String>.from(j['cons'] ?? const []),
        recommendation: j['recommendation'] ?? '',
      );
}

class OfficerReport {
  final String summary;
  final List<String> violations;
  final String decision;

  OfficerReport({
    required this.summary,
    required this.violations,
    required this.decision,
  });

  factory OfficerReport.fromJson(Map<String, dynamic> j) => OfficerReport(
        summary: j['summary'] ?? '',
        violations: List<String>.from(j['violations'] ?? const []),
        decision: j['decision'] ?? '',
      );
}

class DisciplineStats {
  final int total;
  final int allowed;
  final int forbidden;
  final int wait;
  final double avgRr;
  final double avgRisk;
  final List<MapEntry<String, int>> commonForbidReasons;
  final int closed;
  final int wins;
  final int losses;
  final int breakevens;
  final double winRatePct;
  final double avgPnlPercent;
  final double totalPnlPercent;

  DisciplineStats({
    required this.total,
    required this.allowed,
    required this.forbidden,
    required this.wait,
    required this.avgRr,
    required this.avgRisk,
    required this.commonForbidReasons,
    this.closed = 0,
    this.wins = 0,
    this.losses = 0,
    this.breakevens = 0,
    this.winRatePct = 0,
    this.avgPnlPercent = 0,
    this.totalPnlPercent = 0,
  });

  factory DisciplineStats.fromJson(Map<String, dynamic> j) {
    final raw = (j['common_forbid_reasons'] ?? []) as List;
    return DisciplineStats(
      total: j['total'] ?? 0,
      allowed: j['allowed'] ?? 0,
      forbidden: j['forbidden'] ?? 0,
      wait: j['wait'] ?? 0,
      avgRr: (j['avg_rr'] ?? 0).toDouble(),
      avgRisk: (j['avg_risk'] ?? 0).toDouble(),
      commonForbidReasons: raw.map((row) {
        final list = row as List;
        return MapEntry(
          list.isNotEmpty ? (list[0]?.toString() ?? '') : '',
          list.length > 1 ? (list[1] as num).toInt() : 0,
        );
      }).toList(),
      closed: j['closed'] ?? 0,
      wins: j['wins'] ?? 0,
      losses: j['losses'] ?? 0,
      breakevens: j['breakevens'] ?? 0,
      winRatePct: (j['win_rate_pct'] ?? 0).toDouble(),
      avgPnlPercent: (j['avg_pnl_percent'] ?? 0).toDouble(),
      totalPnlPercent: (j['total_pnl_percent'] ?? 0).toDouble(),
    );
  }
}

class CloseTradePayload {
  final String outcome;
  final double? pnlPercent;
  final double? exitPrice;
  final String? notes;

  const CloseTradePayload({
    required this.outcome,
    this.pnlPercent,
    this.exitPrice,
    this.notes,
  });

  Map<String, dynamic> toJson() => {
        'outcome': outcome,
        if (pnlPercent != null) 'pnl_percent': pnlPercent,
        if (exitPrice != null) 'exit_price': exitPrice,
        if (notes != null && notes!.isNotEmpty) 'notes': notes,
      };
}

class UserSettings {
  final double maxRiskPercent;
  final int maxLeverage;
  final double minRr;
  final double dailyLossLimit;

  UserSettings({
    required this.maxRiskPercent,
    required this.maxLeverage,
    required this.minRr,
    required this.dailyLossLimit,
  });

  factory UserSettings.fromJson(Map<String, dynamic> j) => UserSettings(
        maxRiskPercent: (j['max_risk_percent'] ?? 1.0).toDouble(),
        maxLeverage: (j['max_leverage'] ?? 5).toInt(),
        minRr: (j['min_rr'] ?? 2.0).toDouble(),
        dailyLossLimit: (j['daily_loss_limit'] ?? 2.0).toDouble(),
      );

  Map<String, dynamic> toJson() => {
        'max_risk_percent': maxRiskPercent,
        'max_leverage': maxLeverage,
        'min_rr': minRr,
        'daily_loss_limit': dailyLossLimit,
      };
}

class PositionCalcRequest {
  final double deposit;
  final double riskPercent;
  final double entryPrice;
  final double stopLoss;
  final int leverage;

  const PositionCalcRequest({
    required this.deposit,
    required this.riskPercent,
    required this.entryPrice,
    required this.stopLoss,
    this.leverage = 1,
  });

  Map<String, dynamic> toJson() => {
        'deposit': deposit,
        'risk_percent': riskPercent,
        'entry_price': entryPrice,
        'stop_loss': stopLoss,
        'leverage': leverage,
      };
}

class PositionCalcResult {
  final double riskMoney;
  final double slDistance;
  final double positionSizeUnits;
  final double positionValueUsdt;
  final int leverage;
  final double marginRequired;
  final double rrRequiredFor2x;

  PositionCalcResult({
    required this.riskMoney,
    required this.slDistance,
    required this.positionSizeUnits,
    required this.positionValueUsdt,
    required this.leverage,
    required this.marginRequired,
    required this.rrRequiredFor2x,
  });

  factory PositionCalcResult.fromJson(Map<String, dynamic> j) =>
      PositionCalcResult(
        riskMoney: (j['risk_money'] ?? 0).toDouble(),
        slDistance: (j['sl_distance'] ?? 0).toDouble(),
        positionSizeUnits: (j['position_size_units'] ?? 0).toDouble(),
        positionValueUsdt: (j['position_value_usdt'] ?? 0).toDouble(),
        leverage: (j['leverage'] ?? 1) as int,
        marginRequired: (j['margin_required'] ?? 0).toDouble(),
        rrRequiredFor2x: (j['rr_required_for_2x'] ?? 0).toDouble(),
      );
}
