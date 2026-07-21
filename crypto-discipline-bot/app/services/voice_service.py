from __future__ import annotations

import io
import json
import logging

from openai import AsyncOpenAI

from app.config import settings
from app.services.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


PARSE_SYSTEM_PROMPT = """You are an assistant that parses a trader's trade from free text.
The input is in English.

Input is a phrase like:
  "BTC long at 67500 with stop 66800 and take 69200"
  "Short ETH 3500, stop 3550"
  "want to enter SOL long 145, stop 140 take 155"

Return STRICTLY JSON:
{
  "pair": "BTC/USDT",
  "direction": "long",
  "entry_price": 67500,
  "stop_loss": 66800,
  "take_profit": 69200
}

If information is missing (e.g. no entry price) — set the field to null.
Do not invent data. If you can't understand it — return {"error": "not understood"}.
"""


class VoiceService:
    def __init__(
        self,
        openai_api_key: str,
        whisper_model: str = "whisper-1",
        ollama_base_url: str = "",
        ollama_model: str = "qwen2.5-coder:7b",
        openai_text_model: str = "gpt-4o-mini",
    ) -> None:
        self._openai = AsyncOpenAI(api_key=openai_api_key) if openai_api_key else None
        self._whisper_model = whisper_model
        self._openai_text_model = openai_text_model
        self._ollama = (
            OllamaClient(base_url=ollama_base_url, model=ollama_model)
            if ollama_base_url else None
        )

    @property
    def transcription_available(self) -> bool:
        return self._openai is not None

    async def transcribe(self, audio_bytes: bytes, filename: str = "voice.ogg") -> str:
        if self._openai is None:
            raise RuntimeError("OpenAI key required for voice transcription.")
        file = io.BytesIO(audio_bytes)
        file.name = filename
        # Force English transcription for a consistent English-only workflow.
        resp = await self._openai.audio.transcriptions.create(
            model=self._whisper_model,
            file=file,
            language="en",
        )
        return (resp.text or "").strip()

    async def parse_trade(self, text: str) -> dict:
        if self._ollama is not None:
            try:
                return await self._ollama.chat_json(
                    system=PARSE_SYSTEM_PROMPT,
                    user_payload={"text": text},
                    temperature=0.0,
                )
            except Exception as exc:
                logger.warning("Ollama voice parse failed: %s", exc)

        if self._openai is not None:
            try:
                resp = await self._openai.chat.completions.create(
                    model=self._openai_text_model,
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    messages=[
                        {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                        {"role": "user", "content": text},
                    ],
                )
                return json.loads(resp.choices[0].message.content or "{}")
            except Exception as exc:
                logger.warning("OpenAI voice parse failed: %s", exc)

        return {"error": "AI parser is not configured."}


def make_voice_service() -> VoiceService:
    return VoiceService(
        openai_api_key=settings.openai_api_key,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model_coach,
        openai_text_model=settings.openai_model,
    )
