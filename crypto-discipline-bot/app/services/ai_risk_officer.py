from __future__ import annotations

import json
import logging
import re
from typing import Any

from anthropic import AsyncAnthropic

from app.schemas import OfficerReport, RiskCalc, RuleViolation, TradeRequest
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


OFFICER_SYSTEM_PROMPT = """Ты — Risk Officer крипто-трейдера. Ты строгий, дисциплинированный и заботишься только о капитале и психологии трейдера.

Твоя роль:
- проверять каждый параметр сделки против лучших практик риск-менеджмента
- искать признаки эмоциональной торговли, FOMO, revenge trading, переторговки
- запрещать сделку, если что-то не так
- быть честным и прямым, но без оскорблений

Запрещено:
- обещать прибыль
- говорить "точно заработаешь" или "это безопасная сделка"
- использовать слова "гарантия", "100%"

Тебе на вход придёт JSON с полями trade, calculations, rule_violations.
Если уже есть rule_violations с blocking=true — твоё решение должно быть FORBIDDEN.

Ответ СТРОГО в JSON:
{
  "summary": "1-2 предложения, что ты видишь",
  "violations": ["конкретное нарушение 1", "конкретное нарушение 2"],
  "decision": "ALLOWED" | "FORBIDDEN" | "WAIT"
}

Если хотя бы один признак: нет SL, риск >1%, RR<1:2, плечо >5x, эмоциональная торговля,
revenge trading — ставь FORBIDDEN. Если данных мало или сетап слабый — WAIT.
"""


class AIRiskOfficer:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-latest",
        ollama_base_url: str = "",
        ollama_model: str = "llama3.1:8b",
    ) -> None:
        self.model = model
        self._anthropic = AsyncAnthropic(api_key=api_key) if api_key else None
        self._ollama = (
            OllamaClient(base_url=ollama_base_url, model=ollama_model)
            if ollama_base_url else None
        )

    async def review(
        self,
        req: TradeRequest,
        calc: RiskCalc,
        violations: list[RuleViolation],
    ) -> OfficerReport:
        payload: dict[str, Any] = {
            "trade": req.model_dump(),
            "calculations": calc.model_dump(),
            "rule_violations": [v.model_dump() for v in violations],
        }

        if self._ollama is not None:
            try:
                data = await self._ollama.chat_json(
                    system=OFFICER_SYSTEM_PROMPT,
                    user_payload=payload,
                    temperature=0.1,
                )
                return OfficerReport(
                    summary=str(data.get("summary", "")).strip()
                    or "Локальный Ollama Risk Officer.",
                    violations=[str(x) for x in data.get("violations", [])][:8],
                    decision=_normalize_decision(data.get("decision"), violations),
                )
            except Exception as exc:
                logger.warning("Ollama Risk Officer failed: %s", exc)

        if self._anthropic is not None:
            try:
                resp = await self._anthropic.messages.create(
                    model=self.model,
                    max_tokens=600,
                    temperature=0.1,
                    system=OFFICER_SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": json.dumps(payload, ensure_ascii=False),
                        }
                    ],
                )
                text = "".join(
                    block.text for block in resp.content
                    if getattr(block, "type", "") == "text"
                )
                data = _extract_json(text)
                return OfficerReport(
                    summary=str(data.get("summary", "")).strip() or "Без комментариев.",
                    violations=[str(x) for x in data.get("violations", [])][:8],
                    decision=_normalize_decision(data.get("decision"), violations),
                )
            except Exception as exc:
                logger.warning("AI Risk Officer (Claude) failed: %s", exc)

        return self._fallback_from_rules(
            violations, "AI недоступен — опираюсь на правила."
        )

    @staticmethod
    def _fallback_from_rules(
        violations: list[RuleViolation], note: str
    ) -> OfficerReport:
        if any(v.blocking for v in violations):
            return OfficerReport(
                summary=note + " Опираюсь на жёсткие правила: есть нарушения.",
                violations=[v.message for v in violations if v.blocking],
                decision="FORBIDDEN",
            )
        return OfficerReport(
            summary=note + " Жёстких нарушений нет — решение остаётся за rule engine.",
            violations=[],
            decision="ALLOWED",
        )


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return {}


def _normalize_decision(value: Any, violations: list[RuleViolation]) -> str:
    allowed = {"ALLOWED", "FORBIDDEN", "WAIT"}
    s = str(value or "").strip().upper()
    if s not in allowed:
        return "FORBIDDEN" if any(v.blocking for v in violations) else "WAIT"
    if any(v.blocking for v in violations):
        return "FORBIDDEN"
    return s
