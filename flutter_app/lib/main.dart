import 'package:flutter/material.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'screens/dashboard_screen.dart';
import 'screens/signals_screen.dart';
import 'screens/trade_check_screen.dart';
import 'screens/journal_screen.dart';
import 'screens/discipline_stats_screen.dart';
import 'screens/settings_screen.dart';
import 'services/theme_controller.dart';
import 'theme.dart';
import 'widgets/branding.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('ru_RU', null);
  await themeController.load();
  runApp(const RiskAssistantApp());
}

class RiskAssistantApp extends StatelessWidget {
  const RiskAssistantApp({super.key});

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: themeController,
      builder: (_, __) => MaterialApp(
        title: 'AI Risk & Discipline Assistant',
        debugShowCheckedModeBanner: false,
        theme: buildAppTheme(brightness: Brightness.light),
        darkTheme: buildAppTheme(brightness: Brightness.dark),
        themeMode: themeController.mode,
        home: const MainShell(),
      ),
    );
  }
}

class MainShell extends StatefulWidget {
  const MainShell({super.key});

  @override
  State<MainShell> createState() => _MainShellState();
}

class _MainShellState extends State<MainShell> {
  int _index = 0;

  static const _titles = [
    'Сегодня',
    'Сигналы',
    'Проверить сделку',
    'Журнал',
    'Дисциплина',
    'Настройки',
  ];

  static const _subtitles = [
    'Обзор дня',
    'Что нашёл сканер рынка',
    'Risk officer перед входом',
    'История твоих решений',
    'Метрики и графики',
    'Лимиты и Telegram ID',
  ];

  late final List<Widget> _screens = [
    DashboardScreen(onSwitchTab: _switchTab),
    SignalsScreen(onSwitchTab: _switchTab),
    const TradeCheckScreen(),
    JournalScreen(onSwitchTab: _switchTab),
    const DisciplineStatsScreen(),
    const SettingsScreen(),
  ];

  void _switchTab(int i) => setState(() => _index = i);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      extendBodyBehindAppBar: true,
      appBar: GlassAppBar(
        title: _titles[_index],
        subtitle: _subtitles[_index],
        actions: [
          IconButton(
            tooltip: themeController.isDark ? 'Светлая тема' : 'Тёмная тема',
            onPressed: themeController.toggle,
            icon: Icon(themeController.isDark
                ? Icons.light_mode_outlined
                : Icons.dark_mode_outlined),
          ),
        ],
      ),
      body: NoiseBackground(
        child: SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.only(top: 64),
            child: AnimatedSwitcher(
              duration: const Duration(milliseconds: 280),
              switchInCurve: Curves.easeOutCubic,
              switchOutCurve: Curves.easeInCubic,
              transitionBuilder: (child, animation) => FadeTransition(
                opacity: animation,
                child: SlideTransition(
                  position: Tween<Offset>(
                    begin: const Offset(0, 0.02),
                    end: Offset.zero,
                  ).animate(animation),
                  child: child,
                ),
              ),
              child: KeyedSubtree(
                key: ValueKey(_index),
                child: _screens[_index],
              ),
            ),
          ),
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: _switchTab,
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.dashboard_outlined),
            selectedIcon: Icon(Icons.dashboard),
            label: 'Сегодня',
          ),
          NavigationDestination(
            icon: Icon(Icons.signal_cellular_alt_outlined),
            selectedIcon: Icon(Icons.signal_cellular_alt),
            label: 'Сигналы',
          ),
          NavigationDestination(
            icon: Icon(Icons.shield_outlined),
            selectedIcon: Icon(Icons.shield),
            label: 'Проверка',
          ),
          NavigationDestination(
            icon: Icon(Icons.list_alt_outlined),
            selectedIcon: Icon(Icons.list_alt),
            label: 'Журнал',
          ),
          NavigationDestination(
            icon: Icon(Icons.bar_chart_outlined),
            selectedIcon: Icon(Icons.bar_chart),
            label: 'Дисциплина',
          ),
          NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: 'Настройки',
          ),
        ],
      ),
    );
  }
}
