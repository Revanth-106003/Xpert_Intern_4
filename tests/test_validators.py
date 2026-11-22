"""Input validation, JSON extraction, schema validation and duplicate detection."""
import pytest

from errors import InvalidLLMResponseError, RequirementValidationError, TestCaseValidationError
from validators import (
    MAX_REQUIREMENT_CHARS, TestCaseModel, deduplicate, extract_json, normalize_priority,
    normalize_scenario_type, parse_analysis, parse_test_cases, validate_manual_test_case,
    validate_requirement, validate_scenario_selection,
)
from tests.conftest import case


# 1. Empty requirement ---------------------------------------------------------
@pytest.mark.parametrize("text", ["", "   ", "\n\t", None])
def test_empty_requirement_rejected(text):
    with pytest.raises(RequirementValidationError, match="empty"):
        validate_requirement(text)


@pytest.mark.parametrize("text", ["login", "make it work", "a b c"])
def test_too_short_requirement_rejected(text):
    with pytest.raises(RequirementValidationError, match="too short"):
        validate_requirement(text)


def test_symbol_only_requirement_rejected():
    with pytest.raises(RequirementValidationError):
        validate_requirement("123 456 789 000 111 222")


def test_too_long_requirement_rejected():
    with pytest.raises(RequirementValidationError, match="too long"):
        validate_requirement("word " * (MAX_REQUIREMENT_CHARS // 4))


def test_valid_requirement_is_normalised():
    assert validate_requirement("  Users   can log in with email and password.  ") == \
        "Users can log in with email and password."


def test_scenario_selection():
    assert validate_scenario_selection(["edge case", "Positive"]) == ["Positive", "Edge Case"]
    with pytest.raises(RequirementValidationError):
        validate_scenario_selection([])


# Label normalisation ------------------------------------------------------------
@pytest.mark.parametrize("raw,expected", [("high", "High"), ("CRITICAL", "High"), ("p2", "Medium"),
                                          ("Low", "Low"), ("minor", "Low")])
def test_priority_normalisation(raw, expected):
    assert normalize_priority(raw) == expected


def test_invalid_priority_rejected():
    with pytest.raises(ValueError):
        normalize_priority("urgent-ish")


@pytest.mark.parametrize("raw,expected", [("positive", "Positive"), ("Negative Scenario", "Negative"),
                                          ("boundary", "Edge Case"), ("edge_case", "Edge Case")])
def test_scenario_normalisation(raw, expected):
    assert normalize_scenario_type(raw) == expected


# 7. Invalid LLM responses -------------------------------------------------------
def test_extract_json_handles_code_fences_and_prose():
    assert extract_json('Sure! ```json\n{"a": 1}\n``` hope this helps') == {"a": 1}
    assert extract_json('Here you go: {"test_cases": []} done') == {"test_cases": []}


@pytest.mark.parametrize("bad", ["", "not json at all", "{'single': quotes", None])
def test_extract_json_rejects_invalid(bad):
    with pytest.raises(InvalidLLMResponseError):
        extract_json(bad)


def test_parse_test_cases_requires_list():
    with pytest.raises(InvalidLLMResponseError):
        parse_test_cases({"cases": "nope"})
    with pytest.raises(InvalidLLMResponseError, match="zero"):
        parse_test_cases({"test_cases": []})


def test_missing_fields_are_skipped_with_warning():
    good = case("Valid login")
    missing = {"scenario": "No expected result", "scenario_type": "Positive", "priority": "High", "steps": ["x"]}
    bad_prio = case("Bad priority", priority="Urgent")
    valid, warnings = parse_test_cases({"test_cases": [good, missing, bad_prio, "junk"]})
    assert [c.scenario for c in valid] == ["Valid login"]
    assert len(warnings) == 3


def test_all_invalid_cases_raise():
    with pytest.raises(InvalidLLMResponseError, match="None of the generated"):
        parse_test_cases({"test_cases": [{"scenario": "x"}]})


def test_alias_keys_and_string_steps_are_coerced():
    raw = {"test_scenario": "Login works", "type": "positive", "test_steps": "1. Open page\n2. Click login",
           "data": {"email": "a@b.com"}, "expected": "Dashboard shown", "priority": "p1"}
    valid, _ = parse_test_cases([raw])
    tc = valid[0]
    assert tc.steps == ["Open page", "Click login"]
    assert tc.priority == "High" and tc.scenario_type == "Positive"
    assert "a@b.com" in tc.test_data


def test_parse_analysis_validates_and_normalises():
    a = parse_analysis({"title": "Login", "summary": "s", "main_functionality": "m",
                        "applicable_scenarios": ["positive", "boundary", "nonsense"], "clarity": "vague"})
    assert a.applicable_scenarios == ["Positive", "Edge Case"]
    assert a.needs_clarification
    with pytest.raises(InvalidLLMResponseError):
        parse_analysis({"summary": "no title"})


# Duplicates -----------------------------------------------------------------------
def test_duplicates_removed():
    a = TestCaseModel.model_validate(case("Login with valid credentials"))
    b = TestCaseModel.model_validate(case("Login with valid credentials!"))
    c = TestCaseModel.model_validate(case("Login fails with wrong password", "Negative",
                                          test_data="Password: wrong"))
    unique, removed = deduplicate([a, b, c])
    assert removed == 1 and len(unique) == 2


def test_manual_case_validation():
    with pytest.raises(TestCaseValidationError) as exc:
        validate_manual_test_case({"scenario": "Valid", "scenario_type": "Positive", "priority": "High",
                                   "steps": [], "expected_result": ""})
    assert "Test steps" in exc.value.hint and "Expected result" in exc.value.hint
