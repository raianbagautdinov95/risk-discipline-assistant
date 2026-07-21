import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:intl/intl.dart';

import '../models/trade.dart';
import '../services/api_service.dart';
import '../services/user_store.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/premium.dart';
import '../widgets/skeletons.dart';
import 'trade_detail_screen.dart';

class JournalScreen extends StatefulWidget {
  /// Callback used by Trade Detail's "Repeat" — switches to Trade Check tab.
  final ValueChanged<int>? onSwitchTab;
  const JournalScreen({super.key, this.onSwitchTab});

  @override
  State<JournalScreen> createState() => _JournalScreenState();
}

enum JournalFilter { all, allowed, forbidden, wait, wins, losses, pending }

class _JournalScreenState extends State<JournalScreen> {
  final _api = ApiService();
  final _df = DateFormat('dd.MM HH:mm');
  final _searchCtrl = TextEditingController();
  bool _loading = true;
  String? _error;
  int? _tid;
  List<Trade> _trades = [];
  JournalFilter _filter = JournalFilter.all;
  String _query = '';

  List<Trade> get _filtered {
    Iterable<Trade> result = _trades;
    switch (_filter) {
      case JournalFilter.all:
        break;
      case JournalFilter.allowed:
        result = result.where((t) => t.isAllowed);
      case JournalFilter.forbidden:
        result = result.where((t) => t.isForbidden);
      case JournalFilter.wait:
        result = result.where((t) => t.isWait);
      case JournalFilter.wins:
        result = result.where((t) => t.isWin);
      case JournalFilter.losses:
        result = result.where((t) => t.isLoss);
      case JournalFilter.pending:
        result = result.where((t) => !t.isClosed && t.isAllowed);
    }
    if (_query.trim().isNotEmpty) {
      final q = _query.trim().toLowerCase();
      result = result.where((t) => t.pair.toLowerCase().contains(q));
    }
    return result.toList();
  }

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
      _tid = await UserStore.getTelegramId();
      if (_tid == null) {
        _trades = [];
        return;
      }
      _trades = await _api.getJournal(_tid!, limit: 100);
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Color _decisionColor(String d) => switch (d) {
        'ALLOWED' => Colors.green,
        'FORBIDDEN' => Colors.red,
        _ => Colors.orange,
      };

  Color _outcomeColor(String o) => switch (o) {
        'WIN' => Colors.green,
        'LOSS' => Colors.red,
        'BREAKEVEN' => Colors.blueGrey,
        'CANCELED' => Colors.grey,
        _ => Colors.amber,
      };

  String _outcomeIcon(String o) => switch (o) {
        'WIN' => '✅',
        'LOSS' => '❌',
        'BREAKEVEN' => '⚖️',
        'CANCELED' => '🚫',
        _ => '⏳',
      };

