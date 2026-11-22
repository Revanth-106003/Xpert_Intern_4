"""Shared application state: cached resources and cross-page session values."""
from __future__ import annotations

import streamlit as st

from config import SUPPORTED_PROVIDERS, Settings, load_settings
from database import Database
from test_case_generator import TestCaseGeneratorService


@st.cache_resource(show_spinner=False)
def _database(path: str) -> Database:
    return Database(path)


def get_settings() -> Settings:
    base = load_settings()
    override = st.session_state.get("provider_override")
    if override and override in SUPPORTED_PROVIDERS and override != base.llm_provider:
        return base.with_provider(override)
    return base


def get_db() -> Database:
    return _database(str(load_settings().database_path))


def get_service() -> TestCaseGeneratorService:
    return TestCaseGeneratorService(get_settings(), get_db())


def open_session(session_id: int) -> None:
    st.session_state["current_session_id"] = int(session_id)
    # reset per-session view state
    for key in ("tc_search", "tc_prio", "tc_type"):
        st.session_state.pop(key, None)


def current_session_id() -> int | None:
    return st.session_state.get("current_session_id")
