import requests
from typing import Dict, Any, Optional


class MarketData:
    def __init__(self):
        self.base_url = "https://api.bybit.com"

    def get_klines(self, symbol: str, interval: str, limit: int = 100) -> Optional[list]:

        try:
            endpoint = "/v5/market/kline"
            params = {
                "category": "linear",
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }

            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data.get("retCode") == 0:
                return data["result"]["list"]
            return None
        except Exception as e:
            print(f"Error fetching klines: {e}")
            return None

    def get_orderbook(self, symbol: str, limit: int = 25) -> Optional[Dict[str, Any]]:

        try:
            endpoint = "/v5/market/orderbook"
            params = {
                "category": "linear",
                "symbol": symbol,
                "limit": limit
            }

            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            return response.json()
        except Exception as e:
            print(f"Error fetching orderbook: {e}")
            return None

    def get_funding_rate(self, symbol: str) -> Optional[float]:

        try:
            endpoint = "/v5/market/funding/history"
            params = {
                "category": "linear",
                "symbol": symbol,
                "limit": 1
            }

            response = requests.get(
                f"{self.base_url}{endpoint}",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            if data.get("retCode") == 0 and data["result"]["list"]:
                return float(data["result"]["list"][0]["fundingRate"])
            return None
        except Exception as e:
            print(f"Error fetching funding rate: {e}")
            return None