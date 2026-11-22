"""Agent workflow with mocked LLM responses, plus provider error handling."""
import json
from dataclasses import replace

import pytest
import requests

from agent import LLMClient, TestCaseAgent, classify_exception, message_text
from errors import (AuthenticationError, ConfigurationError, InvalidLLMResponseError, LLMProviderError,
                    LLMTimeoutError, ModelNotFoundError, ProviderUnavailableError, RateLimitError,
                    RequirementValidationError)
from tests.conftest import REGISTRATION_CASES, analysis_payload, case, cases_payload, fake_client

REGISTRATION = ("New users register with full name, email and password. The email must be unique. "
                "The password must be at least 8 characters long.")
LOGIN = ("Registered users log in with email and password. After 3 failed attempts the account "
         "is locked for 15 minutes.")


def run(settings, responses, requirement=REGISTRATION, types=("Positive", "Negative", "Edge Case"), **kw):
    agent = TestCaseAgent(fake_client(settings, responses), settings)
    stages = []
    result = agent.run(requirement, list(types), progress=lambda s, m: stages.append(s), **kw)
    return result, stages


# 2. Valid registration requirement --------------------------------------------
def test_registration_requirement_generates_structured_cases(settings):
    result, stages = run(settings, [analysis_payload(), cases_payload(*REGISTRATION_CASES)])
    assert result.status == "completed"
    assert len(result.test_cases) == 5
    assert {c.scenario_type for c in result.test_cases} == {"Positive", "Negative", "Edge Case"}
    for c in result.test_cases:
        assert c.steps and c.expected_result and c.priority in ("High", "Medium", "Low")
    assert result.analysis.validation_rules
    assert stages[:3] == ["validate", "connect", "analyse"] and stages[-1] == "done"
    # assumptions are preserved and explicit
    assert any(c.assumption.startswith("Assumption:") for c in result.test_cases)


# 3. Login requirement -----------------------------------------------------------
def test_login_requirement(settings):
    cases = [case("Login succeeds with valid credentials"),
             case("Account locks after 3 failed attempts", "Negative", test_data="3 wrong passwords"),
             case("Account not locked after 2 failed attempts", "Edge Case", "Medium")]
    result, _ = run(settings, [analysis_payload(title="User Login"), cases_payload(*cases)], LOGIN)
    assert result.analysis.title == "User Login"
    assert [c.scenario_type for c in result.test_cases] == ["Positive", "Negative", "Edge Case"]


# 4/5. Scenario selection: only negative / only edge cases ------------------------
@pytest.mark.parametrize("selected", [("Negative",), ("Edge Case",)])
def test_unselected_scenario_types_are_filtered(settings, selected):
    result, _ = run(settings, [analysis_payload(), cases_payload(*REGISTRATION_CASES)], types=selected)
    assert result.test_cases and all(c.scenario_type == selected[0] for c in result.test_cases)
    assert any("unselected scenario type" in w for w in result.warnings)


def test_missing_selected_type_is_reported(settings):
    only_positive = [case("Register with all valid details")]
    result, _ = run(settings, [analysis_payload(), cases_payload(*only_positive)])
    assert any("No 'Negative'" in w for w in result.warnings)
    assert any("No 'Edge Case'" in w for w in result.warnings)


def test_no_case_for_selected_type_raises(settings):
    with pytest.raises(InvalidLLMResponseError):
        run(settings, [analysis_payload(), cases_payload(case("Only positive"))], types=("Negative",))


# 6. Unclear requirement -------------------------------------------------------------
def test_unclear_requirement_asks_for_clarification(settings):
    unclear = analysis_payload(clarity="unclear", clarification_questions=["Which feature?", "What is 'better'?"])
    result, stages = run(settings, [unclear], "Make the system work better for all users.")
    assert result.status == "needs_clarification"
    assert result.test_cases == []
    assert len(result.analysis.clarification_questions) == 2
    assert "generate" not in stages


def test_unclear_requirement_can_proceed_with_assumptions(settings):
    unclear = analysis_payload(clarity="unclear", clarification_questions=["Which feature?"])
    result, _ = run(settings, [unclear, cases_payload(*REGISTRATION_CASES)],
                    "Make the system work better for all users.", proceed_with_assumptions=True)
    assert result.status == "completed" and result.test_cases


