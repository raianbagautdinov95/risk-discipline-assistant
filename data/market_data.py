"""Получение рыночных данных с OKX через публичные endpoints (без API-ключей)."""
from typing import List, Optional, Dict, Any
import requests
import pandas as pd


class MarketData:
    BASE_URL = "https://www.okx.com"

    # OKX принимает эти значения для bar:
    #   1m, 3m, 5m, 15m, 30m, 1H, 2H, 4H, 6H, 12H, 1D, 1W, 1M
    VALID_TIMEFRAMES = {"1m", "3m", "5m", "15m", "30m", "1H", "2H", "4H", "6H", "12H", "1D", "1W", "1M"}

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    def get_candles(self, symbol: str, timeframe: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """Возвращает DataFrame со свечами [timestamp, open, high, low, close, volume].
        symbol в формате 'BTC-USDT'. Данные отсортированы по возрастанию времени.
        """
        if timeframe not in self.VALID_TIMEFRAMES:
            raise ValueError(f"timeframe '{timeframe}' не поддерживается OKX")

        try:
            url = f"{self.BASE_URL}/api/v5/market/candles"
            params = {"instId": symbol, "bar": timeframe, "limit": str(min(limit, 300))}
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("code") != "0" or not payload.get("data"):
                return None

            # OKX возвращает: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
            rows = payload["data"]
            df = pd.DataFrame(
                rows,
                columns=["timestamp", "open", "high", "low", "close", "volume",
                         "vol_ccy", "vol_ccy_quote", "confirm"]
            )
            # Приводим типы и сортируем по возрастанию времени.
            df = df.astype({
                "timestamp": "int64",
                "open": "float64", "high": "float64", "low": "float64",
                "close": "float64", "volume": "float64",
            })
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df = df.sort_values("timestamp").reset_index(drop=True)
            return df[["timestamp", "datetime", "open", "high", "low", "close", "volume"]]
        except requests.RequestException as e:
            print(f"[market_data] HTTP error for {symbol} {timeframe}: {e}")
            return None
        except Exception as e:
            print(f"[market_data] Unexpected error for {symbol} {timeframe}: {e}")
            return None

    def get_historical_candles(self, symbol: str, timeframe: str,
                                total_candles: int) -> Optional[pd.DataFrame]:
        """Скачивает большой объём истории через пагинацию (endpoint history-candles).
        OKX возвращает максимум 100 за запрос, поэтому делаем несколько вызовов.
        total_candles — сколько свечей нужно всего (например, 2000 для ~3 недель на 15m).
        """
        if timeframe not in self.VALID_TIMEFRAMES:
            raise ValueError(f"timeframe '{timeframe}' не поддерживается OKX")

        all_rows = []
        before_ts = ""  # "" = самые свежие
        batch_size = 100  # максимум для history-candles
        collected = 0
        max_iters = (total_candles // batch_size) + 5  # страховка от бесконечного цикла
        iters = 0

        while collected < total_candles and iters < max_iters:
            iters += 1
            try:
                url = f"{self.BASE_URL}/api/v5/market/history-candles"
                params = {
                    "instId": symbol, "bar": timeframe,
                    "limit": str(batch_size),
                }
                if before_ts:
                    # OKX: after — метка, ДО которой тянуть (идём в прошлое).
                    params["after"] = before_ts

                resp = requests.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                payload = resp.json()
                if payload.get("code") != "0" or not payload.get("data"):
                    break

                rows = payload["data"]
                if not rows:
                    break

                all_rows.extend(rows)
                collected = len(all_rows)
                # Самая старая свеча в этом ответе — её timestamp для следующего запроса.
                before_ts = rows[-1][0]
            except Exception as e:
                print(f"[market_data] Ошибка пагинации для {symbol} {timeframe}: {e}")
                break

        if not all_rows:
            return None

        df = pd.DataFrame(
            all_rows,
            columns=["timestamp", "open", "high", "low", "close", "volume",
                     "vol_ccy", "vol_ccy_quote", "confirm"]
        ).drop_duplicates(subset=["timestamp"])
        df = df.astype({
            "timestamp": "int64",
            "open": "float64", "high": "float64", "low": "float64",
            "close": "float64", "volume": "float64",
        })
        df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df[["timestamp", "datetime", "open", "high", "low", "close", "volume"]]

    def get_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Текущая цена и 24ч статистика."""
        try:
            url = f"{self.BASE_URL}/api/v5/market/ticker"
            resp = requests.get(url, params={"instId": symbol}, timeout=self.timeout)
            resp.raise_for_status()
            payload = resp.json()
            if payload.get("code") != "0" or not payload.get("data"):
                return None
            d = payload["data"][0]
            return {
                "symbol": symbol,
                "last": float(d["last"]),
                "open_24h": float(d["open24h"]),
                "high_24h": float(d["high24h"]),
                "low_24h": float(d["low24h"]),
                "vol_24h": float(d["vol24h"]),
                "change_24h_pct": (float(d["last"]) / float(d["open24h"]) - 1) * 100
                                   if float(d["open24h"]) > 0 else 0.0,
            }
        except Exception as e:
            print(f"[market_data] Ticker error for {symbol}: {e}")
            return None
