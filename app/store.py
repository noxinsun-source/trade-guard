from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
from pathlib import Path

from app.models import OrderRequest, RiskDecision


class IdempotencyConflict(Exception):
    pass


class DecisionStore:
    def __init__(self, database_path: str) -> None:
        self.database_path = database_path
        self._lock = threading.Lock()
        if database_path != ":memory:":
            Path(database_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS risk_decisions (
                decision_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE NOT NULL,
                request_hash TEXT NOT NULL,
                request_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    @staticmethod
    def request_hash(order: OrderRequest) -> str:
        payload = order.model_dump_json(exclude={"idempotency_key"})
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def find_by_key(self, order: OrderRequest) -> RiskDecision | None:
        request_hash = self.request_hash(order)
        row = self._connection.execute(
            "SELECT request_hash, response_json FROM risk_decisions WHERE idempotency_key = ?",
            (order.idempotency_key,),
        ).fetchone()
        if row is None:
            return None
        if row["request_hash"] != request_hash:
            raise IdempotencyConflict("同一幂等键对应了不同的委托内容")
        return RiskDecision.model_validate_json(row["response_json"])

    def save(self, order: OrderRequest, decision: RiskDecision) -> None:
        with self._lock:
            self._connection.execute(
                """
                INSERT INTO risk_decisions (
                    decision_id, idempotency_key, request_hash,
                    request_json, response_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    decision.decision_id,
                    order.idempotency_key,
                    self.request_hash(order),
                    order.model_dump_json(),
                    decision.model_dump_json(),
                    decision.created_at.isoformat(),
                ),
            )
            self._connection.commit()

    def get(self, decision_id: str) -> RiskDecision | None:
        row = self._connection.execute(
            "SELECT response_json FROM risk_decisions WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        return None if row is None else RiskDecision.model_validate_json(row["response_json"])

    def count_by_status(self) -> dict[str, int]:
        rows = self._connection.execute("SELECT response_json FROM risk_decisions").fetchall()
        counts = {"PASS": 0, "REVIEW": 0, "REJECT": 0}
        for row in rows:
            status = json.loads(row["response_json"])["status"]
            counts[status] += 1
        return counts

