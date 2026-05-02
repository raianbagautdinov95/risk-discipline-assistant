"""Бэктестер сигнальной стратегии.

Принцип работы (walk-forward симуляция):
1. Скачивается большой объём исторических свечей (через пагинацию).
2. Индикаторы считаются ОДИН раз на всю историю — это корректно, т.к.
   индикаторы типа RSI/MACD используют только прошлые значения.
3. Идём по истории свеча за свечой. В каждый момент времени имеем
   snapshot индикаторов только для прошлых свечей (slice до текущей).
4. Движок выдаёт сигнал → мы смотрим, что случилось в следующих
   candles_ahead свечах: сработал ли TP или SL первым.
5. Агрегируем: win rate, profit factor, средний R:R, max drawdown.

Запуск:
    python backtest.py                        — тест BTC-USDT, 15m, ~21 день
    python backtest.py --symbol ETH-USDT
    python backtest.py --symbol BTC-USDT --candles 3000 --lookahead 48
"""
import argparse
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from collections import defaultdict

import pandas as pd

from dotenv import load_dotenv

from config.settings import TradingConfig
from config.risk_config import RiskLimits
from data.market_data import MarketData
from ai.indicators import compute_indicators, indicator_snapshot
from ai.signal_engine import SignalEngine


@dataclass
class TradeResult:
    idx: int
    timestamp: int
    action: str
    entry: float
    stop_loss: float
    take_profit: float
    confidence: float
    outcome: str  # WIN | LOSS | OPEN
    pnl_r: float  # прибыль/убыток в единицах риска (R)
    bars_to_exit: int


@dataclass
class BacktestReport:
    symbol: str
    period_start: str
    period_end: str
    total_signals: int = 0
    wins: int = 0
    losses: int = 0
    open_at_end: int = 0
    total_r: float = 0.0
    gross_win_r: float = 0.0
    gross_loss_r: float = 0.0
    max_drawdown_r: float = 0.0
    trades: List[TradeResult] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        closed = self.wins + self.losses
        win_rate = (self.wins / closed * 100) if closed > 0 else 0.0
        avg_r = (self.total_r / closed) if closed > 0 else 0.0
        profit_factor = (self.gross_win_r / abs(self.gross_loss_r)) if self.gross_loss_r != 0 else float("inf")
        return {
            "symbol": self.symbol,
            "period": f"{self.period_start} → {self.period_end}",
            "total_signals": self.total_signals,
            "closed": closed,
            "wins": self.wins,
            "losses": self.losses,
            "open_at_end": self.open_at_end,
            "win_rate_pct": round(win_rate, 1),
            "avg_r_per_trade": round(avg_r, 3),
            "profit_factor": round(profit_factor, 2) if profit_factor != float("inf") else None,
            "total_r": round(self.total_r, 2),
            "max_drawdown_r": round(self.max_drawdown_r, 2),
        }


