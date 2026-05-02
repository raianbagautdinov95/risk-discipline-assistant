"""Движок сигналов: комбинирует технические индикаторы в итоговое решение BUY/SELL/HOLD.

Принцип работы:
1. На старшем таймфрейме (1H) определяем направление тренда — это ФИЛЬТР.
   Лонги разрешены только при UP-тренде, шорты — только при DOWN.
   На боковике (SIDEWAYS) — сигналов нет.
2. На младшем таймфрейме (15m) считаем "голосование" индикаторов.
   Каждый индикатор даёт свой вклад (с весом) за BUY или за SELL.
3. Итоговая уверенность = доля "голосов" в пользу направления.
4. Стоп-лосс считается от ATR (реальной волатильности), тейк-профит = 1:2 от стопа.
5. Если R:R ниже минимального — сигнал отбрасываем.

Это классический multi-factor confluence подход.
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
    reasons: List[str]       # читаемое обоснование
    indicators_snapshot: Dict[str, Any]
    timestamp: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SignalEngine:
    """Генератор сигналов на основе мультитаймфрейм-анализа."""

    def __init__(self, trading_config, risk_limits: RiskLimits):
        self.cfg = trading_config
        self.risk = risk_limits
        # {(symbol, action): timestamp последнего сигнала}
        # Используется для cooldown — не генерируем одинаковый сигнал подряд.
        self._last_signal_ts: Dict = {}

    # ------------------------------------------------------------------ #
    # Публичный API                                                      #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        symbol: str,
        entry_snapshot: Dict[str, Any],
        trend_snapshot: Dict[str, Any],
        htf_snapshot: Dict[str, Any] = None,
    ) -> Signal:
        """Главный метод — строит Signal на основе двух (или трёх) таймфреймов.

        htf_snapshot (4H) — опциональный верхний фильтр. Если он несовпадает с
        1H — сигнал либо режется по уверенности, либо отбрасывается.
        """
        trend_1h = trend_snapshot.get("trend", "SIDEWAYS")
        trend_4h = htf_snapshot.get("trend", "SIDEWAYS") if htf_snapshot else None
        price = entry_snapshot["price"]
        atr = entry_snapshot.get("atr") or (price * 0.01)  # fallback 1%

        votes_buy, votes_sell, buy_reasons, sell_reasons = self._vote(
            entry_snapshot, trend_snapshot
        )

        total = votes_buy + votes_sell
        # Нет данных для решения.
        if total == 0:
            return self._hold(symbol, price, trend_1h, entry_snapshot, ["Индикаторы не дали явных сигналов"])

        # Требуем минимальную абсолютную силу сигнала. Иначе случайный
        # слабый голос даст ложные 100% уверенности.
        MIN_TOTAL_VOTES = 3.0
        if total < MIN_TOTAL_VOTES:
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                [f"Слишком мало подтверждений от индикаторов ({total:.1f} из ~3+)"]
            )

        # Решение в пользу большинства. В финальные reasons попадают только
        # аргументы, поддерживающие принятое решение.
        if votes_buy > votes_sell:
            action = "BUY"
            confidence = (votes_buy / total) * 100
            reasons = buy_reasons
        elif votes_sell > votes_buy:
            action = "SELL"
            confidence = (votes_sell / total) * 100
            reasons = sell_reasons
        else:
            return self._hold(symbol, price, trend_1h, entry_snapshot, ["Силы быков и медведей равны"])

        # Фильтр тренда со старшего таймфрейма (1H).
        if action == "BUY" and trend_1h == "DOWN":
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                ["Есть сигнал на покупку, но 1H тренд — нисходящий. Ждём."]
            )
        if action == "SELL" and trend_1h == "UP":
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                ["Есть сигнал на продажу, но 1H тренд — восходящий. Ждём."]
            )
        if trend_1h == "SIDEWAYS" and confidence < 75:
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                ["Рынок в боковике, сигнал недостаточно сильный для входа"]
            )

        # Верхний фильтр 4H (если передан).
        if trend_4h is not None:
            if action == "BUY" and trend_4h == "DOWN":
                return self._hold(
                    symbol, price, trend_1h, entry_snapshot,
                    [f"1H и 15m бычьи, но 4H тренд — нисходящий. Не торгуем против макро-тренда."]
                )
            if action == "SELL" and trend_4h == "UP":
                return self._hold(
                    symbol, price, trend_1h, entry_snapshot,
                    [f"1H и 15m медвежьи, но 4H тренд — восходящий. Не торгуем против макро-тренда."]
                )
            # Бонус к уверенности при согласии всех трёх таймфреймов.
            if (action == "BUY" and trend_4h == "UP") or (action == "SELL" and trend_4h == "DOWN"):
                # Небольшой буст — но не выходим за 100%.
                confidence = min(100.0, confidence * 1.15)
                reasons_prefix_trend = f"Тренд 4H/1H: {trend_4h}/{trend_1h} (согласованы)"
            else:
                reasons_prefix_trend = f"Тренд 4H/1H: {trend_4h}/{trend_1h}"
        else:
            reasons_prefix_trend = f"Тренд 1H: {trend_1h}"

        # Минимальный порог уверенности.
        if confidence < self.cfg.min_confidence:
            return self._hold(
                symbol, price, trend_1h, entry_snapshot,
                [f"Уверенность {confidence:.0f}% < порога {self.cfg.min_confidence:.0f}%"]
            )

        # Требование "сильной" конфлюэнции: без дивергенции/паттерна на уровне
        # сигнал, основанный только на простых индикаторах, — слишком шумный.
        if getattr(self.cfg, "require_strong_confluence", False):
            has_divergence = entry_snapshot.get("rsi_divergence") or entry_snapshot.get("macd_divergence")
            candle = entry_snapshot.get("candle_pattern")
            at_level = entry_snapshot.get("at_key_level")
            has_key_pattern = bool(candle and at_level)
            if not (has_divergence or has_key_pattern):
                return self._hold(
                    symbol, price, trend_1h, entry_snapshot,
                    ["Нет сильного подтверждения (дивергенции/паттерна на уровне)"]
                )

        # Cooldown: если такой же сигнал был недавно — пропускаем.
        cooldown = getattr(self.cfg, "cooldown_bars", 0)
        if cooldown > 0:
            # В реальном времени время берём в секундах; в бэктесте — timestamp
            # последней свечи. Интервал 15m свечи = 900 секунд.
            now_ts = entry_snapshot.get("timestamp") or int(time.time())
            key = (symbol, action)
            last_ts = self._last_signal_ts.get(key)
            if last_ts is not None:
                # Сколько 15m свечей прошло с прошлого сигнала?
                bar_seconds = 900
                bars_passed = (now_ts - last_ts) / bar_seconds
                if bars_passed < cooldown:
                    return self._hold(
                        symbol, price, trend_1h, entry_snapshot,
                        [f"Cooldown: прошло {bars_passed:.0f} свечей из {cooldown}"]
                    )

        # Расчёт стопа и тейка на основе ATR.
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
                [f"R:R {rr:.2f} < минимального {self.risk.min_risk_reward}"]
            )

        reasons.insert(0, reasons_prefix_trend)
        reasons.insert(1, f"Консенсус индикаторов 15m: {action} ({confidence:.0f}%)")

        sig_ts = entry_snapshot.get("timestamp") or int(time.time())
        # Запоминаем для cooldown.
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
    # Внутреннее                                                         #
    # ------------------------------------------------------------------ #

    def _hold(self, symbol, price, trend_1h, snapshot, reasons) -> Signal:
        return Signal(
            symbol=symbol, action="HOLD", confidence=0.0,
            entry=round(price, 6), stop_loss=0.0, take_profit=0.0, risk_reward=0.0,
            trend_1h=trend_1h, reasons=reasons,
            indicators_snapshot=snapshot, timestamp=int(time.time()),
        )

    def _vote(self, s: Dict[str, Any], t: Dict[str, Any]):
        """Собирает голоса индикаторов. Каждый индикатор имеет вес — важность его сигнала.

        Возвращает (votes_buy, votes_sell, buy_reasons, sell_reasons).
        Причины разделены: в итоговое уведомление попадают только те, что
        поддерживают принятое решение."""
        buy = 0.0
        sell = 0.0
        buy_reasons: List[str] = []
        sell_reasons: List[str] = []

        rsi = s.get("rsi")
        if rsi is not None:
            if rsi < 30:
                buy += 2.0
                buy_reasons.append(f"RSI {rsi:.1f} в зоне перепроданности (<30)")
            elif rsi > 70:
                sell += 2.0
                sell_reasons.append(f"RSI {rsi:.1f} в зоне перекупленности (>70)")
            elif rsi < 45:
                buy += 0.5
            elif rsi > 55:
                sell += 0.5

        # MACD: пересечение сигнальной линии.
        md = s.get("macd_diff")
        md_prev = s.get("macd_diff_prev")
        if md is not None and md_prev is not None:
            if md_prev <= 0 < md:
                buy += 2.0
                buy_reasons.append("MACD пересёк сигнальную вверх (бычий кросс)")
            elif md_prev >= 0 > md:
                sell += 2.0
                sell_reasons.append("MACD пересёк сигнальную вниз (медвежий кросс)")
            elif md > 0:
                buy += 0.5
            elif md < 0:
                sell += 0.5

        # EMA структура.
        price = s.get("price")
        ema20 = s.get("ema_20")
        ema50 = s.get("ema_50")
        if price and ema20 and ema50:
            if price > ema20 > ema50:
                buy += 1.5
                buy_reasons.append("Цена выше EMA20 > EMA50 (бычья структура)")
            elif price < ema20 < ema50:
                sell += 1.5
                sell_reasons.append("Цена ниже EMA20 < EMA50 (медвежья структура)")

        # Bollinger: отскок от полос.
        bb_up = s.get("bb_upper")
        bb_lo = s.get("bb_lower")
        if price and bb_up and bb_lo:
            if price <= bb_lo:
                buy += 1.5
                buy_reasons.append("Касание нижней полосы Боллинджера — возможный отскок")
            elif price >= bb_up:
                sell += 1.5
                sell_reasons.append("Касание верхней полосы Боллинджера — возможный откат")

        # Стохастик.
        sk = s.get("stoch_k")
        sd = s.get("stoch_d")
        if sk is not None and sd is not None:
            if sk < 20 and sk > sd:
                buy += 1.0
                buy_reasons.append(f"Стохастик вышел из перепроданности ({sk:.0f})")
            elif sk > 80 and sk < sd:
                sell += 1.0
                sell_reasons.append(f"Стохастик вышел из перекупленности ({sk:.0f})")

        # ADX + DI: сила тренда.
        adx = s.get("adx")
        dip = s.get("di_plus")
        dim = s.get("di_minus")
        if adx and dip and dim and adx >= 25:
            if dip > dim:
                buy += 1.0
                buy_reasons.append(f"ADX {adx:.0f}, DI+ > DI- (сильный восходящий импульс)")
            else:
                sell += 1.0
                sell_reasons.append(f"ADX {adx:.0f}, DI- > DI+ (сильный нисходящий импульс)")

        # Всплеск объёма — усиливает сторону большинства.
        vs = s.get("volume_spike")
        if vs and vs >= 1.5:
            if buy > sell:
                buy += 1.0
                buy_reasons.append(f"Всплеск объёма x{vs:.1f} подтверждает покупки")
            elif sell > buy:
                sell += 1.0
                sell_reasons.append(f"Всплеск объёма x{vs:.1f} подтверждает продажи")

        # Поддержка/сопротивление: у поддержки — аргумент в пользу покупки
        # (поддержка может удержать цену), у сопротивления — аргумент в пользу продажи.
        support = s.get("support")
        resistance = s.get("resistance")
        if price and support and resistance:
            atr = s.get("atr") or 0
            if abs(price - support) < max(atr * 0.5, price * 0.005):
                buy += 1.0
                buy_reasons.append(f"Цена у поддержки {support:.4f}")
            elif abs(price - resistance) < max(atr * 0.5, price * 0.005):
                sell += 1.0
                sell_reasons.append(f"Цена у сопротивления {resistance:.4f}")

        # --- ПРОДВИНУТЫЕ ПАТТЕРНЫ ---

        # Дивергенции — один из самых сильных сигналов разворота (вес 2.5).
        rsi_div = s.get("rsi_divergence")
        if rsi_div == "BULLISH":
            buy += 2.5
            buy_reasons.append("Бычья дивергенция RSI (цена ниже, RSI выше) — сильный разворотный сигнал")
        elif rsi_div == "BEARISH":
            sell += 2.5
            sell_reasons.append("Медвежья дивергенция RSI (цена выше, RSI ниже) — сильный разворотный сигнал")

        macd_div = s.get("macd_divergence")
        if macd_div == "BULLISH":
            buy += 2.0
            buy_reasons.append("Бычья дивергенция MACD — подтверждение разворота")
        elif macd_div == "BEARISH":
            sell += 2.0
            sell_reasons.append("Медвежья дивергенция MACD — подтверждение разворота")

        # Свечные паттерны — сильные только на ключевых уровнях.
        candle = s.get("candle_pattern")
        at_level = s.get("at_key_level")
        if candle and at_level:
            level_bonus = 2.0  # полный вес у ключевого уровня
            if candle in ("BULLISH_ENGULFING", "HAMMER") and at_level == "SUPPORT":
                buy += level_bonus
                buy_reasons.append(f"Паттерн {candle} на поддержке — высокая вероятность отскока")
            elif candle in ("BEARISH_ENGULFING", "SHOOTING_STAR") and at_level == "RESISTANCE":
                sell += level_bonus
                sell_reasons.append(f"Паттерн {candle} на сопротивлении — высокая вероятность отката")
            elif candle == "DOJI":
                # Doji на уровне = неопределённость, но подсказка о развороте.
                if at_level == "SUPPORT":
                    buy += 0.5
                    buy_reasons.append("Doji на поддержке — нерешительность после снижения")
                elif at_level == "RESISTANCE":
                    sell += 0.5
                    sell_reasons.append("Doji на сопротивлении — нерешительность после роста")
        elif candle in ("BULLISH_ENGULFING", "HAMMER"):
            # Не у уровня — даём слабый бонус.
            buy += 0.5
        elif candle in ("BEARISH_ENGULFING", "SHOOTING_STAR"):
            sell += 0.5

        # Боллинджер-сжатие — не направленный голос, а информационный.
        if s.get("bollinger_squeeze"):
            # Squeeze усиливает сторону большинства (ожидается импульс в её направлении).
            if buy > sell and buy > 0:
                buy += 0.7
                buy_reasons.append("Боллинджер-сжатие: низкая волатильность, ожидается импульс")
            elif sell > buy and sell > 0:
                sell += 0.7
                sell_reasons.append("Боллинджер-сжатие: низкая волатильность, ожидается импульс")

        return buy, sell, buy_reasons, sell_reasons
