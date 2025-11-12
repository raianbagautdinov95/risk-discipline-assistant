import requests
from typing import Dict, Any, Optional
from config.settings import AIConfig


class DeepSeekAnalyzer:
    def __init__(self, config: AIConfig):
        self.config = config
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {config.deepseek_api_key}",
            "Content-Type": "application/json"
        }

    def analyze_market_data(self, market_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:

        try:
            prompt = self._build_prompt(market_data)

            payload = {
                "model": self.config.model,
                "messages": [
                    {"role": "system",
                     "content": "You are a crypto trading analyst. Provide concise market analysis with signals."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            analysis = result["choices"][0]["message"]["content"]

            return self._parse_analysis(analysis)
        except Exception as e:
            print(f"DeepSeek analysis error: {e}")
            return None

    def _build_prompt(self, data: Dict[str, Any]) -> str:

        return f"""
        Analyze BTC/USDT market data:
        - Current Price: {data.get('current_price', 'N/A')}
        - 24h Change: {data.get('change_24h', 'N/A')}%
        - Volume: {data.get('volume', 'N/A')}
        - RSI: {data.get('rsi', 'N/A')}
        - MACD: {data.get('macd', 'N/A')}
        - Support: {data.get('support', 'N/A')}
        - Resistance: {data.get('resistance', 'N/A')}

        Provide:
        1. Signal: BUY/SELL/HOLD
        2. Confidence: 0-100%
        3. Reasoning: brief explanation
        4. Entry: suggested entry price
        5. Stop Loss: suggested SL
        6. Take Profit: suggested TP
        """

    def _parse_analysis(self, analysis: str) -> Dict[str, Any]:

        signal = "HOLD"
        if "BUY" in analysis.upper():
            signal = "BUY"
        elif "SELL" in analysis.upper():
            signal = "SELL"

        return {
            "signal": signal,
            "raw_analysis": analysis,
            "timestamp": int(time.time())
        }