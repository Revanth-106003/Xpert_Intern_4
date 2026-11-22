"""Reusable presentational building blocks (HTML rendered via ``st.html``).

All user-provided / LLM-provided text is HTML-escaped before rendering.
"""
from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Iterable

import streamlit as st

from components.icons import icon
from errors import AppError


def esc(value: Any) -> str:
    return escape(str(value if value is not None else ""), quote=True)


def html(markup: str) -> None:
    """Render trusted markup. Dynamic text must already be escaped with :func:`esc`."""
    st.markdown(markup, unsafe_allow_html=True)


def page_header(title: str, subtitle: str = "", eyebrow: str = "", eyebrow_icon: str = "sparkles") -> None:
    eb = f'<div class="tcg-eyebrow">{icon(eyebrow_icon, 14)} {esc(eyebrow)}</div>' if eyebrow else ""
    sub = f'<div class="tcg-subtitle">{esc(subtitle)}</div>' if subtitle else ""
    html(f'<div class="tcg-header"><div>{eb}<h1 class="tcg-title">{esc(title)}</h1>{sub}</div></div>')


def section_title(title: str, aside: str = "") -> None:
    html(f'<div class="tcg-section"><h3>{esc(title)}</h3><span>{esc(aside)}</span></div>')


def stat_cards(items: Iterable[dict[str, Any]]) -> None:
    """Render KPI cards. Integer values animate with a CSS-only counter."""
    cards = []
    for it in items:
        value = it.get("value", 0)
        if isinstance(value, int):
            val_html = f'<span class="tcg-counter" style="--to:{value}" aria-label="{value}"></span>'
        else:
            val_html = esc(value)
        accent = it.get("accent", "var(--blue-600)")
        cards.append(
            f'<div class="tcg-stat" style="--accent:{accent}">'
            f'<div class="tcg-stat-top"><span class="tcg-stat-label">{esc(it["label"])}</span>'
            f'<span class="tcg-stat-icon" style="color:{accent};background:{it.get("tint", "var(--blue-50)")}">'
            f'{icon(it.get("icon", "layers"))}</span></div>'
            f'<div class="tcg-stat-value">{val_html}</div>'
            f'<div class="tcg-stat-foot">{esc(it.get("foot", ""))}</div></div>'
        )
    html(f'<div class="tcg-stats">{"".join(cards)}</div>')


def badge(text: str, kind: str | None = None) -> str:
    cls = kind or str(text).lower().replace(" ", "-")
    return f'<span class="tcg-badge {esc(cls)}">{esc(text)}</span>'


def alert(kind: str, title: str, message: str = "", hint: str = "") -> None:
    ico = {"error": "x", "warning": "alert", "success": "check", "info": "info"}.get(kind, "info")
    hint_html = f'<div class="tcg-alert-hint"><b>How to fix:</b> {esc(hint)}</div>' if hint else ""
    msg_html = f'<div class="tcg-alert-msg">{esc(message)}</div>' if message else ""
    html(f'<div class="tcg-alert {kind}">{icon(ico, 20)}<div><div class="tcg-alert-title">{esc(title)}</div>'
         f'{msg_html}{hint_html}</div></div>')


def error_alert(exc: AppError) -> None:
    alert("error", exc.title, exc.message, exc.hint)


def empty_state(title: str, message: str, icon_name: str = "inbox") -> None:
    html(f'<div class="tcg-empty"><div class="tcg-empty-icon">{icon(icon_name, 26)}</div>'
         f'<h4>{esc(title)}</h4><p>{esc(message)}</p></div>')


def loader(title: str, detail: str) -> str:
    return (f'<div class="tcg-loader" role="status" aria-live="polite"><div class="tcg-orb"></div>'
            f'<div><b>{esc(title)} <span class="tcg-dots"><span></span><span></span><span></span></span></b>'
            f'<small>{esc(detail)}</small></div></div>')


def bullet_list(items: list[str], empty: str = "None identified.") -> str:
    if not items:
        return f'<div class="tcg-muted">{esc(empty)}</div>'
    return '<ul class="tcg-list">' + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul>"


def fmt_dt(value: str | None) -> str:
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%d %b %Y, %H:%M")
    except ValueError:
        return value


def test_case_html(case: dict[str, Any]) -> str:
    steps = case.get("steps_list") or []
    steps_html = "".join(f"<li>{esc(s)}</li>" for s in steps) or "<li>—</li>"
    assumption = case.get("assumption") or ""
    assume_html = (f'<div class="tc-assume">{icon("lightbulb", 16)}<span>{esc(assumption)}</span></div>'
                   if assumption else "")
    manual = badge("Manually added", "neutral") if case.get("source") == "manual" else ""
    return (
        f'<div class="tc-head"><span class="tcg-code">{esc(case.get("case_code"))}</span>'
        f'{badge(case.get("scenario_type", ""))}{badge(case.get("priority", "") + " priority", str(case.get("priority", "")).lower())}{manual}</div>'
        f'<div class="tc-title">{esc(case.get("scenario"))}</div>'
        f'<div class="tc-grid"><div><div class="tc-label">Test steps</div><ol class="tc-steps">{steps_html}</ol></div>'
        f'<div><div class="tc-label">Test data</div><div class="tc-box data">{esc(case.get("test_data"))}</div>'
        f'<div class="tc-label">Expected result</div><div class="tc-box expected">{esc(case.get("expected_result"))}</div>'
        f'</div></div>{assume_html}'
    )


# --------------------------------------------------------------- flash/toasts
def flash(message: str, kind: str = "success") -> None:
    """Queue a toast that survives the next ``st.rerun()``."""
    st.session_state.setdefault("_flash", []).append((message, kind))


def render_flashes() -> None:
    icons = {"success": ":material/check_circle:", "error": ":material/error:",
             "warning": ":material/warning:", "info": ":material/info:"}
    for message, kind in st.session_state.pop("_flash", []):
        st.toast(message, icon=icons.get(kind, icons["info"]))
