# exchanges/okx_client.py
import hmac
import hashlib
import time
import requests
import json
from typing import Dict, Any, Optional


class OKXClient:


    def __init__(self, api_key: str, api_secret: str, passphrase: str, testnet: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.base_url = "https://www.okx.com"
        self.testnet = testnet



    def _get_server_time(self) -> str:

        try:
            resp = requests.get(f"{self.base_url}/api/v5/public/time", timeout=5).json()
            if resp.get("code") == "0" and resp.get("data"):
                return str(int(resp["data"][0]["ts"]) // 1000)
        except Exception as e:
            print("⚠️ Не удалось получить время с сервера:", e)
        return str(int(time.time()))

    def _signature(self, method: str, endpoint: str, body: str = "") -> Dict[str, str]:

        timestamp = self._get_server_time()
        message = f"{timestamp}{method}{endpoint}{body}"
        mac = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": mac,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }



    def get_market_price(self, symbol: str) -> Optional[float]:

        try:
            endpoint = f"/api/v5/market/ticker?instId={symbol}-USDT"
            resp = requests.get(self.base_url + endpoint, timeout=10).json()
            if resp.get("code") == "0" and resp.get("data"):
                return float(resp["data"][0]["last"])
            print(f"❌ Price Error: {resp.get('msg', 'Unknown')}")
            return None
        except Exception as e:
            print(f"OKX price exception: {e}")
            return None

    def get_balance(self) -> float:

        for inst_type in ("SPOT", "FUNDING", "MARGIN", "SWAP", "FUTURES", "UNIFIED"):
            try:
                endpoint = f"/api/v5/account/balance?instType={inst_type}"
                headers = self._signature("GET", endpoint)
                resp = requests.get(self.base_url + endpoint, headers=headers, timeout=10).json()

                if resp.get("code") == "0" and resp.get("data"):
                    for detail in resp["data"][0].get("details", []):
                        if detail.get("ccy") == "USDT":
                            bal = float(detail.get("cashBal", 0))
                            if bal > 0:
                                print(f"✅ Найдено {bal} USDT в {inst_type}")
                                return bal
            except Exception as e:
                print(f"OKX balance ({inst_type}) exception: {e}")

        print("❌ USDT не найден ни в одной книге")
        return 0.0

    def place_order(self, symbol: str, side: str, qty: float, **kwargs) -> Dict[str, Any]:

        try:
            endpoint = "/api/v5/trade/order"
            body_json = json.dumps(
                {
                    "instId": f"{symbol}-USDT",
                    "tdMode": "cash",
                    "side": side.lower(),
                    "ordType": "market",
                    "sz": str(qty),
                }
            )
            headers = self._signature("POST", endpoint, body_json)
            resp = requests.post(
                self.base_url + endpoint,
                data=body_json,
                headers=headers,
                timeout=10,
            ).json()
            return resp
        except Exception as e:
            print(f"OKX order exception: {e}")
            return {"code": "-1", "msg": str(e)}