# Architecture & Design Decisions

This document records the **why** behind the main technical choices. Each section is short and follows ADR (Architecture Decision Record) style: context → decision → consequences.

---

## 1. Two-tier AI with hard veto

**Context.** A single LLM that "decides" if a trade is OK is fragile: it hallucinates, drifts, and is slow. Pure rule-based check is rigid and ignores nuance like "your stop is technically valid but it sits inside the most volatile range of the day".

**Decision.** Three layers, each with its own authority:
1. **Rule engine** — deterministic checks (no SL, risk above limit, R:R below threshold, leverage, daily loss, two losses in a row, revenge wording, bad emotion). Pure Python, no AI. Has the highest authority — if it forbids, the answer is `FORBIDDEN`, period.
2. **Risk Officer** (Claude or Ollama) — strict reviewer with veto power over the Coach. Sees the same trade + the rule violations and produces its own verdict.
3. **Coach** (OpenAI or Ollama) — softer companion that explains pros/cons in plain language. Advisory only — cannot block.

Final decision = `min(rule_engine, officer, coach)` in terms of permissiveness. If any of the three is unhappy → user does not enter.

**Consequences.**
- Single most reliable layer (rules) is always available, even with no AI key.
- AI never produces a false `ALLOWED` because the rule layer overrides it.
- Adds latency (two AI calls in parallel + rules), but the user is about to risk real money — 5 seconds of waiting is acceptable.

---

## 2. Local-first AI via Ollama

**Context.** Cloud LLMs cost money, leak trade data to a third party, and depend on the network. For a discipline tool that's used many times a day per user, this is bad on all three axes.

**Decision.** Ollama is the default backend for both Coach and Risk Officer. Cloud APIs (OpenAI / Anthropic) are *fallbacks* — used only if `OLLAMA_BASE_URL` is empty. Both clients implement the same `chat_json` contract.

**Consequences.**
- Zero per-request cost on a developer's machine.
- Trade data stays local.
- Initial setup needs `ollama pull qwen2.5-coder:7b` (one-off ~5 GB download).
- On a CPU-only machine inference can take 10-30 sec; on a GPU 1-3 sec.
- Cloud fallback keeps the project usable for users who do not want to install Ollama.

---

## 3. Two FastAPI services, not one

**Context.** Two clearly separate concerns: (a) market scanning that produces BUY/SELL signals from candle data; (b) discipline auditing of trades the user wants to enter. Stuffing them into a single process creates coupling — a slow scan blocks the bot, and a Telegram update bug crashes the scanner.

**Decision.** Two independent FastAPI processes:
- `signal-bot` on port `8765` — periodic market scan, exposes `/signals/active`, `/signals/scan`, `/signal/{symbol}`.
- `discipline-bot` (FastAPI on `8009` + aiogram in a sibling process) — owns Postgres, Telegram FSM, AI calls.

The discipline bot calls the signal bot over plain HTTP (`SignalClient`) when the user runs `/scan` or wants push notifications.

**Consequences.**
- Each service has its own deployment, dependencies, scaling.
- Signal bot can be replaced (different exchange, different strategy) without touching discipline logic.
- Slight latency overhead (~50 ms HTTP roundtrip) is irrelevant for these flows.

---

## 4. aiogram FSM for the trade-check conversation

**Context.** Collecting 13 trade parameters via Telegram needs state that survives between messages. Putting it all in `/trade pair=BTC/USDT direction=long entry=…` (single command with named args) is unusable on mobile.

**Decision.** Use aiogram 3 `StatesGroup` (FSM) with one state per question. Each handler reads the user's reply, validates, stores in `state.update_data()`, and advances to the next state. Voice input pre-fills 5 of 13 fields and jumps the FSM straight to the deposit step.

**Consequences.**
- The flow is forgiving (one question at a time, no parsing).
- State is in-memory (`MemoryStorage`) — restart of the bot loses unfinished checks. This is fine for an MVP; for production we'd swap in `RedisStorage`.

---

## 5. Async SQLAlchemy 2.0 + Alembic

**Context.** Bot, FastAPI and notifier all do DB work concurrently. Sync drivers would force thread pools or block the event loop.

**Decision.** Async SQLAlchemy with `asyncpg`. Migrations via Alembic with a separate sync URL (`psycopg2`) — Alembic itself is sync, and trying to run async migrations is more pain than gain.

