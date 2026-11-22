"""Opt-in integration test against the REAL configured LLM provider.

Skipped by default. Run with:   RUN_LIVE_LLM=1 pytest tests/test_live_llm.py -s
(Windows PowerShell:  $env:RUN_LIVE_LLM=1; pytest tests/test_live_llm.py -s)
"""
import os
from dataclasses import replace

import pytest

from agent import LLMClient, TestCaseAgent
from config import load_settings

pytestmark = pytest.mark.skipif(os.getenv("RUN_LIVE_LLM") != "1", reason="set RUN_LIVE_LLM=1 to call the real LLM")


def test_live_generation_for_registration(tmp_path):
    settings = replace(load_settings(), database_path=tmp_path / "live.db")
    agent = TestCaseAgent(LLMClient(settings), settings)
    result = agent.run(
        "New users register with email and password. The email must be unique. "
        "The password must be at least 8 characters and contain a number.",
        ["Positive", "Negative", "Edge Case"],
    )
    assert result.status == "completed"
    assert len(result.test_cases) >= 4
    assert {c.scenario_type for c in result.test_cases} >= {"Positive", "Negative"}
    text = " ".join(c.scenario.lower() + c.test_data.lower() for c in result.test_cases)
    assert "password" in text and "email" in text  # grounded in the requirement


def test_live_vague_requirement_requests_clarification(tmp_path):
    settings = replace(load_settings(), database_path=tmp_path / "live.db")
    result = TestCaseAgent(LLMClient(settings), settings).run("Make everything better and faster.", ["Positive"])
    assert result.status == "needs_clarification"
    assert result.analysis.clarification_questions
