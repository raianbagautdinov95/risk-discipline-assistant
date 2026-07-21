"""Signal engine: combines technical indicators into a final BUY/SELL/HOLD decision.

How it works:
1. On the higher timeframe (1H) we determine the trend direction — this is the FILTER.
   Longs are allowed only during an UP trend, shorts — only during a DOWN trend.
   In a range (SIDEWAYS) — no signals.
2. On the lower timeframe (15m) we tally an indicator "vote".
   Each indicator contributes (with a weight) toward BUY or toward SELL.
3. Final confidence = share of "votes" in favor of the direction.
4. The stop-loss is derived from ATR (real volatility), the take-profit = 1:2 of the stop.
5. If the R:R is below the minimum — the signal is discarded.

This is the classic multi-factor confluence approach.
"""
from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
import time

from config.risk_config import RiskLimits


@dataclass
class Signal:
    symbol: str
    action: str              # BUY | SELL | HOLD
    confidence: float        # 0..100
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    trend_1h: str            # UP | DOWN | SIDEWAYS
    reasons: List[str]       # human-readable justification
    indicators_snapshot: Dict[str, Any]
    timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SignalEngine:
    """Signal generator based on multi-timeframe analysis."""

    def __init__(self, trading_config, risk_limits: RiskLimits):
        self.cfg = trading_config
        self.risk = risk_limits
        # {(symbol, action): timestamp of the last signal}
        # Used for cooldown — we don't generate the same signal repeatedly.
        self._last_signal_ts: Dict = {}

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        symbol: str,
        entry_snapshot: Dict[str, Any],
        trend_snapshot: Dict[str, Any],
        htf_snapshot: Dict[str, Any] = None,
    ) -> Signal:
        """Main method — builds a Signal from two (or three) timeframes.

        htf_snapshot (4H) — optional upper filter. If it disagrees with
        1H — the signal is either reduced in confidence or discarded.
        """
        trend_1h = trend_snapshot.get("trend", "SIDEWAYS")
        trend_4h = htf_snapshot.get("trend", "SIDEWAYS") if htf_snapshot else None
        price = entry_snapshot["price"]
        atr = entry_snapshot.get("atr") or (price * 0.01)  # fallback 1%

        votes_buy, votes_sell, buy_reasons, sell_reasons = self._vote(
            entry_snapshot, trend_snapshot
        )

        total = votes_buy + votes_sell
        # No data to make a decision.
        if total == 0:
            return self._hold(symbol, price, trend_1h, entry_snapshot, ["Indicators gave no clear signals"])

        # Require a minimum absolute signal strength. Otherwise a random
        # weak vote would produce a false 100% confidence.
        MIN_TOTAL_VOTES = 3.0
        if total < MIN_TOTAL_VOTES:
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                [f"Too few confirmations from indicators ({total:.1f} out of ~3+)"]
            )

        # Decision goes to the majority. Only the arguments supporting the
        # chosen decision make it into the final reasons.
        if votes_buy > votes_sell:
            action = "BUY"
            confidence = (votes_buy / total) * 100
            reasons = buy_reasons
        elif votes_sell > votes_buy:
            action = "SELL"
            confidence = (votes_sell / total) * 100
            reasons = sell_reasons
        else:
            return self._hold(symbol, price, trend_1h, entry_snapshot, ["Bulls and bears are evenly matched"])

        # Trend filter from the higher timeframe (1H).
        if action == "BUY" and trend_1h == "DOWN":
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                ["There is a buy signal, but the 1H trend is down. Waiting."]
            )
        if action == "SELL" and trend_1h == "UP":
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                ["There is a sell signal, but the 1H trend is up. Waiting."]
            )
        if trend_1h == "SIDEWAYS" and confidence < 75:
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                ["Market is ranging, the signal is not strong enough to enter"]
            )

        # Upper 4H filter (if provided).
        if trend_4h is not None:
            if action == "BUY" and trend_4h == "DOWN":
                return self._hold(
                    symbol, price, trend_1h, entry_snapshot,
                    [f"1H and 15m are bullish, but the 4H trend is down. We don't trade against the macro trend."]
                )
            if action == "SELL" and trend_4h == "UP":
                return self._hold(
                    symbol, price, trend_1h, entry_snapshot,
                    [f"1H and 15m are bearish, but the 4H trend is up. We don't trade against the macro trend."]
                )
            # Confidence bonus when all three timeframes agree.
            if (action == "BUY" and trend_4h == "UP") or (action == "SELL" and trend_4h == "DOWN"):
                # Small boost — but we don't exceed 100%.
                confidence = min(100.0, confidence * 1.15)
                reasons_prefix_trend = f"Trend 4H/1H: {trend_4h}/{trend_1h} (aligned)"
            else:
                reasons_prefix_trend = f"Trend 4H/1H: {trend_4h}/{trend_1h}"
        else:
            reasons_prefix_trend = f"Trend 1H: {trend_1h}"

        # Minimum confidence threshold.
        if confidence < self.cfg.min_confidence:
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                [f"Confidence {confidence:.0f}% < threshold {self.cfg.min_confidence:.0f}%"]
            )

        # Requirement of "strong" confluence: without a divergence/pattern at a level,
        # a signal based only on simple indicators is too noisy.
        if getattr(self.cfg, "require_strong_confluence", False):
            has_divergence = entry_snapshot.get("rsi_divergence") or entry_snapshot.get("macd_divergence")
            candle = entry_snapshot.get("candle_pattern")
            at_level = entry_snapshot.get("at_key_level")
            has_key_pattern = bool(candle and at_level)
            if not (has_divergence or has_key_pattern):
                return self._hold(
                    symbol, price, trend_1h, entry_snapshot,
                    ["No strong confirmation (divergence/pattern at a level)"]
                )

        # Cooldown: if the same signal fired recently — we skip it.
        cooldown = getattr(self.cfg, "cooldown_bars", 0)
        if cooldown > 0:
            # In real time we take the time in seconds; in a backtest — the timestamp
            # of the last candle. A 15m candle interval = 900 seconds.
            now_ts = entry_snapshot.get("timestamp") or int(time.time())
            key = (symbol, action)
            last_ts = self._last_signal_ts.get(key)
            if last_ts is not None:
                # How many 15m candles have passed since the previous signal?
                bar_seconds = 900
                bars_passed = (now_ts - last_ts) / bar_seconds
                if bars_passed < cooldown:
                    return self._hold(
                        symbol, price, trend_1h, entry_snapshot,
                        [f"Cooldown: {bars_passed:.0f} of {cooldown} candles passed"]
                    )

        # Compute the stop and take based on ATR.
        if action == "BUY":
            stop_loss = price - atr * self.cfg.stop_loss_atr_mult
            take_profit = price + atr * self.cfg.take_profit_atr_mult
        else:
            stop_loss = price + atr * self.cfg.stop_loss_atr_mult
            take_profit = price - atr * self.cfg.take_profit_atr_mult

        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        rr = reward / risk if risk > 0 else 0.0

        if rr < self.risk.min_risk_reward:
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                [f"R:R {rr:.2f} < minimum {self.risk.min_risk_reward}"]
            )

        reasons.insert(0, reasons_prefix_trend)
        reasons.insert(1, f"15m indicator consensus: {action} ({confidence:.0f}%)")

        sig_ts = entry_snapshot.get("timestamp") or int(time.time())
        # Remember it for cooldown.
        self._last_signal_ts[(symbol, action)] = sig_ts

        return Signal(
            symbol=symbol,
            action=action,
            confidence=round(confidence, 1),
            entry=round(price, 6),
            stop_loss=round(stop_loss, 6),
            take_profit=round(take_profit, 6),
            risk_reward=round(rr, 2),
            trend_1h=trend_1h,
            reasons=reasons,
            indicators_snapshot=entry_snapshot,
            timestamp=sig_ts,
        )

    # ------------------------------------------------------------------ #
    # Internal                                                           #
    # ------------------------------------------------------------------ #

    def _hold(self, symbol, price, trend_1h, snapshot, reasons) -> Signal:
        return Signal(
            symbol=symbol, action="HOLD", confidence=0.0,
            entry=round(price, 6), stop_loss=0.0, take_profit=0.0, risk_reward=0.0,
            trend_1h=trend_1h, reasons=reasons,
            indicators_snapshot=snapshot, timestamp=int(time.time()),
        )

    def _vote(self, s: Dict[str, Any], t: Dict[str, Any]):
        """Collects indicator votes. Each indicator has a weight — the importance of its signal.

        Returns (votes_buy, votes_sell, buy_reasons, sell_reasons).
        The reasons are split: only those supporting the chosen decision
        make it into the final notification."""
        buy = 0.0
        sell = 0.0
        buy_reasons: List[str] = []
        sell_reasons: List[str] = []

        rsi = s.get("rsi")
        if rsi is not None:
            if rsi < 30:
                buy += 2.0
                buy_reasons.append(f"RSI {rsi:.1f} in oversold zone (<30)")
            elif rsi > 70:
                sell += 2.0
                sell_reasons.append(f"RSI {rsi:.1f} in overbought zone (>70)")
            elif rsi < 45:
                buy += 0.5
            elif rsi > 55:
                sell += 0.5

        # MACD: signal line crossover.
        md = s.get("macd_diff")
        md_prev = s.get("macd_diff_prev")
        if md is not None and md_prev is not None:
            if md_prev <= 0 < md:
                buy += 2.0
                buy_reasons.append("MACD crossed the signal line upward (bullish cross)")
            elif md_prev >= 0 > md:
                sell += 2.0
                sell_reasons.append("MACD crossed the signal line downward (bearish cross)")
            elif md > 0:
                buy += 0.5
            elif md < 0:
                sell += 0.5

        # EMA structure.
        price = s.get("price")
        ema20 = s.get("ema_20")
        ema50 = s.get("ema_50")
        if price and ema20 and ema50:
            if price > ema20 > ema50:
                buy += 1.5
                buy_reasons.append("Price above EMA20 > EMA50 (bullish structure)")
            elif price < ema20 < ema50:
                sell += 1.5
                sell_reasons.append("Price below EMA20 < EMA50 (bearish structure)")

        # Bollinger: bounce off the bands.
        bb_up = s.get("bb_upper")
        bb_lo = s.get("bb_lower")
        if price and bb_up and bb_lo:
            if price <= bb_lo:
                buy += 1.5
                buy_reasons.append("Touch of the lower Bollinger band — possible bounce")
            elif price >= bb_up:
                sell += 1.5
                sell_reasons.append("Touch of the upper Bollinger band — possible pullback")

        # Stochastic.
        sk = s.get("stoch_k")
        sd = s.get("stoch_d")
        if sk is not None and sd is not None:
            if sk < 20 and sk > sd:
                buy += 1.0
                buy_reasons.append(f"Stochastic emerged from oversold ({sk:.0f})")
            elif sk > 80 and sk < sd:
                sell += 1.0
                sell_reasons.append(f"Stochastic emerged from overbought ({sk:.0f})")

        # ADX + DI: trend strength.
        adx = s.get("adx")
        dip = s.get("di_plus")
        dim = s.get("di_minus")
        if adx and dip and dim and adx >= 25:
            if dip > dim:
                buy += 1.0
                buy_reasons.append(f"ADX {adx:.0f}, DI+ > DI- (strong upward momentum)")
            else:
                sell += 1.0
                sell_reasons.append(f"ADX {adx:.0f}, DI- > DI+ (strong downward momentum)")

        # Volume spike — reinforces the majority side.
        vs = s.get("volume_spike")
        if vs and vs >= 1.5:
            if buy > sell:
                buy += 1.0
                buy_reasons.append(f"Volume spike x{vs:.1f} confirms buying")
            elif sell > buy:
                sell += 1.0
                sell_reasons.append(f"Volume spike x{vs:.1f} confirms selling")

        # Support/resistance: near support — an argument in favor of buying
        # (support may hold the price), near resistance — an argument in favor of selling.
        support = s.get("support")
        resistance = s.get("resistance")
        if price and support and resistance:
            atr = s.get("atr") or 0
            if abs(price - support) < max(atr * 0.5, price * 0.005):
                buy += 1.0
                buy_reasons.append(f"Price near support {support:.4f}")
            elif abs(price - resistance) < max(atr * 0.5, price * 0.005):
                sell += 1.0
                sell_reasons.append(f"Price near resistance {resistance:.4f}")

        # --- ADVANCED PATTERNS ---

        # Divergences — one of the strongest reversal signals (weight 2.5).
        rsi_div = s.get("rsi_divergence")
        if rsi_div == "BULLISH":
            buy += 2.5
            buy_reasons.append("Bullish RSI divergence (price lower, RSI higher) — strong reversal signal")
        elif rsi_div == "BEARISH":
            sell += 2.5
            sell_reasons.append("Bearish RSI divergence (price higher, RSI lower) — strong reversal signal")

        macd_div = s.get("macd_divergence")
        if macd_div == "BULLISH":
            buy += 2.0
            buy_reasons.append("Bullish MACD divergence — reversal confirmation")
        elif macd_div == "BEARISH":
            sell += 2.0
            sell_reasons.append("Bearish MACD divergence — reversal confirmation")

        # Candlestick patterns — strong only at key levels.
        candle = s.get("candle_pattern")
        at_level = s.get("at_key_level")
        if candle and at_level:
            level_bonus = 2.0  # full weight at a key level
            if candle in ("BULLISH_ENGULFING", "HAMMER") and at_level == "SUPPORT":
                buy += level_bonus
                buy_reasons.append(f"{candle} pattern at support — high probability of a bounce")
            elif candle in ("BEARISH_ENGULFING", "SHOOTING_STAR") and at_level == "RESISTANCE":
                sell += level_bonus
                sell_reasons.append(f"{candle} pattern at resistance — high probability of a pullback")
            elif candle == "DOJI":
                # Doji at a level = uncertainty, but a hint of a reversal.
                if at_level == "SUPPORT":
                    buy += 0.5
                    buy_reasons.append("Doji at support — indecision after a decline")
                elif at_level == "RESISTANCE":
                    sell += 0.5
                    sell_reasons.append("Doji at resistance — indecision after a rise")
        elif candle in ("BULLISH_ENGULFING", "HAMMER"):
            # Not at a level — we give a weak bonus.
            buy += 0.5
        elif candle in ("BEARISH_ENGULFING", "SHOOTING_STAR"):
            sell += 0.5

        # Bollinger squeeze — not a directional vote, but informational.
        if s.get("bollinger_squeeze"):
            # A squeeze reinforces the majority side (an impulse is expected in its direction).
            if buy > sell and buy > 0:
                buy += 0.7
                buy_reasons.append("Bollinger squeeze: low volatility, an impulse is expected")
            elif sell > buy and sell > 0:
                sell += 0.7
                sell_reasons.append("Bollinger squeeze: low volatility, an impulse is expected")

        return buy, sell, buy_reasons, sell_reasons
