"""Input validation and structured-output validation for LLM responses.

The LLM is asked for JSON, but its output is never trusted blindly. This module:
  * validates the user's requirement text before any LLM call,
  * extracts JSON from raw model text (tolerating code fences / prose),
  * validates every object against Pydantic schemas,
  * normalises priority / scenario-type labels to the allowed vocabulary,
  * removes duplicate test cases.
"""
from __future__ import annotations

import json
import re
from difflib import SequenceMatcher
from typing import Any

from pydantic import BaseModel, Field, ValidationError, field_validator

from config import PRIORITIES, SCENARIO_TYPES
from errors import InvalidLLMResponseError, RequirementValidationError, TestCaseValidationError

MIN_REQUIREMENT_CHARS = 15
MIN_REQUIREMENT_WORDS = 4
MAX_REQUIREMENT_CHARS = 8000
DUPLICATE_SIMILARITY = 0.90

_PRIORITY_ALIASES = {
    "high": "High", "critical": "High", "highest": "High", "p1": "High", "p0": "High", "blocker": "High",
    "medium": "Medium", "moderate": "Medium", "normal": "Medium", "p2": "Medium", "med": "Medium",
    "low": "Low", "minor": "Low", "lowest": "Low", "p3": "Low", "trivial": "Low",
}

_SCENARIO_ALIASES = {
    "positive": "Positive", "happy path": "Positive", "valid": "Positive", "functional": "Positive",
    "negative": "Negative", "invalid": "Negative", "error": "Negative",
    "edge": "Edge Case", "edge case": "Edge Case", "edge-case": "Edge Case", "edgecase": "Edge Case",
    "boundary": "Edge Case", "boundary value": "Edge Case", "corner case": "Edge Case", "edge cases": "Edge Case",
}


# --------------------------------------------------------------------------- #
# Requirement input validation
# --------------------------------------------------------------------------- #
def validate_requirement(text: str | None) -> str:
    """Return a cleaned requirement or raise :class:`RequirementValidationError`."""
    cleaned = re.sub(r"[ \t]+", " ", (text or "")).strip()
    if not cleaned:
        raise RequirementValidationError(
            "The requirement is empty.",
            "Describe the feature in plain English, e.g. 'Users can log in with email and password'.",
        )
    if len(cleaned) > MAX_REQUIREMENT_CHARS:
        raise RequirementValidationError(
            f"The requirement is too long ({len(cleaned)} characters).",
            f"Keep it under {MAX_REQUIREMENT_CHARS} characters or split it into smaller requirements.",
        )
    words = re.findall(r"[A-Za-z0-9]+", cleaned)
    if len(cleaned) < MIN_REQUIREMENT_CHARS or len(words) < MIN_REQUIREMENT_WORDS:
        raise RequirementValidationError(
            "The requirement is too short to analyse.",
            "Write at least one complete sentence describing who does what and any rules that apply.",
        )
    if not re.search(r"[A-Za-z]{2,}", cleaned):
        raise RequirementValidationError(
            "The requirement does not contain readable text.",
            "Describe the functionality using words, not only numbers or symbols.",
        )
    return cleaned


def validate_scenario_selection(selected: list[str] | None) -> list[str]:
    chosen = [normalize_scenario_type(s) for s in (selected or [])]
    chosen = [s for s in SCENARIO_TYPES if s in chosen]  # stable canonical order, unique
    if not chosen:
        raise RequirementValidationError(
            "No scenario type selected.",
            "Select at least one of Positive, Negative or Edge Case.",
        )
    return chosen


# --------------------------------------------------------------------------- #
# Label normalisation
# --------------------------------------------------------------------------- #
def normalize_priority(value: Any) -> str:
    key = str(value or "").strip().lower()
    if key in _PRIORITY_ALIASES:
        return _PRIORITY_ALIASES[key]
    raise ValueError(f"Priority must be High, Medium or Low (got '{value}').")


def normalize_scenario_type(value: Any) -> str:
    key = re.sub(r"\s+", " ", str(value or "").strip().lower().replace("_", " "))
    key = key.removesuffix(" scenario").removesuffix(" test")
    if key in _SCENARIO_ALIASES:
        return _SCENARIO_ALIASES[key]
    raise ValueError(f"Scenario type must be Positive, Negative or Edge Case (got '{value}').")


