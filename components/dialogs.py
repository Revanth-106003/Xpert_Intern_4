"""Modal dialogs: add / edit test case and delete confirmations."""
from __future__ import annotations

from typing import Any

import streamlit as st

from components.state import get_service
from components.ui import alert, esc, flash, html
from config import PRIORITIES, SCENARIO_TYPES
from errors import AppError


def _case_form(prefix: str, case: dict[str, Any] | None) -> tuple[bool, bool, dict[str, Any]]:
    case = case or {}
    with st.form(f"{prefix}_form", border=False):
        scenario = st.text_input("Test scenario *", value=case.get("scenario", ""),
                                 placeholder="e.g. Login fails with an incorrect password")
        c1, c2 = st.columns(2)
        stype = c1.selectbox("Scenario type *", SCENARIO_TYPES,
                             index=SCENARIO_TYPES.index(case.get("scenario_type", "Positive")))
        prio = c2.selectbox("Priority *", PRIORITIES, index=PRIORITIES.index(case.get("priority", "Medium")))
        steps = st.text_area("Test steps * (one step per line)", value="\n".join(case.get("steps_list", [])),
                             height=150, placeholder="Open the login page\nEnter a registered email\n…")
        data = st.text_area("Test data", value=case.get("test_data", ""), height=80,
                            placeholder="Email: user@example.com, Password: Wrong@123")
        expected = st.text_area("Expected result *", value=case.get("expected_result", ""), height=90)
        assumption = st.text_input("Assumption (optional)", value=case.get("assumption", ""),
                                   placeholder="Leave empty if the test relies only on stated requirements")
        b1, b2 = st.columns(2)
        cancel = b1.form_submit_button("Cancel", width="stretch")
        save = b2.form_submit_button("Save test case", type="primary", width="stretch", icon=":material/check:")
    payload = {"scenario": scenario, "scenario_type": stype, "priority": prio,
               "steps": [s for s in steps.splitlines() if s.strip()], "test_data": data,
               "expected_result": expected, "assumption": assumption}
    return save, cancel, payload


@st.dialog("Edit test case", width="large", icon=":material/edit_note:")
def edit_case_dialog(case_id: int) -> None:
    service = get_service()
    case = service.db.get_test_case(case_id)
    if case is None:
        alert("error", "Test case not found", "It may have been deleted in another tab.")
        return
    html(f'<div class="tcg-muted">Editing <span class="tcg-code">{esc(case["case_code"])}</span> — '
         f'changes are saved to the session history immediately.</div>')
    save, cancel, payload = _case_form(f"edit_{case_id}", case)
    if cancel:
        st.rerun()
    if save:
        try:
            service.update_test_case(case_id, payload)
        except AppError as exc:
            alert("error", exc.title, exc.message, exc.hint)
            return
        flash(f"{case['case_code']} updated successfully.")
        st.rerun()


@st.dialog("Add test case", width="large", icon=":material/add_circle:")
def add_case_dialog(session_id: int) -> None:
    service = get_service()
    html('<div class="tcg-muted">Add a manual test case to this session. Fields marked * are required.</div>')
    save, cancel, payload = _case_form(f"add_{session_id}", None)
    if cancel:
        st.rerun()
    if save:
        try:
            service.add_test_case(session_id, payload)
        except AppError as exc:
            alert("error", exc.title, exc.message, exc.hint)
            return
        flash("New test case added.")
        st.rerun()


@st.dialog("Delete test cases?", icon=":material/delete:")
def confirm_delete_cases_dialog(cases: list[dict[str, Any]]) -> None:
    n = len(cases)
    codes = ", ".join(c["case_code"] for c in cases[:8]) + (" …" if n > 8 else "")
    alert("warning", f"You are about to permanently delete {n} test case{'s' if n != 1 else ''}.",
          codes, "")
    html('<div class="tcg-muted" style="margin-top:.5rem">This action cannot be undone.</div>')
    c1, c2 = st.columns(2)
    if c1.button("Cancel", width="stretch", key="del_cases_cancel"):
        st.rerun()
    with c2.container(key="dangerfill-del-cases"):
        if st.button("Delete permanently", type="primary", width="stretch", icon=":material/delete:"):
            deleted = get_service().db.delete_test_cases([c["id"] for c in cases])
            flash(f"Deleted {deleted} test case{'s' if deleted != 1 else ''}.")
            st.rerun()


@st.dialog("Delete session?", icon=":material/delete_forever:")
def confirm_delete_session_dialog(session_id: int, title: str, case_count: int) -> None:
    alert("warning", f"Delete “{title}”?",
          f"The requirement, its AI analysis and all {case_count} test case(s) will be permanently removed "
          "from history.")
    c1, c2 = st.columns(2)
    if c1.button("Cancel", width="stretch", key="del_sess_cancel"):
        st.rerun()
    with c2.container(key="dangerfill-del-session"):
        if st.button("Delete session", type="primary", width="stretch", icon=":material/delete_forever:"):
            if get_service().delete_session(session_id):
                if st.session_state.get("current_session_id") == session_id:
                    st.session_state.pop("current_session_id", None)
                flash(f"Session “{title}” deleted.")
            else:
                flash("Session was already deleted.", "warning")
            st.rerun()
