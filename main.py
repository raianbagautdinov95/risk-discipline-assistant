"""Crypto Signal Bot — a signal bot WITHOUT real order execution.
Market analysis and notifications only: when to enter a trade and when to exit.

Usage:
    python main.py           — continuous scanning every N seconds
    python main.py --once    — a single pass over all coins, then exit
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
    """The bot's core. Separated from main() so it can easily be wrapped in a REST API later."""

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
        htf = self.trading_cfg.htf_timeframe or "(off)"
        self.logger.info(
            f"Timeframes: htf={htf}, trend={self.trading_cfg.trend_timeframe}, "
            f"entry={self.trading_cfg.entry_timeframe}"
        )
        self.logger.info(f"AI analysis: {'enabled' if self.ai.is_available() else 'disabled'}")

    # ---------------------------------------------------------------- #
    # The main unit of work — can be called both from the loop and API. #
    # ---------------------------------------------------------------- #

    def analyze_symbol(self, symbol: str) -> Signal:
        """Full analysis of a single coin. Returns a Signal (may be HOLD)."""
        # 1. Download candles from two (or three) timeframes.
        entry_df = self.market.get_candles(
            symbol, self.trading_cfg.entry_timeframe, self.trading_cfg.candles_limit
        )
        trend_df = self.market.get_candles(
            symbol, self.trading_cfg.trend_timeframe, self.trading_cfg.candles_limit
        )
        if entry_df is None or trend_df is None:
            self.logger.warning(f"{symbol}: failed to fetch candles, skipping")
            return None
        if len(entry_df) < 50 or len(trend_df) < 50:
            self.logger.warning(f"{symbol}: too few candles")
            return None

        # Higher timeframe (4H) — optional.
        htf_snap = None
        if self.trading_cfg.htf_timeframe:
            htf_df = self.market.get_candles(
                symbol, self.trading_cfg.htf_timeframe, self.trading_cfg.candles_limit
            )
            if htf_df is not None and len(htf_df) >= 50:
                htf_df = compute_indicators(htf_df, self.trading_cfg.atr_period)
                htf_snap = indicator_snapshot(htf_df)

        # 2. Compute indicators and state snapshots.
        entry_df = compute_indicators(entry_df, self.trading_cfg.atr_period)
        trend_df = compute_indicators(trend_df, self.trading_cfg.atr_period)
        entry_snap = indicator_snapshot(entry_df)
        trend_snap = indicator_snapshot(trend_df)

        # 3. Build the signal (taking 4H into account, if available).
        signal = self.engine.generate(symbol, entry_snap, trend_snap, htf_snap)

        # 4. If there's a real signal — ask the AI (if available) and notify.
        ai_review = None
        if signal.action != "HOLD":
            # Early exit: if there's an open position on this symbol in the
            # opposite direction — close it at the current price.
            closed = self.tracker.close_early(
                symbol=symbol,
                opposite_action=signal.action,
                current_price=signal.entry,
                reason=f"Opposite signal: {signal.action}",
            )
            if closed > 0:
                self.logger.info(
                    f"{symbol}: closed early {closed} position(s) "
                    f"due to opposite {signal.action}"
                )

            if self.ai.is_available():
                ai_review = self.ai.review_signal(symbol, signal.to_dict(), entry_snap)
            self.notifier.send(signal.to_dict(), ai_review)
            self.history.record(signal.to_dict(), ai_review)
            self.tracker.add_signal(signal.to_dict())
        else:
            # HOLD is just logged, not broadcast.
            self.logger.debug(f"{symbol}: HOLD — {'; '.join(signal.reasons)}")

        return signal

    def scan_all(self) -> List[Signal]:
        """A single pass over all coins."""
        # First, refresh the statuses of previously issued signals.
        changes = self.tracker.update_open_signals()
        if any(changes.values()):
            self.logger.info(
                f"Tracker: closed WIN={changes['closed_win']}, "
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
                self.logger.exception(f"{symbol}: analysis error: {e}")
            # A short pause between requests to avoid hitting the OKX rate limit.
            time.sleep(0.3)

        actionable = [s for s in results if s.action != "HOLD"]
        self.logger.info(
            f"Scan complete. Checked: {len(results)}, active signals: {len(actionable)}"
        )

        # Print a tracker summary once per scan.
        summary = self.tracker.summary()
        if summary.get("closed", 0) > 0:
            self.logger.info(
                f"Overall stats: WIN={summary['wins']}, LOSS={summary['losses']}, "
                f"win rate={summary['win_rate_pct']}%, "
                f"P&L={summary['total_r']}R"
            )

        return results

    def run_forever(self) -> None:
        """Infinite scanning loop."""
        self.logger.info(f"Starting continuous scanning (every "
                         f"{self.trading_cfg.scan_interval_sec} sec)")
        try:
            while True:
                self.scan_all()
                time.sleep(self.trading_cfg.scan_interval_sec)
        except KeyboardInterrupt:
            self.logger.info("Stopped by user")
            summary = self.history.summary()
            self.logger.info(f"Total signals recorded: {summary['total']} "
                             f"(BUY: {summary['buy']}, SELL: {summary['sell']})")


def main():
    parser = argparse.ArgumentParser(description="Crypto signal bot (analysis, no trading)")
    parser.add_argument("--once", action="store_true",
                        help="Make a single pass over all coins and exit")
    args = parser.parse_args()

    load_dotenv()
    bot = SignalBot()
    if args.once:
        bot.scan_all()
    else:
        bot.run_forever()


if __name__ == "__main__":
    main()