class Backtester:
    def __init__(self, candles_on_15m: int = 2000, lookahead_bars: int = 48):
        """
        candles_on_15m — сколько 15m свечей тянем для теста (2000 ≈ 3 недели, 8000 ≈ 3 месяца).
        lookahead_bars — сколько свечей после сигнала ждать исхода (48 x 15m = 12 часов).
        """
        self.candles_on_15m = candles_on_15m
        self.lookahead = lookahead_bars
        self.cfg = TradingConfig()
        self.risk = RiskLimits()
        self.market = MarketData()
        self.engine = SignalEngine(self.cfg, self.risk)

    def run(self, symbol: str) -> BacktestReport:
        print(f"[backtest] Качаем данные для {symbol}...")
        # Соотношение: 15m → 1H = 4x меньше свечей, 4H = 16x меньше.
        entry_df = self.market.get_historical_candles(
            symbol, self.cfg.entry_timeframe, self.candles_on_15m
        )
        trend_df = self.market.get_historical_candles(
            symbol, self.cfg.trend_timeframe, self.candles_on_15m // 4 + 100
        )
        htf_df = None
        if self.cfg.htf_timeframe:
            htf_df = self.market.get_historical_candles(
                symbol, self.cfg.htf_timeframe, self.candles_on_15m // 16 + 100
            )

        if entry_df is None or trend_df is None:
            raise RuntimeError("Не удалось получить исторические данные")

        print(f"[backtest] Получено: 15m={len(entry_df)}, 1H={len(trend_df)}, "
              f"4H={len(htf_df) if htf_df is not None else 'выкл'}")

        # Считаем индикаторы один раз на всей истории.
        entry_full = compute_indicators(entry_df, self.cfg.atr_period)
        trend_full = compute_indicators(trend_df, self.cfg.atr_period)
        htf_full = compute_indicators(htf_df, self.cfg.atr_period) if htf_df is not None else None

        report = BacktestReport(
            symbol=symbol,
            period_start=str(entry_full["datetime"].iloc[0]),
            period_end=str(entry_full["datetime"].iloc[-1]),
        )

        min_history = 200  # нужно для 200-EMA и стабильных индикаторов
        # По каждой 15m свече после прогрева — проверяем наличие сигнала.
        for i in range(min_history, len(entry_full) - self.lookahead):
            # Срезы до i-й свечи включительно — чтобы симулировать реальный момент.
            entry_slice = entry_full.iloc[: i + 1]
            entry_ts = entry_slice["timestamp"].iloc[-1]

            # Находим 1H и 4H срезы, которые БЫЛИ ЗАКРЫТЫ на момент entry_ts.
            trend_slice = trend_full[trend_full["timestamp"] <= entry_ts]
            if len(trend_slice) < 50:
                continue
            htf_snap = None
            if htf_full is not None:
                htf_slice = htf_full[htf_full["timestamp"] <= entry_ts]
                if len(htf_slice) >= 50:
                    htf_snap = indicator_snapshot(htf_slice)

            entry_snap = indicator_snapshot(entry_slice)
            trend_snap = indicator_snapshot(trend_slice)

            signal = self.engine.generate(symbol, entry_snap, trend_snap, htf_snap)
            if signal.action == "HOLD":
                continue

            # Симулируем исход по следующим свечам.
            future = entry_full.iloc[i + 1: i + 1 + self.lookahead]
            outcome, pnl_r, bars = self._simulate_outcome(signal, future)

            tr = TradeResult(
                idx=i, timestamp=entry_ts, action=signal.action,
                entry=signal.entry, stop_loss=signal.stop_loss,
                take_profit=signal.take_profit, confidence=signal.confidence,
                outcome=outcome, pnl_r=pnl_r, bars_to_exit=bars,
            )
            report.trades.append(tr)
            report.total_signals += 1
            if outcome == "WIN":
                report.wins += 1
                report.gross_win_r += pnl_r
                report.total_r += pnl_r
            elif outcome == "LOSS":
                report.losses += 1
                report.gross_loss_r += pnl_r  # отрицательное число
                report.total_r += pnl_r
            else:
                report.open_at_end += 1

            # Обновляем max drawdown.
            # Считаем equity curve и максимальную просадку.
        if report.trades:
            equity = 0.0
            peak = 0.0
            dd = 0.0
            for t in report.trades:
                if t.outcome in ("WIN", "LOSS"):
                    equity += t.pnl_r
                    peak = max(peak, equity)
                    dd = min(dd, equity - peak)
            report.max_drawdown_r = dd

        return report

    def _simulate_outcome(self, signal, future_df: pd.DataFrame):
        """Проверяет, что случилось первым: TP или SL.
        Возвращает (outcome, pnl_r, bars_to_exit)."""
        if len(future_df) == 0:
            return "OPEN", 0.0, 0
        risk = abs(signal.entry - signal.stop_loss)
        if risk <= 0:
            return "OPEN", 0.0, 0

        is_long = signal.action == "BUY"

        for bar_idx, (_, row) in enumerate(future_df.iterrows(), start=1):
            high, low = row["high"], row["low"]

            if is_long:
                # SL может сработать, если low опустился ниже стопа.
                sl_hit = low <= signal.stop_loss
                tp_hit = high >= signal.take_profit
            else:  # SHORT
                sl_hit = high >= signal.stop_loss
                tp_hit = low <= signal.take_profit

            # Если в ОДНОЙ свече пересечены оба уровня — считаем пессимистично: SL сработал первым.
            # Это реалистично, т.к. мы не знаем внутрисвечной траектории.
            if sl_hit and tp_hit:
                return "LOSS", -1.0, bar_idx
            if sl_hit:
                return "LOSS", -1.0, bar_idx
            if tp_hit:
                reward = abs(signal.take_profit - signal.entry)
                return "WIN", reward / risk, bar_idx

        return "OPEN", 0.0, len(future_df)


def main():
    parser = argparse.ArgumentParser(description="Бэктест сигнальной стратегии")
    parser.add_argument("--symbol", default="BTC-USDT", help="Торговая пара")
    parser.add_argument("--candles", type=int, default=2000,
                        help="Сколько 15m свечей тянуть (2000 ≈ 3 недели, 8000 ≈ 3 месяца)")
    parser.add_argument("--lookahead", type=int, default=48,
                        help="Макс. свечей ожидания исхода сигнала (48 = 12 ч)")
    parser.add_argument("--all", action="store_true",
                        help="Прогнать по всем символам из config.settings")
    args = parser.parse_args()

    load_dotenv()

    bt = Backtester(candles_on_15m=args.candles, lookahead_bars=args.lookahead)

    symbols = bt.cfg.symbols if args.all else [args.symbol]

    all_reports = []
    for sym in symbols:
        try:
            report = bt.run(sym)
            s = report.summary()
            print()
            print("=" * 60)
            print(f"  Бэктест: {s['symbol']}")
            print(f"  Период:  {s['period']}")
            print("=" * 60)
            print(f"  Сигналов всего:    {s['total_signals']}")
            print(f"  Закрыто:           {s['closed']} (WIN: {s['wins']}, LOSS: {s['losses']})")
            print(f"  Открыто на конце:  {s['open_at_end']}")
            print(f"  Win rate:          {s['win_rate_pct']}%")
            print(f"  Средний R:         {s['avg_r_per_trade']}")
            print(f"  Profit factor:     {s['profit_factor']}")
            print(f"  Общий результат:   {s['total_r']} R")
            print(f"  Max drawdown:      {s['max_drawdown_r']} R")
            all_reports.append(s)
        except Exception as e:
            print(f"[backtest] Ошибка для {sym}: {e}")

    # Агрегированный результат по всем.
    if len(all_reports) > 1:
        total_sig = sum(r["total_signals"] for r in all_reports)
        total_wins = sum(r["wins"] for r in all_reports)
        total_losses = sum(r["losses"] for r in all_reports)
        total_r = sum(r["total_r"] for r in all_reports)
        closed = total_wins + total_losses
        wr = (total_wins / closed * 100) if closed else 0
        print()
        print("=" * 60)
        print("  ИТОГО ПО ВСЕМ СИМВОЛАМ")
        print("=" * 60)
        print(f"  Сигналов:     {total_sig}")
        print(f"  Win rate:     {wr:.1f}% ({total_wins}/{closed})")
        print(f"  Общий P&L:    {total_r:.2f} R")


if __name__ == "__main__":
    main()
