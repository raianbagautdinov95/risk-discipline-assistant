"""aiogram handlers — implements all bot commands and the /trade FSM flow."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message, ReplyKeyboardRemove

from app.bot.keyboards import (
    BTN_HELP,
    BTN_JOURNAL,
    BTN_RULES,
    BTN_SCAN,
    BTN_SETTINGS,
    BTN_SIGNALS,
    BTN_STATS,
    BTN_TRADE,
    direction_kb,
    emotion_kb,
    main_menu_kb,
    onboarding_skip_kb,
    onboarding_style_kb,
    settings_kb,
    skip_kb,
    trade_from_signal_kb,
)
from app.bot.states import Onboarding, SettingsEdit, TradeCheck
from aiogram.types import BufferedInputFile
from app.bot.scheduler import manual_morning_checkin, manual_remind, manual_review
from app.schemas import CloseTradeRequest, PositionCalcRequest
from app.services import achievements, daily_plan_service, export_service
from app.services.position_calc import calculate_position
from app.services.voice_service import make_voice_service
import io
from app.config import settings as cfg
from app.database import AsyncSessionLocal
from app.schemas import TradeRequest, UserSettingsUpdate
from app.services import stats_service
from app.services.ai_coach import AICoach
from app.services.ai_risk_officer import AIRiskOfficer
from app.services.decision_engine import decide
from app.services.risk_engine import UserPolicy
from app.services.signal_client import SignalClient

logger = logging.getLogger(__name__)
router = Router()

SKIP_TOKENS = {"skip", "-", "—"}


# ---------------------------------------------------------------------------
# Static commands
# ---------------------------------------------------------------------------

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    is_new_user = False
    async with AsyncSessionLocal() as session:
        from sqlalchemy import select
        from app.models import User
        existing = (
            await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
        ).scalar_one_or_none()
        is_new_user = existing is None
        await stats_service.get_or_create_user(
            session,
            telegram_id=message.from_user.id,
            username=message.from_user.username,
        )
        await session.commit()

    # New users go through a quick onboarding wizard
    if is_new_user:
        await state.set_state(Onboarding.deposit)
        await message.answer(
            "👋 Hi! I'm your Risk Officer for crypto trading.\n\n"
            "I don't trade and I don't give advice — I check every trade "
            "against 8 risk-management rules and block the dangerous ones.\n\n"
            "Let's set you up in 1 minute. Step 1/3:\n"
            "What's your trading deposit, USDT?\n"
            "(type a number, e.g.: 1000)",
            reply_markup=onboarding_skip_kb(),
        )
        return

    await message.answer(
        "Hi! I'm your Risk & Discipline Assistant.\n\n"
        "I help you check discipline and risk BEFORE a trade.\n"
        "I don't give financial advice and I don't promise profit.\n\n"
        "Discipline commands:\n"
        "/trade — check a trade\n"
        "/journal — recent trades\n"
        "/stats — statistics (incl. win-rate)\n"
        "/close 12 win 2.5 — close a trade with its outcome\n"
        "/calc 1000 1 67500 66800 — position calculator\n"
        "/export — export journal to CSV\n"
        "/remind — show open trades\n"
        "/review — weekly AI review (Ollama)\n"
        "/plan — set today's plan\n"
        "/rules — risk rules\n"
        "/settings — settings\n\n"
        "🎙 Voice works too! Record: \"BTC long 67500 stop 66800 take 69200\".\n\n"
        "Market scanner commands:\n"
        "/scan — full market scan\n"
        "/signals — active signals\n"
        "/analyze BTC-USDT — analyze a pair\n\n"
        "/help — help\n\n"
        "🔔 Every day at 22:00 UTC I'll remind you about open trades.\n"
        "📊 Every Sunday at 18:00 UTC I'll send a weekly AI review.\n"
        "👇 Use the buttons below — it's faster.",
        reply_markup=main_menu_kb(),
    )


# ---------------------------------------------------------------------------
# Reply-keyboard button aliases — fire only when no FSM state is active.
# Each button just calls the matching command handler.
# ---------------------------------------------------------------------------

@router.message(StateFilter(None), F.text == BTN_SIGNALS)
async def btn_signals(message: Message) -> None:
    await cmd_signals(message)


@router.message(StateFilter(None), F.text == BTN_SCAN)
async def btn_scan(message: Message) -> None:
    await cmd_scan(message)


@router.message(StateFilter(None), F.text == BTN_TRADE)
async def btn_trade(message: Message, state: FSMContext) -> None:
    await cmd_trade(message, state)


@router.message(StateFilter(None), F.text == BTN_JOURNAL)
async def btn_journal(message: Message) -> None:
    await cmd_journal(message)


@router.message(StateFilter(None), F.text == BTN_STATS)
async def btn_stats(message: Message) -> None:
    await cmd_stats(message)


@router.message(StateFilter(None), F.text == BTN_SETTINGS)
async def btn_settings(message: Message) -> None:
    await cmd_settings(message)


@router.message(StateFilter(None), F.text == BTN_RULES)
async def btn_rules(message: Message) -> None:
    await cmd_rules(message)


@router.message(StateFilter(None), F.text == BTN_HELP)
async def btn_help(message: Message) -> None:
    await cmd_help(message)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "I'll ask you questions about the trade (pair, entry, SL, TP, deposit, "
        "risk, leverage, reason, setup, emotions). Based on the math + two AI "
        "models I'll give a verdict: ALLOWED / FORBIDDEN / WAIT.\n\n"
        "⚠️ This is not financial advice."
    )


# ---------------------------------------------------------------------------
# Signal scanner commands — proxy to the signal-bot HTTP API
# ---------------------------------------------------------------------------

def _signal_client() -> SignalClient:
    return SignalClient(cfg.signal_bot_url)


def _format_signal(s: dict) -> str:
    """Render a single signal dict (from signal-bot) as a Telegram-friendly block."""
    sym = s.get("symbol", "?")
    action = (s.get("action") or "HOLD").upper()
    arrow = "🟢 BUY" if action == "BUY" else "🔴 SELL" if action == "SELL" else "⚪ HOLD"
    conf = s.get("confidence")
    rr = s.get("risk_reward")
    entry = s.get("entry")
    sl = s.get("stop_loss")
    tp = s.get("take_profit")
    trend = s.get("trend_1h", "—")
    reasons = s.get("reasons") or []
    lines = [
        f"{arrow}  {sym}",
        f"  entry: {entry}   SL: {sl}   TP: {tp}",
    ]
    if isinstance(rr, (int, float)) and rr:
        lines.append(f"  R:R = {round(rr, 2)}")
    if isinstance(conf, (int, float)):
        # Bot gives confidence in 0..100; render as %.
        pct = conf if conf > 1 else conf * 100
        lines.append(f"  confidence: {round(pct)}%   1H trend: {trend}")
    if reasons:
        joined = " · ".join(str(r) for r in reasons[:3])
        lines.append(f"  • {joined}")
    return "\n".join(lines)


async def _render_signal(message: Message, s: dict) -> None:
    """Send a single signal as a message with an inline 'Check discipline' button."""
    text = _format_signal(s)
    symbol = s.get("symbol", "")
    action = (s.get("action") or "HOLD").upper()
    # Inline button only makes sense for actionable signals.
    kb = trade_from_signal_kb(symbol) if action in ("BUY", "SELL") and symbol else None
    await message.answer(text, reply_markup=kb)


@router.message(Command("scan"))
async def cmd_scan(message: Message) -> None:
    await message.answer(
        "⏳ Scanning the market, this takes 10-30 seconds…",
        reply_markup=main_menu_kb(),
    )
    try:
        signals = await _signal_client().scan_now()
    except Exception as exc:
        logger.warning("scan failed: %s", exc)
        await message.answer(
            f"⚠️ Could not reach the signal bot.\n"
            f"Make sure it is running (uvicorn api:app --port 8765).\n"
            f"Error: {exc.__class__.__name__}"
        )
        return
    if not signals:
        await message.answer(
            "Scan finished. No active signals right now — the market is quiet "
            "or the filters are strict.\n\n"
            "You can use /analyze SYMBOL to look at a specific pair."
        )
        return
    await message.answer(f"📡 Signals found: {len(signals)}")
    for s in signals:
        await _render_signal(message, s)


@router.message(Command("signals"))
async def cmd_signals(message: Message) -> None:
    try:
        signals = await _signal_client().get_active()
    except Exception as exc:
        logger.warning("get_active failed: %s", exc)
        await message.answer(
            f"⚠️ Signal bot is unavailable.\n"
            f"Error: {exc.__class__.__name__}"
        )
        return
    if not signals:
        await message.answer(
            "No active signals right now.\nRun a full scan: /scan",
            reply_markup=main_menu_kb(),
        )
        return
    await message.answer(f"📡 Active signals: {len(signals)}")
    for s in signals:
        await _render_signal(message, s)


@router.message(Command("analyze"))
async def cmd_analyze(message: Message) -> None:
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "Specify a pair, for example:\n"
            "/analyze BTC-USDT\n"
            "/analyze ETH-USDT"
        )
        return
    symbol = parts[1].strip().upper()
    await message.answer(f"⏳ Analyzing {symbol}…")
    try:
        s = await _signal_client().analyze(symbol)
    except Exception as exc:
        logger.warning("analyze %s failed: %s", symbol, exc)
        await message.answer(
            f"⚠️ Could not analyze {symbol}.\n"
            f"Check that the pair is on the list (BTC-USDT, ETH-USDT, etc.).\n"
            f"Error: {exc.__class__.__name__}"
        )
        return
    await _render_signal(message, s)


@router.callback_query(F.data.startswith("signal_to_trade:"))
async def cb_signal_to_trade(callback: CallbackQuery, state: FSMContext) -> None:
    """Inline-button click: prefill FSM with signal data, ask only the missing
    fields (deposit, risk, leverage, reason, setup, emotion, losses, consec).
    """
    symbol = callback.data.split(":", 1)[1] if callback.data else ""
    await callback.answer()
    if not symbol:
        await callback.message.answer("⚠️ Couldn't tell which pair to check.")
        return

    # Fetch fresh signal data from the signal-bot (the cached result may be stale).
    try:
        s = await _signal_client().analyze(symbol)
    except Exception as exc:
        logger.warning("signal_to_trade fetch %s failed: %s", symbol, exc)
        await callback.message.answer(
            f"⚠️ Could not fetch the signal data.\nError: {exc.__class__.__name__}"
        )
        return

    action = (s.get("action") or "HOLD").upper()
    if action not in ("BUY", "SELL"):
        await callback.message.answer(
            "This pair is currently HOLD — no signal. Better to skip it."
        )
        return

    direction = "long" if action == "BUY" else "short"
    pair = symbol.replace("-", "/")  # signal-bot uses "BTC-USDT", discipline uses "BTC/USDT"

    await state.clear()
    await state.update_data(
        pair=pair,
        direction=direction,
        entry_price=float(s.get("entry") or 0),
        stop_loss=float(s.get("stop_loss") or 0) or None,
        take_profit=float(s.get("take_profit") or 0) or None,
    )
    await state.set_state(TradeCheck.deposit)

    await callback.message.answer(
        f"✅ Prefilled the signal data:\n"
        f"  Pair: {pair}\n"
        f"  Direction: {direction}\n"
        f"  Entry: {s.get('entry')}\n"
        f"  SL: {s.get('stop_loss')}\n"
        f"  TP: {s.get('take_profit')}\n\n"
        f"Now a few quick questions.\n"
        f"1/8. Deposit, USDT?",
        reply_markup=ReplyKeyboardRemove(),
    )


# ---------------------------------------------------------------------------

@router.message(Command("rules"))
async def cmd_rules(message: Message) -> None:
    await message.answer(
        "🛡️ Hard risk rules (defaults):\n"
        f"• Max risk: {cfg.default_max_risk_percent}% per trade\n"
        f"• Max leverage: x{cfg.default_max_leverage}\n"
        f"• Min R:R: 1:{cfg.default_min_rr}\n"
        f"• Daily loss limit: -{cfg.default_daily_loss_limit}%\n\n"
        "A trade is BLOCKED if:\n"
        "• no stop-loss\n"
        "• 2 losing trades in a row\n"
        "• emotions: anger / panic / greed / FOMO\n"
        "• trying to win losses back (revenge trading)\n\n"
        "You can set your own limits in /settings."
    )


# ---------------------------------------------------------------------------
# /journal & /stats
# ---------------------------------------------------------------------------

@router.message(Command("journal"))
async def cmd_journal(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        trades = await stats_service.list_recent_trades(session, user, limit=10)
        await session.commit()

    if not trades:
        await message.answer("Journal is empty. Run /trade to add your first entry.")
        return

    lines = ["📒 Recent trades:\n"]
    for t in trades:
        rr = f"{t.rr_ratio}" if t.rr_ratio else "—"
        outcome_icon = {
            "WIN": "✅",
            "LOSS": "❌",
            "BREAKEVEN": "⚖️",
            "CANCELED": "🚫",
        }.get(t.outcome, "⏳")
        pnl_str = f" {t.pnl_percent:+.2f}%" if t.pnl_percent is not None else ""
        lines.append(
            f"#{t.id} {outcome_icon} {t.pair} {t.direction} | {t.decision} | "
            f"R:R={rr}{pnl_str} | {t.created_at:%d.%m %H:%M}"
        )
    lines.append("\n💡 Close a trade: /close <id> win|loss|breakeven [pnl%]")
    await message.answer("\n".join(lines))


@router.message(Command("stats"))
async def cmd_stats(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        s = await stats_service.compute_stats(session, user)
        await session.commit()

    if s.total == 0:
        await message.answer("No data yet. Run /trade.")
        return

    body = (
        f"📊 Discipline statistics:\n"
        f"Total checks: {s.total}\n"
        f"  • ALLOWED: {s.allowed}\n"
        f"  • FORBIDDEN: {s.forbidden}\n"
        f"  • WAIT: {s.wait}\n"
        f"Average R:R: {s.avg_rr}\n"
        f"Average risk: {s.avg_risk}%\n"
    )
    if s.closed > 0:
        body += (
            f"\n💰 Real results ({s.closed} closed):\n"
            f"  • WIN: {s.wins}\n"
            f"  • LOSS: {s.losses}\n"
            f"  • BREAKEVEN: {s.breakevens}\n"
            f"  • Win-rate: {s.win_rate_pct}%\n"
            f"  • Average P&L: {s.avg_pnl_percent:+.2f}%\n"
            f"  • Total P&L: {s.total_pnl_percent:+.2f}%\n"
        )
    else:
        body += (
            "\n💡 To see your real win-rate, close trades with:\n"
            "/close <id> win|loss|breakeven [pnl%]\n"
            "Trade IDs are in /journal"
        )
    if s.common_forbid_reasons:
        body += "\n\nMost common block reasons:\n" + "\n".join(
            f"• {reason} ({count})" for reason, count in s.common_forbid_reasons
        )
    await message.answer(body)


# ---------------------------------------------------------------------------
# /settings
# ---------------------------------------------------------------------------

@router.message(Command("settings"))
async def cmd_settings(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        s = user.settings
        await session.commit()

    await message.answer(
        "⚙️ Current settings:\n"
        f"• Max risk: {s.max_risk_percent}%\n"
        f"• Max leverage: x{s.max_leverage}\n"
        f"• Min R:R: 1:{s.min_rr}\n"
        f"• Daily limit: -{s.daily_loss_limit}%\n\n"
        "What would you like to change?",
        reply_markup=settings_kb(),
    )


@router.callback_query(F.data.startswith("set:"))
async def cb_settings_choose(callback: CallbackQuery, state: FSMContext) -> None:
    field = callback.data.split(":", 1)[1]
    await state.set_state(SettingsEdit.value)
    await state.update_data(field=field)
    label = {
        "max_risk_percent": "max risk, %",
        "max_leverage": "max leverage (integer)",
        "min_rr": "min R:R (e.g. 2)",
        "daily_loss_limit": "daily loss limit, %",
    }[field]
    await callback.message.answer(f"Enter the new value: {label}")
    await callback.answer()


@router.message(SettingsEdit.value)
async def settings_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field = data["field"]
    raw = (message.text or "").replace(",", ".").strip()
    try:
        if field == "max_leverage":
            value: float | int = int(raw)
        else:
            value = float(raw)
    except ValueError:
        await message.answer("That doesn't look like a number. Try again or /settings.")
        return

    update = UserSettingsUpdate(**{field: value})
    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        s = user.settings
        if update.max_risk_percent is not None:
            s.max_risk_percent = update.max_risk_percent
        if update.max_leverage is not None:
            s.max_leverage = update.max_leverage
        if update.min_rr is not None:
            s.min_rr = update.min_rr
        if update.daily_loss_limit is not None:
            s.daily_loss_limit = update.daily_loss_limit
        await session.commit()

    await state.clear()
    await message.answer("✅ Saved. View: /settings")


# ---------------------------------------------------------------------------
# /trade flow
# ---------------------------------------------------------------------------

@router.message(Command("trade"))
async def cmd_trade(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(TradeCheck.pair)
    await message.answer(
        "Let's check a trade. I'll ask a few questions.\n\n"
        "1/13. Trading pair? (example: BTC/USDT)",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(TradeCheck.pair)
async def st_pair(message: Message, state: FSMContext) -> None:
    pair = (message.text or "").strip().upper()
    if "/" not in pair or len(pair) > 32:
        await message.answer("Invalid format. Example: BTC/USDT.")
        return
    await state.update_data(pair=pair)
    await state.set_state(TradeCheck.direction)
    await message.answer("2/13. Direction?", reply_markup=direction_kb())


@router.message(TradeCheck.direction)
async def st_direction(message: Message, state: FSMContext) -> None:
    val = (message.text or "").strip().lower()
    if val not in {"long", "short"}:
        await message.answer("Type long or short.")
        return
    await state.update_data(direction=val)
    await state.set_state(TradeCheck.entry_price)
    await message.answer("3/13. Entry price?", reply_markup=ReplyKeyboardRemove())


async def _read_float(message: Message) -> float | None:
    raw = (message.text or "").replace(",", ".").strip()
    try:
        return float(raw)
    except ValueError:
        return None


@router.message(TradeCheck.entry_price)
async def st_entry(message: Message, state: FSMContext) -> None:
    val = await _read_float(message)
    if val is None or val <= 0:
        await message.answer("Enter a positive number.")
        return
    await state.update_data(entry_price=val)
    await state.set_state(TradeCheck.stop_loss)
    await message.answer(
        "4/13. Stop-loss? (enter a number or 'skip' — skipping will block the trade)",
        reply_markup=skip_kb(),
    )


@router.message(TradeCheck.stop_loss)
async def st_sl(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    if text in SKIP_TOKENS:
        await state.update_data(stop_loss=None)
    else:
        val = await _read_float(message)
        if val is None or val <= 0:
            await message.answer("Enter a positive number or 'skip'.")
            return
        await state.update_data(stop_loss=val)
    await state.set_state(TradeCheck.take_profit)
    await message.answer("5/13. Take-profit? (number or 'skip')", reply_markup=skip_kb())


@router.message(TradeCheck.take_profit)
async def st_tp(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    if text in SKIP_TOKENS:
        await state.update_data(take_profit=None)
    else:
        val = await _read_float(message)
        if val is None or val <= 0:
            await message.answer("Enter a positive number or 'skip'.")
            return
        await state.update_data(take_profit=val)
    await state.set_state(TradeCheck.deposit)
    await message.answer("6/13. Deposit, USDT?", reply_markup=ReplyKeyboardRemove())


@router.message(TradeCheck.deposit)
async def st_deposit(message: Message, state: FSMContext) -> None:
    val = await _read_float(message)
    if val is None or val <= 0:
        await message.answer("Enter a positive number.")
        return
    await state.update_data(deposit=val)
    await state.set_state(TradeCheck.risk_percent)
    await message.answer("7/13. Risk per trade, % (e.g. 1)?")


@router.message(TradeCheck.risk_percent)
async def st_risk(message: Message, state: FSMContext) -> None:
    val = await _read_float(message)
    if val is None or val <= 0:
        await message.answer("Enter a positive number.")
        return
    await state.update_data(risk_percent=val)
    await state.set_state(TradeCheck.leverage)
    await message.answer("8/13. Leverage? (1 = no leverage)")


@router.message(TradeCheck.leverage)
async def st_leverage(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        val = int(raw)
        if val < 1:
            raise ValueError
    except ValueError:
        await message.answer("Enter an integer >= 1.")
        return
    await state.update_data(leverage=val)
    await state.set_state(TradeCheck.reason)
    await message.answer("9/13. Why are you entering? (one sentence)")


@router.message(TradeCheck.reason)
async def st_reason(message: Message, state: FSMContext) -> None:
    await state.update_data(reason=(message.text or "").strip())
    await state.set_state(TradeCheck.setup)
    await message.answer("10/13. Setup? (e.g.: breakout, bounce, retest)")


@router.message(TradeCheck.setup)
async def st_setup(message: Message, state: FSMContext) -> None:
    await state.update_data(setup=(message.text or "").strip())
    await state.set_state(TradeCheck.emotion)
    await message.answer("11/13. Emotional state?", reply_markup=emotion_kb())


@router.message(TradeCheck.emotion)
async def st_emotion(message: Message, state: FSMContext) -> None:
    await state.update_data(emotion=(message.text or "").strip())
    await state.set_state(TradeCheck.losses_today)
    await message.answer(
        "12/13. Current daily loss, % (0 — if no losses today)?",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(TradeCheck.losses_today)
async def st_losses_today(message: Message, state: FSMContext) -> None:
    val = await _read_float(message)
    if val is None or val < 0:
        await message.answer("Enter a number >= 0.")
        return
    await state.update_data(losses_today=val)
    await state.set_state(TradeCheck.consecutive_losses)
    await message.answer("13/13. How many losing trades in a row today?")


@router.message(TradeCheck.consecutive_losses)
async def st_consecutive_losses(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    try:
        val = int(raw)
        if val < 0:
            raise ValueError
    except ValueError:
        await message.answer("Enter an integer >= 0.")
        return
    data = await state.update_data(consecutive_losses=val)
    await state.clear()

    await message.answer("Analyzing the trade, give me a few seconds...")

    req = TradeRequest(
        pair=data["pair"],
        direction=data["direction"],
        entry_price=data["entry_price"],
        stop_loss=data.get("stop_loss"),
        take_profit=data.get("take_profit"),
        deposit=data["deposit"],
        risk_percent=data["risk_percent"],
        leverage=data["leverage"],
        reason=data.get("reason"),
        setup=data.get("setup"),
        emotion=data.get("emotion"),
        losses_today=data.get("losses_today", 0.0),
        consecutive_losses=data.get("consecutive_losses", 0),
    )

    coach = AICoach(
        api_key=cfg.openai_api_key,
        model=cfg.openai_model,
        ollama_base_url=cfg.ollama_base_url,
        ollama_model=cfg.ollama_model_coach,
    )
    officer = AIRiskOfficer(
        api_key=cfg.anthropic_api_key,
        model=cfg.anthropic_model,
        ollama_base_url=cfg.ollama_base_url,
        ollama_model=cfg.ollama_model_officer,
    )

    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        s = user.settings
        policy = UserPolicy(
            max_risk_percent=s.max_risk_percent,
            max_leverage=s.max_leverage,
            min_rr=s.min_rr,
            daily_loss_limit=s.daily_loss_limit,
        )
        response = await decide(req, policy, coach, officer)
        await stats_service.save_trade(session, user, req, response)
        await session.commit()

    await message.answer(
        response.formatted_message + "\n\n"
        f"💡 The trade is saved in your journal. Close it once it's done:\n"
        f"   /close 47 win 2.5\n"
        f"   Trade IDs are in /journal",
        reply_markup=main_menu_kb(),
    )


# ---------------------------------------------------------------------------
# /close — record the trade outcome
# ---------------------------------------------------------------------------

@router.message(Command("close"))
async def cmd_close(message: Message) -> None:
    """Usage:
        /close 12 win 2.5
        /close 12 loss -1.0
        /close 12 breakeven
        /close 12 canceled
    """
    parts = (message.text or "").split()
    if len(parts) < 3:
        await message.answer(
            "Format:\n"
            "/close <id> <win|loss|breakeven|canceled> [pnl%]\n\n"
            "Examples:\n"
            "/close 12 win 2.5\n"
            "/close 12 loss -1.0\n"
            "/close 12 breakeven\n\n"
            "Trade IDs are in /journal."
        )
        return
    try:
        trade_id = int(parts[1])
    except ValueError:
        await message.answer("ID must be a number.")
        return
    outcome_raw = parts[2].lower()
    outcome_map = {
        "win": "WIN", "won": "WIN", "w": "WIN",
        "loss": "LOSS", "lost": "LOSS", "l": "LOSS",
        "breakeven": "BREAKEVEN", "be": "BREAKEVEN",
        "canceled": "CANCELED", "cancel": "CANCELED",
    }
    outcome = outcome_map.get(outcome_raw)
    if outcome is None:
        await message.answer(
            "Outcome must be: win | loss | breakeven | canceled."
        )
        return
    pnl = None
    if len(parts) >= 4:
        try:
            pnl = float(parts[3].replace(",", ".").rstrip("%"))
        except ValueError:
            await message.answer("P&L must be a number, e.g. 2.5 or -1.3.")
            return

    payload = CloseTradeRequest(outcome=outcome, pnl_percent=pnl)
    new_records: list = []
    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        trade = await stats_service.close_trade(session, user, trade_id, payload)
        if trade is not None:
            new_records = await achievements.detect_after_close(session, user)
        await session.commit()

    if trade is None:
        await message.answer(f"Trade #{trade_id} not found in your journal.")
        return
    label = {
        "WIN": "✅ WIN",
        "LOSS": "❌ LOSS",
        "BREAKEVEN": "⚖️ BE",
        "CANCELED": "🚫 CANCELED",
    }[outcome]
    pnl_str = f"  P&L: {pnl:+.2f}%" if pnl is not None else ""
    await message.answer(
        f"Trade #{trade_id} closed: {label}{pnl_str}\n"
        f"/stats — see the totals"
    )
    # Personal-record celebrations
    for ach in new_records:
        await message.answer(
            f"{ach.title}\n\n{ach.body}",
            reply_markup=main_menu_kb(),
        )


# ---------------------------------------------------------------------------
# /calc — position calculator
# ---------------------------------------------------------------------------

@router.message(Command("calc"))
async def cmd_calc(message: Message) -> None:
    """Usage:
        /calc <deposit> <risk%> <entry> <stop> [leverage]
    Examples:
        /calc 1000 1 67500 66800 1
        /calc 5000 0.5 3500 3450 5
    """
    parts = (message.text or "").split()
    if len(parts) < 5:
        await message.answer(
            "Format:\n"
            "/calc <deposit> <risk%> <entry> <stop> [leverage]\n\n"
            "Example:\n"
            "/calc 1000 1 67500 66800 1\n\n"
            "The bot calculates: position size, position value, margin."
        )
        return
    try:
        deposit = float(parts[1])
        risk = float(parts[2])
        entry = float(parts[3])
        stop = float(parts[4])
        leverage = int(parts[5]) if len(parts) >= 6 else 1
    except ValueError:
        await message.answer("Couldn't parse the numbers. All arguments must be numeric.")
        return
    try:
        result = calculate_position(PositionCalcRequest(
            deposit=deposit,
            risk_percent=risk,
            entry_price=entry,
            stop_loss=stop,
            leverage=leverage,
        ))
    except ValueError as exc:
        await message.answer(f"Error: {exc}")
        return
    await message.answer(
        f"📐 Position calculator:\n\n"
        f"• Risk in money: {result.risk_money} USDT\n"
        f"• SL distance: {result.sl_distance}\n"
        f"• Position size: {result.position_size_units} coins\n"
        f"• Position value: {result.position_value_usdt} USDT\n"
        f"• Leverage: x{result.leverage}\n"
        f"• Margin required: {result.margin_required} USDT\n\n"
        f"💡 For R:R 1:2 place your TP {result.rr_required_for_2x} away from entry."
    )


# ---------------------------------------------------------------------------
# /export — journal export to CSV
# ---------------------------------------------------------------------------

@router.message(Command("export"))
async def cmd_export(message: Message) -> None:
    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, message.from_user.id, message.from_user.username
        )
        data = await export_service.export_trades_csv(session, user)
        await session.commit()
    if not data or len(data) < 100:  # only header
        await message.answer("Journal is empty — nothing to export.")
        return
    await message.answer_document(
        BufferedInputFile(data, filename=f"trades_{message.from_user.id}.csv"),
        caption="📊 Your trade journal (opens in Excel/Google Sheets)",
    )


# ---------------------------------------------------------------------------
# /remind — show open trades right now
# ---------------------------------------------------------------------------

@router.message(Command("remind"))
async def cmd_remind(message: Message) -> None:
    text = await manual_remind(message.bot, message.from_user.id)
    await message.answer(text, reply_markup=main_menu_kb())


# ---------------------------------------------------------------------------
# /review — AI review of the last 7 days (Ollama, free)
# ---------------------------------------------------------------------------

@router.message(Command("review"))
async def cmd_review(message: Message) -> None:
    await message.answer(
        "🧠 Analyzing your journal for the week… (10-30 sec)"
    )
    text = await manual_review(message.bot, message.from_user.id)
    await message.answer(text, reply_markup=main_menu_kb())


# ---------------------------------------------------------------------------
# /plan — morning check-in on demand + inline-button callback
# ---------------------------------------------------------------------------

@router.message(Command("plan"))
async def cmd_plan(message: Message) -> None:
    await manual_morning_checkin(message.bot, message.from_user.id)


@router.callback_query(F.data.startswith("plan:"))
async def cb_plan(callback: CallbackQuery) -> None:
    intent = callback.data.split(":", 1)[1] if callback.data else ""
    if not daily_plan_service.is_valid_intent(intent):
        await callback.answer("Unknown plan.")
        return
    label = daily_plan_service.INTENT_LABELS[intent]
    desc = daily_plan_service.INTENT_DESCRIPTIONS[intent]

    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session,
            telegram_id=callback.from_user.id,
            username=callback.from_user.username,
        )
        await daily_plan_service.upsert_plan(session, user, intent)
        await session.commit()

    await callback.answer(f"Plan: {label}")
    await callback.message.answer(
        f"✅ Today's plan: {label}\n"
        f"  ({desc})\n\n"
        f"In the evening I'll check how well you followed it. Good trades!"
    )


# ---------------------------------------------------------------------------
# Voice message — transcribe + parse + start FSM with prefilled data
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Onboarding wizard (3 steps)
# ---------------------------------------------------------------------------

_STYLE_PRESETS = {
    "scalp": {"max_risk_percent": 0.5, "max_leverage": 5, "min_rr": 1.5,
              "label": "⚡ Scalping — short trades, low risk, frequent attempts"},
    "intraday": {"max_risk_percent": 1.0, "max_leverage": 5, "min_rr": 2.0,
                 "label": "📊 Intraday — standard settings"},
    "swing": {"max_risk_percent": 2.0, "max_leverage": 3, "min_rr": 3.0,
              "label": "📈 Swing — fewer trades, higher R:R"},
    "any": {"max_risk_percent": 1.0, "max_leverage": 5, "min_rr": 2.0,
            "label": "🤷 Standard — we'll tune it later"},
}


@router.callback_query(F.data == "ob_skip")
async def cb_onboarding_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.answer("Skipped")
    await callback.message.answer(
        "Okay, keeping the default limits (risk 1%, leverage x5, R:R 1:2).\n"
        "Change them anytime — /settings.\n\n"
        "Main commands:\n"
        "🛡 /trade — check a trade\n"
        "📡 /scan — market signals\n"
        "📒 /journal — your journal\n"
        "📊 /stats — statistics\n"
        "❓ /help — all commands",
        reply_markup=main_menu_kb(),
    )


@router.message(Onboarding.deposit)
async def ob_deposit(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").replace(",", ".").strip()
    try:
        deposit = float(raw)
        if deposit <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Type a number, e.g.: 1000")
        return
    await state.update_data(deposit=deposit)
    await state.set_state(Onboarding.style)
    await message.answer(
        f"✅ Deposit: {deposit:.0f} USDT\n\n"
        "Step 2/3: What's your trading style?\n"
        "(I'll pick limits to match it)",
        reply_markup=onboarding_style_kb(),
    )


@router.callback_query(F.data.startswith("ob_style:"))
async def ob_style(callback: CallbackQuery, state: FSMContext) -> None:
    style = callback.data.split(":", 1)[1] if callback.data else ""
    if style not in _STYLE_PRESETS:
        await callback.answer("Unknown style")
        return
    preset = _STYLE_PRESETS[style]

    # Apply preset to user settings
    async with AsyncSessionLocal() as session:
        user = await stats_service.get_or_create_user(
            session, callback.from_user.id, callback.from_user.username
        )
        s = user.settings
        s.max_risk_percent = preset["max_risk_percent"]
        s.max_leverage = preset["max_leverage"]
        s.min_rr = preset["min_rr"]
        await session.commit()

    await callback.answer("Limits selected")
    await state.clear()
    await callback.message.answer(
        f"✅ {preset['label']}\n\n"
        f"I've set your limits:\n"
        f"  • Risk per trade: {preset['max_risk_percent']}%\n"
        f"  • Max leverage: x{preset['max_leverage']}\n"
        f"  • Min R:R: 1:{preset['min_rr']}\n\n"
        "All set! 🎉\n\n"
        "The main action is **/trade** before every trade.\n\n"
        "Also:\n"
        "📡 /scan — market signals from the scanner\n"
        "📒 /journal — your journal\n"
        "📊 /stats — win-rate and charts\n"
        "🎙 Voice works too — record \"BTC long 67500 stop 66800\"\n\n"
        "Want to try it on a test trade right now? Tap /trade",
        reply_markup=main_menu_kb(),
    )


# ---------------------------------------------------------------------------

@router.message(F.voice)
async def on_voice(message: Message, state: FSMContext) -> None:
    """User sends a voice note like 'BTC long 67500 stop 66800' — bot
    transcribes it and starts /trade FSM with the parsed values already filled.
    """
    voice_svc = make_voice_service()
    if not voice_svc.transcription_available:
        await message.answer(
            "🎙 Voice input requires an OpenAI key for Whisper.\n"
            "It is not configured right now. Use /trade with text answers."
        )
        return

    await message.answer("🎙 Transcribing your voice…")

    # Download voice file from Telegram
    try:
        file = await message.bot.get_file(message.voice.file_id)
        buf = io.BytesIO()
        await message.bot.download_file(file.file_path, destination=buf)
        audio_bytes = buf.getvalue()
    except Exception as exc:
        await message.answer(f"⚠️ Could not download the audio: {exc.__class__.__name__}")
        return

    # Whisper
    try:
        text = await voice_svc.transcribe(audio_bytes)
    except Exception as exc:
        await message.answer(
            f"⚠️ Whisper failed: {exc.__class__.__name__}\n"
            "Try again or use /trade with text."
        )
        return

    if not text:
        await message.answer("The voice note is empty — nothing recognized.")
        return

    # Parse → dict
    parsed = await voice_svc.parse_trade(text)
    if not isinstance(parsed, dict) or parsed.get("error"):
        await message.answer(
            f"📝 Transcribed: {text}\n\n"
            f"⚠️ Couldn't understand the trade parameters. Run /trade and enter them manually."
        )
        return

    pair = str(parsed.get("pair") or "").upper()
    direction = str(parsed.get("direction") or "").lower()
    entry = parsed.get("entry_price")
    sl = parsed.get("stop_loss")
    tp = parsed.get("take_profit")

    if not pair or "/" not in pair or direction not in ("long", "short") or entry is None:
        await message.answer(
            f"📝 Transcribed: {text}\n\n"
            f"⚠️ The voice note is missing required fields "
            "(pair, direction, entry price). Use /trade."
        )
        return

    # Pre-fill FSM, skip first 5 questions, ask deposit
    await state.clear()
    await state.update_data(
        pair=pair,
        direction=direction,
        entry_price=float(entry),
        stop_loss=float(sl) if sl is not None else None,
        take_profit=float(tp) if tp is not None else None,
    )
    await state.set_state(TradeCheck.deposit)

    await message.answer(
        f"📝 Transcribed: {text}\n\n"
        f"✅ Prefilled the parameters:\n"
        f"  Pair: {pair}\n"
        f"  Direction: {direction}\n"
        f"  Entry: {entry}\n"
        f"  SL: {sl if sl is not None else '—'}\n"
        f"  TP: {tp if tp is not None else '—'}\n\n"
        f"1/8. Deposit, USDT?",
        reply_markup=ReplyKeyboardRemove(),
    )
