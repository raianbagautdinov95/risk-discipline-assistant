"""Outcome tracker for live signals.

Idea: every time the bot runs a scan, we check previously issued signals that
are still OPEN. For each one we look at the latest candles and mark whether TP
was hit, SL was hit, or the signal hasn't closed yet.

The result is a `reports/signals_tracked.json` file with the bot's real
statistics: how many signals played out, the win rate, and the profit factor.
"""
import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import numpy as np

from data.market_data import MarketData


class _NumpyAwareEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


class SignalTracker:
    """Stores signals with their status: OPEN, WIN, LOSS, EXPIRED.
    On each update_open_signals() call it checks prices and closes those where
    TP/SL has been breached.
    """

    # Maximum lifetime of a signal — once it expires we mark it EXPIRED.
    DEFAULT_TTL_HOURS = 12

    def __init__(self, reports_dir: str = "reports", market: Optional[MarketData] = None,
                 entry_timeframe: str = "15m"):
        self.dir = Path(reports_dir)
        self.dir.mkdir(exist_ok=True)
        self.file = self.dir / "signals_tracked.json"
        self.market = market or MarketData()
        self.entry_tf = entry_timeframe

    # ------------------------------------------------------------------ #
    # Storage                                                            #
    # ------------------------------------------------------------------ #

    def _load(self) -> List[Dict[str, Any]]:
        if not self.file.exists():
            return []
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def _save(self, data: List[Dict[str, Any]]) -> None:
        # Keep at most 2000 records.
        data = data[-2000:]
        self.file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, cls=_NumpyAwareEncoder),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------ #
    # API                                                                #
    # ------------------------------------------------------------------ #

    def add_signal(self, signal: Dict[str, Any]) -> None:
        """Registers a new signal as OPEN."""
        if signal.get("action") == "HOLD":
            return
        # Deduplication: if we already have an active signal for this symbol
        # with the same action, don't add it (most likely the same situation).
        data = self._load()
        for s in data:
            if (s["symbol"] == signal["symbol"]
                    and s.get("status") == "OPEN"
                    and s["action"] == signal["action"]):
                # A similar open signal already exists.
                return

        entry = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "signal_timestamp": signal["timestamp"],
            "symbol": signal["symbol"],
            "action": signal["action"],
            "entry": signal["entry"],
            "stop_loss": signal["stop_loss"],
            "take_profit": signal["take_profit"],
            "risk_reward": signal.get("risk_reward", 0),
            "confidence": signal.get("confidence", 0),
            "trend_1h": signal.get("trend_1h"),
            "reasons": signal.get("reasons", []),
            "status": "OPEN",
            "closed_at": None,
            "bars_to_exit": None,
            "pnl_r": None,
        }
        data.append(entry)
        self._save(data)

    def update_open_signals(self, ttl_hours: int = DEFAULT_TTL_HOURS) -> Dict[str, int]:
        """Iterates over all OPEN signals, pulls fresh candles and closes those
        where TP/SL has been breached or the TTL has expired. Returns a summary
        of the changes."""
        data = self._load()
        changes = {"closed_win": 0, "closed_loss": 0, "expired": 0, "still_open": 0}

        now_ts = int(datetime.now(timezone.utc).timestamp())

        for s in data:
            if s.get("status") != "OPEN":
                continue

            # TTL: if the signal is older than ttl_hours, close it as EXPIRED.
            age_sec = now_ts - int(s["signal_timestamp"])
            if age_sec > ttl_hours * 3600:
                s["status"] = "EXPIRED"
                s["closed_at"] = datetime.now(timezone.utc).isoformat()
                s["pnl_r"] = 0.0
                changes["expired"] += 1
                continue

            # Pull candles since the signal was issued.
            candles = self.market.get_candles(s["symbol"], self.entry_tf, limit=100)
            if candles is None:
                changes["still_open"] += 1
                continue

            # Only candles after the signal.
            future = candles[candles["timestamp"] > s["signal_timestamp"] * 1000].reset_index(drop=True)
            if len(future) == 0:
                changes["still_open"] += 1
                continue

            outcome, pnl_r, bars = self._check_outcome(s, future)
            if outcome in ("WIN", "LOSS"):
                s["status"] = outcome
                s["closed_at"] = datetime.now(timezone.utc).isoformat()
                s["bars_to_exit"] = bars
                s["pnl_r"] = pnl_r
                if outcome == "WIN":
                    changes["closed_win"] += 1
                else:
                    changes["closed_loss"] += 1
            else:
                changes["still_open"] += 1

        self._save(data)
        return changes

    def close_early(self, symbol: str, opposite_action: str, current_price: float,
                    reason: str = "Opposite signal from the bot") -> int:
        """Closes all OPEN positions for a symbol when an opposite signal
        appears. Returns the number of positions closed.

        opposite_action — the action of the new signal ('BUY' or 'SELL'). We
        close positions WHOSE direction is opposite to the new signal (i.e. if
        the new signal is SELL, we close open BUYs).
        """
        closing_action = "BUY" if opposite_action == "SELL" else "SELL"
        data = self._load()
        closed = 0
        for s in data:
            if (s.get("status") == "OPEN"
                    and s["symbol"] == symbol
                    and s["action"] == closing_action):
                # Compute PnL in R at the current price.
                risk = abs(s["entry"] - s["stop_loss"])
                if risk <= 0:
                    continue
                if s["action"] == "BUY":
                    pnl_r = (current_price - s["entry"]) / risk
                else:
                    pnl_r = (s["entry"] - current_price) / risk

                s["status"] = "WIN" if pnl_r > 0 else "LOSS"
                s["closed_at"] = datetime.now(timezone.utc).isoformat()
                s["close_reason"] = "EARLY_EXIT"
                s["close_price"] = current_price
                s["exit_comment"] = reason
                s["pnl_r"] = round(pnl_r, 3)
                closed += 1

        if closed > 0:
            self._save(data)
        return closed

    def summary(self, since_seconds: Optional[int] = None) -> Dict[str, Any]:
        """Summary of all accumulated statistics.
        since_seconds — if given, take only signals closed within the last N seconds.
        """
        data = self._load()
        if not data:
            return {"total": 0, "message": "No data yet"}

        if since_seconds is not None:
            cutoff = datetime.now(timezone.utc).timestamp() - since_seconds

            def is_recent(s):
                ca = s.get("closed_at")
                if not ca:
                    return False
                try:
                    return datetime.fromisoformat(ca.replace("Z", "+00:00")).timestamp() >= cutoff
                except Exception:
                    return False

            data_closed = [s for s in data if s.get("status") in ("WIN", "LOSS") and is_recent(s)]
            data = data_closed + [s for s in data if s.get("status") == "OPEN"]

        wins = [s for s in data if s.get("status") == "WIN"]
        losses = [s for s in data if s.get("status") == "LOSS"]
        open_ = [s for s in data if s.get("status") == "OPEN"]
        expired = [s for s in data if s.get("status") == "EXPIRED"]
        closed = len(wins) + len(losses)

        win_rate = (len(wins) / closed * 100) if closed else 0
        total_r = sum(s.get("pnl_r") or 0 for s in wins + losses)
        gross_win = sum(s.get("pnl_r") or 0 for s in wins)
        gross_loss = sum(s.get("pnl_r") or 0 for s in losses)
        profit_factor = (gross_win / abs(gross_loss)) if gross_loss != 0 else None

        # Per symbol.
        by_symbol: Dict[str, Dict[str, int]] = {}
        for s in data:
            sym = s["symbol"]
            by_symbol.setdefault(sym, {"total": 0, "wins": 0, "losses": 0})
            by_symbol[sym]["total"] += 1
            if s.get("status") == "WIN":
                by_symbol[sym]["wins"] += 1
            elif s.get("status") == "LOSS":
                by_symbol[sym]["losses"] += 1

        return {
            "total": len(data),
            "open": len(open_),
            "closed": closed,
            "wins": len(wins),
            "losses": len(losses),
            "expired": len(expired),
            "win_rate_pct": round(win_rate, 1),
            "total_r": round(total_r, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor is not None else None,
            "by_symbol": by_symbol,
        }

    # ------------------------------------------------------------------ #

    def _check_outcome(self, s: Dict[str, Any], future_df):
        """Checks whether TP/SL has been breached in future_df. Returns (outcome, pnl_r, bars)."""
        risk = abs(s["entry"] - s["stop_loss"])
        if risk <= 0:
            return "OPEN", None, 0

        is_long = s["action"] == "BUY"
        for bar_idx, (_, row) in enumerate(future_df.iterrows(), start=1):
            high, low = row["high"], row["low"]
            if is_long:
                sl_hit = low <= s["stop_loss"]
                tp_hit = high >= s["take_profit"]
            else:
                sl_hit = high >= s["stop_loss"]
                tp_hit = low <= s["take_profit"]

            if sl_hit and tp_hit:
                # Pessimistically — stop first.
                return "LOSS", -1.0, bar_idx
            if sl_hit:
                return "LOSS", -1.0, bar_idx
            if tp_hit:
                reward = abs(s["take_profit"] - s["entry"])
                return "WIN", reward / risk, bar_idx

        return "OPEN", None, len(future_df)