def _coerce_text(value: Any) -> str:
    """Turn strings, lists or dicts returned by the LLM into clean display text."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        return "; ".join(f"{k}: {_coerce_text(v)}" for k, v in value.items()).strip()
    if isinstance(value, (list, tuple)):
        return "; ".join(_coerce_text(v) for v in value if _coerce_text(v)).strip()
    return str(value).strip()


_STEP_PREFIX = re.compile(r"^\s*(?:step\s*)?\d+\s*[.):-]\s*", re.IGNORECASE)


def _coerce_steps(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p for p in re.split(r"\r?\n", value) if p.strip()]
        if len(parts) == 1:  # "1. a 2. b" on one line
            parts = [p for p in re.split(r"\s(?=\d+[.)]\s)", value) if p.strip()]
    elif isinstance(value, (list, tuple)):
        parts = [_coerce_text(v) for v in value]
    else:
        parts = [str(value)]
    return [_STEP_PREFIX.sub("", p).strip() for p in parts if _STEP_PREFIX.sub("", p).strip()]


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class RequirementAnalysis(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    summary: str = Field(min_length=1)
    main_functionality: str = Field(min_length=1)
    actors: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    validation_rules: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    applicable_scenarios: list[str] = Field(default_factory=list)
    clarity: str = "clear"
    clarification_questions: list[str] = Field(default_factory=list)

    @field_validator("title", "summary", "main_functionality", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str:
        return _coerce_text(v)

    @field_validator(
        "actors", "inputs", "validation_rules", "missing_information",
        "assumptions", "clarification_questions", mode="before",
    )
    @classmethod
    def _list(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, str):
            v = [v]
        return [t for t in (_coerce_text(i) for i in v) if t]

    @field_validator("applicable_scenarios", mode="before")
    @classmethod
    def _scenarios(cls, v: Any) -> list[str]:
        out: list[str] = []
        for item in (v or []):
            try:
                norm = normalize_scenario_type(item)
            except ValueError:
                continue
            if norm not in out:
                out.append(norm)
        return out

    @field_validator("clarity", mode="before")
    @classmethod
    def _clarity(cls, v: Any) -> str:
        key = str(v or "clear").strip().lower().replace(" ", "_").replace("-", "_")
        if key in {"clear", "partially_clear", "unclear"}:
            return key
        if key in {"partial", "partly_clear", "somewhat_clear", "ambiguous"}:
            return "partially_clear"
        if key in {"vague", "insufficient", "not_clear"}:
            return "unclear"
        return "partially_clear"

    @property
    def needs_clarification(self) -> bool:
        return self.clarity == "unclear"


class TestCaseModel(BaseModel):
    __test__ = False  # not a pytest test class

    scenario: str = Field(min_length=3, max_length=500)
    scenario_type: str
    steps: list[str] = Field(min_length=1)
    test_data: str = ""
    expected_result: str = Field(min_length=3)
    priority: str
    assumption: str = ""

    @field_validator("scenario", "expected_result", "test_data", "assumption", mode="before")
    @classmethod
    def _text(cls, v: Any) -> str:
        return _coerce_text(v)

    @field_validator("steps", mode="before")
    @classmethod
    def _steps(cls, v: Any) -> list[str]:
        return _coerce_steps(v)

    @field_validator("priority", mode="before")
    @classmethod
    def _priority(cls, v: Any) -> str:
        return normalize_priority(v)

    @field_validator("scenario_type", mode="before")
    @classmethod
    def _stype(cls, v: Any) -> str:
        return normalize_scenario_type(v)

    @field_validator("test_data")
    @classmethod
    def _data_default(cls, v: str) -> str:
        return v or "N/A"


# --------------------------------------------------------------------------- #
# JSON extraction
# --------------------------------------------------------------------------- #
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    """Parse JSON from a model response that may contain fences or prose."""
    if text is None or not str(text).strip():
        raise InvalidLLMResponseError("The model returned an empty response.")
    raw = str(text).strip()
    candidates = [raw]
    candidates += [m.strip() for m in _FENCE.findall(raw)]
    for open_ch, close_ch in (("{", "}"), ("[", "]")):
        start, end = raw.find(open_ch), raw.rfind(close_ch)
        if start != -1 and end > start:
            candidates.append(raw[start:end + 1])
    for cand in candidates:
        try:
            return json.loads(cand)
        except (json.JSONDecodeError, TypeError):
            continue
    snippet = raw[:160].replace("\n", " ")
    raise InvalidLLMResponseError(
        "The model response was not valid JSON.",
        f"Response started with: {snippet!r}",
    )


def parse_analysis(payload: Any) -> RequirementAnalysis:
    if isinstance(payload, dict) and isinstance(payload.get("analysis"), dict):
        payload = payload["analysis"]
    if not isinstance(payload, dict):
        raise InvalidLLMResponseError("Requirement analysis must be a JSON object.")
    try:
        return RequirementAnalysis.model_validate(payload)
    except ValidationError as exc:
        raise InvalidLLMResponseError(
            "Requirement analysis is missing required fields.", _summarise_errors(exc)
        ) from exc


def parse_test_cases(payload: Any) -> tuple[list[TestCaseModel], list[str]]:
    """Validate raw test-case objects.

    Returns the valid cases and a list of human-readable warnings for rejected
    items. Raises if *no* valid case can be recovered.
    """
    items = payload
    if isinstance(payload, dict):
        items = payload.get("test_cases", payload.get("testCases", payload.get("tests")))
    if not isinstance(items, list):
        raise InvalidLLMResponseError("Response did not contain a 'test_cases' list.")
    if not items:
        raise InvalidLLMResponseError("The model returned zero test cases.")

    valid: list[TestCaseModel] = []
    warnings: list[str] = []
    for idx, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            warnings.append(f"Item {idx} skipped: not a JSON object.")
            continue
        item = {_canonical_key(k): v for k, v in item.items()}
        try:
            valid.append(TestCaseModel.model_validate(item))
        except ValidationError as exc:
            warnings.append(f"Item {idx} skipped: {_summarise_errors(exc)}")
    if not valid:
        raise InvalidLLMResponseError(
            "None of the generated test cases passed validation.", " | ".join(warnings[:3])
        )
    return valid, warnings


_KEY_ALIASES = {
    "test_scenario": "scenario", "title": "scenario", "description": "scenario", "name": "scenario",
    "type": "scenario_type", "scenariotype": "scenario_type", "category": "scenario_type",
    "test_steps": "steps", "teststeps": "steps",
    "testdata": "test_data", "data": "test_data", "input_data": "test_data",
    "expected": "expected_result", "expectedresult": "expected_result", "expected_results": "expected_result",
    "assumptions": "assumption", "notes": "assumption",
}


def _canonical_key(key: str) -> str:
    k = re.sub(r"[\s\-]+", "_", str(key).strip().lower())
    return _KEY_ALIASES.get(k, _KEY_ALIASES.get(k.replace("_", ""), k))


_FIELD_LABELS = {
    "scenario": "Test scenario", "scenario_type": "Scenario type", "steps": "Test steps",
    "test_data": "Test data", "expected_result": "Expected result", "priority": "Priority",
    "assumption": "Assumption", "title": "Title", "summary": "Summary", "main_functionality": "Main functionality",
}


def _summarise_errors(exc: ValidationError) -> str:
    parts = []
    for err in exc.errors()[:4]:
        loc = err.get("loc", ())
        field = _FIELD_LABELS.get(str(loc[0]), ".".join(str(p) for p in loc)) if loc else "object"
        msg = str(err.get("msg", "invalid")).removeprefix("Value error, ")
        msg = msg.replace("String should have at least 3 characters", "must contain at least 3 characters")
        msg = msg.replace("List should have at least 1 item after validation, not 0", "needs at least one step")
        msg = msg.replace("Field required", "is required")
        parts.append(f"{field} {msg}" if not msg[0].isupper() else f"{field}: {msg}")
    return "; ".join(parts)


# --------------------------------------------------------------------------- #
# Duplicate removal
# --------------------------------------------------------------------------- #
def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]+", "", text.lower()).strip()


def is_duplicate(a: TestCaseModel, b: TestCaseModel) -> bool:
    sa, sb = _norm(a.scenario), _norm(b.scenario)
    if sa == sb:
        return True
    body_a = sa + " " + _norm(" ".join(a.steps)) + " " + _norm(a.test_data)
    body_b = sb + " " + _norm(" ".join(b.steps)) + " " + _norm(b.test_data)
    return (
        SequenceMatcher(None, sa, sb).ratio() >= DUPLICATE_SIMILARITY
        and SequenceMatcher(None, body_a, body_b).ratio() >= DUPLICATE_SIMILARITY
    )


def deduplicate(cases: list[TestCaseModel]) -> tuple[list[TestCaseModel], int]:
    unique: list[TestCaseModel] = []
    for case in cases:
        if not any(is_duplicate(case, kept) for kept in unique):
            unique.append(case)
    return unique, len(cases) - len(unique)


def validate_manual_test_case(data: dict[str, Any]) -> TestCaseModel:
    """Validate a test case entered or edited by the user in the UI."""
    try:
        return TestCaseModel.model_validate(data)
    except ValidationError as exc:
        raise TestCaseValidationError("Please complete the required fields.", _summarise_errors(exc)) from exc
