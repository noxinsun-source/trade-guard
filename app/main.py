from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse

from app.models import HealthResponse, OrderRequest, RiskDecision
from app.risk import RiskEngine
from app.store import DecisionStore, IdempotencyConflict


def create_app(database_path: str | None = None) -> FastAPI:
    db_path = database_path or os.getenv("TRADE_GUARD_DB", "data/trade_guard.db")
    store = DecisionStore(db_path)
    engine = RiskEngine()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.store = store
        app.state.engine = engine
        yield

    app = FastAPI(
        title="TradeGuard",
        version="1.0.0",
        description="面向证券中后台的可解释交易前风控与审计服务",
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", service="trade-guard")

    @app.post("/v1/risk/check", response_model=RiskDecision)
    def check_order(order: OrderRequest, request: Request) -> RiskDecision:
        decision_store: DecisionStore = request.app.state.store
        try:
            previous = decision_store.find_by_key(order)
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if previous is not None:
            return previous

        decision = request.app.state.engine.evaluate(order, str(uuid.uuid4()))
        decision_store.save(order, decision)
        return decision

    @app.get("/v1/risk/decisions/{decision_id}", response_model=RiskDecision)
    def get_decision(decision_id: str, request: Request) -> RiskDecision:
        decision = request.app.state.store.get(decision_id)
        if decision is None:
            raise HTTPException(status_code=404, detail="未找到该风控决策")
        return decision

    @app.get("/metrics", response_class=PlainTextResponse)
    def metrics(request: Request) -> str:
        counts = request.app.state.store.count_by_status()
        lines = [
            "# HELP trade_guard_decisions_total Total pre-trade risk decisions",
            "# TYPE trade_guard_decisions_total counter",
        ]
        lines.extend(
            f'trade_guard_decisions_total{{status="{status}"}} {count}'
            for status, count in counts.items()
        )
        return "\n".join(lines) + "\n"

    return app


app = create_app()

