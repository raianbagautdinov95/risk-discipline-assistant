import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../services/user_store.dart';
import '../theme.dart';
import '../widgets/common.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _api = ApiService();
  final _tidCtrl = TextEditingController();
  final _riskCtrl = TextEditingController();
  final _levCtrl = TextEditingController();
  final _rrCtrl = TextEditingController();
  final _dayCtrl = TextEditingController();

  int? _tid;
  bool _loading = true;
  String? _error;
  String? _ok;

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
      _tidCtrl.text = _tid?.toString() ?? '';
      if (_tid != null) {
        final s = await _api.getSettings(_tid!);
        _riskCtrl.text = s.maxRiskPercent.toString();
        _levCtrl.text = s.maxLeverage.toString();
        _rrCtrl.text = s.minRr.toString();
        _dayCtrl.text = s.dailyLossLimit.toString();
      }
    } catch (e) {
      _error = e.toString();
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _saveTid() async {
    final raw = _tidCtrl.text.trim();
    final tid = int.tryParse(raw);
    if (tid == null || tid <= 0) {
      setState(() => _error = 'Telegram ID должен быть положительным числом');
      return;
    }
    await UserStore.setTelegramId(tid);
    setState(() {
      _tid = tid;
      _ok = 'Telegram ID сохранён';
      _error = null;
    });
    await _load();
  }

  Future<void> _saveLimits() async {
    if (_tid == null) {
      setState(() => _error = 'Сначала сохрани Telegram ID');
      return;
    }
    setState(() {
      _error = null;
      _ok = null;
    });
    final patch = <String, dynamic>{};
    final risk = double.tryParse(_riskCtrl.text.replaceAll(',', '.'));
    final lev = int.tryParse(_levCtrl.text);
    final rr = double.tryParse(_rrCtrl.text.replaceAll(',', '.'));
    final day = double.tryParse(_dayCtrl.text.replaceAll(',', '.'));
    if (risk != null) patch['max_risk_percent'] = risk;
    if (lev != null) patch['max_leverage'] = lev;
    if (rr != null) patch['min_rr'] = rr;
    if (day != null) patch['daily_loss_limit'] = day;
    if (patch.isEmpty) {
      setState(() => _error = 'Заполни хотя бы одно поле');
      return;
    }
    try {
      await _api.updateSettings(_tid!, patch);
      setState(() => _ok = 'Лимиты обновлены');
    } catch (e) {
      setState(() => _error = e.toString());
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
        children: [header, const SizedBox(height: 12), child],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    return SingleChildScrollView(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 32),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _section(
            header: const SectionHeader(
              icon: Icons.account_circle,
              title: 'Учётная запись',
              subtitle:
                  'Привязка к боту в Telegram',
              color: AppColors.info,
            ),
            child: Column(children: [
              const Text(
                'Введи свой Telegram ID — тот же что у @RiskGuradBot. '
                'Узнать его можно у @userinfobot или в /start у самого бота.',
                style: TextStyle(
                    fontSize: 12, color: AppColors.textMuted, height: 1.4),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _tidCtrl,
                keyboardType: TextInputType.number,
                decoration:
                    const InputDecoration(labelText: 'Telegram ID'),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _saveTid,
                icon: const Icon(Icons.save),
                label: const Text('Сохранить ID и загрузить настройки'),
              ),
            ]),
          ),

          _section(
            header: const SectionHeader(
              icon: Icons.shield,
              title: 'Лимиты риска',
              subtitle: 'Используются rule engine для блокировки',
              color: AppColors.warn,
            ),
            child: Column(children: [
              TextField(
                controller: _riskCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Макс. риск на сделку, %',
                  helperText: 'По умолчанию 1%',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _levCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Макс. плечо',
                  helperText: 'По умолчанию x5',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _rrCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Мин. R:R',
                  helperText: '2.0 = 1:2',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _dayCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Дневной лимит убытка, %',
                  helperText: 'После этого порога торговля заблокирована',
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _saveLimits,
                icon: const Icon(Icons.check),
                label: const Text('Сохранить лимиты'),
              ),
            ]),
          ),

          if (_error != null)
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 10),
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
          if (_ok != null)
            Container(
              padding: const EdgeInsets.all(12),
              margin: const EdgeInsets.only(bottom: 10),
              decoration: BoxDecoration(
                color: AppColors.success.withValues(alpha: 0.12),
                border: Border.all(
                    color: AppColors.success.withValues(alpha: 0.5)),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Row(children: [
                const Icon(Icons.check_circle, color: AppColors.success),
                const SizedBox(width: 8),
                Expanded(child: Text(_ok!)),
              ]),
            ),

          _section(
            header: const SectionHeader(
              icon: Icons.info_outline,
              title: 'О продукте',
              color: AppColors.primary,
            ),
            child: const Text(
              'AI Risk & Discipline Assistant\n'
              'Telegram + Web интерфейс\n'
              'Backend: FastAPI + PostgreSQL\n'
              'AI: OpenAI Coach + Claude Risk Officer\n\n'
              '⚠️ Это не финансовая рекомендация.',
              style: TextStyle(
                  fontSize: 12, color: AppColors.textMuted, height: 1.5),
            ),
          ),
        ],
      ),
    );
  }
}
