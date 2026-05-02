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
BTN_SIGNALS = "📡 Сигналы"
BTN_SCAN = "🔍 Скан рынка"
BTN_TRADE = "🛡 Проверить сделку"
BTN_JOURNAL = "📒 Журнал"
BTN_STATS = "📊 Дисциплина"
BTN_SETTINGS = "⚙️ Настройки"
BTN_RULES = "📜 Правила"
BTN_HELP = "❓ Помощь"


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
        input_field_placeholder="Выбери команду или напиши...",
    )


# ---------------------------------------------------------------------------
# Inline keyboards
# ---------------------------------------------------------------------------

def trade_from_signal_kb(symbol: str) -> InlineKeyboardMarkup:
    """Single 'check discipline' button shown under each scanned signal."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="🛡 Проверить дисциплину",
                callback_data=f"signal_to_trade:{symbol}",
            )
        ]]
    )


def onboarding_style_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⚡ Скальп", callback_data="ob_style:scalp"),
            InlineKeyboardButton(text="📊 Интрадей", callback_data="ob_style:intraday"),
        ],
        [
            InlineKeyboardButton(text="📈 Свинг", callback_data="ob_style:swing"),
            InlineKeyboardButton(text="🤷 Не уверен", callback_data="ob_style:any"),
        ],
    ])


def onboarding_skip_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="⏭ Пропустить онбординг", callback_data="ob_skip")],
    ])


def morning_plan_kb() -> InlineKeyboardMarkup:
    """4 inline buttons for the morning check-in."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="👀 Наблюдать", callback_data="plan:watch"),
            InlineKeyboardButton(
                text="📊 До 3 сделок", callback_data="plan:few"),
        ],
        [
            InlineKeyboardButton(
                text="🔥 Активно искать", callback_data="plan:active"),
            InlineKeyboardButton(
                text="🛌 Не торгую", callback_data="plan:off"),
        ],
    ])


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Макс. риск, %", callback_data="set:max_risk_percent")],
            [InlineKeyboardButton(text="Макс. плечо", callback_data="set:max_leverage")],
            [InlineKeyboardButton(text="Мин. R:R", callback_data="set:min_rr")],
            [InlineKeyboardButton(text="Дневной лимит, %", callback_data="set:daily_loss_limit")],
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
        keyboard=[[KeyboardButton(text="пропустить")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def emotion_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="спокоен"), KeyboardButton(text="уверен")],
            [KeyboardButton(text="злость"), KeyboardButton(text="FOMO")],
            [KeyboardButton(text="паника"), KeyboardButton(text="жадность")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
