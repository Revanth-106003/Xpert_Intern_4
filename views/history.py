"""History: every saved session, persisted in SQLite across restarts."""
from __future__ import annotations

import streamlit as st

from components.dialogs import confirm_delete_session_dialog
from components.state import get_db, open_session
from components.ui import badge, empty_state, esc, fmt_dt, html, page_header
from export_utils import cases_to_dataframe, dataframe_to_csv_bytes, export_filename

PAGE_SIZE = 8


def render() -> None:
    db = get_db()
    page_header("Session history",
                "Every analysed requirement and its test cases are stored in SQLite and survive restarts. "
                "Open a session to view, edit or extend its test cases.", "History", "history")

    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    search = c1.text_input("Search sessions", placeholder="Search by title or requirement text…",
                           icon=":material/search:", key="hist_search")
    sort = c2.selectbox("Sort by", ["Newest first", "Oldest first", "Most test cases"], key="hist_sort")

    sessions = db.list_sessions(search)
    if sort == "Oldest first":
        sessions = list(reversed(sessions))
    elif sort == "Most test cases":
        sessions = sorted(sessions, key=lambda s: s["case_count"], reverse=True)

    if not sessions:
        if search:
            empty_state("No matching sessions", f"Nothing matches “{search}”. Try another search term.", "search")
        else:
            empty_state("No history yet", "Generated sessions will appear here automatically.", "history")
            if st.button("Generate your first test suite", type="primary", icon=":material/auto_awesome:"):
                st.switch_page("views/generate.py")
        return

    pages = max(1, -(-len(sessions) // PAGE_SIZE))
    page = st.session_state.get("hist_page", 1)
    page = min(max(page, 1), pages)
    current = sessions[(page - 1) * PAGE_SIZE: page * PAGE_SIZE]

    html(f'<div class="tcg-muted">{len(sessions)} session{"s" if len(sessions) != 1 else ""}</div>')
    for s in current:
        with st.container(key=f"cardhover-hist-{s['id']}"):
            left, right = st.columns([4.2, 1], vertical_alignment="center")
            with left:
                types = "".join(badge(t) for t in s["scenario_types"])
                html(
                    f'<div class="sess-title">{esc(s["title"])}</div>'
                    f'<div class="sess-req">{esc(s["requirement"])}</div>'
                    f'<div class="sess-meta"><span>{fmt_dt(s["created_at"])}</span><span>·</span>{types}'
                    f'{badge(str(s["high_count"]) + " High", "high")}{badge(str(s["medium_count"]) + " Medium", "medium")}'
                    f'{badge(str(s["low_count"]) + " Low", "low")}'
                    f'{badge((s.get("provider") or "").title() + " · " + (s.get("model") or ""), "neutral")}</div>'
                )
            with right:
                html(f'<div class="sess-count"><b>{s["case_count"]}</b><span>test cases</span></div>')
            with st.container(horizontal=True, horizontal_alignment="right", gap="small"):
                if st.button("Open session", key=f"hist_open_{s['id']}", icon=":material/open_in_new:",
                             type="primary"):
                    open_session(s["id"])
                    st.switch_page("views/results.py")
                full = db.get_test_cases(s["id"])
                st.download_button("CSV", data=dataframe_to_csv_bytes(cases_to_dataframe(full)),
                                   file_name=export_filename(s["title"]), mime="text/csv",
                                   key=f"hist_dl_{s['id']}", icon=":material/download:",
                                   disabled=not full, on_click="ignore")
                with st.container(key=f"danger-hist-del-{s['id']}", width="content"):
                    if st.button("Delete", key=f"hist_del_{s['id']}", icon=":material/delete:"):
                        confirm_delete_session_dialog(s["id"], s["title"], s["case_count"])

    if pages > 1:
        with st.container(horizontal=True, horizontal_alignment="center", vertical_alignment="center"):
            if st.button("Previous", disabled=page <= 1, icon=":material/chevron_left:", key="hist_prev"):
                st.session_state["hist_page"] = page - 1
                st.rerun()
            html(f'<div class="tcg-muted">Page {page} of {pages}</div>')
            if st.button("Next", disabled=page >= pages, icon=":material/chevron_right:", key="hist_next"):
                st.session_state["hist_page"] = page + 1
                st.rerun()


render()
