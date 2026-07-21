"""Optional second opinion from DeepSeek AI.
Called ONLY if DEEPSEEK_API_KEY is set in .env.
Used as a sanity check on the already-computed technical signal."""
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
        """Asks the AI to evaluate an already-formed technical signal.

        Returns a dict:
          { "agree": bool, "confidence": 0..100, "comment": str }
        or None if the AI is unavailable/errors out.
        """
        if not self.is_available():
            return None

        prompt = self._build_prompt(symbol, technical_signal, indicators)
        try:
            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content":
                     "You are an experienced crypto analyst. You are given a technical signal and "
                     "indicators. Evaluate the signal. Respond with STRICTLY valid JSON "
                     "without a markdown wrapper, using the schema: "
                     '{"agree": true|false, "confidence": 0-100, "comment": "short text"}'},
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
Analyze the trading signal for {symbol}.

Technical signal:
- Action: {sig.get('action')}
- Confidence: {sig.get('confidence')}%
- Entry: {sig.get('entry')}
- Stop: {sig.get('stop_loss')}
- Take: {sig.get('take_profit')}
- R:R: {sig.get('risk_reward')}
- Trend 1H: {sig.get('trend_1h')}

Key indicators (15m):
- RSI: {ind.get('rsi')}
- MACD diff: {ind.get('macd_diff')}
- ADX: {ind.get('adx')}
- Price vs EMA20/EMA50: {ind.get('price')} / {ind.get('ema_20')} / {ind.get('ema_50')}
- Support/Resistance: {ind.get('support')} / {ind.get('resistance')}
- ATR: {ind.get('atr')}
- Volume spike: x{ind.get('volume_spike')}

Do you agree with the signal? Respond in JSON.
""".strip()
