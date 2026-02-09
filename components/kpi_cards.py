"""
COPPER POC - KPI metric card wrappers.
"""

from typing import Dict, List

import streamlit as st


def render_kpi_row(kpis: List[Dict]) -> None:
    """
    Render a row of KPI cards.
    Each kpi dict: {"label": str, "value": str/number, "delta": str (optional), "delta_color": str (optional)}
    """
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            delta = kpi.get("delta")
            delta_color = kpi.get("delta_color", "normal")
            col.metric(
                label=kpi["label"],
                value=kpi["value"],
                delta=delta,
                delta_color=delta_color,
            )


def format_currency(value):
    """Format number as currency."""
    if value >= 1_000_000_000:
        return f"${value/1e9:.1f}B"
    elif value >= 1_000_000:
        return f"${value/1e6:.1f}M"
    elif value >= 1_000:
        return f"${value/1e3:.1f}K"
    return f"${value:,.0f}"


def format_number(value):
    """Format as integer with commas."""
    return f"{int(value):,}"
