"""REST API для Flutter-приложения и Flutter Web сайта.

Установка и запуск:
    pip install fastapi uvicorn
    uvicorn api:app --reload --host 0.0.0.0 --port 8765

Порт 8765 выбран, чтобы не конфликтовать с типичными сервисами (порт 8000
часто занят всякими gateway/dashboard/API gateway на Windows).

ВАЖНО: при старте API автоматически запускается ФОНОВЫЙ СКАНЕР, который
анализирует рынок каждые scan_interval_sec (по умолчанию 15 минут) и
наполняет трекер реальными сигналами. Отдельно запускать main.py не нужно.

Endpoints:
    GET  /health                   — проверка работы
    GET  /symbols                  — список отслеживаемых монет
    GET  /signals/active           — открытые сигналы (сейчас в позиции)
    GET  /signals/history          — история закрытых сигналов
    GET  /signals/scan             — немедленный скан всех монет
    GET  /signal/{symbol}          — анализ конкретной монеты по требованию
    GET  /stats/summary            — общая статистика (за всё время)
    GET  /stats/period/{period}    — статистика за период: day | week | month
    GET  /symbol/{symbol}/stats    — статистика по монете

CORS разрешён для всех источников, чтобы Flutter Web (обычно localhost:xxxx)
мог обращаться к этому API без проблем.
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
        "FastAPI не установлен. Выполните: pip install fastapi uvicorn"
    )

from dotenv import load_dotenv

load_dotenv()

from main import SignalBot  # noqa: E402

# Lock, чтобы скан не запустился из фонового таска и из ручного /signals/scan одновременно.
_scan_lock = threading.Lock()


def _do_scan(bot: SignalBot):
    """Запускает scan_all под локом. Используется и фоновым таском, и ручным endpoint."""
    with _scan_lock:
        return bot.scan_all()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Стартуем фоновый сканер при старте и аккуратно останавливаем при выключении."""
    bot = get_bot()
    stop_event = asyncio.Event()
    interval = bot.trading_cfg.scan_interval_sec

    async def scanner_loop():
        # Первый скан — сразу, не ждём 15 минут.
        print(f"[scanner] Фоновый сканер запущен. Интервал: {interval}с")
        while not stop_event.is_set():
            try:
                await asyncio.to_thread(_do_scan, bot)
            except Exception as e:
                print(f"[scanner] Ошибка скана: {e}")
            # Ждём интервал или пока не прилетит сигнал остановки.
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=interval)
            except asyncio.TimeoutError:
                pass
        print("[scanner] Фоновый сканер остановлен")

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

# CORS нужен для браузера (Flutter Web шлёт preflight OPTIONS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ленивая инициализация бота — чтобы импорт модуля не падал, если нет сети.
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
# СИГНАЛЫ                                                                #
# ---------------------------------------------------------------------- #


@app.get("/signals/active")
def active_signals():
    """Открытые сделки — те, что ещё не хитнули TP/SL и не устарели."""
    data = get_bot().tracker._load()
    return [s for s in data if s.get("status") == "OPEN"]


@app.get("/signals/history")
def history(limit: int = 100):
    """История закрытых сигналов (WIN/LOSS/EXPIRED)."""
    data = get_bot().tracker._load()
    closed = [s for s in data if s.get("status") != "OPEN"]
    # Последние сверху.
    closed.sort(key=lambda s: s.get("closed_at") or s.get("created_at") or "", reverse=True)
    return closed[:limit]


@app.get("/signal/{symbol}")
def single_signal(symbol: str):
    """Анализирует конкретную монету по запросу — для on-demand проверок."""
    bot = get_bot()
    try:
        sig = bot.analyze_symbol(symbol.upper())
        if sig is None:
            raise HTTPException(404, "Не удалось получить данные для символа")
        return sig.to_dict()
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Ошибка анализа: {e}")


@app.get("/signals/scan")
def scan_now():
    """Ручной скан всех монет. Возвращает активные сигналы.
    Использует общий lock с фоновым сканером — одновременных сканов не будет."""
    bot = get_bot()
    signals = _do_scan(bot)
    return [s.to_dict() for s in signals if s is not None and s.action != "HOLD"]


@app.get("/scanner/status")
def scanner_status():
    """Статус фонового сканера и конфиг."""
    bot = get_bot()
    return {
        "interval_sec": bot.trading_cfg.scan_interval_sec,
        "symbols": bot.trading_cfg.symbols,
        "min_confidence": bot.trading_cfg.min_confidence,
        "cooldown_bars": getattr(bot.trading_cfg, "cooldown_bars", 0),
        "is_scanning_now": _scan_lock.locked(),
    }


# ---------------------------------------------------------------------- #
# СТАТИСТИКА                                                             #
# ---------------------------------------------------------------------- #


def _period_to_seconds(period: str) -> int:
    mapping = {
        "day": 24 * 3600,
        "week": 7 * 24 * 3600,
        "month": 30 * 24 * 3600,
    }
    if period not in mapping:
        raise HTTPException(400, f"period должен быть: {', '.join(mapping)}")
    return mapping[period]


@app.get("/stats/summary")
def stats_summary():
    """Общая статистика за всё время."""
    return get_bot().tracker.summary()


@app.get("/stats/period/{period}")
def stats_period(period: str):
    """Статистика за период: day | week | month."""
    seconds = _period_to_seconds(period)
    summary = get_bot().tracker.summary(since_seconds=seconds)
    summary["period"] = period
    return summary


@app.get("/stats/timeseries")
def stats_timeseries(period: str = "week"):
    """Разбивка P&L по дням за указанный период — для построения графика."""
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

    # Сортируем по дате.
    return sorted(by_day.values(), key=lambda d: d["date"])


@app.get("/symbol/{symbol}/stats")
def symbol_stats(symbol: str):
    """Статистика по одной монете."""
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
