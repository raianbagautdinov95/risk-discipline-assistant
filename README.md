<div align="center">

# 🛡️ Risk Discipline Assistant

### AI risk-management for crypto traders — where deterministic rules, not the LLM, have the final word.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Flutter](https://img.shields.io/badge/Flutter-Web-02569B?logo=flutter&logoColor=white)](https://flutter.dev/)
[![AI](https://img.shields.io/badge/AI-OpenAI%20%C2%B7%20Anthropic%20%C2%B7%20Ollama-8A2BE2)](#tech-stack)
[![Tests](https://github.com/raianbagautdinov95/risk-discipline-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/raianbagautdinov95/risk-discipline-assistant/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

</div>

**Risk Discipline Assistant** checks every crypto trade against eight deterministic risk rules *before* any AI is involved, then layers an **AI Risk Officer** (which can veto) and an **AI Coach** (advisory only) on top. The result is a system that reasons like an LLM but stays predictable, testable, and safe: the language model can explain and advise, but it can never override a business rule.

The platform spans a Telegram bot, an async FastAPI backend, a standalone market-scanning signal engine, and a Flutter Web dashboard — all in this monorepo.

---

## 🎥 Demo

<!-- Drop an animated GIF of the full Check Trade flow here once recorded. -->
_A short screen recording of the full **Check Trade** flow — coming soon._

---

## Screenshots

### Trade Validation Workflow

![Questionnaire](docs/images/trade-check-1.png)

The assistant collects structured trading information through a guided 13-step questionnaire before any validation runs.

---

![Trade Details](docs/images/trade-check-2.png)

The trader provides market context, leverage and psychological state — the same inputs the rule engine and AI layers reason over.

---

![Validation Result](docs/images/trade-check-3.png)

The final result is layered and transparent: **deterministic validation** (8/8 rule checks), an **AI Risk Officer** verdict, **AI Coach** feedback, and a single final recommendation — combining hard business rules with AI analysis.

---

## Monorepo layout

This repository contains the full platform. Each component has a single responsibility and can evolve independently.

| Path | Component | Responsibility |
| --- | --- | --- |
| [`crypto-discipline-bot/`](crypto-discipline-bot/) | **Discipline Backend + Telegram Bot** | Async FastAPI service and aiogram bot: the deterministic rule engine, AI Risk Officer, AI Coach, journal, stats and voice input. |
| [`ai/`](ai/) | **Signal Engine** | Technical indicators, chart-pattern detection and an LLM analyzer that produce market signals. |
| [`main.py`](main.py) · [`api.py`](api.py) | **Signal Bot / API** | Standalone market scanner (analysis & notifications only — never executes orders) and a small REST API over the signals. |
| [`monitoring/`](monitoring/) | **Monitoring** | Signal tracking, reporting and notifications. |
| [`config/`](config/) · [`data/`](data/) · [`utils/`](utils/) | **Shared infra** | Settings, risk limits, market-data access, logging. |
| [`backtest.py`](backtest.py) | **Backtesting** | Replays the signal engine over historical data. |
| [`flutter_app/`](flutter_app/) | **Flutter Web Dashboard** | Cross-platform client for the discipline journal, stats and signals. |

> The two backends communicate over HTTP, so the Signal Bot and the Discipline Backend can be deployed and scaled independently.

---

## Why this architecture?

LLMs are excellent at reasoning, but they should not enforce critical business rules. In financial software, deterministic validation must remain the source of truth, so the platform follows a layered decision architecture:

```
Trade Request
      │
      ▼
Deterministic Rule Engine   ← source of truth, can block
      │
      ▼
AI Risk Officer             ← can veto, never approve
      │
      ▼
AI Coach                    ← advises, never turns ALLOWED into FORBIDDEN
      │
      ▼
Final Decision
```

- **Deterministic Rule Engine** — eight independently testable blocking rules: stop-loss present, risk %, leverage limit, minimum R:R, daily-loss protection, consecutive-loss protection, emotional-state validation, revenge-trading detection.
- **AI Risk Officer** — contextual review that can **veto** a trade the rules allowed, but can never approve one they blocked.
- **AI Coach** — explains strengths, weaknesses and psychology. It can advise waiting, but can never turn an `ALLOWED` decision into `FORBIDDEN`.

The full reasoning behind each design decision — the two-tier AI veto, local-first Ollama, two FastAPI services, Whisper voice input, pure-code risk rules — is documented in **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

---

## Quick Start

The Discipline Backend and Telegram bot run with a single command:

```bash
cd crypto-discipline-bot
cp .env.example .env        # set BOT_TOKEN + at least one AI provider (or Ollama)
docker compose up --build
```

- API docs (Swagger): http://localhost:8009/docs
- PostgreSQL: `localhost:5433`

Runs **fully offline with Ollama** — set `OLLAMA_BASE_URL` and no cloud API keys are required. Apply database migrations with `alembic upgrade head`, and run the test suite with `pytest`.

The standalone signal scanner runs from the repo root:

```bash
python main.py            # continuous market scan
python main.py --once     # single pass over all pairs
```

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Backend | FastAPI, Uvicorn, Pydantic v2 |
| Bot | aiogram 3 |
| Database | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| AI providers | OpenAI, Anthropic, Ollama (behind a provider abstraction) |
| Voice | OpenAI Whisper |
| Signal engine | pandas, numpy, `ta` (technical analysis) |
| Frontend | Flutter Web (PWA) |
| Infrastructure | Docker, Docker Compose, GitHub Actions CI |

---

## Production Readiness

**Already implemented**

- Docker Compose deployment
- environment-based configuration
- database migrations (Alembic)
- asynchronous backend
- modular, service-oriented monorepo
- provider abstraction (OpenAI · Anthropic · Ollama)
- local AI deployment (Ollama)
- automatic API documentation (OpenAPI / Swagger)
- **CI pipeline** (GitHub Actions runs the backend test suite on every push/PR)
- unit tests for the rule and decision engines

**Planned improvements**

- Redis caching · Celery task queue
- JWT authentication · rate limiting
- Prometheus metrics + Grafana dashboards
- centralized logging · distributed tracing
- Kubernetes deployment

---

## Engineering Philosophy

- **AI should assist, not control.** Business rules remain deterministic; LLMs provide reasoning rather than authority.
- **Simplicity over complexity.** Each component has a clearly defined responsibility; the architecture favors maintainability over unnecessary abstraction.
- **Provider independence.** No business logic depends on a specific AI vendor; cloud and local inference are interchangeable.
- **Production-first thinking.** Every decision considers maintainability, scalability, testing, deployment and long-term evolution.

---

## About the Author

Hi, I'm **Raian Bagautdinov** — an Applied AI Engineer focused on designing production-ready AI systems with FastAPI, PostgreSQL, LLMs, RAG and local AI.

My primary interest is building AI applications that combine deterministic software engineering with modern language models to create reliable, maintainable systems where AI enhances decision-making without becoming the source of truth.

---

## License

Released under the [MIT License](LICENSE).
