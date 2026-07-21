import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../models/trade.dart';
import '../services/api_service.dart';
import '../services/prefill_bus.dart';
import '../theme.dart';
import '../widgets/common.dart';

class TradeDetailScreen extends StatelessWidget {
  final Trade trade;
  final int telegramId;
  final VoidCallback? onClosed;
  final VoidCallback? onRepeat;

  const TradeDetailScreen({
    super.key,
    required this.trade,
    required this.telegramId,
    this.onClosed,
    this.onRepeat,
  });

  Color get _color => switch (trade.decision) {
        'ALLOWED' => AppColors.success,
        'FORBIDDEN' => AppColors.danger,
        _ => AppColors.warn,
      };

  Color get _outcomeColor => switch (trade.outcome) {
        'WIN' => AppColors.success,
        'LOSS' => AppColors.danger,
        'BREAKEVEN' => AppColors.textSecondary,
        'CANCELED' => AppColors.textMuted,
        _ => AppColors.warn,
      };

  String get _outcomeLabel => switch (trade.outcome) {
        'WIN' => '✅ WIN',
        'LOSS' => '❌ LOSS',
        'BREAKEVEN' => '⚖️ BREAKEVEN',
        'CANCELED' => '🚫 CANCELED',
        _ => '⏳ Open',
      };

  void _repeat(BuildContext context) {
    tradePrefillBus.value = TradePrefill(
      pair: trade.pair,
      direction: trade.direction,
      entryPrice: trade.entryPrice,
      stopLoss: trade.stopLoss,
      takeProfit: trade.takeProfit,
    );
    Navigator.of(context).pop();
    onRepeat?.call();
  }

  Future<void> _showCloseDialog(BuildContext context) async {
    final result = await showDialog<CloseTradePayload>(
      context: context,
      builder: (_) => _CloseTradeDialog(trade: trade),
    );
    if (result == null) return;
    try {
      await ApiService().closeTrade(telegramId, trade.id, result);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Trade #${trade.id}: ${result.outcome}')),
      );
      Navigator.of(context).pop();
      onClosed?.call();
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  Widget _section(
      {required Widget header, required Widget child, EdgeInsets? margin}) {
    return Container(
      margin: margin ?? const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [header, const SizedBox(height: 12), child],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd.MM.yyyy HH:mm');
    final t = trade;
    final hasSL = t.stopLoss != null;
    final hasTP = t.takeProfit != null;

    return Scaffold(
      appBar: AppBar(title: Text('#${t.id} • ${t.pair}')),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 96),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  _color.withValues(alpha: 0.30),
                  _color.withValues(alpha: 0.08),
                ],
              ),
              border: Border.all(color: _color, width: 1.5),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: _color,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      t.decisionRu,
                      style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w800,
                          fontSize: 12,
                          letterSpacing: 0.6),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Container(
                    padding: const EdgeInsets.symmetric(
                        horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                      color: _outcomeColor.withValues(alpha: 0.18),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(_outcomeLabel,
                        style: TextStyle(
                            color: _outcomeColor,
                            fontWeight: FontWeight.w700,
                            fontSize: 11)),
                  ),
                  const Spacer(),
                  Text('${t.score}/10',
                      style: TextStyle(
                          color: _color,
                          fontWeight: FontWeight.w900,
                          fontSize: 22)),
                ]),
                const SizedBox(height: 10),
                Row(children: [
                  Icon(
                      t.isLong ? Icons.trending_up : Icons.trending_down,
                      color: _color,
                      size: 20),
                  const SizedBox(width: 6),
                  Text(t.direction.toUpperCase(),
                      style: TextStyle(
                          color: _color,
                          fontWeight: FontWeight.w700,
                          fontSize: 14)),
                  const SizedBox(width: 8),
                  Text('• x${t.leverage}',
                      style: const TextStyle(fontSize: 13)),
                  const SizedBox(width: 8),
                  Text('• ${df.format(t.createdAt)}',
                      style: const TextStyle(
                          fontSize: 11, color: AppColors.textMuted)),
                ]),
                if (t.pnlPercent != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    '${t.pnlPercent! >= 0 ? '+' : ''}${t.pnlPercent!.toStringAsFixed(2)}%',
                    style: TextStyle(
                        color: _outcomeColor,
                        fontWeight: FontWeight.w900,
                        fontSize: 28),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 14),

          _section(
            header: const SectionHeader(
              icon: Icons.show_chart,
              title: 'Prices',
              color: AppColors.info,
            ),
            child: Wrap(spacing: 8, runSpacing: 8, children: [
              PricePill(
                label: 'Entry',
                value: t.entryPrice.toString(),
                color: AppColors.info,
                icon: Icons.flag_outlined,
              ),
              if (hasSL)
                PricePill(
                  label: 'SL',
                  value: t.stopLoss!.toString(),
                  color: AppColors.danger,
                  icon: Icons.shield_outlined,
                ),
              if (hasTP)
                PricePill(
                  label: 'TP',
                  value: t.takeProfit!.toString(),
                  color: AppColors.success,
                  icon: Icons.flag,
                ),
              if (t.exitPrice != null)
                PricePill(
                  label: 'Exit',
                  value: t.exitPrice!.toString(),
                  color: _outcomeColor,
                  icon: Icons.exit_to_app,
                ),
              if (t.rrRatio != null)
                PricePill(
                  label: 'R:R',
                  value: t.rrRatio!.toStringAsFixed(2),
                  color: AppColors.warn,
                  icon: Icons.balance,
                ),
            ]),
          ),

          _section(
            header: const SectionHeader(
              icon: Icons.shield,
              title: 'Risk',
              color: AppColors.warn,
            ),
            child: Wrap(spacing: 8, runSpacing: 8, children: [
              PricePill(
                label: 'Deposit',
                value: '${t.deposit.toStringAsFixed(2)} \$',
                color: AppColors.success,
              ),
              PricePill(
                label: 'Risk',
                value: '${t.riskPercent}%',
                color: AppColors.warn,
              ),
              PricePill(
                label: 'Leverage',
                value: 'x${t.leverage}',
                color: t.leverage > 5 ? AppColors.danger : AppColors.info,
              ),
            ]),
          ),

          if ((t.reason ?? '').isNotEmpty ||
              (t.setup ?? '').isNotEmpty ||
              (t.emotion ?? '').isNotEmpty)
            _section(
              header: const SectionHeader(
                icon: Icons.psychology,
                title: 'Psychology and setup',
                color: AppColors.primary,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if ((t.reason ?? '').isNotEmpty)
                    _meta('Reason', t.reason!),
                  if ((t.setup ?? '').isNotEmpty)
                    _meta('Setup', t.setup!),
                  if ((t.emotion ?? '').isNotEmpty)
                    _meta('Emotion', t.emotion!),
                ],
              ),
            ),

          if ((t.forbidReasons ?? '').isNotEmpty)
            _section(
              header: const SectionHeader(
                icon: Icons.warning_rounded,
                title: 'Rule violations',
                color: AppColors.danger,
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (final reason in t.forbidReasons!.split('|'))
                    if (reason.trim().isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Row(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const Icon(Icons.fiber_manual_record,
                                  size: 8, color: AppColors.danger),
                              const SizedBox(width: 8),
                              Expanded(child: Text(reason.trim())),
                            ]),
                      ),
                ],
              ),
            ),

          if ((t.officerSummary ?? '').isNotEmpty)
            _section(
              header: const SectionHeader(
                icon: Icons.policy,
                title: 'Risk Officer',
                color: AppColors.danger,
              ),
              child: Text(t.officerSummary!),
            ),
          if ((t.coachSummary ?? '').isNotEmpty)
            _section(
              header: const SectionHeader(
                icon: Icons.school,
                title: 'Coach',
                color: AppColors.primary,
              ),
              child: Text(t.coachSummary!),
            ),

          if ((t.notes ?? '').isNotEmpty)
            _section(
              header: const SectionHeader(
                icon: Icons.sticky_note_2,
                title: 'Notes',
                color: AppColors.info,
              ),
              child: Text(t.notes!),
            ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                  foregroundColor: _color,
                  side: BorderSide(color: _color, width: 1.4),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: () => _repeat(context),
                icon: const Icon(Icons.replay, size: 18),
                label: const Text('Repeat'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: t.isClosed ? AppColors.surfaceAlt : _color,
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(10)),
                ),
                onPressed: t.isClosed
                    ? null
                    : () => _showCloseDialog(context),
                icon: const Icon(Icons.task_alt, size: 18),
                label: Text(t.isClosed ? 'Already closed' : 'Close trade'),
              ),
            ),
          ]),
        ),
      ),
    );
  }

  Widget _meta(String label, String value) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: const TextStyle(
                  color: AppColors.textMuted,
                  fontSize: 11,
                  fontWeight: FontWeight.w500)),
          Text(value, style: const TextStyle(fontSize: 14)),
        ],
      ),
    );
  }
}

