"""Interactive test-case workspace: filters, table/card views, CRUD and export."""
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from components.dialogs import add_case_dialog, confirm_delete_cases_dialog, edit_case_dialog
from components.ui import empty_state, html, test_case_html
from config import PRIORITIES, SCENARIO_TYPES
from export_utils import cases_to_dataframe, dataframe_to_csv_bytes, export_filename, filter_cases

_PRIO_STYLE = {"High": "color:#B91C1C;font-weight:600", "Medium": "color:#B45309;font-weight:600",
               "Low": "color:#15803D;font-weight:600"}


def _table_frame(cases: list[dict[str, Any]]) -> pd.DataFrame:
    rows = [{
        "ID": c["case_code"],
        "Test Scenario": c["scenario"],
        "Type": c["scenario_type"],
        "Priority": c["priority"],
        "Test Steps": "  →  ".join(c["steps_list"]),
        "Test Data": c["test_data"],
        "Expected Result": c["expected_result"],
        "Assumption": c["assumption"] or "—",
    } for c in cases]
    return pd.DataFrame(rows, columns=["ID", "Test Scenario", "Type", "Priority", "Test Steps",
                                       "Test Data", "Expected Result", "Assumption"])


def render_workspace(session: dict[str, Any]) -> None:
    sid = session["id"]
    cases = session["test_cases"]

    # -------------------------------------------------------------- toolbar
    with st.container(key="card-toolbar"):
        c1, c2, c3 = st.columns([2.2, 1.6, 2.1], vertical_alignment="bottom")
        search = c1.text_input("Search test cases", key="tc_search", placeholder="Search ID, scenario, steps, data…",
                               icon=":material/search:")
        prios = c2.pills("Priority", PRIORITIES, selection_mode="multi", default=list(PRIORITIES), key="tc_prio")
        types = c3.pills("Scenario type", SCENARIO_TYPES, selection_mode="multi", default=list(SCENARIO_TYPES),
                         key="tc_type")

    filtered = filter_cases(cases, search, list(prios) or list(PRIORITIES), list(types) or list(SCENARIO_TYPES))

    bar = st.container(horizontal=True, vertical_alignment="center")
    with bar:
        html(f'<div class="tcg-muted"><b style="color:var(--navy-800)">{len(filtered)}</b> of {len(cases)} '
             f'test cases shown</div>')
        st.space("stretch")
        view = st.segmented_control("View", ["Cards", "Table"], default="Cards", key="tc_view",
                                    label_visibility="collapsed")
        if st.button("Add test case", icon=":material/add:", key="add_case_btn"):
            add_case_dialog(sid)
        st.download_button(
            "Export filtered CSV", data=dataframe_to_csv_bytes(cases_to_dataframe(filtered)),
            file_name=export_filename(f"{session['title']}_filtered"), mime="text/csv",
            icon=":material/download:", disabled=not filtered, key="dl_filtered", on_click="ignore",
        )

    if not cases:
        empty_state("This session has no test cases", "Add a test case manually or generate a new session.")
        return
    if not filtered:
        empty_state("No test cases match your filters", "Clear the search or select more priorities / types.",
                    "search")
        return

    if (view or "Cards") == "Table":
        _render_table(session, filtered)
    else:
        _render_cards(filtered)


def _render_table(session: dict[str, Any], filtered: list[dict[str, Any]]) -> None:
    df = _table_frame(filtered)
    styled = df.style.map(lambda v: _PRIO_STYLE.get(v, ""), subset=["Priority"])
    event = st.dataframe(
        styled, hide_index=True, on_select="rerun", selection_mode="multi-row", key=f"tc_table_{session['id']}",
        height=min(42 + 36 * len(df), 520),
        column_config={
            "ID": st.column_config.TextColumn(width=80, pinned=True),
            "Test Scenario": st.column_config.TextColumn(width="large"),
            "Type": st.column_config.TextColumn(width=95),
            "Priority": st.column_config.TextColumn(width=80),
            "Test Steps": st.column_config.TextColumn(width="large"),
            "Test Data": st.column_config.TextColumn(width="medium"),
            "Expected Result": st.column_config.TextColumn(width="large"),
            "Assumption": st.column_config.TextColumn(width="medium"),
        },
    )
    rows = [r for r in event.selection.rows if r < len(filtered)] if event else []
    selected = [filtered[r] for r in rows]

    with st.container(horizontal=True, vertical_alignment="center"):
        html(f'<div class="tcg-muted">{len(selected)} selected — tick rows to edit, delete or export them.</div>')
        st.space("stretch")
        if st.button("Edit selected", icon=":material/edit:", disabled=len(selected) != 1, key="tbl_edit",
                     help="Select exactly one row to edit"):
            edit_case_dialog(selected[0]["id"])
        with st.container(key="danger-tbl-del", width="content"):
            if st.button("Delete selected", icon=":material/delete:", disabled=not selected, key="tbl_del"):
                confirm_delete_cases_dialog(selected)
        st.download_button(
            "Export selected CSV", data=dataframe_to_csv_bytes(cases_to_dataframe(selected)),
            file_name=export_filename(f"{session['title']}_selected"), mime="text/csv",
            icon=":material/download:", disabled=not selected, key="dl_selected", on_click="ignore",
        )


def _render_cards(filtered: list[dict[str, Any]]) -> None:
    for case in filtered:
        with st.container(key=f"card-tc-{case['id']}"):
            html(test_case_html(case))
            with st.container(horizontal=True, horizontal_alignment="right", gap="small"):
                if st.button("Edit", icon=":material/edit:", key=f"edit_{case['id']}", type="tertiary"):
                    edit_case_dialog(case["id"])
                with st.container(key=f"danger-del-{case['id']}", width="content"):
                    if st.button("Delete", icon=":material/delete:", key=f"del_{case['id']}", type="tertiary"):
                        confirm_delete_cases_dialog([case])
