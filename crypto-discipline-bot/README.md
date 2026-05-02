# AI Risk & Discipline Assistant

Telegram-бот, который помогает крипто-трейдеру **перед входом в сделку** проверить дисциплину, риск, плечо, stop-loss, take-profit, R:R и эмоциональное состояние. Бот возвращает один из трёх вердиктов: **РАЗРЕШЕНО / ЗАПРЕЩЕНО / ЖДАТЬ**.

> ⚠️ Это не финансовая рекомендация. Бот не обещает прибыль и не гарантирует исход сделок. Он работает как risk officer и discipline coach.

## Что внутри

- **Telegram-бот** на `aiogram` 3.x — диалог с FSM собирает параметры сделки.
- **FastAPI backend** — те же расчёты доступны через REST для будущих SaaS-клиентов.
- **Risk Engine** — детерминированные правила (нет SL → блок, риск > лимит → блок, R:R < минимума → блок, плечо > лимит → блок, эмоции / revenge trading → блок).
- **AI Coach (OpenAI)** — мягкий разбор с плюсами/минусами. Только совет, без права вето.
- **AI Risk Officer (Claude)** — строгий аудитор с правом запретить сделку.
- **Decision Engine** — правила имеют приоритет над Officer, Officer — над Coach.
- **PostgreSQL + SQLAlchemy + Alembic** — журнал сделок и пользовательские настройки.
- **Docker + docker-compose** — поднимается в три контейнера: db, api, bot.

## Структура проекта

```
crypto-discipline-bot/
  app/
    main.py              # FastAPI
    config.py            # настройки из .env
    database.py          # async SQLAlchemy
    models.py            # User, UserSettings, Trade
    schemas.py           # Pydantic
    services/
      risk_engine.py     # расчёты + жёсткие правила
      ai_coach.py        # OpenAI
      ai_risk_officer.py # Claude
      decision_engine.py # объединение
      stats_service.py   # журнал и статистика
    bot/
      main.py            # точка входа aiogram
      handlers.py        # все команды + FSM
      states.py          # FSM-состояния
      keyboards.py       # клавиатуры
  alembic/               # миграции
  tests/                 # unit-тесты
  docker-compose.yml
  Dockerfile
  requirements.txt
  .env.example
```

## Команды бота

| Команда     | Описание                                  |
|-------------|--------------------------------------------|
| `/start`    | приветствие, регистрация                  |
| `/help`     | как пользоваться                           |
| `/trade`    | начать проверку сделки (13 вопросов)       |
| `/journal`  | последние 10 сделок                        |
| `/stats`    | сводная статистика                         |
| `/rules`    | правила риска по умолчанию                 |
| `/settings` | настроить лимиты (риск, плечо, R:R, daily) |

## Как запустить

### 1. Подготовка

```bash
cd crypto-discipline-bot
cp .env.example .env
# отредактируй .env: BOT_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY, пароли БД
```

### 2. Запуск через Docker (рекомендуется)

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

После этого:
- бот стартует и слушает Telegram
- API доступен на `http://localhost:8000` (Swagger: `/docs`)

### 3. Запуск локально без Docker

```bash
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
.venv\Scripts\activate             # Windows
pip install -r requirements.txt

# Применить миграции (нужна работающая Postgres из .env)
alembic upgrade head

# Терминал 1 — backend
uvicorn app.main:app --reload

# Терминал 2 — бот
python -m app.bot.main
```

## Настройка .env

| Переменная                | Назначение                                       |
|--------------------------|---------------------------------------------------|
| `BOT_TOKEN`              | токен от @BotFather                               |
| `DATABASE_URL`           | async URL для приложения (`postgresql+asyncpg://...`) |
| `ALEMBIC_DATABASE_URL`   | sync URL для миграций (`postgresql+psycopg2://...`)   |
| `OPENAI_API_KEY`         | ключ OpenAI (Coach)                               |
| `OPENAI_MODEL`           | модель, по умолчанию `gpt-4o-mini`                |
| `ANTHROPIC_API_KEY`      | ключ Anthropic (Risk Officer)                     |
| `ANTHROPIC_MODEL`        | модель, по умолчанию `claude-3-5-sonnet-latest`   |
| `DEFAULT_MAX_RISK_PERCENT` | дефолтный лимит риска (1%)                      |
| `DEFAULT_MAX_LEVERAGE`   | дефолтное максимальное плечо (5)                  |
| `DEFAULT_MIN_RR`         | минимальный R:R (2.0 = 1:2)                       |
| `DEFAULT_DAILY_LOSS_LIMIT` | дневной лимит убытка (-2%)                      |

## Жёсткие правила (блокируют сделку)

Сделка **автоматически запрещается**, если:

1. Не указан stop-loss
2. Риск на сделку выше лимита (по умолчанию 1%)
3. R:R ниже минимума (по умолчанию 1:2)
4. Плечо выше лимита (по умолчанию x5)
5. Дневной убыток достиг лимита (-2%)
6. Две убыточные сделки подряд
7. Пользователь упомянул "отыграться" / revenge / tilt
8. Эмоция: злость / паника / жадность / FOMO

## Тесты

```bash
pip install -r requirements.txt
pytest -q
```

Покрыто:
- расчёт R:R и distance
- запрет без stop-loss
- запрет при риске выше лимита
- запрет при R:R ниже минимума
- запрет при большом плече
- определение revenge trading в тексте
- vето правил над AI Coach и AI Risk Officer
- vето Officer над Coach

## Безопасность и дисклеймер

- Все секреты — только через `.env`. В коде ключей нет.
- Бот **никогда** не пишет "гарантированный доход", "точно заработаешь", "100%".
- В каждом ответе есть дисклеймер: *"Это не финансовая рекомендация. Бот помогает контролировать риск и дисциплину."*
- Финальное решение и ответственность остаются за трейдером.

## Roadmap (для SaaS)

- Web-кабинет (FastAPI уже готов как API-слой)
- Биллинг и тарифы
- Импорт сделок с биржи
- Интеграция с TradingView webhook
- Командные роли (трейдер / тимлид / risk manager)
