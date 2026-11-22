"""Pandas-based tabular transforms and CSV export."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Iterable

import pandas as pd

EXPORT_COLUMNS = [
    "Test Case ID", "Test Scenario", "Scenario Type", "Priority",
    "Test Steps", "Test Data", "Expected Result", "Assumption",
]


def number_steps(steps: Iterable[str]) -> str:
    return "\n".join(f"{i}. {s}" for i, s in enumerate(steps, start=1))


def cases_to_dataframe(cases: list[dict[str, Any]], include_session: bool = False) -> pd.DataFrame:
    """Convert DB test-case rows to a display/export DataFrame."""
    columns = (["Session"] if include_session else []) + EXPORT_COLUMNS
    if not cases:
        return pd.DataFrame(columns=columns)
    rows = []
    for c in cases:
        steps = c.get("steps_list") or [s for s in str(c.get("steps", "")).splitlines() if s.strip()]
        row = {
            "Test Case ID": c.get("case_code", ""),
            "Test Scenario": c.get("scenario", ""),
            "Scenario Type": c.get("scenario_type", ""),
            "Priority": c.get("priority", ""),
            "Test Steps": number_steps(steps),
            "Test Data": c.get("test_data", ""),
            "Expected Result": c.get("expected_result", ""),
            "Assumption": c.get("assumption", ""),
        }
        if include_session:
            row = {"Session": c.get("session_title", ""), **row}
        rows.append(row)
    return pd.DataFrame(rows, columns=columns)


def filter_cases(cases: list[dict[str, Any]], search: str = "", priorities: list[str] | None = None,
                 scenario_types: list[str] | None = None) -> list[dict[str, Any]]:
    """Case-insensitive search across all text fields plus priority/type filters."""
    term = (search or "").strip().lower()
    out = []
    for c in cases:
        if priorities is not None and c.get("priority") not in priorities:
            continue
        if scenario_types is not None and c.get("scenario_type") not in scenario_types:
            continue
        if term:
            hay = " ".join(str(c.get(k, "")) for k in (
                "case_code", "scenario", "steps", "test_data", "expected_result", "assumption")).lower()
            if term not in hay:
                continue
        out.append(c)
    return out


def dataframe_to_csv_bytes(df: pd.DataFrame) -> bytes:
    """UTF-8 with BOM so Excel opens non-ASCII characters and multi-line cells correctly."""
    return df.to_csv(index=False, lineterminator="\r\n").encode("utf-8-sig")


def export_filename(label: str = "test_cases") -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").lower()[:50] or "test_cases"
    return f"{slug}_{datetime.now():%Y%m%d_%H%M%S}.csv"
