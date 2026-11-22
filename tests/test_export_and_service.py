"""CSV export and the service layer (generation -> history -> edit -> export)."""
import io

import pandas as pd
import pytest

from database import Database
from errors import RequirementValidationError, TestCaseValidationError
from export_utils import (EXPORT_COLUMNS, cases_to_dataframe, dataframe_to_csv_bytes, export_filename,
                          filter_cases)
from test_case_generator import TestCaseGeneratorService
from tests.conftest import REGISTRATION_CASES, analysis_payload, cases_payload, fake_client

REQ = "New users register with email and password. The email must be unique and the password 8+ characters."


# 11. CSV export ------------------------------------------------------------------
def _read_csv(data: bytes) -> pd.DataFrame:
    assert data.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM for Excel
    return pd.read_csv(io.BytesIO(data), encoding="utf-8-sig", keep_default_na=False)


def test_csv_contains_all_fields(make_service):
    out = make_service([analysis_payload(), cases_payload(*REGISTRATION_CASES)]).generate(REQ, ["Positive", "Negative", "Edge Case"])
    cases = out and make_service([]).db.get_test_cases(out.session_id)
    df = _read_csv(dataframe_to_csv_bytes(cases_to_dataframe(cases)))
    assert list(df.columns) == EXPORT_COLUMNS
    assert len(df) == 5
    assert df.iloc[0]["Test Steps"].startswith("1. Open the registration page\n2. Fill in the form")
    assert set(df["Priority"]) <= {"High", "Medium", "Low"}


def test_csv_export_of_empty_dataset():
    df = cases_to_dataframe([])
    assert df.empty and list(df.columns) == EXPORT_COLUMNS
    parsed = _read_csv(dataframe_to_csv_bytes(df))
    assert parsed.empty and list(parsed.columns) == EXPORT_COLUMNS


def test_csv_with_session_column_and_special_characters(db):
    tricky = {**REGISTRATION_CASES[0], "test_data": 'Name: "Zoë, O\'Brien"; Emoji: ✅', "steps": ["a, b", "c\nd"]}
    sid = db.create_session(title="Special", requirement="r", scenario_types=["Positive"], test_cases=[tricky])
    rows = db.get_all_test_cases()
    df = _read_csv(dataframe_to_csv_bytes(cases_to_dataframe(rows, include_session=True)))
    assert df.iloc[0]["Session"] == "Special"
    assert df.iloc[0]["Test Data"] == 'Name: "Zoë, O\'Brien"; Emoji: ✅'
    assert sid


def test_filtered_export():
    rows = [{"case_code": "TC-001", "scenario": "Login ok", "priority": "High", "scenario_type": "Positive",
             "steps": "x", "test_data": "", "expected_result": "", "assumption": ""},
            {"case_code": "TC-002", "scenario": "Cart total", "priority": "Low", "scenario_type": "Edge Case",
             "steps": "y", "test_data": "", "expected_result": "", "assumption": ""}]
    assert [r["case_code"] for r in filter_cases(rows, priorities=["High"])] == ["TC-001"]
    assert [r["case_code"] for r in filter_cases(rows, scenario_types=["Edge Case"])] == ["TC-002"]
    assert [r["case_code"] for r in filter_cases(rows, search="cart")] == ["TC-002"]
    assert filter_cases(rows, priorities=["Medium"]) == []


def test_export_filename_is_safe():
    name = export_filename("Login / Lockout: v2?")
    assert name.startswith("login_lockout_v2_") and name.endswith(".csv")


# 10. Saving & retrieving history via the service ------------------------------------------
def test_generation_is_saved_to_history(make_service):
    svc = make_service([analysis_payload(), cases_payload(*REGISTRATION_CASES)])
    out = svc.generate(REQ, ["Positive", "Negative", "Edge Case"])
    assert out.session_id is not None
    session = svc.db.get_session(out.session_id)
    assert session["requirement"] == REQ
    assert session["case_count"] == 5 and session["provider"] == "ollama"
    assert session["analysis"]["title"] == "User Registration"


def test_clarification_is_not_saved(make_service):
    svc = make_service([analysis_payload(clarity="unclear", clarification_questions=["What?"])])
    out = svc.generate("Make the system work better for everyone please.", ["Positive"])
    assert out.session_id is None and out.result.status == "needs_clarification"
    assert svc.db.list_sessions() == []


def test_edit_add_delete_through_service(make_service):
    svc = make_service([analysis_payload(), cases_payload(*REGISTRATION_CASES)])
    sid = svc.generate(REQ, ["Positive", "Negative", "Edge Case"]).session_id
    first = svc.db.get_test_cases(sid)[0]
    svc.update_test_case(first["id"], {**REGISTRATION_CASES[0], "priority": "critical", "steps": "1. A\n2. B"})
    edited = svc.db.get_test_case(first["id"])
    assert edited["priority"] == "High" and edited["steps_list"] == ["A", "B"]
    with pytest.raises(TestCaseValidationError):
        svc.update_test_case(first["id"], {**REGISTRATION_CASES[0], "expected_result": ""})
    new_id = svc.add_test_case(sid, REGISTRATION_CASES[1])
    assert svc.db.get_test_case(new_id)["case_code"] == "TC-006"
    assert svc.delete_test_case(new_id)
    assert svc.delete_session(sid) and svc.db.get_session(sid) is None


def test_service_rejects_empty_requirement(make_service):
    with pytest.raises(RequirementValidationError):
        make_service([]).generate("", ["Positive"])


def test_history_survives_restart(settings):
    svc = TestCaseGeneratorService(settings, Database(settings.database_path),
                                   client_factory=lambda s: fake_client(s, [analysis_payload(),
                                                                            cases_payload(*REGISTRATION_CASES)]))
    sid = svc.generate(REQ, ["Positive", "Negative", "Edge Case"]).session_id
    restarted = TestCaseGeneratorService(settings, Database(settings.database_path))
    assert [s["id"] for s in restarted.db.list_sessions()] == [sid]
    assert len(restarted.db.get_test_cases(sid)) == 5
