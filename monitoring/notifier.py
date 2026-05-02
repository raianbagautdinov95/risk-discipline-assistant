"""Отправка уведомлений о сигналах: в консоль, опционально — в Telegram."""
from typing import Optional, Dict, Any
import logging
import requests

from config.settings import NotifyConfig


class Notifier:
    def __init__(self, config: NotifyConfig, logger: Optional[logging.Logger] = None):
        self.cfg = config
        self.logger = logger

    def send(self, signal_dict: Dict[str, Any], ai_review: Optional[Dict[str, Any]] = None) -> None:
        """Рассылает сигнал по всем включённым каналам."""
        message = self._format(signal_dict, ai_review)

        if self.cfg.console:
            self._console(message)

        if self.cfg.telegram_enabled:
            self._telegram(message)

    # -------------------------------------------------------------- #

    def _format(self, s: Dict[str, Any], ai_review: Optional[Dict[str, Any]]) -> str:
        action = s["action"]
        emoji = {"BUY": "🟢 LONG", "SELL": "🔴 SHORT", "HOLD": "⚪ HOLD"}.get(action, action)

        lines = [
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"  {emoji}  {s['symbol']}",
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            f"Уверенность: {s['confidence']}%",
            f"Цена входа:  {s['entry']}",
        ]
        if action != "HOLD":
            lines += [
                f"Stop Loss:   {s['stop_loss']}",
                f"Take Profit: {s['take_profit']}",
                f"R:R:         {s['risk_reward']}",
            ]
        lines.append(f"Тренд 1H:    {s['trend_1h']}")
        lines.append("")
        lines.append("Обоснование:")
        for r in s.get("reasons", []):
            lines.append(f"  • {r}")

        if ai_review:
            lines.append("")
            agree = "согласен" if ai_review.get("agree") else "НЕ согласен"
            lines.append(f"AI-обзор ({agree}, {ai_review.get('confidence', 0):.0f}%):")
            comment = ai_review.get("comment", "")
            if comment:
                lines.append(f"  {comment}")

        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        return "\n".join(lines)

    def _console(self, message: str) -> None:
        if self.logger:
            for line in message.splitlines():
                self.logger.info(line)
        else:
            print(message)

    def _telegram(self, message: str) -> None:
        """Отправка в Telegram. Работает только если задан TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID."""
        if not (self.cfg.telegram_token and self.cfg.telegram_chat_id):
            return
        try:
            url = f"https://api.telegram.org/bot{self.cfg.telegram_token}/sendMessage"
            payload = {
                "chat_id": self.cfg.telegram_chat_id,
                "text": f"```\n{message}\n```",
                "parse_mode": "Markdown",
            }
            requests.post(url, json=payload, timeout=10)
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Telegram send failed: {e}")
