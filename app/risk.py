from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.models import (
    DecisionStatus,
    OrderRequest,
    RiskDecision,
    RuleResult,
    RuleSeverity,
    Side,
)


@dataclass(frozen=True)
class RiskLimits:
    max_order_notional: Decimal = Decimal(200000)
    max_daily_turnover: Decimal = Decimal(1000000)
    max_position_concentration: Decimal = Decimal("0.25")
    review_price_deviation: Decimal = Decimal("0.05")
    reject_price_deviation: Decimal = Decimal("0.10")


class RiskEngine:
    def __init__(self, limits: RiskLimits | None = None) -> None:
        self.limits = limits or RiskLimits()

    def evaluate(self, order: OrderRequest, decision_id: str) -> RiskDecision:
        notional = order.price * order.quantity
        signed_quantity = order.quantity if order.side is Side.BUY else -order.quantity
        projected_position = order.current_position + signed_quantity
        projected_exposure = max(projected_position, 0) * order.price
        concentration = projected_exposure / order.portfolio_value
        deviation = abs(order.price - order.reference_price) / order.reference_price

        rules = [
            self._rule(
                "ORDER_NOTIONAL_LIMIT",
                notional <= self.limits.max_order_notional,
                RuleSeverity.REJECT,
                f"{notional:.2f}",
                f"<= {self.limits.max_order_notional:.2f}",
                "单笔委托金额不得超过账户限额",
            ),
            self._rule(
                "SELL_POSITION_CHECK",
                order.side is Side.BUY or projected_position >= 0,
                RuleSeverity.REJECT,
                str(projected_position),
                ">= 0",
                "卖出数量不得超过可用持仓",
            ),
            self._rule(
                "PRICE_DEVIATION_REJECT",
                deviation <= self.limits.reject_price_deviation,
                RuleSeverity.REJECT,
                f"{deviation:.2%}",
                f"<= {self.limits.reject_price_deviation:.2%}",
                "委托价与参考价偏离过大",
            ),
            self._rule(
                "PRICE_DEVIATION_REVIEW",
                deviation <= self.limits.review_price_deviation,
                RuleSeverity.REVIEW,
                f"{deviation:.2%}",
                f"<= {self.limits.review_price_deviation:.2%}",
                "价格偏离超过复核阈值",
            ),
            self._rule(
                "POSITION_CONCENTRATION",
                concentration <= self.limits.max_position_concentration,
                RuleSeverity.REVIEW,
                f"{concentration:.2%}",
                f"<= {self.limits.max_position_concentration:.2%}",
                "交易后单一证券持仓集中度超过阈值",
            ),
            self._rule(
                "DAILY_TURNOVER_LIMIT",
                order.daily_traded_notional + notional <= self.limits.max_daily_turnover,
                RuleSeverity.REVIEW,
                f"{order.daily_traded_notional + notional:.2f}",
                f"<= {self.limits.max_daily_turnover:.2f}",
                "账户当日累计交易额超过复核阈值",
            ),
        ]

        status = DecisionStatus.PASS
        if any(not r.passed and r.severity is RuleSeverity.REJECT for r in rules):
            status = DecisionStatus.REJECT
        elif any(not r.passed and r.severity is RuleSeverity.REVIEW for r in rules):
            status = DecisionStatus.REVIEW

        return RiskDecision(
            decision_id=decision_id,
            status=status,
            account_id=order.account_id,
            instrument=order.instrument,
            order_notional=notional,
            projected_position=projected_position,
            rules=rules,
        )

    @staticmethod
    def _rule(
        code: str,
        passed: bool,
        severity: RuleSeverity,
        observed: str,
        threshold: str,
        message: str,
    ) -> RuleResult:
        return RuleResult(
            rule_code=code,
            severity=severity,
            passed=passed,
            observed=observed,
            threshold=threshold,
            message=message,
        )
