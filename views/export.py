"""Export: build a CSV from one session or the whole history, with filters and preview."""
from __future__ import annotations

import streamlit as st

from components.state import current_session_id, get_db
from components.ui import empty_state, html, page_header, stat_cards
from config import PRIORITIES, SCENARIO_TYPES
from export_utils import cases_to_dataframe, dataframe_to_csv_bytes, export_filename, filter_cases


def render() -> None:
    db = get_db()
    page_header("Export test cases",
                "Download test cases as a CSV file ready for Excel, Jira/Xray, TestRail or Zephyr import.",
                "Export", "download")

    sessions = db.list_sessions()
    if not sessions:
        empty_state("Nothing to export yet", "Generate test cases first — they will be exportable here.", "download")
        return

    labels = {s["id"]: f"#{s['id']} · {s['title']} ({s['case_count']} cases)" for s in sessions}
    with st.container(key="card-export-opts"):
        c1, c2 = st.columns([1, 2])
        scope = c1.radio("Scope", ["Single session", "All sessions"], key="exp_scope")
        if scope == "Single session":
            ids = list(labels)
            cur = current_session_id()
            idx = ids.index(cur) if cur in ids else 0
            sid = c2.selectbox("Session", ids, index=idx, format_func=lambda i: labels[i], key="exp_session")
            cases = db.get_test_cases(sid)
            name = next(s["title"] for s in sessions if s["id"] == sid)
        else:
            c2.markdown("&nbsp;")
            cases = db.get_all_test_cases()
            name = "all_sessions"
        f1, f2, f3 = st.columns([1.3, 1.3, 1.6], vertical_alignment="bottom")
        prios = f1.pills("Priority", PRIORITIES, selection_mode="multi", default=list(PRIORITIES), key="exp_prio")
        types = f2.pills("Scenario type", SCENARIO_TYPES, selection_mode="multi", default=list(SCENARIO_TYPES),
                         key="exp_type")
        search = f3.text_input("Keyword filter", key="exp_search", placeholder="Optional keyword…")

    selected = filter_cases(cases, search, list(prios) or list(PRIORITIES), list(types) or list(SCENARIO_TYPES))
    df = cases_to_dataframe(selected, include_session=(scope == "All sessions"))

    stat_cards([
        {"label": "Rows in export", "value": len(df), "icon": "file", "foot": f"of {len(cases)} available"},
        {"label": "Columns", "value": len(df.columns), "icon": "layers", "foot": "All test case fields"},
        {"label": "High priority rows", "value": int((df["Priority"] == "High").sum()) if len(df) else 0,
         "icon": "flag", "accent": "#DC2626", "tint": "#FDEDED", "foot": "In this export"},
    ])

    if df.empty:
        empty_state("No rows match the current filters",
                    "Select more priorities or scenario types, or clear the keyword.", "search")
        st.download_button("Download CSV", data=b"", disabled=True, icon=":material/download:", key="exp_dl_disabled")
        return

    with st.container(horizontal=True, vertical_alignment="center"):
        html('<div class="tcg-muted">Preview (first 10 rows). Multi-line steps are preserved inside quoted CSV '
             'cells; the file is UTF-8 encoded for Excel.</div>')
        st.space("stretch")
        st.download_button("Download CSV", data=dataframe_to_csv_bytes(df), file_name=export_filename(name),
                           mime="text/csv", type="primary", icon=":material/download:", key="exp_dl",
                           on_click="ignore")
    st.dataframe(df.head(10), hide_index=True, width="stretch")


render()
