import 'dart:convert';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:http/http.dart' as http;

import '../models/market_signal.dart';
import '../models/trade.dart';

String _baseUrl(int port) {
  if (kIsWeb) return 'http://localhost:$port';
  try {
    if (Platform.isAndroid) return 'http://10.0.2.2:$port';
    return 'http://localhost:$port';
  } catch (_) {
    return 'http://localhost:$port';
  }
}

const Duration _kTimeout = Duration(seconds: 30);

Future<dynamic> _get(String url) async {
  final resp = await http.get(Uri.parse(url)).timeout(_kTimeout);
  if (resp.statusCode != 200) {
    throw Exception('API ${resp.statusCode}: ${resp.body}');
  }
  return jsonDecode(utf8.decode(resp.bodyBytes));
}

Future<dynamic> _post(String url, Map<String, dynamic> body) async {
  final resp = await http
      .post(
        Uri.parse(url),
        headers: const {'Content-Type': 'application/json; charset=utf-8'},
        body: jsonEncode(body),
      )
      .timeout(_kTimeout);
  if (resp.statusCode >= 400) {
    throw Exception('API ${resp.statusCode}: ${resp.body}');
  }
  return jsonDecode(utf8.decode(resp.bodyBytes));
}

Future<dynamic> _patch(String url, Map<String, dynamic> body) async {
  final resp = await http
      .patch(
        Uri.parse(url),
        headers: const {'Content-Type': 'application/json; charset=utf-8'},
        body: jsonEncode(body),
      )
      .timeout(_kTimeout);
  if (resp.statusCode >= 400) {
    throw Exception('API ${resp.statusCode}: ${resp.body}');
  }
  return jsonDecode(utf8.decode(resp.bodyBytes));
}

class ApiService {
  static const int apiPort = 8009;
  static String get baseUrl => _baseUrl(apiPort);

  Future<TradeResponse> checkTrade(int telegramId, TradeRequest req) async {
    final data = await _post(
      '$baseUrl/users/$telegramId/trades/check',
      req.toJson(),
    ) as Map<String, dynamic>;
    return TradeResponse.fromJson(data);
  }

  Future<List<Trade>> getJournal(int telegramId, {int limit = 50}) async {
    final data =
        await _get('$baseUrl/users/$telegramId/trades?limit=$limit') as List;
    return data
        .map((j) => Trade.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<DisciplineStats> getStats(int telegramId) async {
    final data = await _get('$baseUrl/users/$telegramId/stats')
        as Map<String, dynamic>;
    return DisciplineStats.fromJson(data);
  }

  Future<UserSettings> getSettings(int telegramId) async {
    final data = await _get('$baseUrl/users/$telegramId/settings')
        as Map<String, dynamic>;
    return UserSettings.fromJson(data);
  }

  Future<UserSettings> updateSettings(
    int telegramId,
    Map<String, dynamic> patch,
  ) async {
    final data = await _patch('$baseUrl/users/$telegramId/settings', patch)
        as Map<String, dynamic>;
    return UserSettings.fromJson(data);
  }

  Future<Trade> closeTrade(
    int telegramId,
    int tradeId,
    CloseTradePayload payload,
  ) async {
    final data = await _patch(
      '$baseUrl/users/$telegramId/trades/$tradeId/close',
      payload.toJson(),
    ) as Map<String, dynamic>;
    return Trade.fromJson(data);
  }

  String exportCsvUrl(int telegramId) =>
      '$baseUrl/users/$telegramId/trades/export.csv';

  Future<PositionCalcResult> calcPosition(PositionCalcRequest req) async {
    final data = await _post('$baseUrl/calc/position', req.toJson())
        as Map<String, dynamic>;
    return PositionCalcResult.fromJson(data);
  }

  Future<bool> healthCheck() async {
    try {
      final data = await _get('$baseUrl/health') as Map<String, dynamic>;
      return data['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }
}

class SignalApiService {
  static const int apiPort = 8765;
  static String get baseUrl => _baseUrl(apiPort);

  Future<List<MarketSignal>> getActive() async {
    final data = await _get('$baseUrl/signals/active') as List;
    return data
        .map((j) => MarketSignal.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<List<MarketSignal>> getHistory({int limit = 100}) async {
    final data =
        await _get('$baseUrl/signals/history?limit=$limit') as List;
    return data
        .map((j) => MarketSignal.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<List<MarketSignal>> scanNow() async {
    final data = await _get('$baseUrl/signals/scan') as List;
    return data
        .map((j) => MarketSignal.fromJson(j as Map<String, dynamic>))
        .toList();
  }

  Future<MarketSignal> analyzeSymbol(String symbol) async {
    final data = await _get('$baseUrl/signal/$symbol') as Map<String, dynamic>;
    return MarketSignal.fromJson(data);
  }

  Future<List<String>> getSymbols() async {
    final data = await _get('$baseUrl/symbols') as Map<String, dynamic>;
    return List<String>.from(data['symbols'] ?? const []);
  }

  Future<bool> healthCheck() async {
    try {
      final data = await _get('$baseUrl/health') as Map<String, dynamic>;
      return data['status'] == 'ok';
    } catch (_) {
      return false;
    }
  }
}
