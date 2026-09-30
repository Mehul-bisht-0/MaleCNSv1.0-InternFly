from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from .domain import AgentSnapshot, Provenance


SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS events (
  sequence INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT UNIQUE NOT NULL,
  event_type TEXT NOT NULL,
  occurred_at TEXT NOT NULL,
  correlation_id TEXT NOT NULL,
  causation_id TEXT,
  idempotency_key TEXT UNIQUE,
  actor_type TEXT NOT NULL,
  provenance_class TEXT NOT NULL,
  payload TEXT NOT NULL,
  payload_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS agent_state (
  singleton INTEGER PRIMARY KEY CHECK(singleton=1),
  version INTEGER NOT NULL,
  snapshot TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  job_id TEXT PRIMARY KEY,
  canonical_identity TEXT UNIQUE NOT NULL,
  company TEXT NOT NULL,
  title TEXT NOT NULL,
  location TEXT NOT NULL,
  description TEXT NOT NULL,
  source TEXT NOT NULL,
  score REAL,
  decision TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
  draft_id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL REFERENCES jobs(job_id),
  version INTEGER NOT NULL,
  status TEXT NOT NULL,
  content TEXT NOT NULL,
  evidence_map TEXT NOT NULL,
  unsupported_claims TEXT NOT NULL,
  content_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(job_id, version)
);
CREATE TABLE IF NOT EXISTS approvals (
  approval_id TEXT PRIMARY KEY,
  draft_id TEXT NOT NULL REFERENCES drafts(draft_id),
  draft_content_hash TEXT NOT NULL,
  decision TEXT NOT NULL,
  reason TEXT,
  decided_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
  attempt_id TEXT PRIMARY KEY,
  cycle INTEGER NOT NULL,
  problem_key TEXT NOT NULL,
  attempt_no INTEGER NOT NULL,
  strategy TEXT NOT NULL,
  outcome TEXT NOT NULL,
  runtime_ms REAL NOT NULL,
  memory_bytes INTEGER NOT NULL,
  code_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(cycle, problem_key, attempt_no)
);
CREATE TABLE IF NOT EXISTS memories (
  memory_id TEXT PRIMARY KEY,
  memory_type TEXT NOT NULL,
  content TEXT NOT NULL,
  confidence REAL NOT NULL,
  strength REAL NOT NULL,
  fictional INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dreams (
  dream_id TEXT PRIMARY KEY,
  cycle INTEGER NOT NULL,
  text TEXT NOT NULL,
  created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(UTC).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class EventStore:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        with self.connect() as db:
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def append(
        self,
        event_type: str,
        payload: dict[str, Any],
        provenance: Provenance,
        *,
        actor: str = "orchestrator",
        idempotency_key: str | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
    ) -> dict[str, Any]:
        body = canonical_json(payload)
        event = {
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "occurred_at": now(),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "causation_id": causation_id,
            "idempotency_key": idempotency_key,
            "actor_type": actor,
            "provenance_class": provenance.value,
            "payload": payload,
            "payload_hash": hashlib.sha256(body.encode()).hexdigest(),
        }
        with self._lock, self.connect() as db:
            try:
                cur = db.execute(
                    """INSERT INTO events(event_id,event_type,occurred_at,correlation_id,causation_id,
                       idempotency_key,actor_type,provenance_class,payload,payload_hash)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        event["event_id"], event_type, event["occurred_at"], event["correlation_id"],
                        causation_id, idempotency_key, actor, provenance.value, body, event["payload_hash"],
                    ),
                )
                event["sequence"] = cur.lastrowid
            except sqlite3.IntegrityError:
                if not idempotency_key:
                    raise
                row = db.execute("SELECT * FROM events WHERE idempotency_key=?", (idempotency_key,)).fetchone()
                return self._event_row(row)
        return event

    @staticmethod
    def _event_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        return item

    def events(self, limit: int = 100, after: int = 0) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT * FROM events WHERE sequence>? ORDER BY sequence DESC LIMIT ?", (after, limit)
            ).fetchall()
        return [self._event_row(row) for row in reversed(rows)]

    def save_snapshot(self, snapshot: AgentSnapshot) -> None:
        body = canonical_json(snapshot.to_dict())
        with self._lock, self.connect() as db:
            current = db.execute("SELECT version FROM agent_state WHERE singleton=1").fetchone()
            version = (current["version"] + 1) if current else 1
            db.execute(
                """INSERT INTO agent_state(singleton,version,snapshot,updated_at) VALUES(1,?,?,?)
                   ON CONFLICT(singleton) DO UPDATE SET version=excluded.version,
                   snapshot=excluded.snapshot,updated_at=excluded.updated_at""",
                (version, body, now()),
            )

    def load_snapshot(self) -> AgentSnapshot | None:
        with self.connect() as db:
            row = db.execute("SELECT snapshot FROM agent_state WHERE singleton=1").fetchone()
        return AgentSnapshot.from_dict(json.loads(row["snapshot"])) if row else None

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> int:
        with self._lock, self.connect() as db:
            cur = db.execute(sql, params)
            return cur.rowcount

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as db:
            return [dict(row) for row in db.execute(sql, params).fetchall()]

    def counts(self) -> dict[str, Any]:
        with self.connect() as db:
            scalar = lambda query: db.execute(query).fetchone()[0]
            attempts = scalar("SELECT COUNT(*) FROM attempts")
            solved = scalar("SELECT COUNT(*) FROM attempts WHERE outcome='solved'")
            return {
                "events": scalar("SELECT COUNT(*) FROM events"),
                "cycles_completed": scalar("SELECT COUNT(*) FROM events WHERE event_type='cycle.completed'"),
                "dsa_attempted": attempts,
                "dsa_solved": solved,
                "dsa_success_rate": round(100 * solved / attempts, 1) if attempts else 0,
                "jobs_discovered": scalar("SELECT COUNT(*) FROM jobs"),
                "jobs_evaluated": scalar("SELECT COUNT(*) FROM jobs WHERE score IS NOT NULL"),
                "drafts_created": scalar("SELECT COUNT(*) FROM drafts"),
                "drafts_pending": scalar("SELECT COUNT(*) FROM drafts WHERE status='pending'"),
                "drafts_approved": scalar("SELECT COUNT(*) FROM drafts WHERE status='approved'"),
                "dreams_generated": scalar("SELECT COUNT(*) FROM dreams"),
                "memories": scalar("SELECT COUNT(*) FROM memories"),
            }

