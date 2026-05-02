import 'package:flutter/material.dart';

import '../models/trade.dart';
import '../services/api_service.dart';
import '../services/prefill_bus.dart';
import '../services/user_store.dart';
import '../theme.dart';
import '../widgets/common.dart';
import '../widgets/position_calc_sheet.dart';

class TradeCheckScreen extends StatefulWidget {
  const TradeCheckScreen({super.key});

  @override
  State<TradeCheckScreen> createState() => _TradeCheckScreenState();
}

class _TradeCheckScreenState extends State<TradeCheckScreen> {
  final _formKey = GlobalKey<FormState>();
  final _api = ApiService();

  final _pair = TextEditingController(text: 'BTC/USDT');
  String _direction = 'long';
  final _entry = TextEditingController();
  final _sl = TextEditingController();
  final _tp = TextEditingController();
  final _deposit = TextEditingController(text: '1000');
  final _risk = TextEditingController(text: '1');
  final _leverage = TextEditingController(text: '1');
  final _reason = TextEditingController();
  final _setup = TextEditingController();
  String _emotion = 'спокоен';
  final _lossesToday = TextEditingController(text: '0');
  final _consec = TextEditingController(text: '0');

  bool _busy = false;
  TradeResponse? _result;
  String? _error;
  int? _tid;

  @override
  void initState() {
    super.initState();
    UserStore.getTelegramId().then((v) => setState(() => _tid = v));
    tradePrefillBus.addListener(_applyPrefill);
    _applyPrefill();
  }

  @override
  void dispose() {
    tradePrefillBus.removeListener(_applyPrefill);
    super.dispose();
  }

  void _applyPrefill() {
    final p = tradePrefillBus.value;
    if (p == null) return;
    setState(() {
      _pair.text = p.pair;
      _direction = p.direction;
      _entry.text = p.entryPrice.toString();
      _sl.text = p.stopLoss?.toString() ?? '';
      _tp.text = p.takeProfit?.toString() ?? '';
      _result = null;
      _error = null;
    });
    tradePrefillBus.value = null;
  }

  double? _parseDouble(String s) =>
      double.tryParse(s.trim().replaceAll(',', '.'));

