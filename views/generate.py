"""Generate Test Cases: requirement workspace and agent execution with live progress."""
from __future__ import annotations

import streamlit as st

from components.state import get_service, get_settings, open_session
from components.ui import alert, bullet_list, error_alert, esc, flash, html, loader, page_header
from config import SCENARIO_TYPES
from errors import AppError
from validators import MAX_REQUIREMENT_CHARS

EXAMPLES = {
    "User registration": (
        "New users can register by entering their full name, email address, password and confirm password. "
        "The email must be unique and in a valid format. The password must be at least 8 characters long and "
        "contain at least one uppercase letter, one number and one special character. Confirm password must match "
        "the password. After successful registration a verification email is sent to the user."
    ),
    "Login with lockout": (
        "Registered users log in with their email address and password. Passwords are case-sensitive. "
        "After 3 consecutive failed login attempts the account is locked for 15 minutes. "
        "A 'Remember me' option keeps the user signed in for 30 days."
    ),
    "Shopping cart": (
        "A logged-in customer can add products to the shopping cart. The quantity of each product must be between "
        "1 and 10. If the requested quantity exceeds the available stock, an error message is shown. The cart "
        "total is recalculated whenever an item is added, removed or its quantity changes."
    ),
    "Password reset": (
        "A user who forgot their password can request a reset link by entering their registered email address. "
        "The reset link is valid for 30 minutes and can be used only once. The new password cannot be the same "
        "as the last 3 passwords."
    ),
    "File upload": (
        "Users can upload a profile picture. Only JPG and PNG files up to 5 MB are allowed. "
        "The image is resized to 400x400 pixels and displayed on the profile page."
    ),
}

STAGES = {"validate": 0.06, "connect": 0.12, "analyse": 0.22, "clarify": 1.0, "generate": 0.55,
          "repair": 0.75, "validate_output": 0.9, "done": 1.0}
STAGE_TITLES = {"validate": "Validating input", "connect": "Connecting to model", "analyse": "Analysing requirement",
                "generate": "Designing test cases", "repair": "Self-correcting response",
                "validate_output": "Validating output", "done": "Completed", "clarify": "Clarification needed"}


def _use_example(name: str) -> None:
    st.session_state["req_text"] = EXAMPLES[name]
    st.session_state.pop("clarification", None)
    st.session_state.pop("gen_error", None)


def _clear() -> None:
    st.session_state["req_text"] = ""
    st.session_state.pop("clarification", None)
    st.session_state.pop("gen_error", None)


def _run(requirement: str, scenario_types: list[str], proceed: bool) -> None:
    service = get_service()
    slot = st.empty()
    bar = st.progress(0.0)
    status = st.status("Agent started…", expanded=True)
    done_steps: list[str] = []

    def progress(stage: str, message: str) -> None:
        bar.progress(STAGES.get(stage, 0.5))
        slot.markdown(loader(STAGE_TITLES.get(stage, "Working"), message), unsafe_allow_html=True)
        status.update(label=message)
        status.write(f"**{STAGE_TITLES.get(stage, stage)}** — {message}")
        done_steps.append(stage)

    try:
        outcome = service.generate(requirement, scenario_types, proceed_with_assumptions=proceed,
                                   progress=progress)
    except AppError as exc:
        slot.empty(); bar.empty()
        status.update(label=f"{exc.title}: {exc.message}", state="error", expanded=False)
        st.session_state["gen_error"] = {"title": exc.title, "message": exc.message, "hint": exc.hint}
        st.toast(exc.title, icon=":material/error:")
        return
    except Exception as exc:  # last-resort guard: the UI must never crash
        slot.empty(); bar.empty()
        status.update(label="Unexpected error", state="error", expanded=False)
        st.session_state["gen_error"] = {"title": "Unexpected error", "message": str(exc)[:400],
                                         "hint": "Please retry. If the problem persists check the terminal log."}
        return

    slot.empty(); bar.empty()
    result = outcome.result
    if result.status == "needs_clarification":
        status.update(label="The requirement needs clarification", state="complete", expanded=False)
        st.session_state["clarification"] = {
            "requirement": requirement, "scenario_types": scenario_types,
            "analysis": result.analysis.model_dump(),
        }
        st.rerun()
    status.update(label=f"Generated {len(result.test_cases)} test cases in {result.elapsed_seconds}s",
                  state="complete", expanded=False)
    open_session(outcome.session_id)
    flash(f"Generated {len(result.test_cases)} validated test cases and saved them to history.")
    st.switch_page("views/results.py")


