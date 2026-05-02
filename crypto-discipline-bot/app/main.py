from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.schemas import (
    CloseTradeRequest,
    PositionCalcRequest,
    PositionCalcResult,
    StatsOut,
    TradeOut,
    TradeRequest,
    TradeResponse,
    UserSettingsOut,
    UserSettingsUpdate,
)
from app.services import export_service, stats_service
from app.services.ai_coach import AICoach
from app.services.ai_risk_officer import AIRiskOfficer
from app.services.decision_engine import decide
from app.services.position_calc import calculate_position
from app.services.risk_engine import UserPolicy

logging.basicConfig(level=settings.log_level)

app = FastAPI(
    title="AI Risk & Discipline Assistant",
    version="0.1.0",
    description="Backend for crypto trade-discipline bot. Not a financial advisor.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_db() -> AsyncSession:  # type: ignore[misc]
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_coach() -> AICoach:
    return AICoach(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model_coach,
    )


def get_officer() -> AIRiskOfficer:
    return AIRiskOfficer(
        api_key=settings.anthropic_api_key,
        model=settings.anthropic_model,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model_officer,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/users/{telegram_id}/trades/check", response_model=TradeResponse)
async def check_trade(
    telegram_id: int,
    req: TradeRequest,
    session: AsyncSession = Depends(get_db),
    coach: AICoach = Depends(get_coach),
    officer: AIRiskOfficer = Depends(get_officer),
) -> TradeResponse:
    user = await stats_service.get_or_create_user(session, telegram_id)
    s = user.settings
    policy = UserPolicy(
        max_risk_percent=s.max_risk_percent,
        max_leverage=s.max_leverage,
        min_rr=s.min_rr,
        daily_loss_limit=s.daily_loss_limit,
    )
    response = await decide(req, policy, coach, officer)
    await stats_service.save_trade(session, user, req, response)
    return response


@app.get("/users/{telegram_id}/trades", response_model=list[TradeOut])
async def list_trades(
    telegram_id: int = Path(..., ge=1),
    limit: int = 10,
    session: AsyncSession = Depends(get_db),
) -> list[TradeOut]:
    user = await stats_service.get_or_create_user(session, telegram_id)
    return await stats_service.list_recent_trades(session, user, limit=limit)


@app.get("/users/{telegram_id}/stats", response_model=StatsOut)
async def get_stats(
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
) -> StatsOut:
    user = await stats_service.get_or_create_user(session, telegram_id)
    return await stats_service.compute_stats(session, user)


@app.get("/users/{telegram_id}/settings", response_model=UserSettingsOut)
async def read_settings(
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
) -> UserSettingsOut:
    user = await stats_service.get_or_create_user(session, telegram_id)
    return UserSettingsOut.model_validate(user.settings)


@app.patch("/users/{telegram_id}/settings", response_model=UserSettingsOut)
async def update_settings(
    telegram_id: int,
    update: UserSettingsUpdate,
    session: AsyncSession = Depends(get_db),
) -> UserSettingsOut:
    user = await stats_service.get_or_create_user(session, telegram_id)
    s = user.settings
    if update.max_risk_percent is not None:
        s.max_risk_percent = update.max_risk_percent
    if update.max_leverage is not None:
        s.max_leverage = update.max_leverage
    if update.min_rr is not None:
        s.min_rr = update.min_rr
    if update.daily_loss_limit is not None:
        s.daily_loss_limit = update.daily_loss_limit
    if all(v is None for v in update.model_dump().values()):
        raise HTTPException(status_code=400, detail="Nothing to update")
    return UserSettingsOut.model_validate(s)


@app.patch("/users/{telegram_id}/trades/{trade_id}/close", response_model=TradeOut)
async def close_trade(
    telegram_id: int,
    trade_id: int,
    payload: CloseTradeRequest,
    session: AsyncSession = Depends(get_db),
) -> TradeOut:
    user = await stats_service.get_or_create_user(session, telegram_id)
    trade = await stats_service.close_trade(session, user, trade_id, payload)
    if trade is None:
        raise HTTPException(status_code=404, detail="Trade not found")
    return TradeOut.model_validate(trade)


@app.post("/calc/position", response_model=PositionCalcResult)
async def calc_position(req: PositionCalcRequest) -> PositionCalcResult:
    try:
        return calculate_position(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/users/{telegram_id}/trades/export.csv")
async def export_trades(
    telegram_id: int,
    session: AsyncSession = Depends(get_db),
) -> Response:
    user = await stats_service.get_or_create_user(session, telegram_id)
    csv_bytes = await export_service.export_trades_csv(session, user)
    return Response(
        content=csv_bytes,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="trades_{telegram_id}.csv"'
        },
    )
