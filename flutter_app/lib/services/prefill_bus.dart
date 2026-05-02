import 'package:flutter/foundation.dart';

class TradePrefill {
  final String pair;
  final String direction;
  final double entryPrice;
  final double? stopLoss;
  final double? takeProfit;

  const TradePrefill({
    required this.pair,
    required this.direction,
    required this.entryPrice,
    this.stopLoss,
    this.takeProfit,
  });
}

final ValueNotifier<TradePrefill?> tradePrefillBus = ValueNotifier(null);
