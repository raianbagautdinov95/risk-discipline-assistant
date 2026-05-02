"""Crypto Signal Bot — сигнальный бот БЕЗ реального исполнения ордеров.
Только анализ рынка и уведомления: когда входить в сделку и когда выходить.

Запуск:
    python main.py           — непрерывное сканирование раз в N секунд
    python main.py --once    — один проход по всем монетам и выход
"""
import argparse
import sys
import time
from typing import List

from dotenv import load_dotenv

from config.settings import TradingConfig, AIConfig, NotifyConfig
from config.risk_config import RiskLimits
from data.market_data import MarketData
from ai.indicators import compute_indicators, indicator_snapshot
from ai.signal_engine import SignalEngine, Signal
from ai.deepseek_analyzer import DeepSeekAnalyzer
from monitoring.notifier import Notifier
from monitoring.reporter import SignalHistory
from monitoring.tracker import SignalTracker
from utils.logger import setup_logger


class SignalBot:
    """Ядро бота. Отделено от main(), чтобы потом легко обернуть в REST API."""

    def __init__(self):
        self.logger = setup_logger()

        self.trading_cfg = TradingConfig()
        self.ai_cfg = AIConfig()
        self.notify_cfg = NotifyConfig()
        self.risk = RiskLimits()

        self.market = MarketData()
        self.engine = SignalEngine(self.trading_cfg, self.risk)
        self.ai = DeepSeekAnalyzer(self.ai_cfg)
        self.notifier = Notifier(self.notify_cfg, logger=self.logger)
        self.history = SignalHistory()
        self.tracker = SignalTracker(
            market=self.market,
            entry_timeframe=self.trading_cfg.entry_timeframe,
        )

        self.logger.info("Signal Bot initialized")
        self.logger.info(f"Symbols: {', '.join(self.trading_cfg.symbols)}")
        htf = self.trading_cfg.htf_timeframe or "(выкл)"
        self.logger.info(
            f"Timeframes: htf={htf}, trend={self.trading_cfg.trend_timeframe}, "
            f"entry={self.trading_cfg.entry_timeframe}"
        )
        self.logger.info(f"AI-анализ: {'включён' if self.ai.is_available() else 'выключен'}")

    # ---------------------------------------------------------------- #
    # Главная единица работы — может вызываться и из цикла, и из API.  #
    # ---------------------------------------------------------------- #

    def analyze_symbol(self, symbol: str) -> Signal:
        """Полный анализ одной монеты. Возвращает Signal (может быть HOLD)."""
        # 1. Скачиваем свечи с двух (или трёх) таймфреймов.
        entry_df = self.market.get_candles(
            symbol, self.trading_cfg.entry_timeframe, self.trading_cfg.candles_limit
        )
        trend_df = self.market.get_candles(
            symbol, self.trading_cfg.trend_timeframe, self.trading_cfg.candles_limit
        )
        if entry_df is None or trend_df is None:
            self.logger.warning(f"{symbol}: не удалось получить свечи, пропускаем")
            return None
        if len(entry_df) < 50 or len(trend_df) < 50:
            self.logger.warning(f"{symbol}: слишком мало свечей")
            return None

        # Верхний таймфрейм (4H) — опциональный.
        htf_snap = None
        if self.trading_cfg.htf_timeframe:
            htf_df = self.market.get_candles(
                symbol, self.trading_cfg.htf_timeframe, self.trading_cfg.candles_limit
            )
            if htf_df is not None and len(htf_df) >= 50:
                htf_df = compute_indicators(htf_df, self.trading_cfg.atr_period)
                htf_snap = indicator_snapshot(htf_df)

        # 2. Считаем индикаторы и снимки состояния.
        entry_df = compute_indicators(entry_df, self.trading_cfg.atr_period)
        trend_df = compute_indicators(trend_df, self.trading_cfg.atr_period)
        entry_snap = indicator_snapshot(entry_df)
        trend_snap = indicator_snapshot(trend_df)

        # 3. Строим сигнал (с учётом 4H, если доступен).
        signal = self.engine.generate(symbol, entry_snap, trend_snap, htf_snap)

        # 4. Если есть реальный сигнал — просим AI (если доступен) и уведомляем.
        ai_review = None
        if signal.action != "HOLD":
            # Ранний выход: если на этом символе есть открытая позиция в
            # противоположном направлении — закрываем её по текущей цене.
            closed = self.tracker.close_early(
                symbol=symbol,
                opposite_action=signal.action,
                current_price=signal.entry,
                reason=f"Противоположный сигнал: {signal.action}",
            )
            if closed > 0:
                self.logger.info(
                    f"{symbol}: закрыто досрочно {closed} позиц. "
                    f"из-за противоположного {signal.action}"
                )

            if self.ai.is_available():
                ai_review = self.ai.review_signal(symbol, signal.to_dict(), entry_snap)
            self.notifier.send(signal.to_dict(), ai_review)
            self.history.record(signal.to_dict(), ai_review)
            self.tracker.add_signal(signal.to_dict())
        else:
            # HOLD просто логируем, не рассылаем.
            self.logger.debug(f"{symbol}: HOLD — {'; '.join(signal.reasons)}")

        return signal

    def scan_all(self) -> List[Signal]:
        """Один проход по всем монетам."""
        # Сначала обновим статусы ранее выданных сигналов.
        changes = self.tracker.update_open_signals()
        if any(changes.values()):
            self.logger.info(
                f"Трекер: закрыто WIN={changes['closed_win']}, "
                f"LOSS={changes['closed_loss']}, EXPIRED={changes['expired']}, "
                f"OPEN={changes['still_open']}"
            )

        results: List[Signal] = []
        for symbol in self.trading_cfg.symbols:
            try:
                sig = self.analyze_symbol(symbol)
                if sig is not None:
                    results.append(sig)
            except Exception as e:
                self.logger.exception(f"{symbol}: ошибка анализа: {e}")
            # Небольшая пауза между запросами, чтобы не упереться в rate limit OKX.
            time.sleep(0.3)

        actionable = [s for s in results if s.action != "HOLD"]
        self.logger.info(
            f"Скан завершён. Проверено: {len(results)}, активных сигналов: {len(actionable)}"
        )

        # Выводим сводку по трекеру раз в скан.
        summary = self.tracker.summary()
        if summary.get("closed", 0) > 0:
            self.logger.info(
                f"Общая статистика: WIN={summary['wins']}, LOSS={summary['losses']}, "
                f"win rate={summary['win_rate_pct']}%, "
                f"P&L={summary['total_r']}R"
            )

        return results

    def run_forever(self) -> None:
        """Бесконечный цикл сканирования."""
        self.logger.info(f"Старт непрерывного сканирования (каждые "
                         f"{self.trading_cfg.scan_interval_sec} сек)")
        try:
            while True:
                self.scan_all()
                time.sleep(self.trading_cfg.scan_interval_sec)
        except KeyboardInterrupt:
            self.logger.info("Остановлено пользователем")
            summary = self.history.summary()
            self.logger.info(f"Всего записано сигналов: {summary['total']} "
                             f"(BUY: {summary['buy']}, SELL: {summary['sell']})")


def main():
    parser = argparse.ArgumentParser(description="Crypto signal bot (анализ, без торговли)")
    parser.add_argument("--once", action="store_true",
                        help="Сделать один проход по всем монетам и выйти")
    args = parser.parse_args()

    load_dotenv()
    bot = SignalBot()
    if args.once:
        bot.scan_all()
    else:
        bot.run_forever()


if __name__ == "__main__":
    main()
