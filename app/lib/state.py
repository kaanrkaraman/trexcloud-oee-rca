"""Shared session-state helpers for cross-page selectors and RCA->What-If handoff."""
from __future__ import annotations
import streamlit as st


def set_whatif_hint(hint: dict):
    st.session_state["whatif_hint"] = hint


def pop_whatif_hint():
    return st.session_state.pop("whatif_hint", None)


def get_whatif_hint():
    return st.session_state.get("whatif_hint")