  Future<void> _showCloseDialog(Trade trade) async {
    final result = await showDialog<CloseTradePayload>(
      context: context,
      builder: (_) => _CloseTradeDialog(trade: trade),
    );
    if (result == null || _tid == null) return;
    try {
      await _api.closeTrade(_tid!, trade.id, result);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Trade #${trade.id} closed: ${result.outcome}')),
      );
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error: $e')),
      );
    }
  }

  Future<void> _openDetail(Trade t) async {
    if (_tid == null) return;
    await Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => TradeDetailScreen(
          trade: t,
          telegramId: _tid!,
          onClosed: _load,
          onRepeat: () => widget.onSwitchTab?.call(1),
        ),
      ),
    );
  }

  void _exportCsv() {
    if (_tid == null) return;
    final url = _api.exportCsvUrl(_tid!);
    Clipboard.setData(ClipboardData(text: url));
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('CSV link copied — open it in a new tab'),
        action: SnackBarAction(
          label: 'OK',
          onPressed: () {},
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const JournalSkeleton();
    if (_error != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error, color: Colors.red, size: 48),
              const SizedBox(height: 8),
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 12),
              FilledButton(onPressed: _load, child: const Text('Retry')),
            ],
          ),
        ),
      );
    }
    if (_tid == null) {
      return const HintState(
        icon: Icons.account_circle_outlined,
        title: 'Telegram ID not set',
        subtitle:
            'Go to "Settings" and enter your ID to see your journal.',
      );
    }
    if (_trades.isEmpty) {
      return const HintState(
        icon: Icons.history_edu,
        title: 'Journal is empty',
        subtitle: 'Run your first trade check — it will show up here.',
      );
    }
    final visible = _filtered;
    return Scaffold(
      body: Column(
        children: [
          _filterBar(),
          Expanded(
            child: visible.isEmpty
                ? const HintState(
                    icon: Icons.filter_alt_off,
                    title: 'Nothing matches the filter',
                    subtitle:
                        'Clear the filter or search to see all trades.',
                  )
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.separated(
                      padding:
                          const EdgeInsets.fromLTRB(12, 4, 12, 96),
                      itemCount: visible.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 10),
                      itemBuilder: (_, i) {
                        final t = visible[i];
                        return StaggeredFadeIn(
                          index: i,
                          child: HoverCard(
                            onTap: () => _openDetail(t),
                            child: _PremiumTradeCard(
                              trade: t,
                              onClose: () => _showCloseDialog(t),
                            ),
                          ),
                        );
                      },
                    ),
                  ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _exportCsv,
        icon: const Icon(Icons.download),
        label: const Text('Export CSV'),
      ),
    );
  }

  Widget _filterBar() {
    Widget chip(String label, JournalFilter f, {Color? color}) {
      final selected = _filter == f;
      final c = color ?? AppColors.primary;
      return Padding(
        padding: const EdgeInsets.only(right: 6),
        child: ChoiceChip(
          label: Text(label),
          selected: selected,
          onSelected: (_) => setState(() => _filter = f),
          backgroundColor: AppColors.surface,
          selectedColor: c.withValues(alpha: 0.2),
          side: BorderSide(
              color: selected ? c : AppColors.border, width: selected ? 1.2 : 1),
          labelStyle: TextStyle(
              color: selected ? c : AppColors.textSecondary,
              fontSize: 12,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(8),
          ),
        ),
      );
    }

    return Container(
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Column(
        children: [
          TextField(
            controller: _searchCtrl,
            onChanged: (v) => setState(() => _query = v),
            decoration: InputDecoration(
              prefixIcon: const Icon(Icons.search, size: 18),
              hintText: 'Search by pair (BTC, ETH)',
              isDense: true,
              suffixIcon: _query.isEmpty
                  ? null
                  : IconButton(
                      icon: const Icon(Icons.clear, size: 18),
                      onPressed: () {
                        _searchCtrl.clear();
                        setState(() => _query = '');
                      },
                    ),
            ),
          ),
          const SizedBox(height: 8),
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            child: Row(children: [
              chip('All ${_trades.length}', JournalFilter.all),
              chip('ALLOWED', JournalFilter.allowed,
                  color: AppColors.success),
              chip('FORBIDDEN', JournalFilter.forbidden,
                  color: AppColors.danger),
              chip('WAIT', JournalFilter.wait, color: AppColors.warn),
              chip('✅ WIN', JournalFilter.wins, color: AppColors.success),
              chip('❌ LOSS', JournalFilter.losses, color: AppColors.danger),
              chip('⏳ Open', JournalFilter.pending,
                  color: AppColors.warn),
            ]),
          ),
        ],
      ),
    );
  }
}

class _PremiumTradeCard extends StatelessWidget {
  final Trade trade;
  final VoidCallback onClose;

  const _PremiumTradeCard({required this.trade, required this.onClose});

