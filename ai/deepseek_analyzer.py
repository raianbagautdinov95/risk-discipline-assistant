"""Опциональный второй мнение от DeepSeek AI.
Вызывается ТОЛЬКО если в .env задан DEEPSEEK_API_KEY.
Используется как sanity-check к уже посчитанному техническому сигналу."""
import time
import json
import requests
from typing import Dict, Any, Optional

from config.settings import AIConfig


class DeepSeekAnalyzer:
    def __init__(self, config: AIConfig):
        self.config = config
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    def is_available(self) -> bool:
        return self.config.enabled and bool(self.config.api_key)

    def review_signal(self, symbol: str, technical_signal: Dict[str, Any],
                      indicators: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Просит AI оценить уже сформированный технический сигнал.

        Возвращает dict:
          { "agree": bool, "confidence": 0..100, "comment": str }
        или None, если AI недоступен/ошибка.
        """
        if not self.is_available():
            return None

        prompt = self._build_prompt(symbol, technical_signal, indicators)
        try:
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content":
                     "Ты — опытный крипто-аналитик. Тебе даётся технический сигнал и "
                     "индикаторы. Оцени сигнал. Отвечай СТРОГО валидным JSON "
                     "без markdown-обёртки, со схемой: "
                     '{"agree": true|false, "confidence": 0-100, "comment": "краткий текст"}'},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "response_format": {"type": "json_object"},
            }

            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers, json=payload, timeout=30,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return {
                "agree": bool(parsed.get("agree", False)),
                "confidence": float(parsed.get("confidence", 0)),
                "comment": str(parsed.get("comment", "")),
                "timestamp": int(time.time()),
            }
        except Exception as e:
            print(f"[deepseek] error: {e}")
            return None

    def _build_prompt(self, symbol: str, sig: Dict[str, Any], ind: Dict[str, Any]) -> str:
        return f"""
Проанализируй торговый сигнал по {symbol}.

Технический сигнал:
- Действие: {sig.get('action')}
- Уверенность: {sig.get('confidence')}%
- Вход: {sig.get('entry')}
- Стоп: {sig.get('stop_loss')}
- Тейк: {sig.get('take_profit')}
- R:R: {sig.get('risk_reward')}
- Тренд 1H: {sig.get('trend_1h')}

Ключевые индикаторы (15m):
- RSI: {ind.get('rsi')}
- MACD diff: {ind.get('macd_diff')}
- ADX: {ind.get('adx')}
- Цена vs EMA20/EMA50: {ind.get('price')} / {ind.get('ema_20')} / {ind.get('ema_50')}
- Поддержка/Сопротивление: {ind.get('support')} / {ind.get('resistance')}
- ATR: {ind.get('atr')}
- Всплеск объёма: x{ind.get('volume_spike')}

Согласен ли ты с сигналом? Ответь в JSON.
""".strip()