  Future<void> _submit() async {
    if (_tid == null) {
      setState(() => _error = 'Сначала укажи Telegram ID в Настройках');
      return;
    }
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _busy = true;
      _error = null;
      _result = null;
    });
    try {
      final req = TradeRequest(
        pair: _pair.text.trim().toUpperCase(),
        direction: _direction,
        entryPrice: _parseDouble(_entry.text)!,
        stopLoss: _parseDouble(_sl.text),
        takeProfit: _parseDouble(_tp.text),
        deposit: _parseDouble(_deposit.text)!,
        riskPercent: _parseDouble(_risk.text)!,
        leverage: int.tryParse(_leverage.text.trim()) ?? 1,
        reason: _reason.text.trim().isEmpty ? null : _reason.text.trim(),
        setup: _setup.text.trim().isEmpty ? null : _setup.text.trim(),
        emotion: _emotion,
        lossesToday: _parseDouble(_lossesToday.text) ?? 0,
        consecutiveLosses: int.tryParse(_consec.text.trim()) ?? 0,
      );
      final resp = await _api.checkTrade(_tid!, req);
      setState(() => _result = resp);
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _section({required Widget header, required Widget child}) {
    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.border),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          header,
          const SizedBox(height: 14),
          child,
        ],
      ),
    );
  }

  Widget _input(
    TextEditingController c, {
    required String label,
    TextInputType keyboard = TextInputType.text,
    bool required = false,
  }) {
    return TextFormField(
      controller: c,
      keyboardType: keyboard,
      decoration: InputDecoration(labelText: label),
      validator: required
          ? (v) => (v == null || v.trim().isEmpty) ? 'Обязательно' : null
          : null,
    );
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          if (_tid == null)
            Container(
              padding: const EdgeInsets.all(14),
              margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(
                color: AppColors.warn.withValues(alpha: 0.12),
                border: Border.all(
                    color: AppColors.warn.withValues(alpha: 0.5)),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Row(
                children: [
                  Icon(Icons.warning_amber, color: AppColors.warn),
                  SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      'Укажи Telegram ID в "Настройках", чтобы сделки сохранились '
                      'в твой журнал.',
                      style: TextStyle(fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),

          Form(
            key: _formKey,
            child: Column(
              children: [
                _section(
                  header: const SectionHeader(
                    icon: Icons.show_chart,
                    title: 'Сделка',
                    subtitle: 'Что и куда',
                    color: AppColors.info,
                  ),
                  child: Column(children: [
                    _input(_pair, label: 'Пара (BTC/USDT)'),
                    const SizedBox(height: 10),
                    Row(children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _direction,
                          decoration:
                              const InputDecoration(labelText: 'Направление'),
                          items: const [
                            DropdownMenuItem(
                                value: 'long', child: Text('long')),
                            DropdownMenuItem(
                                value: 'short', child: Text('short')),
                          ],
                          onChanged: (v) =>
                              setState(() => _direction = v ?? 'long'),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                          child: _input(_leverage,
                              label: 'Плечо',
                              keyboard: TextInputType.number)),
                    ]),
                    const SizedBox(height: 10),
                    Row(children: [
                      Expanded(
                          child: _input(_entry,
                              label: 'Цена входа',
                              keyboard: TextInputType.number,
                              required: true)),
                      const SizedBox(width: 10),
                      Expanded(
                          child: _input(_sl,
                              label: 'Stop-loss',
                              keyboard: TextInputType.number)),
                      const SizedBox(width: 10),
                      Expanded(
                          child: _input(_tp,
                              label: 'Take-profit',
                              keyboard: TextInputType.number)),
                    ]),
                  ]),
                ),

                _section(
                  header: SectionHeader(
                    icon: Icons.shield,
                    title: 'Риск',
                    subtitle: 'Сколько готов потерять',
                    color: AppColors.warn,
                    trailing: TextButton.icon(
                      style: TextButton.styleFrom(
                        foregroundColor: AppColors.primary,
                        padding: const EdgeInsets.symmetric(
                            horizontal: 8, vertical: 4),
                      ),
                      onPressed: () => PositionCalcSheet.show(
                        context,
                        deposit: _parseDouble(_deposit.text),
                        riskPercent: _parseDouble(_risk.text),
                        entry: _parseDouble(_entry.text),
                        stopLoss: _parseDouble(_sl.text),
                        leverage: int.tryParse(_leverage.text.trim()),
                      ),
                      icon: const Icon(Icons.calculate, size: 16),
                      label: const Text('Калькулятор',
                          style: TextStyle(fontSize: 12)),
                    ),
                  ),
                  child: Row(children: [
                    Expanded(
                        child: _input(_deposit,
                            label: 'Депозит, USDT',
                            keyboard: TextInputType.number,
                            required: true)),
                    const SizedBox(width: 10),
                    Expanded(
                        child: _input(_risk,
                            label: 'Риск, %',
                            keyboard: TextInputType.number,
                            required: true)),
                  ]),
                ),

                _section(
                  header: const SectionHeader(
                    icon: Icons.psychology,
                    title: 'Дисциплина',
                    subtitle: 'Сетап и эмоции',
                    color: AppColors.primary,
                  ),
                  child: Column(children: [
                    _input(_reason, label: 'Причина входа'),
                    const SizedBox(height: 10),
                    _input(_setup, label: 'Сетап (пробой / отскок / ретест)'),
                    const SizedBox(height: 10),
                    DropdownButtonFormField<String>(
                      value: _emotion,
                      decoration:
                          const InputDecoration(labelText: 'Эмоция'),
                      items: const [
                        DropdownMenuItem(
                            value: 'спокоен', child: Text('🧘 спокоен')),
                        DropdownMenuItem(
                            value: 'уверен', child: Text('💪 уверен')),
                        DropdownMenuItem(
                            value: 'злость', child: Text('😡 злость')),
                        DropdownMenuItem(
                            value: 'FOMO', child: Text('🚨 FOMO')),
                        DropdownMenuItem(
                            value: 'паника', child: Text('😱 паника')),
                        DropdownMenuItem(
                            value: 'жадность', child: Text('🤑 жадность')),
                      ],
                      onChanged: (v) =>
                          setState(() => _emotion = v ?? 'спокоен'),
                    ),
                    const SizedBox(height: 10),
                    Row(children: [
                      Expanded(
                          child: _input(_lossesToday,
                              label: 'Дневной убыток, %',
                              keyboard: TextInputType.number)),
                      const SizedBox(width: 10),
                      Expanded(
                          child: _input(_consec,
                              label: 'Убытков подряд',
                              keyboard: TextInputType.number)),
                    ]),
                  ]),
                ),
              ],
            ),
          ),

          SizedBox(
            height: 56,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
              ),
              onPressed: _busy ? null : _submit,
              icon: _busy
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(
                          strokeWidth: 2, color: Colors.white),
                    )
                  : const Icon(Icons.shield, size: 20),
              label: Text(
                _busy ? 'Анализирую...' : 'Проверить сделку',
                style: const TextStyle(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 0.3),
              ),
            ),
          ),

          if (_error != null) ...[
            const SizedBox(height: 14),
            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.danger.withValues(alpha: 0.12),
                border: Border.all(
                    color: AppColors.danger.withValues(alpha: 0.5)),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(children: [
                const Icon(Icons.error_outline, color: AppColors.danger),
                const SizedBox(width: 8),
                Expanded(child: Text(_error!)),
              ]),
            ),
          ],

          if (_result != null) ...[
            const SizedBox(height: 16),
            DecisionHero(
              decision: _result!.decision,
              decisionRu: _result!.decisionRu,
              score: _result!.score,
              recommendation: _result!.recommendation,
            ),
            const SizedBox(height: 14),
            _ResultDetails(resp: _result!),
          ],
        ],
      ),
    );
  }
}

