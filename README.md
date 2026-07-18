# Crypto Trading Suite

[![Tests](https://github.com/raianbagautdinov95/risk-discipline-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/raianbagautdinov95/risk-discipline-assistant/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/)
[![Flutter](https://img.shields.io/badge/flutter-3.x-blue.svg)](https://flutter.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Discipline-first toolkit for crypto traders: a Telegram bot that audits every trade you're about to take, a market scanner that produces actionable BUY/SELL ideas, and a Flutter web dashboard that ties them together.

This is **not** a trading advisor. It does not predict price. It checks your risk, leverage, R:R and emotional state against the rules you set, and refuses trades that would blow up your account.

> ⚠️ Not financial advice. The bot helps you keep risk and discipline. Decisions and responsibility are yours.

<!-- Replace these placeholders once you record screenshots / GIFs:
     1. docs/screenshots/dashboard.png   — Flutter "Today" tab
     2. docs/screenshots/discipline.png  — Discipline tab with calendar heatmap
     3. docs/screenshots/telegram.gif    — voice message → trade prefill flow
-->

![Today dashboard](docs/screenshots/dashboard.png)
![Discipline page](docs/screenshots/discipline.png)
![Telegram voice flow](docs/screenshots/telegram.gif)

---

## What's inside

The repo is a small monorepo with three independent components.

| Folder | What it is |
|---|---|
| `crypto-discipline-bot/` | Discipline backend — FastAPI + Telegram bot + Postgres |
| `.` (root: `main.py`, `api.py`, `ai/`, etc.) | Signal scanner — separate FastAPI service that scans 10 OKX pairs |
| `flutter_app/` | Web dashboard / PWA — installable from Chrome, dark + light themes |

The three talk to each other over HTTP. You can run any one of them on its own.

---

## Highlights

**Discipline engine** — eight hard rules that block a trade automatically: no stop-loss, risk above limit, R:R below threshold, leverage above limit, daily loss reached, two losses in a row, revenge-trading wording, bad emotional state.

**Two-tier AI audit** — a strict Risk Officer (Claude or local Ollama) with veto power, plus a softer Coach (OpenAI or local Ollama) that explains pros/cons. Rules > Officer > Coach. Falls back to pure rule logic when no AI is configured.

**Local-first AI** — runs entirely on local Ollama (`qwen2.5-coder:7b`, `llama3.1:8b`, etc.). Zero API costs, full privacy. Cloud APIs are optional fallbacks.

**Voice input** — record a voice note like *"BTC long 67500, stop 66800, take 69200"* and the bot transcribes (Whisper), parses it, and pre-fills the discipline check. Three follow-up questions instead of thirteen.

**Habit-forming UX** — calendar heatmap, daily streaks, personal records pushed as Telegram messages, weekly AI review on Sundays, morning intent check-in at 09:00 UTC, evening pending-trades reminder at 22:00 UTC.

**Market scanner** — separate service that runs every 15 minutes, multi-timeframe analysis (4H trend / 1H direction / 15m entry), tight confidence filters, strict confluence requirements. Pushes new signals into Telegram with an inline "Check discipline" button.

**Production-grade web app** — Flutter Web compiled to PWA, Inter typography, glassmorphism app bar, hover states, animated counters, staggered list animations, fl_chart equity curves with gradient fills, calendar heatmap, light/dark theme toggle.

---

## Architecture

```
                         ┌──────────────────┐
                         │  Flutter Web/PWA │
                         │   :8080          │
                         └────────┬─────────┘
                                  │
          ┌──────────────────────┼──────────────────────────┐
          │                      │                          │
    ┌─────┴──────┐        ┌──────┴──────┐           ┌───────┴───────┐
    │ Signal Bot │        │ Discipline  │           │  Telegram Bot │
    │  :8765     │        │  Backend    │◄──────────┤  (aiogram)    │
    │ (scanner)  │        │  FastAPI    │           │               │
    └────────────┘        │  :8009      │           └───────┬───────┘
                          └──────┬──────┘                   │
                                 │                          │
                          ┌──────┴──────┐                   │
                          │  Postgres   │                   │
                          │  + Ollama   │◄──────────────────┘
                          │  (local AI) │
                          └─────────────┘
```

---

## Quick start (Docker)

You need Docker Desktop, a Telegram bot token from `@BotFather`, and (optionally) Ollama installed locally.

```bash
git clone https://github.com/raianbagautdinov95/risk-discipline-assistant.git
cd risk-discipline-assistant/crypto-discipline-bot

cp .env.example .env
# Edit .env: set BOT_TOKEN, POSTGRES_PASSWORD, OLLAMA_BASE_URL

docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose logs -f bot
```

When you see `Run polling for bot @YourBot`, open Telegram, find your bot, send `/start`. New users go through a 3-step onboarding wizard that sets risk limits based on their style.

The web dashboard is a separate process:

```bash
cd ../flutter_app
flutter pub get
flutter run -d web-server --web-port 8080
```

Open `http://localhost:8080`. In **Settings**, paste your Telegram ID (find it via `@userinfobot`) — the dashboard then mirrors your Telegram journal.

The signal scanner is also separate:

```bash
cd ..
pip install -r requirements.txt
uvicorn api:app --host 0.0.0.0 --port 8765
```

---

## Local AI (Ollama)

The bot prefers a local model over cloud APIs. After installing Ollama:

```bash
ollama pull qwen2.5-coder:7b   # 4.7 GB, recommended
# or smaller / faster:
ollama pull llama3.2:3b        # 2 GB
```

Then in `.env`:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL_COACH=qwen2.5-coder:7b
OLLAMA_MODEL_OFFICER=qwen2.5-coder:7b
```

On a GPU (CUDA, Metal), responses come back in 2–3 seconds. On CPU expect 15–30 seconds.

---

## Telegram commands

| Command | What it does |
|---|---|
| `/start` | First-run wizard for new users; menu for returning |
| `/trade` | 13-step FSM for a discipline check |
| `/journal` | Last 10 trades with outcome icons |
| `/stats` | Total + win-rate + average P&L + common forbid reasons |
| `/close <id> win\|loss\|breakeven [pnl%]` | Mark a trade as closed |
| `/calc <deposit> <risk%> <entry> <stop> [leverage]` | Position-size calculator |
| `/export` | Send the full journal as a CSV |
| `/remind` | Show currently-open trades right now |
| `/review` | Generate an AI weekly review on demand |
| `/plan` | Set today's intent (watch / few / active / off) |
| `/scan` | Force a market scan (10–30 sec) |
| `/signals` | List active signals from cache |
| `/analyze BTC-USDT` | Per-pair analysis with reasons |
| `/settings` | Tweak risk limits inline |
| `/rules` | Show the eight hard rules |
| Voice message | Transcribed + parsed → starts the FSM with prefilled fields |

There's a persistent reply-keyboard with the eight most common actions.

---

## Web dashboard tabs

1. **Today** — greeting, KPIs (streak, win-rate, today's count), big "check a trade" CTA, teasers of active signals and pending trades.
2. **Signals** — terminal-style cards with confidence bar, entry / SL / TP / R:R pills, "Check discipline" button per signal.
3. **Check** — sectioned form (Trade / Risk / Discipline). Result card is a cinematic gradient hero with score, computations, violations, AI commentary.
4. **Journal** — searchable, filterable list (All / Allowed / Forbidden / Wait / Wins / Losses / Pending). Tap a card for the full detail screen with "Repeat" and "Close" actions.
5. **Discipline** — animated KPI tiles, equity curve, win-rate per day, calendar heatmap (12 weeks × 7 days), achievements, share-as-PNG.
6. **Settings** — Telegram ID + risk limits + about.

---

## Tech stack

**Backend**: Python 3.11 · FastAPI · async SQLAlchemy 2.0 · Alembic · PostgreSQL 16 · aiogram 3.x · OpenAI · Anthropic · Ollama · httpx · Docker Compose

**Frontend**: Flutter 3.x · Material 3 · `google_fonts` (Inter) · `fl_chart` · `shared_preferences` · PWA

**Signal scanner**: pandas · `ta` (technical indicators) · OKX REST API · DeepSeek (optional)

**Tests**: pytest + pytest-asyncio (29 unit tests on rule engine + decision engine)

---

## Configuration

All secrets are loaded from `.env`. Nothing is hardcoded. Both subprojects (`crypto-discipline-bot/`, root signal scanner) ship a `.env.example`.

Key variables for the discipline bot:

```env
BOT_TOKEN=                         # Telegram bot token from @BotFather
DATABASE_URL=                      # postgresql+asyncpg://...
ALEMBIC_DATABASE_URL=              # postgresql+psycopg2://... (sync, for migrations)

OPENAI_API_KEY=                    # optional — Coach + Whisper voice
ANTHROPIC_API_KEY=                 # optional — Risk Officer
OLLAMA_BASE_URL=                   # http://host.docker.internal:11434 if local
OLLAMA_MODEL_COACH=qwen2.5-coder:7b
OLLAMA_MODEL_OFFICER=qwen2.5-coder:7b

SIGNAL_BOT_URL=http://host.docker.internal:8765   # signal scanner
DEFAULT_MAX_RISK_PERCENT=1.0
DEFAULT_MAX_LEVERAGE=5
DEFAULT_MIN_RR=2.0
DEFAULT_DAILY_LOSS_LIMIT=2.0
```

Passwords containing `@` must be URL-encoded (`@` → `%40`) inside `DATABASE_URL` / `ALEMBIC_DATABASE_URL`.

---

## Tests

```bash
cd crypto-discipline-bot
pip install -r requirements.txt
pytest -q
```

Covers position-size math, R:R, all eight blocking rules, AI vetoes, decision-engine combinations.

---

## Architecture & Design Decisions

Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for a short ADR-style write-up of the main technical decisions: why two AI tiers, why Ollama-first, why two FastAPI services, why async SQLAlchemy, etc.

## Roadmap

What's already in: discipline engine, two-tier AI, signal scanner, web/PWA, voice input, calendar heatmap, achievements, weekly review, daily reminders, morning check-in.

What's next:
- Public deployment guide (Hetzner / Fly.io)
- JWT authentication on the FastAPI surface
- Rate limiting + Sentry
- TradingView webhook → discipline check
- Trade screenshot OCR via vision LLM
- Subscription tiers (Free / Pro / Team)
- English UI localisation

---

## License

MIT. See `LICENSE`.

---

## Disclaimer

This software is provided for educational and personal-discipline purposes only. It does not provide financial advice, does not execute trades, and does not predict markets. The author is not liable for any losses resulting from its use. Trading cryptocurrency involves substantial risk.