def render() -> None:
    settings = get_settings()
    page_header("Generate test cases",
                "Write the requirement the way a business analyst would. The agent understands it first, "
                "then designs the tests.", "Requirement workspace", "sparkles")

    left, right = st.columns([2.15, 1], gap="large")
    with left:
        with st.container(key="card-input"):
            st.text_area(
                "Software requirement", key="req_text", height=230, max_chars=MAX_REQUIREMENT_CHARS,
                placeholder="Example: Users can reset their password using a link sent to their registered email. "
                            "The link expires after 30 minutes…",
            )
            html('<div class="tcg-muted" style="font-size:.8rem;margin:-.3rem 0 .2rem">'
                 'Try an example requirement:</div>')
            with st.container(horizontal=True, key="examples", gap="small"):
                for name in EXAMPLES:
                    st.button(name, key=f"ex_{name}", on_click=_use_example, args=(name,))

            st.pills("Scenario types to cover", SCENARIO_TYPES, selection_mode="multi",
                     default=list(SCENARIO_TYPES), key="gen_types")
            with st.container(horizontal=True, vertical_alignment="center"):
                st.button("Clear", icon=":material/backspace:", on_click=_clear, key="clear_btn")
                st.space("stretch")
                generate = st.button("Generate test cases", type="primary", icon=":material/auto_awesome:",
                                     key="generate_btn")

    with right:
        with st.container(key="card-pipeline"):
            html(
                '<div class="tcg-card-title">How the agent works</div>'
                '<div class="tcg-card-sub">A two-stage LangChain workflow with validation</div>'
                '<ol class="tcg-pipe">'
                '<li data-n="1"><b>Understand</b><span>Functionality, actors, inputs and the rules that are '
                'explicitly stated.</span></li>'
                '<li data-n="2"><b>Question</b><span>Missing information and assumptions are flagged — rules are '
                'never invented.</span></li>'
                '<li data-n="3"><b>Design</b><span>Positive, negative and edge-case tests with steps, data, '
                'expected results and priority.</span></li>'
                '<li data-n="4"><b>Validate</b><span>JSON schema checks, self-repair, scenario filtering and '
                'duplicate removal.</span></li>'
                '<li data-n="5"><b>Persist</b><span>Saved to SQLite history, ready to edit and export.</span></li>'
                '</ol>'
            )
        with st.container(key="card-model"):
            html(f'<div class="tcg-card-title">Active model</div>'
                 f'<div class="tcg-muted">{esc(settings.llm_provider.title())} · '
                 f'<span class="tcg-code">{esc(settings.active_model)}</span></div>'
                 f'<div class="tcg-muted" style="font-size:.8rem;margin-top:.4rem">'
                 f'Change it on the System Status page.</div>')

    work = st.container()

    if generate:
        st.session_state.pop("clarification", None)
        st.session_state.pop("gen_error", None)
        with work:
            _run(st.session_state.get("req_text", ""), list(st.session_state.get("gen_types") or []), False)

    err = st.session_state.get("gen_error")
    if err:
        with work:
            alert("error", err["title"], err["message"], err["hint"])

    clar = st.session_state.get("clarification")
    if clar:
        with work:
            _render_clarification(clar)


def _render_clarification(clar: dict) -> None:
    a = clar["analysis"]
    with st.container(key="card-clarify"):
        alert("warning", "The requirement is too vague to test reliably",
              "The agent could not determine the expected behaviour. Answer the questions below by refining "
              "the requirement, or continue and let the agent proceed with explicitly labelled assumptions.")
        c1, c2 = st.columns(2)
        with c1:
            html('<div class="tc-label" style="margin-top:.8rem">Clarification questions</div>'
                 + bullet_list(a.get("clarification_questions", [])))
        with c2:
            html('<div class="tc-label" style="margin-top:.8rem">Assumptions the agent would make</div>'
                 + bullet_list(a.get("assumptions", [])))
        with st.container(horizontal=True):
            st.space("stretch")
            if st.button("I'll refine the requirement", icon=":material/edit:", key="clar_refine"):
                st.session_state.pop("clarification", None)
                st.rerun()
            if st.button("Generate with assumptions", type="primary", icon=":material/auto_awesome:",
                         key="clar_go"):
                st.session_state.pop("clarification", None)
                _run(clar["requirement"], clar["scenario_types"], True)


render()
