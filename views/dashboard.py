"""Dashboard: live KPIs, distributions, activity and recent sessions (all from SQLite)."""
from __future__ import annotations

import streamlit as st

from components import charts
from components.state import get_db, get_settings, open_session
from components.ui import badge, empty_state, esc, fmt_dt, html, section_title, stat_cards
from config import APP_NAME


def render() -> None:
    db = get_db()
    stats = db.get_statistics()
    settings = get_settings()

    html(
        f'<div class="tcg-hero"><div class="tcg-eyebrow">AI-powered QA engineering</div>'
        f'<h1>{esc(APP_NAME)}</h1>'
        f'<p>Describe a software requirement in plain English. The agent analyses its functionality, '
        f'extracts the stated validation rules, flags missing information and designs structured positive, '
        f'negative and edge-case test cases with priorities, steps, data and expected results.</p>'
        f'<div class="tcg-hero-chips"><span class="tcg-hero-chip">LangChain agent</span>'
        f'<span class="tcg-hero-chip">{esc(settings.llm_provider.title())} · {esc(settings.active_model)}</span>'
        f'<span class="tcg-hero-chip">SQLite history</span><span class="tcg-hero-chip">CSV export</span></div></div>'
    )
    with st.container(horizontal=True, key="dash-actions"):
        if st.button("New test session", type="primary", icon=":material/add_circle:"):
            st.switch_page("views/generate.py")
        if st.button("Browse history", icon=":material/history:"):
            st.switch_page("views/history.py")

    p = stats["priority"]
    total = stats["test_cases"]
    avg = total / stats["sessions"] if stats["sessions"] else 0
    stat_cards([
        {"label": "Requirements analysed", "value": stats["sessions"], "icon": "file",
         "foot": f"Avg. {stats['avg_generation_seconds']}s per generation" if stats["sessions"] else "No sessions yet"},
        {"label": "Test cases generated", "value": total, "icon": "layers",
         "foot": f"{avg:.1f} per requirement" if stats["sessions"] else "Start your first session"},
        {"label": "High priority", "value": p["High"], "icon": "flag", "accent": "#DC2626", "tint": "#FDEDED",
         "foot": f"{p['High'] / total:.0%} of all cases" if total else "—"},
        {"label": "Medium priority", "value": p["Medium"], "icon": "gauge", "accent": "#D97706", "tint": "#FEF6E7",
         "foot": f"{p['Medium'] / total:.0%} of all cases" if total else "—"},
        {"label": "Low priority", "value": p["Low"], "icon": "arrow-down", "accent": "#16A34A", "tint": "#EAF7EF",
         "foot": f"{p['Low'] / total:.0%} of all cases" if total else "—"},
    ])

    if not total:
        empty_state("No test cases yet",
                    "Charts and recent sessions appear here as soon as you generate your first test suite.",
                    "sparkles")
        return

    c1, c2, c3 = st.columns(3)
    with c1, st.container(key="card-chart-type"):
        html('<div class="tcg-card-title">Scenario coverage</div>'
             '<div class="tcg-card-sub">Test cases by scenario type</div>')
        st.plotly_chart(charts.scenario_chart(stats["scenario_type"]), config={"displayModeBar": False},
                        key="ch_type")
    with c2, st.container(key="card-chart-prio"):
        html('<div class="tcg-card-title">Priority distribution</div>'
             '<div class="tcg-card-sub">Risk-based ranking of all test cases</div>')
        st.plotly_chart(charts.priority_chart(p), config={"displayModeBar": False}, key="ch_prio")
    with c3, st.container(key="card-chart-activity"):
        html('<div class="tcg-card-title">Generation activity</div>'
             '<div class="tcg-card-sub">Test cases created per day</div>')
        st.plotly_chart(charts.activity_chart(stats["timeline"]), config={"displayModeBar": False},
                        key="ch_activity")

    sessions = db.list_sessions()[:5]
    section_title("Recent test sessions", f"{stats['sessions']} total")
    for s in sessions:
        with st.container(key=f"cardhover-recent-{s['id']}"):
            left, right = st.columns([5, 1.2], vertical_alignment="center")
            with left:
                html(
                    f'<div class="sess-title">{esc(s["title"])}</div>'
                    f'<div class="sess-req">{esc(s["requirement"])}</div>'
                    f'<div class="sess-meta">{fmt_dt(s["created_at"])} · '
                    f'{badge(str(s["high_count"]) + " High", "high")}{badge(str(s["medium_count"]) + " Medium", "medium")}'
                    f'{badge(str(s["low_count"]) + " Low", "low")}</div>'
                )
            with right:
                html(f'<div class="sess-count"><b>{s["case_count"]}</b><span>test cases</span></div>')
                if st.button("Open", key=f"dash_open_{s['id']}", icon=":material/arrow_forward:", width="stretch"):
                    open_session(s["id"])
                    st.switch_page("views/results.py")


render()