# 7. Invalid LLM response + self-repair ---------------------------------------------
def test_invalid_json_is_repaired(settings):
    result, stages = run(settings, ["this is not json", analysis_payload(), cases_payload(*REGISTRATION_CASES)])
    assert result.status == "completed"
    assert result.repair_attempts == 1 and "repair" in stages


def test_invalid_json_after_repair_raises(settings):
    with pytest.raises(InvalidLLMResponseError):
        run(settings, ["garbage", "still garbage"])


def test_missing_fields_in_all_cases_raises(settings):
    broken = json.dumps({"test_cases": [{"scenario": "x"}, {"priority": "High"}]})
    with pytest.raises(InvalidLLMResponseError):
        run(settings, [analysis_payload(), broken, broken])


def test_duplicates_are_removed_by_agent(settings):
    dupes = REGISTRATION_CASES + [case("Register with all valid details.")]
    result, _ = run(settings, [analysis_payload(), cases_payload(*dupes)])
    assert result.duplicates_removed == 1 and len(result.test_cases) == 5


def test_empty_requirement_never_calls_llm(settings):
    with pytest.raises(RequirementValidationError):
        run(settings, [], "   ")


# Provider error handling ------------------------------------------------------------
def test_ollama_not_running(settings):
    s = replace(settings, llm_provider="ollama", ollama_base_url="http://127.0.0.1:9")
    with pytest.raises(ProviderUnavailableError) as exc:
        LLMClient(s).check_ready()
    assert "ollama pull" in exc.value.hint


def test_ollama_model_not_installed(settings, monkeypatch):
    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"models": [{"name": "llama3.2:3b"}]}
    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
    s = replace(settings, llm_provider="ollama", ollama_model="qwen2.5:7b")
    with pytest.raises(ModelNotFoundError) as exc:
        LLMClient(s).check_ready()
    assert "ollama pull qwen2.5:7b" in exc.value.hint


def test_ollama_model_installed_passes(settings, monkeypatch):
    class Resp:
        def raise_for_status(self): pass
        def json(self): return {"models": [{"name": "qwen2.5:7b"}]}
    monkeypatch.setattr(requests, "get", lambda *a, **k: Resp())
    LLMClient(replace(settings, llm_provider="ollama", ollama_model="qwen2.5:7b")).check_ready()


def test_gemini_without_key(settings):
    s = replace(settings, llm_provider="gemini", gemini_api_key="")
    with pytest.raises(ConfigurationError):
        LLMClient(s).check_ready()


def test_unknown_provider(settings):
    with pytest.raises(ConfigurationError):
        LLMClient(replace(settings, llm_provider="openai")).check_ready()


@pytest.mark.parametrize("exc,expected", [
    (TimeoutError("Request timed out"), LLMTimeoutError),
    (Exception("400 API key not valid. Please pass a valid API key. [reason: API_KEY_INVALID]"), AuthenticationError),
    (Exception("404 models/foo is not found for API version v1beta"), ModelNotFoundError),
    (Exception("503 This model is currently experiencing high demand"), RateLimitError),
    (Exception("429 RESOURCE_EXHAUSTED quota"), RateLimitError),
    (ConnectionError("[WinError 10061] No connection could be made because the target machine actively refused it"),
     ProviderUnavailableError),
    (ValueError("something odd"), LLMProviderError),
])
def test_exception_classification(exc, expected):
    assert isinstance(classify_exception(exc, "gemini", "gemini-x"), expected)


@pytest.mark.parametrize("raised,expected", [
    (TimeoutError("Request timed out"), LLMTimeoutError),
    (Exception("API key not valid"), AuthenticationError),
])
def test_llm_failure_inside_chain_is_typed_and_does_not_crash(settings, raised, expected):
    from langchain_core.runnables import RunnableLambda

    def boom(_):
        raise raised

    agent = TestCaseAgent(LLMClient(settings, chat_model=RunnableLambda(boom)), settings)
    with pytest.raises(expected):
        agent.run(REGISTRATION, ["Positive"])


def test_message_text_handles_content_blocks():
    class Msg:
        content = [{"type": "text", "text": '{"a":'}, {"type": "text", "text": " 1}"}, {"type": "thinking"}]
    assert message_text(Msg()) == '{"a": 1}'
