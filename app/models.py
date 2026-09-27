from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, Field, model_validator


class Side(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class DecisionStatus(str, Enum):
    PASS = "PASS"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class RuleSeverity(str, Enum):
    INFO = "INFO"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


class OrderRequest(BaseModel):
    account_id: str = Field(min_length=1, max_length=64)
    instrument: str = Field(min_length=1, max_length=32)
    side: Side
    quantity: int = Field(gt=0)
    price: Decimal = Field(gt=0, decimal_places=4)
    reference_price: Decimal = Field(gt=0, decimal_places=4)
    current_position: int = Field(ge=0)
    portfolio_value: Decimal = Field(gt=0)
    daily_traded_notional: Decimal = Field(ge=0)
    idempotency_key: str = Field(min_length=8, max_length=128)

    @model_validator(mode="after")
    def normalize_instrument(self) -> OrderRequest:
        self.instrument = self.instrument.strip().upper()
        self.account_id = self.account_id.strip()
        return self


class RuleResult(BaseModel):
    rule_code: str
    severity: RuleSeverity
    passed: bool
    observed: str
    threshold: str
    message: str


class RiskDecision(BaseModel):
    decision_id: str
    status: DecisionStatus
    account_id: str
    instrument: str
    order_notional: Decimal
    projected_position: int
    rules: list[RuleResult]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(BaseModel):
    status: str
    service: str
