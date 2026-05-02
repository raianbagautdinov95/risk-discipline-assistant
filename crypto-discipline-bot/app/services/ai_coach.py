from __future__ import annotations

import json
import logging
from typing import Any

from openai import AsyncOpenAI

from app.schemas import CoachReport, RiskCalc, RuleViolation, TradeRequest
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


COACH_SYSTEM_PROMPT = """Ты — крипто-коуч, который помогает трейдеру обдумать сделку.
Ты НЕ финансовый советник, ты НЕ обещаешь прибыль и НЕ гарантируешь исход.
Ты говоришь простым языком и используешь факты из расчётов и описания сделки.

Задача: дать сбалансированный разбор — плюсы, минусы, мягкая рекомендация.

Отвечай СТРОГО в формате JSON со схемой:
{
  "summary": "2-3 предложения простым языком",
  "pros": ["короткий плюс 1", "короткий плюс 2"],
  "cons": ["короткий минус 1", "короткий минус 2"],
  "recommendation": "enter" | "wait" | "reduce_risk" | "skip"
}

Запрещено:
- обещать прибыль или результат
- говорить, что сделка точно сработает
- использовать слова "гарантия", "100%", "точно заработаешь"

Если данных не хватает — честно скажи об этом в summary и поставь recommendation="wait".
"""


class AICoach:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        ollama_base_url: str = "",
        ollama_model: str = "llama3.1:8b",
    ) -> None:
        self.model = model
        self._openai = AsyncOpenAI(api_key=api_key) if api_key else None
        self._ollama = (
            OllamaClient(base_url=ollama_base_url, model=ollama_model)
            if ollama_base_url else None
        )

    async def coach(
        self,
        req: TradeRequest,
        calc: RiskCalc,
        violations: list[RuleViolation],
    ) -> CoachReport:
        payload: dict[str, Any] = {
            "trade": req.model_dump(),
            "calculations": calc.model_dump(),
            "rule_violations": [v.model_dump() for v in violations],
        }

        if self._ollama is not None:
            try:
                data = await self._ollama.chat_json(
                    system=COACH_SYSTEM_PROMPT,
                    user_payload=payload,
                    temperature=0.3,
                )
                return CoachReport(
                    summary=str(data.get("summary", "")).strip() or "Локальный Coach.",
                    pros=[str(x) for x in data.get("pros", [])][:5],
                    cons=[str(x) for x in data.get("cons", [])][:5],
                    recommendation=_normalize_coach_rec(data.get("recommendation")),
                )
            except Exception as exc:
                logger.warning("Ollama Coach failed: %s", exc)

        if self._openai is not None:
            try:
                resp = await self._openai.chat.completions.create(
                    model=self.model,
                    response_format={"type": "json_object"},
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": COACH_SYSTEM_PROMPT},
                        {
                            "role": "user",
                            "content": json.dumps(payload, ensure_ascii=False),
                        },
                    ],
                )
                raw = resp.choices[0].message.content or "{}"
                data = json.loads(raw)
                return CoachReport(
                    summary=str(data.get("summary", "")).strip() or "Нет деталей.",
                    pros=[str(x) for x in data.get("pros", [])][:5],
                    cons=[str(x) for x in data.get("cons", [])][:5],
                    recommendation=_normalize_coach_rec(data.get("recommendation")),
                )
            except Exception as exc:
                logger.warning("AI Coach (OpenAI) failed: %s", exc)

        return self._fallback(
            "AI Coach недоступен — нет ни Ollama, ни облачного провайдера."
        )

    @staticmethod
    def _fallback(reason: str) -> CoachReport:
        return CoachReport(summary=reason, pros=[], cons=[], recommendation="wait")


def _normalize_coach_rec(value: Any) -> str:
    allowed = {"enter", "wait", "reduce_risk", "skip"}
    s = str(value or "").strip().lower()
    return s if s in allowed else "wait"