**Consequences.**
- Two URLs in `.env` (`DATABASE_URL` async, `ALEMBIC_DATABASE_URL` sync).
- Need `selectinload` for eager loading or `lazy="selectin"` on relationships, otherwise async lazy load raises `MissingGreenlet`.
- `expire_on_commit=False` on the session factory so attributes survive commit.

---

## 6. Flutter Web (PWA), not native first

**Context.** Building three native apps (iOS, Android, web) is 3× the effort. The product is data-light and UI-heavy — perfect for cross-platform.

**Decision.** Flutter Web compiled to PWA. Same codebase later targets Android/iOS with one `flutter build` command. PWA means the user can "install" the app from Chrome and have it on their dock without an App Store.

**Consequences.**
- One codebase, three deploy targets when needed.
- Initial bundle is ~3 MB (acceptable for a tool you use daily).
- `google_fonts` downloads Inter at first load — can be bundled later for offline-first.

---

## 7. Risk-side hard rules in pure code, not AI

**Context.** Some rules are non-negotiable: no SL = no trade. If the AI gets cute and "explains" why this case is fine — the user blows their account. AI must not have a vote on the boolean.

**Decision.** All eight blocking rules live in `risk_engine.check_rules()` as plain Python with explicit `RuleViolation(blocking=True)` objects. The decision engine respects the boolean before consulting any AI.

**Consequences.**
- Rules are unit-tested (29 tests covering every blocker).
- Adding a new rule is a one-line change + one test.
- Makes the AI layer "advisory plus" — it can downgrade `ALLOWED` to `WAIT` or `FORBIDDEN`, but it can never lift a hard block.

---

## 8. Decision storage in English literals, UI in Russian

**Context.** The product targets Russian-speaking traders, but mixing Russian and English in DB constants makes joins, indexing and code review harder.

**Decision.** All enum-like values in DB and code are English (`ALLOWED`, `FORBIDDEN`, `WAIT`, `WIN`, `LOSS`). User-facing strings are translated at the edge (Telegram replies, Flutter labels) via a `DECISION_LABELS` map.

**Consequences.**
- Easy to add an English UI later — only the labels map changes.
- Easier to grep / write SQL.
- Slight duplication in two places (Telegram + Flutter), but it's static data that rarely changes.

---

## 9. Background jobs in the bot process, not Celery

**Context.** We have three recurring jobs: morning check-in (09:00 UTC), evening pending-trade reminder (22:00 UTC), weekly AI review (Sunday 18:00 UTC), plus a 60-second push poller for new market signals.

**Decision.** Plain `asyncio.create_task` loops inside the aiogram process. State (last-run date) is in memory.

**Consequences.**
- Zero infrastructure overhead — no Redis broker, no worker, no Beat.
- Bot restart misses one tick of any scheduled job — acceptable, jobs are not safety-critical.
- For >100 users we'd move to APScheduler or Celery Beat, but at MVP scale this is overkill.

---

## 10. Voice input via Whisper + LLM parsing

**Context.** Typing a trade on a phone is slow. Voice is natural — "BTC long 67500 stop 66800 take 69200" is a 4-second utterance.

**Decision.** Telegram voice → OpenAI Whisper (paid) → Ollama (local, free) parses the transcript into structured JSON → FSM is pre-filled. Whisper is the only paid path; if no OpenAI key is configured, the feature degrades to "send text instead".

**Consequences.**
- Cost per voice message ≈ $0.001 (Whisper bills at $0.006/min).
- Russian transcription quality is excellent.
- Could later swap Whisper for `whisper.cpp` running locally to make the whole pipeline free.

---

## Trade-offs we accepted, on purpose

- **No authentication on the FastAPI surface yet.** The product is single-user / private deployment for now; a token gate is on the roadmap before any public hosting.
- **No rate limit on AI endpoints.** Same reason. With OpenAI keys in `.env`, a malicious caller could rack up bills — to be solved with both auth and a per-token bucket.
- **No CI on the Flutter side.** `flutter analyze` is run manually; adding it to CI requires a Flutter setup step that doubles workflow time.
- **In-memory FSM storage.** Good enough for restart-once-a-week MVP, not for multi-replica production.

These are listed openly because pretending they don't exist would be dishonest, and a recruiter or a future contributor will spot them in 30 seconds anyway.
