"""SQLite persistence layer.

Schema
------
sessions          one row per analysed requirement
session_metadata  1:1 with sessions - analysis, provider, timing and quality metrics
test_cases        N:1 with sessions - the generated / edited test cases

Foreign keys use ``ON DELETE CASCADE`` so deleting a session removes its
metadata and test cases atomically. All statements are parameterised.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from config import PRIORITIES, SCENARIO_TYPES

SCHEMA_VERSION = 1

_SCHEMA = f"""
CREATE TABLE IF NOT EXISTS sessions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    title           TEXT    NOT NULL,
    requirement     TEXT    NOT NULL,
    scenario_types  TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'completed',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS session_metadata (
    session_id          INTEGER PRIMARY KEY REFERENCES sessions(id) ON DELETE CASCADE,
    provider            TEXT,
    model               TEXT,
    analysis_json       TEXT,
    warnings_json       TEXT,
    generation_seconds  REAL    DEFAULT 0,
    raw_case_count      INTEGER DEFAULT 0,
    duplicates_removed  INTEGER DEFAULT 0,
    repair_attempts     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS test_cases (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id       INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    case_code        TEXT    NOT NULL,
    scenario         TEXT    NOT NULL,
    scenario_type    TEXT    NOT NULL CHECK (scenario_type IN ({", ".join(repr(s) for s in SCENARIO_TYPES)})),
    steps            TEXT    NOT NULL,
    test_data        TEXT    NOT NULL DEFAULT 'N/A',
    expected_result  TEXT    NOT NULL,
    priority         TEXT    NOT NULL CHECK (priority IN ({", ".join(repr(p) for p in PRIORITIES)})),
    assumption       TEXT    NOT NULL DEFAULT '',
    source           TEXT    NOT NULL DEFAULT 'ai',
    position         INTEGER NOT NULL DEFAULT 0,
    created_at       TEXT    NOT NULL,
    updated_at       TEXT    NOT NULL,
    UNIQUE (session_id, case_code)
);

CREATE INDEX IF NOT EXISTS idx_test_cases_session ON test_cases(session_id, position);
CREATE INDEX IF NOT EXISTS idx_sessions_created ON sessions(created_at);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def steps_to_text(steps: list[str] | str) -> str:
    if isinstance(steps, str):
        return steps.strip()
    return "\n".join(s.strip() for s in steps if s and s.strip())


def text_to_steps(text: str) -> list[str]:
    return [line.strip() for line in (text or "").splitlines() if line.strip()]


class Database:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    # ------------------------------------------------------------------ core
    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(_SCHEMA)
            conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")

    # ------------------------------------------------------------- sessions
    def create_session(self, *, title: str, requirement: str, scenario_types: list[str],
                       test_cases: list[dict[str, Any]], status: str = "completed",
                       metadata: dict[str, Any] | None = None) -> int:
        """Insert a session, its metadata and its test cases in one transaction."""
        meta = metadata or {}
        now = _now()
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO sessions (title, requirement, scenario_types, status, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (title.strip()[:120] or "Untitled requirement", requirement, json.dumps(scenario_types),
                 status, now, now),
            )
            session_id = int(cur.lastrowid)
            conn.execute(
                "INSERT INTO session_metadata (session_id, provider, model, analysis_json, warnings_json, "
                "generation_seconds, raw_case_count, duplicates_removed, repair_attempts) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (session_id, meta.get("provider"), meta.get("model"),
                 json.dumps(meta.get("analysis") or {}, ensure_ascii=False),
                 json.dumps(meta.get("warnings") or [], ensure_ascii=False),
                 float(meta.get("generation_seconds") or 0), int(meta.get("raw_case_count") or 0),
                 int(meta.get("duplicates_removed") or 0), int(meta.get("repair_attempts") or 0)),
            )
            for pos, case in enumerate(test_cases, start=1):
                self._insert_case(conn, session_id, case, f"TC-{pos:03d}", pos, now)
        return session_id

    @staticmethod
    def _insert_case(conn: sqlite3.Connection, session_id: int, case: dict[str, Any],
                     code: str, position: int, now: str) -> int:
        cur = conn.execute(
            "INSERT INTO test_cases (session_id, case_code, scenario, scenario_type, steps, test_data, "
            "expected_result, priority, assumption, source, position, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (session_id, code, case["scenario"], case["scenario_type"], steps_to_text(case["steps"]),
             case.get("test_data") or "N/A", case["expected_result"], case["priority"],
             case.get("assumption") or "", case.get("source", "ai"), position, now, now),
        )
        return int(cur.lastrowid)

    def list_sessions(self, search: str = "") -> list[dict[str, Any]]:
        sql = (
            "SELECT s.*, m.provider, m.model, m.generation_seconds, "
            "COUNT(t.id) AS case_count, "
            "SUM(CASE WHEN t.priority='High' THEN 1 ELSE 0 END) AS high_count, "
            "SUM(CASE WHEN t.priority='Medium' THEN 1 ELSE 0 END) AS medium_count, "
            "SUM(CASE WHEN t.priority='Low' THEN 1 ELSE 0 END) AS low_count "
            "FROM sessions s LEFT JOIN session_metadata m ON m.session_id = s.id "
            "LEFT JOIN test_cases t ON t.session_id = s.id "
        )
        params: list[Any] = []
        if search.strip():
            sql += "WHERE s.title LIKE ? OR s.requirement LIKE ? "
            like = f"%{search.strip()}%"
            params += [like, like]
        sql += "GROUP BY s.id ORDER BY s.created_at DESC, s.id DESC"
        with self.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [self._session_row(r) for r in rows]

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT s.*, m.provider, m.model, m.analysis_json, m.warnings_json, m.generation_seconds, "
                "m.raw_case_count, m.duplicates_removed, m.repair_attempts "
                "FROM sessions s LEFT JOIN session_metadata m ON m.session_id = s.id WHERE s.id = ?",
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        data = self._session_row(row)
        data["analysis"] = json.loads(row["analysis_json"] or "{}")
        data["warnings"] = json.loads(row["warnings_json"] or "[]")
        data["test_cases"] = self.get_test_cases(session_id)
        data["case_count"] = len(data["test_cases"])
        return data

    @staticmethod
    def _session_row(row: sqlite3.Row) -> dict[str, Any]:
        d = {k: row[k] for k in row.keys() if k not in ("analysis_json", "warnings_json")}
        d["scenario_types"] = json.loads(d.get("scenario_types") or "[]")
        for k in ("case_count", "high_count", "medium_count", "low_count"):
            if k in d:
                d[k] = int(d[k] or 0)
        return d

    def rename_session(self, session_id: int, title: str) -> bool:
        with self.connect() as conn:
            cur = conn.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?",
                               (title.strip()[:120], _now(), session_id))
        return cur.rowcount > 0

    def delete_session(self, session_id: int) -> bool:
        with self.connect() as conn:
            cur = conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0

    def _touch(self, conn: sqlite3.Connection, session_id: int) -> None:
        conn.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (_now(), session_id))

    # ----------------------------------------------------------- test cases
    def get_test_cases(self, session_id: int) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM test_cases WHERE session_id = ? ORDER BY position, id", (session_id,)
            ).fetchall()
        return [self._case_row(r) for r in rows]

    def get_test_case(self, case_id: int) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM test_cases WHERE id = ?", (case_id,)).fetchone()
        return self._case_row(row) if row else None

    @staticmethod
    def _case_row(row: sqlite3.Row) -> dict[str, Any]:
        d = dict(row)
        d["steps_list"] = text_to_steps(d["steps"])
        return d

    def add_test_case(self, session_id: int, case: dict[str, Any]) -> int:
        now = _now()
        with self.connect() as conn:
            if not conn.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone():
                raise ValueError(f"Session {session_id} does not exist.")
            codes = conn.execute("SELECT case_code FROM test_cases WHERE session_id = ?",
                                 (session_id,)).fetchall()
            nums = [int(c[0].split("-")[-1]) for c in codes if c[0].split("-")[-1].isdigit()]
            next_num = max(nums, default=0) + 1
            pos = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM test_cases WHERE session_id = ?",
                               (session_id,)).fetchone()[0]
            case = {**case, "source": case.get("source", "manual")}
            new_id = self._insert_case(conn, session_id, case, f"TC-{next_num:03d}", pos, now)
            self._touch(conn, session_id)
        return new_id

    def update_test_case(self, case_id: int, case: dict[str, Any]) -> bool:
        with self.connect() as conn:
            cur = conn.execute(
                "UPDATE test_cases SET scenario = ?, scenario_type = ?, steps = ?, test_data = ?, "
                "expected_result = ?, priority = ?, assumption = ?, updated_at = ? WHERE id = ?",
                (case["scenario"], case["scenario_type"], steps_to_text(case["steps"]),
                 case.get("test_data") or "N/A", case["expected_result"], case["priority"],
                 case.get("assumption") or "", _now(), case_id),
            )
            if cur.rowcount:
                sid = conn.execute("SELECT session_id FROM test_cases WHERE id = ?", (case_id,)).fetchone()[0]
                self._touch(conn, sid)
        return cur.rowcount > 0

    def delete_test_case(self, case_id: int) -> bool:
        with self.connect() as conn:
            row = conn.execute("SELECT session_id FROM test_cases WHERE id = ?", (case_id,)).fetchone()
            if row is None:
                return False
            conn.execute("DELETE FROM test_cases WHERE id = ?", (case_id,))
            self._touch(conn, row[0])
        return True

    def delete_test_cases(self, case_ids: list[int]) -> int:
        if not case_ids:
            return 0
        deleted = 0
        for cid in case_ids:
            deleted += int(self.delete_test_case(int(cid)))
        return deleted

    # ------------------------------------------------------------ analytics
    def get_statistics(self) -> dict[str, Any]:
        with self.connect() as conn:
            sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            total = conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0]
            prio = {p: 0 for p in PRIORITIES}
            for r in conn.execute("SELECT priority, COUNT(*) FROM test_cases GROUP BY priority"):
                prio[r[0]] = r[1]
            stype = {s: 0 for s in SCENARIO_TYPES}
            for r in conn.execute("SELECT scenario_type, COUNT(*) FROM test_cases GROUP BY scenario_type"):
                stype[r[0]] = r[1]
            avg = conn.execute("SELECT AVG(generation_seconds) FROM session_metadata "
                               "WHERE generation_seconds > 0").fetchone()[0]
            assumptions = conn.execute("SELECT COUNT(*) FROM test_cases WHERE assumption <> ''").fetchone()[0]
            timeline = [dict(r) for r in conn.execute(
                "SELECT substr(s.created_at, 1, 10) AS day, COUNT(DISTINCT s.id) AS sessions, "
                "COUNT(t.id) AS cases FROM sessions s LEFT JOIN test_cases t ON t.session_id = s.id "
                "GROUP BY day ORDER BY day")]
        return {
            "sessions": sessions, "test_cases": total, "priority": prio, "scenario_type": stype,
            "avg_generation_seconds": round(avg or 0, 1), "assumption_cases": assumptions,
            "timeline": timeline,
        }

    def get_all_test_cases(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT t.*, s.title AS session_title FROM test_cases t "
                "JOIN sessions s ON s.id = t.session_id ORDER BY s.created_at DESC, t.position"
            ).fetchall()
        return [self._case_row(r) for r in rows]
