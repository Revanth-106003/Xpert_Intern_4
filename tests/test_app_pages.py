"""Headless UI tests: every page renders without exceptions (Streamlit AppTest)."""
import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from database import Database
from tests.conftest import REGISTRATION_CASES

ROOT = Path(__file__).resolve().parents[1]
PAGES = ["dashboard", "generate", "results", "history", "export", "status"]


@pytest.fixture
def seeded_db(tmp_path, monkeypatch):
    path = tmp_path / "ui.db"
    monkeypatch.setenv("DATABASE_PATH", str(path))
    db = Database(path)
    sid = db.create_session(title="Registration", requirement="Users register with email and password.",
                            scenario_types=["Positive", "Negative", "Edge Case"], test_cases=REGISTRATION_CASES,
                            metadata={"provider": "ollama", "model": "qwen2.5:7b", "analysis": {
                                "title": "Registration", "summary": "s", "main_functionality": "m",
                                "validation_rules": ["Email unique"], "clarity": "clear"}})
    return sid


def test_app_shell_renders(seeded_db):
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not at.exception


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(seeded_db, page):
    at = AppTest.from_file(str(ROOT / "views" / f"{page}.py"), default_timeout=60)
    at.session_state["current_session_id"] = seeded_db
    at.run()
    assert not at.exception, [e.value for e in at.exception]


def test_results_page_shows_all_cases(seeded_db):
    at = AppTest.from_file(str(ROOT / "views" / "results.py"), default_timeout=60)
    at.session_state["current_session_id"] = seeded_db
    at.run()
    html = " ".join(m.value for m in at.markdown)
    for c in REGISTRATION_CASES:
        assert c["scenario"] in html


def test_generate_page_empty_requirement_shows_error(seeded_db):
    at = AppTest.from_file(str(ROOT / "views" / "generate.py"), default_timeout=60).run()
    at.button(key="generate_btn").click().run()
    assert not at.exception
    assert "The requirement is empty" in " ".join(m.value for m in at.markdown)


def test_example_button_fills_requirement(seeded_db):
    at = AppTest.from_file(str(ROOT / "views" / "generate.py"), default_timeout=60).run()
    at.button(key="ex_Login with lockout").click().run()
    assert "locked for 15 minutes" in at.text_area(key="req_text").value
    at.button(key="clear_btn").click().run()
    assert at.text_area(key="req_text").value == ""
