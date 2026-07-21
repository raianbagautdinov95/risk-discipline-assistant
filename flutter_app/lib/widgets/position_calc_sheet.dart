import 'package:flutter/material.dart';

import '../models/trade.dart';
import '../services/api_service.dart';
import '../theme.dart';
import 'common.dart';

class PositionCalcSheet extends StatefulWidget {
  final double? entry;
  final double? stopLoss;
  final double? deposit;
  final double? riskPercent;
  final int? leverage;

  const PositionCalcSheet({
    super.key,
    this.entry,
    this.stopLoss,
    this.deposit,
    this.riskPercent,
    this.leverage,
  });

  static Future<void> show(BuildContext context,
      {double? entry,
      double? stopLoss,
      double? deposit,
      double? riskPercent,
      int? leverage}) {
    return showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: AppColors.bg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (_) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
        ),
        child: PositionCalcSheet(
          entry: entry,
          stopLoss: stopLoss,
          deposit: deposit,
          riskPercent: riskPercent,
          leverage: leverage,
        ),
      ),
    );
  }

  @override
  State<PositionCalcSheet> createState() => _PositionCalcSheetState();
}

class _PositionCalcSheetState extends State<PositionCalcSheet> {
  late final _deposit =
      TextEditingController(text: (widget.deposit ?? 1000).toString());
  late final _risk =
      TextEditingController(text: (widget.riskPercent ?? 1).toString());
  late final _entry =
      TextEditingController(text: widget.entry?.toString() ?? '');
  late final _sl =
      TextEditingController(text: widget.stopLoss?.toString() ?? '');
  late final _leverage =
      TextEditingController(text: (widget.leverage ?? 1).toString());

  final _api = ApiService();
  bool _busy = false;
  String? _error;
  PositionCalcResult? _result;

  double? _d(TextEditingController c) =>
      double.tryParse(c.text.trim().replaceAll(',', '.'));

  Future<void> _calc() async {
    final deposit = _d(_deposit);
    final risk = _d(_risk);
    final entry = _d(_entry);
    final sl = _d(_sl);
    final lev = int.tryParse(_leverage.text.trim()) ?? 1;
    if (deposit == null ||
        risk == null ||
        entry == null ||
        sl == null ||
        deposit <= 0 ||
        risk <= 0 ||
        entry <= 0 ||
        sl <= 0) {
      setState(() => _error = 'Fill in all 4 numbers.');
      return;
    }
    if (entry == sl) {
      setState(() => _error = 'Entry price and SL cannot be the same.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final res = await _api.calcPosition(PositionCalcRequest(
        deposit: deposit,
        riskPercent: risk,
        entryPrice: entry,
        stopLoss: sl,
        leverage: lev,
      ));
      setState(() => _result = res);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _input(TextEditingController c, String label, {String? suffix}) {
    return TextField(
      controller: c,
      keyboardType: TextInputType.number,
      decoration: InputDecoration(labelText: label, suffixText: suffix),
    );
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(20, 12, 20, 24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                margin: const EdgeInsets.only(bottom: 12),
                decoration: BoxDecoration(
                  color: AppColors.border,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SectionHeader(
              icon: Icons.calculate,
              title: 'Position calculator',
              subtitle: 'How many coins to buy at the given risk',
              color: AppColors.primary,
            ),
            const SizedBox(height: 18),
            Row(children: [
              Expanded(child: _input(_deposit, 'Deposit', suffix: '\$')),
              const SizedBox(width: 10),
              Expanded(child: _input(_risk, 'Risk', suffix: '%')),
            ]),
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: _input(_entry, 'Entry price')),
              const SizedBox(width: 10),
              Expanded(child: _input(_sl, 'Stop-loss')),
            ]),
            const SizedBox(height: 10),
            _input(_leverage, 'Leverage', suffix: 'x'),
            const SizedBox(height: 16),
            FilledButton.icon(
              onPressed: _busy ? null : _calc,
              icon: _busy
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.functions),
              label: Text(_busy ? 'Calculating...' : 'Calculate'),
            ),
            if (_error != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: AppColors.danger.withValues(alpha: 0.12),
                  border: Border.all(
                      color: AppColors.danger.withValues(alpha: 0.5)),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(children: [
                  const Icon(Icons.error_outline,
                      color: AppColors.danger, size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text(_error!)),
                ]),
              ),
            ],
            if (_result != null) ...[
              const SizedBox(height: 18),
              _ResultBlock(r: _result!),
            ],
          ],
        ),
      ),
    );
  }
}

class _ResultBlock extends StatelessWidget {
  final PositionCalcResult r;
  const _ResultBlock({required this.r});

  @override
  Widget build(BuildContext context) {
    Widget row(IconData icon, String label, String value, Color color) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 4),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(6),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Icon(icon, size: 14, color: color),
          ),
          const SizedBox(width: 10),
          Expanded(
              child: Text(label,
                  style:
                      const TextStyle(color: AppColors.textSecondary))),
          Text(value,
              style: TextStyle(
                  color: color,
                  fontWeight: FontWeight.w800,
                  fontSize: 15)),
        ]),
      );
    }

    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(children: [
        row(Icons.warning_amber_rounded, 'Risk in money',
            '${r.riskMoney.toStringAsFixed(2)} \$', AppColors.warn),
        row(Icons.straighten, 'SL distance',
            r.slDistance.toStringAsFixed(4), AppColors.info),
        row(Icons.scale, 'Position size',
            r.positionSizeUnits.toStringAsFixed(6), AppColors.primary),
        row(Icons.account_balance_wallet, 'Position value',
            '${r.positionValueUsdt.toStringAsFixed(2)} \$', AppColors.success),
        row(Icons.layers, 'Margin',
            '${r.marginRequired.toStringAsFixed(2)} \$', AppColors.success),
        const Divider(height: 20),
        row(Icons.balance, 'TP distance for R:R 1:2',
            r.rrRequiredFor2x.toStringAsFixed(4), AppColors.primary),
      ]),
    );
  }
}
