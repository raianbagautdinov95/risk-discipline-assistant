"""Inline & reply keyboards for the bot."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


# ---------------------------------------------------------------------------
# Main menu (always-visible reply keyboard)
# ---------------------------------------------------------------------------

# Button labels (kept here so handlers can match them via F.text == BTN_X).
BTN_SIGNALS = "📡 Signals"
BTN_SCAN = "🔍 Market Scan"
BTN_TRADE = "🛡 Check Trade"
BTN_JOURNAL = "📒 Journal"
BTN_STATS = "📊 Discipline"
BTN_SETTINGS = "⚙️ Settings"
BTN_RULES = "📜 Rules"
BTN_HELP = "❓ Help"


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Bottom keyboard. Shown after /start and after each action."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_SIGNALS), KeyboardButton(text=BTN_SCAN)],
            [KeyboardButton(text=BTN_TRADE), KeyboardButton(text=BTN_JOURNAL)],
            [KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_SETTINGS)],
            [KeyboardButton(text=BTN_RULES), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Pick a command or type...",
    )


# ---------------------------------------------------------------------------
# Inline keyboards
# ---------------------------------------------------------------------------

def trade_from_signal_kb(symbol: str) -> InlineKeyboardMarkup:
    """Single 'check discipline' button shown under each scanned signal."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🛡 Check discipline",
                callback_data=f"signal_to_trade:{symbol}",
            )
        ]]
    )


def onboarding_style_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Scalping", callback_data="ob_style:scalp"),
            InlineKeyboardButton(text="📊 Intraday", callback_data="ob_style:intraday"),
        ],
        [
            InlineKeyboardButton(text="📈 Swing", callback_data="ob_style:swing"),
            InlineKeyboardButton(text="🤷 Not sure", callback_data="ob_style:any"),
        ],
    ])


def onboarding_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⏭ Skip onboarding", callback_data="ob_skip")],
    ])


def morning_plan_kb() -> InlineKeyboardMarkup:
    """4 inline buttons for the morning check-in."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👀 Watch only", callback_data="plan:watch"),
            InlineKeyboardButton(
                text="📊 Up to 3 trades", callback_data="plan:few"),
        ],
        [
            InlineKeyboardButton(
                text="🔥 Actively hunt", callback_data="plan:active"),
            InlineKeyboardButton(
                text="🛌 Day off", callback_data="plan:off"),
        ],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Max risk, %", callback_data="set:max_risk_percent")],
            [InlineKeyboardButton(text="Max leverage", callback_data="set:max_leverage")],
            [InlineKeyboardButton(text="Min R:R", callback_data="set:min_rr")],
            [InlineKeyboardButton(text="Daily loss limit, %", callback_data="set:daily_loss_limit")],
        ]
    )


# ---------------------------------------------------------------------------
# FSM-step keyboards
# ---------------------------------------------------------------------------

def direction_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="long"), KeyboardButton(text="short")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def skip_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="skip")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def emotion_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="calm"), KeyboardButton(text="confident")],
            [KeyboardButton(text="anger"), KeyboardButton(text="FOMO")],
            [KeyboardButton(text="panic"), KeyboardButton(text="greed")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
