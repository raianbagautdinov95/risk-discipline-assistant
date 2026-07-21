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
      setState(() => _error = 'Telegram ID must be a positive number');
      return;
    }
    await UserStore.setTelegramId(tid);
    setState(() {
      _tid = tid;
      _ok = 'Telegram ID saved';
      _error = null;
    });
    await _load();
  }

  Future<void> _saveLimits() async {
    if (_tid == null) {
      setState(() => _error = 'Save your Telegram ID first');
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
      setState(() => _error = 'Fill in at least one field');
      return;
    }
    try {
      await _api.updateSettings(_tid!, patch);
      setState(() => _ok = 'Limits updated');
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
              title: 'Account',
              subtitle:
                  'Link to your Telegram bot',
              color: AppColors.info,
            ),
            child: Column(children: [
              const Text(
                'Enter your Telegram ID — the same one used with @RiskGuradBot. '
                'You can find it via @userinfobot or by sending /start to the bot.',
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
                label: const Text('Save ID and load settings'),
              ),
            ]),
          ),

          _section(
            header: const SectionHeader(
              icon: Icons.shield,
              title: 'Risk limits',
              subtitle: 'Used by the rule engine to block trades',
              color: AppColors.warn,
            ),
            child: Column(children: [
              TextField(
                controller: _riskCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Max risk per trade, %',
                  helperText: 'Default 1%',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _levCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Max leverage',
                  helperText: 'Default x5',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _rrCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Min R:R',
                  helperText: '2.0 = 1:2',
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: _dayCtrl,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Daily loss limit, %',
                  helperText: 'Trading is blocked once this threshold is hit',
                ),
              ),
              const SizedBox(height: 12),
              FilledButton.icon(
                onPressed: _saveLimits,
                icon: const Icon(Icons.check),
                label: const Text('Save limits'),
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
              title: 'About',
              color: AppColors.primary,
            ),
            child: const Text(
              'AI Risk & Discipline Assistant\n'
              'Telegram + Web interface\n'
              'Backend: FastAPI + PostgreSQL\n'
              'AI: OpenAI Coach + Claude Risk Officer\n\n'
              '⚠️ This is not financial advice.',
              style: TextStyle(
                  fontSize: 12, color: AppColors.textMuted, height: 1.5),
            ),
          ),
        ],
      ),
    );
  }
}
