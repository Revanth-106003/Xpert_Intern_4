"""SQLite CRUD, relationships, statistics and persistence across restarts."""
import sqlite3

import pytest

from database import Database
from tests.conftest import REGISTRATION_CASES


def _create(db, title="Registration", cases=REGISTRATION_CASES):
    return db.create_session(title=title, requirement="Users register with email and password.",
                             scenario_types=["Positive", "Negative", "Edge Case"], test_cases=cases,
                             metadata={"provider": "ollama", "model": "qwen2.5:7b", "generation_seconds": 3.2,
                                       "analysis": {"title": title}, "warnings": ["note"]})


# 12. Database operations --------------------------------------------------------
def test_schema_created(db):
    with db.connect() as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sessions", "session_metadata", "test_cases"} <= tables


def test_insert_and_read_session(db):
    sid = _create(db)
    s = db.get_session(sid)
    assert s["title"] == "Registration" and s["case_count"] == 5
    assert [c["case_code"] for c in s["test_cases"]] == ["TC-001", "TC-002", "TC-003", "TC-004", "TC-005"]
    assert s["analysis"] == {"title": "Registration"} and s["warnings"] == ["note"]
    assert s["test_cases"][0]["steps_list"] == REGISTRATION_CASES[0]["steps"]
    listed = db.list_sessions()
    assert listed[0]["high_count"] == 2 and listed[0]["case_count"] == 5


# 8. Editing ---------------------------------------------------------------------------
def test_update_test_case(db):
    sid = _create(db)
    tc = db.get_session(sid)["test_cases"][0]
    updated = {**REGISTRATION_CASES[0], "scenario": "Edited scenario", "priority": "Low",
               "steps": ["Step A", "Step B"]}
    assert db.update_test_case(tc["id"], updated)
    again = db.get_test_case(tc["id"])
    assert again["scenario"] == "Edited scenario" and again["priority"] == "Low"
    assert again["steps_list"] == ["Step A", "Step B"]


def test_constraints_reject_invalid_priority(db):
    sid = _create(db)
    tc = db.get_session(sid)["test_cases"][0]
    with pytest.raises(sqlite3.IntegrityError):
        db.update_test_case(tc["id"], {**REGISTRATION_CASES[0], "priority": "Urgent"})


# 9. Deleting ----------------------------------------------------------------------------
def test_delete_test_case(db):
    sid = _create(db)
    ids = [c["id"] for c in db.get_test_cases(sid)]
    assert db.delete_test_case(ids[0]) and not db.delete_test_case(ids[0])
    assert db.delete_test_cases(ids[1:3]) == 2
    assert len(db.get_test_cases(sid)) == 2


def test_add_case_continues_numbering_after_delete(db):
    sid = _create(db)
    last = db.get_test_cases(sid)[-1]
    db.delete_test_case(last["id"])
    new_id = db.add_test_case(sid, REGISTRATION_CASES[0])
    assert db.get_test_case(new_id)["case_code"] == "TC-005"
    assert db.get_test_case(new_id)["source"] == "manual"


def test_add_case_to_missing_session(db):
    with pytest.raises(ValueError):
        db.add_test_case(999, REGISTRATION_CASES[0])


def test_delete_session_cascades(db):
    sid = _create(db)
    assert db.delete_session(sid)
    assert db.get_session(sid) is None
    with db.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM test_cases").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM session_metadata").fetchone()[0] == 0


def test_search_is_parameterised(db):
    _create(db, "Login")
    _create(db, "Cart")
    assert [s["title"] for s in db.list_sessions("Cart")] == ["Cart"]
    assert db.list_sessions("' OR 1=1 --") == []  # injection string treated as plain text
    assert len(db.list_sessions()) == 2


def test_statistics(db):
    _create(db)
    _create(db, "Second")
    stats = db.get_statistics()
    assert stats["sessions"] == 2 and stats["test_cases"] == 10
    assert stats["priority"] == {"High": 4, "Medium": 4, "Low": 2}
    assert stats["scenario_type"] == {"Positive": 2, "Negative": 4, "Edge Case": 4}
    assert stats["assumption_cases"] == 2 and stats["timeline"][0]["cases"] == 10


# 13. Restart & persistence -----------------------------------------------------------
def test_data_persists_after_restart(settings):
    first = Database(settings.database_path)
    sid = _create(first)
    del first
    reopened = Database(settings.database_path)  # simulates application restart
    s = reopened.get_session(sid)
    assert s is not None and s["case_count"] == 5 and s["title"] == "Registration"
