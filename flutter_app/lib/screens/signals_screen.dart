import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/market_signal.dart';
import '../services/api_service.dart';
import '../services/prefill_bus.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/premium.dart';
import '../widgets/skeletons.dart';

class SignalsScreen extends StatefulWidget {
  final ValueChanged<int> onSwitchTab;
  const SignalsScreen({super.key, required this.onSwitchTab});

  @override
  State<SignalsScreen> createState() => _SignalsScreenState();
}

class _SignalsScreenState extends State<SignalsScreen> {
  final _api = SignalApiService();
  final _df = DateFormat('dd.MM HH:mm');

  bool _loading = true;
  bool _scanning = false;
  String? _error;
  List<MarketSignal> _signals = [];

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
    try {
      _signals = await _api.getActive();
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _scan() async {
    setState(() {
      _scanning = true;
      _error = null;
    });
    try {
      _signals = await _api.scanNow();
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) setState(() => _scanning = false);
    }
  }

  void _sendToCheck(MarketSignal s) {
    tradePrefillBus.value = TradePrefill(
      pair: s.pairForDiscipline,
      direction: s.directionForDiscipline,
      entryPrice: s.entry,
      stopLoss: s.stopLoss,
      takeProfit: s.takeProfit,
    );
    widget.onSwitchTab(1);
  }

  @override
  Widget build(BuildContext context) {
    final body = _loading
        ? const JournalSkeleton(count: 3)
        : _error != null
            ? HintState(
                icon: Icons.cloud_off,
                title: 'Сигнал-бот недоступен',
                subtitle:
                    'Проверь, что он запущен:\nuvicorn api:app --port 8765\n\n$_error',
                action: FilledButton.icon(
                  onPressed: _load,
                  icon: const Icon(Icons.refresh),
                  label: const Text('Повторить'),
                ),
              )
            : _signals.isEmpty
                ? HintState(
                    icon: Icons.satellite_alt,
                    title: 'Активных сигналов нет',
                    subtitle:
                        'Сканер работает в фоне каждые 15 минут.\nИли запусти полный скан прямо сейчас.',
                    action: FilledButton.icon(
                      onPressed: _scanning ? null : _scan,
                      icon: _scanning
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child:
                                  CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Icon(Icons.refresh),
                      label: Text(_scanning ? 'Сканирую...' : 'Скан рынка'),
                    ),
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(12, 12, 12, 96),
                      itemCount: _signals.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (_, i) => StaggeredFadeIn(
                        index: i,
                        child: HoverCard(
                          child: _SignalCard(
                            signal: _signals[i], onCheck: _sendToCheck),
                        ),
                      ),
                    ),
                  );
    return Scaffold(
      body: body,
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _scanning ? null : _scan,
        icon: _scanning
            ? const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                    strokeWidth: 2, color: Colors.white),
              )
            : const Icon(Icons.radar),
        label: Text(_scanning ? 'Сканирую...' : 'Скан рынка'),
      ),
    );
  }
}

class _SignalCard extends StatelessWidget {
  final MarketSignal signal;
  final ValueChanged<MarketSignal> onCheck;
  const _SignalCard({required this.signal, required this.onCheck});

  Color get _color => signal.isLong
      ? AppColors.success
      : signal.isShort
          ? AppColors.danger
          : AppColors.textMuted;

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd.MM HH:mm');
    final confPct =
        (signal.confidence > 1 ? signal.confidence : signal.confidence * 100)
            .clamp(0.0, 100.0);

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: _color.withValues(alpha: 0.4), width: 1.5),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [
          BoxShadow(
            color: _color.withValues(alpha: 0.08),
            blurRadius: 24,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Row(children: [
                  Text(
                    signal.symbol,
                    style: const TextStyle(
                      fontWeight: FontWeight.w800,
                      fontSize: 20,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(width: 10),
                  ActionBadge(action: signal.action),
                ]),
              ),
              if (signal.timestamp > 0)
                Text(
                  df.format(DateTime.fromMillisecondsSinceEpoch(
                      signal.timestamp * 1000)),
                  style: const TextStyle(
                      fontSize: 11, color: AppColors.textMuted),
                ),
            ],
          ),
          const SizedBox(height: 12),

          Row(children: [
            const Icon(Icons.psychology_outlined,
                size: 14, color: AppColors.textSecondary),
            const SizedBox(width: 4),
            const Text('confidence',
                style: TextStyle(
                    fontSize: 11, color: AppColors.textSecondary)),
            const SizedBox(width: 8),
            Expanded(
                child: ConfidenceBar(value0to1: confPct / 100, color: _color)),
            const SizedBox(width: 8),
            Text('${confPct.toStringAsFixed(0)}%',
                style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: _color)),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            const Icon(Icons.trending_up,
                size: 14, color: AppColors.textSecondary),
            const SizedBox(width: 4),
            Text('1H тренд: ${signal.trendOneHour}',
                style: const TextStyle(
                    fontSize: 11, color: AppColors.textSecondary)),
          ]),
          const SizedBox(height: 14),

          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              PricePill(
                label: 'Entry',
                value: signal.entry.toString(),
                color: AppColors.info,
                icon: Icons.flag_outlined,
              ),
              PricePill(
                label: 'SL',
                value: signal.stopLoss.toString(),
                color: AppColors.danger,
                icon: Icons.shield_outlined,
              ),
              PricePill(
                label: 'TP',
                value: signal.takeProfit.toString(),
                color: AppColors.success,
                icon: Icons.flag,
              ),
              PricePill(
                label: 'R:R',
                value: signal.riskReward.toStringAsFixed(2),
                color: AppColors.warn,
                icon: Icons.balance,
              ),
            ],
          ),

          if (signal.reasons.isNotEmpty) ...[
            const SizedBox(height: 14),
            Wrap(
              spacing: 6,
              runSpacing: 6,
              children: [
                for (final r in signal.reasons.take(4))
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 4),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceAlt,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    child: Text(r,
                        style: const TextStyle(
                            fontSize: 11, color: AppColors.textSecondary)),
                  ),
              ],
            ),
          ],

          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                backgroundColor: _color,
                padding: const EdgeInsets.symmetric(vertical: 14),
              ),
              onPressed: () => onCheck(signal),
              icon: const Icon(Icons.shield),
              label: const Text(
                'Проверить дисциплину',
                style: TextStyle(
                    fontWeight: FontWeight.w700, letterSpacing: 0.3),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