class _ResultDetails extends StatelessWidget {
  final TradeResponse resp;
  const _ResultDetails({required this.resp});

  @override
  Widget build(BuildContext context) {
    final c = switch (resp.decision) {
      'ALLOWED' => AppColors.success,
      'FORBIDDEN' => AppColors.danger,
      _ => AppColors.warn,
    };
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: AppColors.surface,
            border: Border.all(color: AppColors.border),
            borderRadius: BorderRadius.circular(14),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SectionHeader(
                icon: Icons.calculate,
                title: 'Расчёты',
                color: AppColors.info,
              ),
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  PricePill(
                    label: 'Риск',
                    value: '${resp.calc.riskMoney} \$',
                    color: AppColors.warn,
                    icon: Icons.warning_amber_rounded,
                  ),
                  PricePill(
                    label: 'R:R',
                    value: resp.calc.rrRatio?.toStringAsFixed(2) ?? '—',
                    color: AppColors.info,
                    icon: Icons.balance,
                  ),
                  PricePill(
                    label: 'Размер',
                    value:
                        resp.calc.positionSize?.toStringAsFixed(6) ?? '—',
                    color: AppColors.primary,
                    icon: Icons.pie_chart_outline,
                  ),
                  if (resp.calc.leverageCritical)
                    PricePill(
                      label: 'Плечо',
                      value: 'КРИТИЧНО',
                      color: AppColors.danger,
                      icon: Icons.bolt,
                    ),
                ],
              ),
            ],
          ),
        ),

        if (resp.violations.isNotEmpty) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SectionHeader(
                  icon: Icons.warning_rounded,
                  title: 'Нарушения правил',
                  subtitle:
                      '${resp.violations.length} ${resp.violations.length == 1 ? "нарушение" : "нарушений"}',
                  color: AppColors.danger,
                ),
                const SizedBox(height: 12),
                for (var i = 0; i < resp.violations.length; i++)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Container(
                        margin: const EdgeInsets.only(top: 2),
                        width: 18,
                        height: 18,
                        alignment: Alignment.center,
                        decoration: BoxDecoration(
                          color: AppColors.danger.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text('${i + 1}',
                            style: const TextStyle(
                                color: AppColors.danger,
                                fontSize: 11,
                                fontWeight: FontWeight.bold)),
                      ),
                      const SizedBox(width: 8),
                      Expanded(child: Text(resp.violations[i].message)),
                    ]),
                  ),
              ],
            ),
          ),
        ],

        if (resp.officer != null) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionHeader(
                  icon: Icons.policy,
                  title: 'Risk Officer',
                  color: AppColors.danger,
                ),
                const SizedBox(height: 10),
                Text(resp.officer!.summary),
              ],
            ),
          ),
        ],

        if (resp.coach != null && resp.coach!.summary.isNotEmpty) ...[
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              border: Border.all(color: AppColors.border),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SectionHeader(
                  icon: Icons.school,
                  title: 'Coach',
                  color: AppColors.primary,
                ),
                const SizedBox(height: 10),
                Text(resp.coach!.summary),
                if (resp.coach!.pros.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final p in resp.coach!.pros)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.success.withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text('✓ $p',
                              style: const TextStyle(
                                  fontSize: 11,
                                  color: AppColors.success,
                                  fontWeight: FontWeight.w600)),
                        ),
                    ],
                  ),
                ],
                if (resp.coach!.cons.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final n in resp.coach!.cons)
                        Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: AppColors.danger.withValues(alpha: 0.18),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text('✗ $n',
                              style: const TextStyle(
                                  fontSize: 11,
                                  color: AppColors.danger,
                                  fontWeight: FontWeight.w600)),
                        ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ],

        const SizedBox(height: 14),
        Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: AppColors.surfaceAlt,
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(children: [
            Icon(Icons.info_outline, size: 16, color: c),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                resp.disclaimer,
                style: const TextStyle(
                    fontSize: 11,
                    color: AppColors.textMuted,
                    fontStyle: FontStyle.italic),
              ),
            ),
          ]),
        ),
      ],
    );
  }
}
