"""Signal history. Saves every non-HOLD signal to a JSON file.
Useful later when evaluating which signals played out and which didn't."""
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

import numpy as np


class _NumpyAwareEncoder(json.JSONEncoder):
    """Can serialize numpy types (bool_, int64, float64, ndarray, etc.).
    Needed because pandas/numpy often supply their own types instead of native Python ones."""
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


class SignalHistory:
    def __init__(self, reports_dir: str = "reports"):
        self.dir = Path(reports_dir)
        self.dir.mkdir(exist_ok=True)
        self.file = self.dir / "signals_history.json"

    def record(self, signal: Dict[str, Any], ai_review: Dict[str, Any] = None) -> None:
        """Adds a signal to the history. HOLD signals are skipped (there are many and they aren't interesting)."""
        if signal.get("action") == "HOLD":
            return

        entry = {
            "datetime": datetime.utcnow().isoformat() + "Z",
            **signal,
        }
        if ai_review:
            entry["ai_review"] = ai_review

        data = self._load()
        data.append(entry)
        # Keep at most 1000 records so the file doesn't bloat.
        data = data[-1000:]
        self.file.write_text(
            json.dumps(data, indent=2, ensure_ascii=False, cls=_NumpyAwareEncoder),
            encoding="utf-8",
        )

    def _load(self) -> List[Dict[str, Any]]:
        if not self.file.exists():
            return []
        try:
            return json.loads(self.file.read_text(encoding="utf-8"))
        except Exception:
            return []

    def summary(self) -> Dict[str, Any]:
        """Summary of the accumulated history for a quick overview."""
        data = self._load()
        if not data:
            return {"total": 0, "buy": 0, "sell": 0, "by_symbol": {}}

        buy = sum(1 for s in data if s.get("action") == "BUY")
        sell = sum(1 for s in data if s.get("action") == "SELL")
        by_symbol: Dict[str, int] = {}
        for s in data:
            by_symbol[s["symbol"]] = by_symbol.get(s["symbol"], 0) + 1

        return {
            "total": len(data),
            "buy": buy,
            "sell": sell,
            "by_symbol": by_symbol,
            "first": data[0].get("datetime"),
            "last": data[-1].get("datetime"),
        }
