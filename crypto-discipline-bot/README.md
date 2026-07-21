# Discipline Backend + Telegram Bot

The core of [Risk Discipline Assistant](../README.md): an async FastAPI service and an aiogram Telegram bot that check a crypto trade **before entry** against discipline, risk, leverage, stop-loss, take-profit, R:R and emotional state. Every trade gets one of three verdicts: **ALLOWED / FORBIDDEN / WAIT**.

> ⚠️ Not financial advice. The bot does not promise profit or guarantee outcomes — it acts as a risk officer and discipline coach.

## What's inside

- **Telegram bot** (`aiogram` 3.x) — an FSM dialog collects trade parameters through a 13-step questionnaire.
- **FastAPI backend** — the same checks are exposed over REST for other clients (e.g. the Flutter dashboard).
- **Risk Engine** — deterministic rules (no SL → block, risk > limit → block, R:R < minimum → block, leverage > limit → block, emotional / revenge trading → block).
- **AI Coach (OpenAI/Ollama)** — soft review with pros and cons. Advisory only, no veto power.
- **AI Risk Officer (Anthropic/Ollama)** — strict auditor that can forbid a trade.
- **Decision Engine** — rules take priority over the Officer, the Officer over the Coach.
- **PostgreSQL + SQLAlchemy + Alembic** — trade journal and user settings.
- **Docker + docker-compose** — runs as three containers: db, api, bot.

## Quick start

```bash
cp .env.example .env        # set BOT_TOKEN + at least one AI provider (or Ollama)
docker compose up --build
alembic upgrade head        # apply migrations
```

- API docs (Swagger): http://localhost:8009/docs
- PostgreSQL: `localhost:5433`

Runs fully offline with Ollama — set `OLLAMA_BASE_URL` and no cloud API keys are required.

## Tests

```bash
pytest
```

Unit tests cover the deterministic rule engine and the decision engine.

## Configuration

All settings come from environment variables (see [`.env.example`](.env.example)). The database URL is built from the `POSTGRES_*` variables, so the password is defined in exactly one place; set `DATABASE_URL` / `ALEMBIC_DATABASE_URL` only to override with an external database.
