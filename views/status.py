"""System Status: provider configuration, live connectivity test and database health."""
from __future__ import annotations

import os

import streamlit as st

from agent import LLMClient
from components.state import get_db, get_settings
from components.ui import alert, badge, esc, flash, html, page_header
from config import APP_VERSION, SUPPORTED_PROVIDERS, load_settings
from errors import AppError


def _mask(key: str) -> str:
    return "Not configured" if not key else f"Configured ({key[:4]}…{key[-3:]})"


def render() -> None:
    base = load_settings()
    settings = get_settings()
    page_header("System status", "Configure the active LLM provider for this browser session and verify "
                "that every dependency is reachable.", "Settings", "cpu")

    left, right = st.columns([1.35, 1], gap="large")
    with left, st.container(key="card-provider"):
        html('<div class="tcg-card-title">LLM provider</div>'
             '<div class="tcg-card-sub">Default comes from LLM_PROVIDER in .env. Switching here is an explicit choice '
             'for this session — the app never switches providers silently.</div>')
        choice = st.segmented_control(
            "Provider", list(SUPPORTED_PROVIDERS), default=settings.llm_provider,
            format_func=lambda p: {"ollama": "Ollama (local)", "gemini": "Google Gemini"}[p], key="prov_choice",
        )
        if choice and choice != settings.llm_provider:
            st.session_state["provider_override"] = choice
            flash(f"Provider switched to {choice.title()} for this session.", "info")
            st.rerun()

        rows = [
            ("Active provider", f"{settings.llm_provider.title()}" +
             (" (session override)" if settings.llm_provider != base.llm_provider else " (.env default)")),
            ("Model", settings.active_model),
        ]
        if settings.llm_provider == "ollama":
            rows.append(("Ollama URL", settings.ollama_base_url))
        else:
            rows.append(("Gemini API key", _mask(settings.gemini_api_key if settings.gemini_key_configured else "")))
        rows += [("Temperature", str(settings.temperature)), ("Timeout", f"{settings.timeout_seconds}s"),
                 ("Self-repair attempts", str(settings.max_repair_attempts))]
        html('<div style="margin-top:.6rem">' + "".join(
            f'<div class="sb-row" style="border-bottom:1px solid var(--border-2);padding:.45rem 0">'
            f'<span class="tcg-muted">{esc(k)}</span><b style="color:var(--navy-800)">{esc(v)}</b></div>'
            for k, v in rows) + "</div>")

        st.write("")
        if st.button("Test connection", type="primary", icon=":material/network_check:", key="ping"):
            with st.spinner(f"Contacting {settings.llm_provider}…"):
                try:
                    res = LLMClient(settings).ping()
                    st.session_state["ping_result"] = ("success", f"{settings.llm_provider.title()} · "
                                                       f"{settings.active_model} responded in "
                                                       f"{res['latency_seconds']}s.", "")
                except AppError as exc:
                    st.session_state["ping_result"] = ("error", f"{exc.title}: {exc.message}", exc.hint)
        res = st.session_state.get("ping_result")
        if res:
            alert(res[0], "Connection successful" if res[0] == "success" else "Connection failed", res[1], res[2])

    with right:
        db = get_db()
        stats = db.get_statistics()
        size_kb = os.path.getsize(db.path) / 1024 if db.path.exists() else 0
        with st.container(key="card-db"):
            html(
                f'<div class="tcg-card-title">SQLite database {badge("Connected", "low")}</div>'
                f'<div class="tcg-card-sub" style="word-break:break-all">{esc(db.path)}</div>'
                + "".join(
                    f'<div class="sb-row" style="border-bottom:1px solid var(--border-2);padding:.45rem 0">'
                    f'<span class="tcg-muted">{k}</span><b style="color:var(--navy-800)">{v}</b></div>'
                    for k, v in [("Sessions", stats["sessions"]), ("Test cases", stats["test_cases"]),
                                 ("Cases with assumptions", stats["assumption_cases"]),
                                 ("File size", f"{size_kb:.1f} KB"),
                                 ("Tables", "sessions · session_metadata · test_cases")])
            )
        with st.container(key="card-ollama-help"):
            html(
                '<div class="tcg-card-title">Using Ollama locally</div>'
                '<ol class="tcg-list" style="padding-left:1.2rem">'
                '<li>Install Ollama from <a href="https://ollama.com/download" target="_blank">ollama.com/download</a>.</li>'
                f'<li>Pull the model: <span class="tcg-code">ollama pull {esc(base.ollama_model)}</span></li>'
                '<li>Set <span class="tcg-code">LLM_PROVIDER=ollama</span> in <span class="tcg-code">.env</span> '
                'or switch provider above.</li></ol>'
                f'<div class="tcg-muted" style="font-size:.78rem;margin-top:.6rem">Version {APP_VERSION}</div>'
            )


render()