  Color get _decisionColor => switch (trade.decision) {
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

  String get _outcomeIcon => switch (trade.outcome) {
        'WIN' => '✅',
        'LOSS' => '❌',
        'BREAKEVEN' => '⚖️',
        'CANCELED' => '🚫',
        _ => '⏳',
      };

  @override
  Widget build(BuildContext context) {
    final df = DateFormat('dd.MM HH:mm');
    final t = trade;
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border:
            Border.all(color: _decisionColor.withValues(alpha: 0.4), width: 1.2),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: _decisionColor.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                t.isLong ? Icons.trending_up : Icons.trending_down,
                color: _decisionColor,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Text(
                      t.pair,
                      style: const TextStyle(
                          fontWeight: FontWeight.w800, fontSize: 16),
                    ),
                    const SizedBox(width: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: _decisionColor.withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: Text(
                        '${t.direction.toUpperCase()} • x${t.leverage}',
                        style: TextStyle(
                            fontSize: 10,
                            color: _decisionColor,
                            fontWeight: FontWeight.w700),
                      ),
                    ),
                  ]),
                  Text(
                    '#${t.id}  •  ${df.format(t.createdAt)}',
                    style: const TextStyle(
                        fontSize: 11, color: AppColors.textMuted),
                  ),
                ],
              ),
            ),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: _decisionColor,
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                t.decisionRu,
                style: const TextStyle(
                    color: Colors.white,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.4),
              ),
            ),
          ]),

          const SizedBox(height: 10),

          Wrap(spacing: 6, runSpacing: 6, children: [
            PricePill(
              label: 'risk',
              value: '${t.riskPercent}%',
              color: AppColors.warn,
            ),
            PricePill(
              label: 'R:R',
              value: t.rrRatio?.toStringAsFixed(2) ?? '—',
              color: AppColors.info,
            ),
            PricePill(
              label: 'score',
              value: '${t.score}',
              color: AppColors.primary,
            ),
          ]),

          const SizedBox(height: 12),
          const Divider(height: 1),
          const SizedBox(height: 10),

          Row(children: [
            Text(_outcomeIcon, style: const TextStyle(fontSize: 18)),
            const SizedBox(width: 6),
            Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: _outcomeColor.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(6),
              ),
              child: Text(
                t.isClosed ? t.outcome : 'open',
                style: TextStyle(
                  color: _outcomeColor,
                  fontWeight: FontWeight.w700,
                  fontSize: 11,
                ),
              ),
            ),
            if (t.pnlPercent != null) ...[
              const SizedBox(width: 8),
              Text(
                '${t.pnlPercent! >= 0 ? '+' : ''}${t.pnlPercent!.toStringAsFixed(2)}%',
                style: TextStyle(
                  color: _outcomeColor,
                  fontWeight: FontWeight.w800,
                  fontSize: 14,
                ),
              ),
            ],
            const Spacer(),
            if (!t.isClosed)
              FilledButton.tonalIcon(
                style: FilledButton.styleFrom(
                  visualDensity: VisualDensity.compact,
                  backgroundColor:
                      _decisionColor.withValues(alpha: 0.18),
                  foregroundColor: _decisionColor,
                ),
                onPressed: onClose,
                icon: const Icon(Icons.task_alt, size: 14),
                label: const Text('Close'),
              ),
          ]),
        ],
      ),
    );
  }
}

/// Dialog to mark a trade as won/lost/breakeven and (optionally) save P&L %.
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
            const Text('Outcome:', style: TextStyle(fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Wrap(
              spacing: 6,
              children: [
                _chip('WIN', '✅', Colors.green),
                _chip('LOSS', '❌', Colors.red),
                _chip('BREAKEVEN', '⚖️', Colors.blueGrey),
                _chip('CANCELED', '🚫', Colors.grey),
              ],
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _pnl,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'P&L, % (e.g. 2.5 or -1.0)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _exit,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Exit price (optional)',
                border: OutlineInputBorder(),
              ),
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _notes,
              maxLines: 2,
              decoration: const InputDecoration(
                labelText: 'Notes (optional)',
                border: OutlineInputBorder(),
              ),
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
            final pnl = double.tryParse(_pnl.text.replaceAll(',', '.').trim());
            final exit =
                double.tryParse(_exit.text.replaceAll(',', '.').trim());
            Navigator.pop(
              context,
              CloseTradePayload(
                outcome: _outcome,
                pnlPercent: pnl,
                exitPrice: exit,
                notes: _notes.text.trim().isEmpty ? null : _notes.text.trim(),
              ),
            );
          },
          child: const Text('Save'),
        ),
      ],
    );
  }

  Widget _chip(String value, String icon, Color color) {
    final selected = _outcome == value;
    return ChoiceChip(
      label: Text('$icon $value'),
      selected: selected,
      onSelected: (_) => setState(() => _outcome = value),
      selectedColor: color.withValues(alpha: 0.25),
      labelStyle:
          TextStyle(color: selected ? color : Colors.black, fontWeight: FontWeight.bold),
    );
  }
}
