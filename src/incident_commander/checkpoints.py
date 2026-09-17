from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def _encode(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _encode(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {key: _encode(item) for key, item in value.items() if key not in {"gateway", "checkpoint_store"}}
    if isinstance(value, (list, tuple)):
        return [_encode(item) for item in value]
    return value


class CheckpointStore:
    """Durable run snapshots; the interface can later be backed by PostgreSQL."""

    def __init__(self, path: str):
        self.connection = sqlite3.connect(path)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS checkpoints ("
            "run_id TEXT PRIMARY KEY, incident_id TEXT NOT NULL, status TEXT NOT NULL, "
            "state_json TEXT NOT NULL)"
        )
        self.connection.commit()

    def save(self, run_id: str, incident_id: str, status: str, state: dict[str, Any]) -> None:
        payload = json.dumps(_encode(state), sort_keys=True)
        self.connection.execute(
            "INSERT INTO checkpoints(run_id, incident_id, status, state_json) VALUES (?, ?, ?, ?) "
            "ON CONFLICT(run_id) DO UPDATE SET status=excluded.status, state_json=excluded.state_json",
            (run_id, incident_id, status, payload),
        )
        self.connection.commit()

    def load(self, run_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT run_id, incident_id, status, state_json FROM checkpoints WHERE run_id = ?", (run_id,)
        ).fetchone()
        if row is None:
            return None
        return {"run_id": row[0], "incident_id": row[1], "status": row[2], "state": json.loads(row[3])}

    def list_runs(self) -> list[dict[str, str]]:
        rows = self.connection.execute(
            "SELECT run_id, incident_id, status FROM checkpoints ORDER BY run_id"
        ).fetchall()
        return [{"run_id": row[0], "incident_id": row[1], "status": row[2]} for row in rows]

    def load_by_approval(self, approval_id: str) -> dict[str, Any] | None:
        rows = self.connection.execute(
            "SELECT run_id, incident_id, status, state_json FROM checkpoints"
        ).fetchall()
        for row in rows:
            state = json.loads(row[3])
            if state.get("approval_id") == approval_id:
                return {"run_id": row[0], "incident_id": row[1], "status": row[2], "state": state}
        return None

    def close(self) -> None:
        self.connection.close()