class _CloseTradeDialog extends StatefulWidget {
  final Trade trade;
  const _CloseTradeDialog({required this.trade});

  @override
  State<_CloseTradeDialog> createState() => _CloseTradeDialogState();
}

class _CloseTradeDialogState extends State<_CloseTradeDialog> {
  String _outcome = 'WIN';
  final _pnl = TextEditingController();
  final _exit = TextEditingController();
  final _notes = TextEditingController();

  Widget _chip(String value, String icon, Color color) {
    final selected = _outcome == value;
    return ChoiceChip(
      label: Text('$icon $value'),
      selected: selected,
      onSelected: (_) => setState(() => _outcome = value),
      selectedColor: color.withValues(alpha: 0.25),
      labelStyle: TextStyle(
          color: selected ? color : AppColors.textPrimary,
          fontWeight: FontWeight.bold),
    );
  }

  @override
  Widget build(BuildContext context) {
    final t = widget.trade;
    return AlertDialog(
      title: Text('Close #${t.id}  ${t.pair}'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text('Outcome:',
                style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              children: [
                _chip('WIN', '✅', AppColors.success),
                _chip('LOSS', '❌', AppColors.danger),
                _chip('BREAKEVEN', '⚖️', AppColors.textSecondary),
                _chip('CANCELED', '🚫', AppColors.textMuted),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pnl,
              keyboardType: TextInputType.number,
              decoration:
                  const InputDecoration(labelText: 'P&L, % (optional)'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _exit,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                  labelText: 'Exit price (optional)'),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _notes,
              maxLines: 2,
              decoration: const InputDecoration(
                  labelText: 'Notes (optional)'),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            final pnl =
                double.tryParse(_pnl.text.replaceAll(',', '.').trim());
            final exit =
                double.tryParse(_exit.text.replaceAll(',', '.').trim());
            Navigator.pop(
              context,
              CloseTradePayload(
                outcome: _outcome,
                pnlPercent: pnl,
                exitPrice: exit,
                notes: _notes.text.trim().isEmpty
                    ? null
                    : _notes.text.trim(),
              ),
            );
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}
