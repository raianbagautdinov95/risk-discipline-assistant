"""REST API for the Flutter app and the Flutter Web site.

Installation and startup:
    pip install fastapi uvicorn
    uvicorn api:app --reload --host 0.0.0.0 --port 8765

Port 8765 was chosen to avoid conflicting with typical services (port 8000
is often taken by various gateway/dashboard/API gateway apps on Windows).

IMPORTANT: on API startup a BACKGROUND SCANNER is launched automatically. It
analyzes the market every scan_interval_sec (15 minutes by default) and
fills the tracker with real signals. There's no need to run main.py separately.

Endpoints:
    GET  /health                   — health check
    GET  /symbols                  — list of tracked coins
    GET  /signals/active           — open signals (currently in a position)
    GET  /signals/history          — history of closed signals
    GET  /signals/scan             — immediate scan of all coins
    GET  /signal/{symbol}          — on-demand analysis of a specific coin
    GET  /stats/summary            — overall statistics (all time)
    GET  /stats/period/{period}    — statistics for a period: day | week | month
    GET  /symbol/{symbol}/stats    — statistics for a coin

CORS is allowed for all origins so that Flutter Web (usually localhost:xxxx)
can reach this API without issues.
"""
import asyncio
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Optional

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:  # pragma: no cover
    raise SystemExit(
        "FastAPI is not installed. Run: pip install fastapi uvicorn"
    )

from dotenv import load_dotenv

load_dotenv()

from main import SignalBot  # noqa: E402

# Lock so a scan doesn't run from the background task and the manual /signals/scan at the same time.
_scan_lock = threading.Lock()


def _do_scan(bot: SignalBot):
    """Runs scan_all under the lock. Used by both the background task and the manual endpoint."""
    with _scan_lock:
        return bot.scan_all()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the background scanner on startup and shut it down gracefully on exit."""
    bot = get_bot()
    stop_event = asyncio.Event()
    interval = bot.trading_cfg.scan_interval_sec

    async def scanner_loop():
        # First scan — immediately, we don't wait 15 minutes.
        print(f"[scanner] Background scanner started. Interval: {interval}s")
        while not stop_event.is_set():
            try:
                await asyncio.to_thread(_do_scan, bot)
            except Exception as e:
                print(f"[scanner] Scan error: {e}")
            # Wait for the interval or until a stop signal arrives.
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
        print("[scanner] Background scanner stopped")

    task = asyncio.create_task(scanner_loop())
    try:
        yield
    finally:
        stop_event.set()
        try:
            await asyncio.wait_for(task, timeout=5)
        except (asyncio.TimeoutError, Exception):
            pass


app = FastAPI(title="Crypto Signal Bot API", version="1.0.0", lifespan=lifespan)

# CORS is needed for the browser (Flutter Web sends preflight OPTIONS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Lazy bot initialization — so importing the module doesn't fail if there's no network.
_bot: Optional[SignalBot] = None


def get_bot() -> SignalBot:
    global _bot
    if _bot is None:
        _bot = SignalBot()
    return _bot


# ---------------------------------------------------------------------- #
# BASIC                                                                  #
# ---------------------------------------------------------------------- #


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/symbols")
def symbols():
    return {"symbols": get_bot().trading_cfg.symbols}


# ---------------------------------------------------------------------- #
# SIGNALS                                                                #
# ---------------------------------------------------------------------- #


@app.get("/signals/active")
def active_signals():
    """Open trades — those that haven't hit TP/SL yet and haven't expired."""
    data = get_bot().tracker._load()
    return [s for s in data if s.get("status") == "OPEN"]


@app.get("/signals/history")
def history(limit: int = 100):
    """History of closed signals (WIN/LOSS/EXPIRED)."""
    data = get_bot().tracker._load()
    closed = [s for s in data if s.get("status") != "OPEN"]
    # Most recent first.
    closed.sort(key=lambda s: s.get("closed_at") or s.get("created_at") or "", reverse=True)
    return closed[:limit]


@app.get("/signal/{symbol}")
def single_signal(symbol: str):
    """Analyzes a specific coin on request — for on-demand checks."""
    bot = get_bot()
    try:
        sig = bot.analyze_symbol(symbol.upper())
        if sig is None:
            raise HTTPException(404, "Failed to fetch data for the symbol")
        return sig.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis error: {e}")


@app.get("/signals/scan")
def scan_now():
    """Manual scan of all coins. Returns active signals.
    Uses a shared lock with the background scanner — no concurrent scans."""
    bot = get_bot()
    signals = _do_scan(bot)
    return [s.to_dict() for s in signals if s is not None and s.action != "HOLD"]


@app.get("/scanner/status")
def scanner_status():
    """Background scanner status and config."""
    bot = get_bot()
    return {
        "interval_sec": bot.trading_cfg.scan_interval_sec,
        "symbols": bot.trading_cfg.symbols,
        "min_confidence": bot.trading_cfg.min_confidence,
        "cooldown_bars": getattr(bot.trading_cfg, "cooldown_bars", 0),
        "is_scanning_now": _scan_lock.locked(),
    }


# ---------------------------------------------------------------------- #
# STATISTICS                                                             #
# ---------------------------------------------------------------------- #


def _period_to_seconds(period: str) -> int:
    mapping = {
        "day": 24 * 3600,
        "week": 7 * 24 * 3600,
        "month": 30 * 24 * 3600,
    }
    if period not in mapping:
        raise HTTPException(400, f"period must be one of: {', '.join(mapping)}")
    return mapping[period]


@app.get("/stats/summary")
def stats_summary():
    """Overall statistics for all time."""
    return get_bot().tracker.summary()


@app.get("/stats/period/{period}")
def stats_period(period: str):
    """Statistics for a period: day | week | month."""
    seconds = _period_to_seconds(period)
    summary = get_bot().tracker.summary(since_seconds=seconds)
    summary["period"] = period
    return summary


@app.get("/stats/timeseries")
def stats_timeseries(period: str = "week"):
    """P&L breakdown by day for the given period — for building a chart."""
    seconds = _period_to_seconds(period)
    cutoff = datetime.now(timezone.utc).timestamp() - seconds
    data = get_bot().tracker._load()

    by_day: dict = {}
    for s in data:
        if s.get("status") not in ("WIN", "LOSS"):
            continue
        ca = s.get("closed_at")
        if not ca:
            continue
        try:
            ts = datetime.fromisoformat(ca.replace("Z", "+00:00")).timestamp()
        except Exception:
            continue
        if ts < cutoff:
            continue
        day = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        by_day.setdefault(day, {"date": day, "trades": 0, "wins": 0, "losses": 0, "pnl_r": 0.0})
        by_day[day]["trades"] += 1
        if s.get("status") == "WIN":
            by_day[day]["wins"] += 1
        else:
            by_day[day]["losses"] += 1
        by_day[day]["pnl_r"] += s.get("pnl_r") or 0.0

    # Sort by date.
    return sorted(by_day.values(), key=lambda d: d["date"])


@app.get("/symbol/{symbol}/stats")
def symbol_stats(symbol: str):
    """Statistics for a single coin."""
    data = get_bot().tracker._load()
    rel = [s for s in data if s["symbol"] == symbol.upper()]
    closed = [s for s in rel if s.get("status") in ("WIN", "LOSS")]
    wins = [s for s in closed if s.get("status") == "WIN"]
    pnl = sum(s.get("pnl_r") or 0 for s in closed)
    return {
        "symbol": symbol.upper(),
        "total": len(rel),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(closed) - len(wins),
        "win_rate_pct": round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "pnl_r": round(pnl, 2),
    }
