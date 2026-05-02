"""FSM states for the trade-check conversation."""
from aiogram.fsm.state import State, StatesGroup


class TradeCheck(StatesGroup):
    pair = State()
    direction = State()
    entry_price = State()
    stop_loss = State()
    take_profit = State()
    deposit = State()
    risk_percent = State()
    leverage = State()
    reason = State()
    setup = State()
    emotion = State()
    losses_today = State()
    consecutive_losses = State()


class SettingsEdit(StatesGroup):
    field = State()
    value = State()


class Onboarding(StatesGroup):
    deposit = State()
    style = State()
    risk = State()
