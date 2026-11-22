"""Test Case Results: the active session's requirement, AI analysis and editable test cases."""
from __future__ import annotations

import streamlit as st

from components.state import current_session_id, get_db, open_session
from components.test_case_view import render_workspace
from components.ui import (alert, badge, bullet_list, empty_state, esc, fmt_dt, html, page_header,
                           stat_cards)


def render() -> None:
    db = get_db()
    sid = current_session_id()
    session = db.get_session(sid) if sid else None

    if session is None:
        page_header("Test case results", "Review, refine and export the test cases of a session.",
                    "Results", "layers")
        if sid:
            st.session_state.pop("current_session_id", None)
        sessions = db.list_sessions()
        empty_state("No session open",
                    "Generate test cases for a new requirement, or open a previous session from history.",
                    "layers")
        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.button("Generate test cases", type="primary", icon=":material/auto_awesome:"):
                st.switch_page("views/generate.py")
            if sessions and st.button(f"Open latest session ({sessions[0]['title']})", icon=":material/history:"):
                open_session(sessions[0]["id"])
                st.rerun()
        return

    cases = session["test_cases"]
    a = session.get("analysis") or {}
    meta_chips = (
        f'{badge(f"Session #{session["id"]}", "neutral")}'
        f'{badge(fmt_dt(session["created_at"]), "neutral")}'
        f'{badge(f"{(session.get("provider") or "").title()} · {session.get("model") or "—"}", "neutral")}'
        f'{badge(f"{session.get("generation_seconds") or 0:.1f}s generation", "neutral")}'
    )
    page_header(session["title"], "", "Test case results", "layers")
    html(f'<div class="tcg-kv" style="margin-top:-.4rem">{meta_chips}</div>')

    prio = {p: sum(1 for c in cases if c["priority"] == p) for p in ("High", "Medium", "Low")}
    stat_cards([
        {"label": "Test cases", "value": len(cases), "icon": "layers",
         "foot": f"{sum(1 for c in cases if c['assumption'])} rely on assumptions"},
        {"label": "High priority", "value": prio["High"], "icon": "flag", "accent": "#DC2626", "tint": "#FDEDED",
         "foot": "Core flows, security, data integrity"},
        {"label": "Medium priority", "value": prio["Medium"], "icon": "gauge", "accent": "#D97706",
         "tint": "#FEF6E7", "foot": "Validations & alternate flows"},
        {"label": "Low priority", "value": prio["Low"], "icon": "arrow-down", "accent": "#16A34A",
         "tint": "#EAF7EF", "foot": "Cosmetic & rare conditions"},
    ])

    with st.expander("Requirement & AI analysis", expanded=False, icon=":material/psychology:"):
        html(f'<div class="tc-label">Original requirement</div><div class="tcg-req">{esc(session["requirement"])}</div>')
        if a:
            clarity = {"clear": ("Clear", "low"), "partially_clear": ("Partially clear", "medium"),
                       "unclear": ("Unclear — generated with assumptions", "high")}.get(a.get("clarity"), ("—", "neutral"))
            html(
                f'<div class="tcg-divider"></div>'
                f'<div class="tc-head"><div class="tc-label" style="margin:0">Requirement clarity</div>'
                f'{badge(clarity[0], clarity[1])}</div>'
                f'<div class="tc-grid" style="margin-top:.9rem">'
                f'<div><div class="tc-label">Summary</div><div class="tcg-muted" style="color:var(--text)">'
                f'{esc(a.get("summary", ""))}</div>'
                f'<div class="tc-label" style="margin-top:.9rem">Main functionality</div>'
                f'<div class="tcg-muted" style="color:var(--text)">{esc(a.get("main_functionality", ""))}</div>'
                f'<div class="tc-label" style="margin-top:.9rem">Actors · Inputs</div>'
                f'<div class="tcg-kv">{"".join(badge(x, "neutral") for x in a.get("actors", []))}'
                f'{"".join(badge(x, "positive") for x in a.get("inputs", []))}</div></div>'
                f'<div><div class="tc-label">Validation rules (stated)</div>'
                f'{bullet_list(a.get("validation_rules", []), "No explicit rules stated.")}</div></div>'
                f'<div class="tc-grid" style="margin-top:.9rem">'
                f'<div><div class="tc-label">Missing / unclear information</div>'
                f'{bullet_list(a.get("missing_information", []))}</div>'
                f'<div><div class="tc-label">Assumptions</div>{bullet_list(a.get("assumptions", []))}</div></div>'
            )
    for w in session.get("warnings") or []:
        alert("info", "Validation note", w)

    render_workspace(session)


render()
