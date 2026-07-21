import 'dart:typed_data';
import 'dart:ui' as ui;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:fl_chart/fl_chart.dart';

import '../models/trade.dart';
import '../theme.dart';

class ShareCard extends StatelessWidget {
  final DisciplineStats stats;
  final List<Trade> trades;
  final String? username;

  const ShareCard({
    super.key,
    required this.stats,
    required this.trades,
    this.username,
  });

  List<FlSpot> _equity() {
    final closed = trades
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

  @override
  Widget build(BuildContext context) {
    final spots = _equity();
    final last = spots.isEmpty ? 0 : spots.last.y;
    final color = last >= 0 ? AppColors.success : AppColors.danger;
    return Container(
      width: 600,
      height: 400,
      padding: const EdgeInsets.all(28),
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF14171F), Color(0xFF0A0B12)],
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              width: 40,
              height: 40,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [AppColors.primary, AppColors.primaryDeep],
                ),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.shield, color: Colors.white, size: 22),
            ),
            const SizedBox(width: 12),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('AI Risk & Discipline',
                    style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.w800,
                        fontSize: 18)),
                Text('@RiskGuradBot',
                    style: TextStyle(color: AppColors.textMuted, fontSize: 12)),
              ],
            ),
            const Spacer(),
            if (username != null)
              Text('@$username',
                  style: const TextStyle(
                      color: AppColors.textSecondary, fontSize: 13)),
          ]),
          const SizedBox(height: 22),
          Text('My result',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.55),
                fontSize: 12,
                letterSpacing: 1.2,
              )),
          const SizedBox(height: 4),
          Text(
            '${last >= 0 ? '+' : ''}${last.toStringAsFixed(2)}%',
            style: TextStyle(
                color: color, fontSize: 56, fontWeight: FontWeight.w900),
          ),
          const SizedBox(height: 18),
          SizedBox(
            height: 130,
            child: spots.length <= 1
                ? const Center(
                    child: Text('Build up history — a chart will appear',
                        style: TextStyle(color: AppColors.textMuted)),
                  )
                : LineChart(
                    LineChartData(
                      gridData: const FlGridData(show: false),
                      borderData: FlBorderData(show: false),
                      titlesData: const FlTitlesData(
                        leftTitles:
                            AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        bottomTitles:
                            AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        rightTitles:
                            AxisTitles(sideTitles: SideTitles(showTitles: false)),
                        topTitles:
                            AxisTitles(sideTitles: SideTitles(showTitles: false)),
                      ),
                      lineBarsData: [
                        LineChartBarData(
                          spots: spots,
                          isCurved: true,
                          color: color,
                          barWidth: 3,
                          dotData: const FlDotData(show: false),
                          belowBarData: BarAreaData(
                            show: true,
                            gradient: LinearGradient(
                              begin: Alignment.topCenter,
                              end: Alignment.bottomCenter,
                              colors: [
                                color.withValues(alpha: 0.4),
                                color.withValues(alpha: 0.0),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
          ),
          const SizedBox(height: 18),
          Row(children: [
            _stat('Win-rate', '${stats.winRatePct.toStringAsFixed(0)}%'),
            const SizedBox(width: 22),
            _stat('Trades', '${stats.closed}'),
            const SizedBox(width: 22),
            _stat('Discipline',
                '${stats.total == 0 ? 0 : (stats.allowed * 100 / stats.total).toStringAsFixed(0)}%'),
            const Spacer(),
            const Text('Risk Officer kept the account from blowing up.',
                style: TextStyle(
                    color: AppColors.textMuted,
                    fontSize: 11,
                    fontStyle: FontStyle.italic)),
          ]),
        ],
      ),
    );
  }

  Widget _stat(String label, String value) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label,
            style:
                const TextStyle(color: AppColors.textMuted, fontSize: 11)),
        Text(value,
            style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w800)),
      ],
    );
  }
}

Future<Uint8List?> renderShareCardToPng(GlobalKey boundaryKey) async {
  final boundary =
      boundaryKey.currentContext?.findRenderObject() as RenderRepaintBoundary?;
  if (boundary == null) return null;
  final image = await boundary.toImage(pixelRatio: 2.0);
  final byteData = await image.toByteData(format: ui.ImageByteFormat.png);
  return byteData?.buffer.asUint8List();
}

Future<void> downloadPng(
  Uint8List bytes, {
  String filename = 'risk-share.png',
}) async {
  if (!kIsWeb) return;
}
