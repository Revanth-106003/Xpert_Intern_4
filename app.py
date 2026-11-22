"""AI Test Case Generator Agent - Streamlit entry point.

Run with:  streamlit run app.py   (or use run.bat / run.sh)
"""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from agent import LLMClient
from components.state import get_db, get_settings
from components.styles import inject_css
from components.ui import esc, html, render_flashes
from config import APP_NAME, APP_VERSION

ASSETS = Path(__file__).parent / "assets"

st.set_page_config(
    page_title=APP_NAME,
    page_icon=str(ASSETS / "icon.svg"),
    layout="wide",
    initial_sidebar_state="auto",  # expanded on desktop, collapsed on phones
)
inject_css()
st.logo(str(ASSETS / "logo.svg"), icon_image=str(ASSETS / "icon.svg"), size="large")


@st.cache_data(ttl=30, show_spinner=False)
def _provider_status(provider: str, model: str) -> dict:
    """Cheap readiness probe (no LLM call); cached so navigation stays fast."""
    return LLMClient(get_settings()).describe_status()


pages = {
    "Workspace": [
        st.Page("views/dashboard.py", title="Dashboard", icon=":material/space_dashboard:", default=True),
        st.Page("views/generate.py", title="Generate Test Cases", icon=":material/auto_awesome:"),
        st.Page("views/results.py", title="Test Case Results", icon=":material/fact_check:"),
    ],
    "Manage": [
        st.Page("views/history.py", title="History", icon=":material/history:"),
        st.Page("views/export.py", title="Export CSV", icon=":material/download:"),
        st.Page("views/status.py", title="System Status", icon=":material/settings:"),
    ],
}
nav = st.navigation(pages, position="sidebar", expanded=True)

# ---------------------------------------------------------------- sidebar
settings = get_settings()
status = _provider_status(settings.llm_provider, settings.active_model)
stats = get_db().get_statistics()
with st.sidebar:
    dot = "ok" if status.get("ok") else "bad"
    state_text = "Ready" if status.get("ok") else "Not ready"
    html(
        '<div class="sb-section">AI engine</div>'
        f'<div class="sb-card"><div class="sb-row"><span><span class="sb-dot {dot}"></span>{state_text}</span>'
        f'<b>{esc(settings.llm_provider.title())}</b></div>'
        f'<div class="sb-row"><span>Model</span><b>{esc(settings.active_model)}</b></div></div>'
        '<div class="sb-section">Workspace</div>'
        f'<div class="sb-card"><div class="sb-row"><span>Sessions</span><b>{stats["sessions"]}</b></div>'
        f'<div class="sb-row"><span>Test cases</span><b>{stats["test_cases"]}</b></div>'
        f'<div class="sb-row"><span>High priority</span><b>{stats["priority"]["High"]}</b></div></div>'
        f'<div class="sb-foot">{esc(APP_NAME)} · v{APP_VERSION}<br>LangChain · Streamlit · SQLite</div>'
    )

render_flashes()
nav.run()
