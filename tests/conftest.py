"""Shared pytest fixtures.

LLM calls are replaced by LangChain's ``FakeListChatModel`` so tests are fast,
deterministic and offline. The real providers are exercised separately by
``tests/test_live_llm.py`` (opt-in).
"""
from __future__ import annotations

import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent import LLMClient  # noqa: E402
from config import load_settings  # noqa: E402
from database import Database  # noqa: E402
from test_case_generator import TestCaseGeneratorService  # noqa: E402


# --------------------------------------------------------------- payloads
def analysis_payload(**overrides) -> str:
    data = {
        "title": "User Registration",
        "summary": "New users register with name, email and password.",
        "main_functionality": "Account creation with input validation",
        "actors": ["Visitor"],
        "inputs": ["Full name", "Email", "Password", "Confirm password"],
        "validation_rules": ["Email must be unique", "Password must be at least 8 characters"],
        "missing_information": ["Maximum name length is not specified"],
        "assumptions": ["Assumption: name accepts up to 50 characters"],
        "applicable_scenarios": ["Positive", "Negative", "Edge Case"],
        "clarity": "partially_clear",
        "clarification_questions": [],
    }
    data.update(overrides)
    return json.dumps(data)


def case(scenario, stype="Positive", priority="High", **kw) -> dict:
    return {
        "scenario": scenario,
        "scenario_type": stype,
        "steps": kw.get("steps", ["Open the registration page", "Fill in the form", "Click Register"]),
        "test_data": kw.get("test_data", "Email: priya@example.com, Password: Secure@123"),
        "expected_result": kw.get("expected_result", "Account is created and a verification email is sent"),
        "priority": priority,
        "assumption": kw.get("assumption", ""),
    }


def cases_payload(*cases) -> str:
    return json.dumps({"test_cases": list(cases)})


REGISTRATION_CASES = [
    case("Register with all valid details"),
    case("Registration rejected for an already registered email", "Negative", "High",
         test_data="Email: existing@example.com"),
    case("Registration rejected when password has 7 characters", "Negative", "Medium",
         test_data="Password: Abc@123"),
    case("Registration succeeds with password of exactly 8 characters", "Edge Case", "Medium",
         test_data="Password: Abcd@123"),
    case("Name with 50 characters is accepted", "Edge Case", "Low",
         assumption="Assumption: name accepts up to 50 characters"),
]


# --------------------------------------------------------------- fixtures
@pytest.fixture
def settings(tmp_path):
    return replace(load_settings(), database_path=tmp_path / "test.db", max_repair_attempts=1,
                   llm_provider="ollama")


@pytest.fixture
def db(settings):
    return Database(settings.database_path)


def fake_client(settings, responses: list[str]) -> LLMClient:
    return LLMClient(settings, chat_model=FakeListChatModel(responses=responses))


@pytest.fixture
def make_service(settings, db):
    def _make(responses: list[str]) -> TestCaseGeneratorService:
        return TestCaseGeneratorService(settings, db, client_factory=lambda s: fake_client(s, responses))
    return _make
