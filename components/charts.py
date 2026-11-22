"""Plotly charts following the project's data-viz rules.

* Scenario type = categorical identity -> validated 3-hue palette in fixed order.
* Priority      = ordinal magnitude    -> single navy ramp (dark = High).
* Thin bars, value labels at the bar tip, hairline recessive grid, hover on every mark.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

import plotly.graph_objects as go

from config import PRIORITIES, SCENARIO_TYPES

SCENARIO_COLORS = {"Positive": "#2563EB", "Negative": "#D9822B", "Edge Case": "#0F9F8C"}
PRIORITY_COLORS = {"High": "#14213D", "Medium": "#3E64A8", "Low": "#8FA8D6"}
TEXT, MUTED, GRID = "#172033", "#64748B", "#EDF1F7"
FONT = "Inter, system-ui, sans-serif"


def _layout(fig: go.Figure, height: int) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=8, r=40, t=8, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=FONT, size=13, color=TEXT), showlegend=False, bargap=0.45,
        hoverlabel=dict(bgcolor="#14213D", bordercolor="#14213D", font=dict(color="#fff", family=FONT, size=12)),
    )
    return fig


def horizontal_bars(counts: dict[str, int], order: tuple[str, ...], colors: dict[str, str],
                    noun: str = "test cases") -> go.Figure:
    labels = list(reversed(order))
    values = [counts.get(k, 0) for k in labels]
    total = sum(values) or 1
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=[colors[k] for k in labels], cornerradius=4, line=dict(width=0)),
        text=[f"{v}  ·  {v / total:.0%}" for v in values], textposition="outside",
        textfont=dict(color=TEXT, size=12), cliponaxis=False, width=0.5,
        hovertemplate="<b>%{y}</b><br>%{x} " + noun + "<extra></extra>",
    ))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False, showticklabels=False,
                     range=[0, max(values + [1]) * 1.3], fixedrange=True)
    fig.update_yaxes(showgrid=False, tickfont=dict(color=MUTED, size=13), fixedrange=True, ticksuffix="  ")
    return _layout(fig, 210)


def scenario_chart(counts: dict[str, int]) -> go.Figure:
    return horizontal_bars(counts, SCENARIO_TYPES, SCENARIO_COLORS)


def priority_chart(counts: dict[str, int]) -> go.Figure:
    return horizontal_bars(counts, PRIORITIES, PRIORITY_COLORS)


def activity_chart(timeline: list[dict[str, Any]]) -> go.Figure:
    timeline = timeline[-14:]  # last 14 active days
    days = [datetime.strptime(t["day"], "%Y-%m-%d").strftime("%d %b") for t in timeline]
    cases = [t["cases"] for t in timeline]
    sessions = [t["sessions"] for t in timeline]
    fig = go.Figure(go.Bar(
        x=days, y=cases, marker=dict(color="#2563EB", cornerradius=4), customdata=sessions,
        width=min(0.6, 0.05 * max(len(days), 1)),  # ~28px bars regardless of day count
        text=cases, textposition="outside", textfont=dict(color=TEXT, size=12), cliponaxis=False,
        hovertemplate="<b>%{x}</b><br>%{y} test cases<br>%{customdata} session(s)<extra></extra>",
    ))
    fig.update_xaxes(type="category", showgrid=False, tickfont=dict(color=MUTED), fixedrange=True)
    fig.update_yaxes(showgrid=True, gridcolor=GRID, zeroline=False, tickfont=dict(color=MUTED), fixedrange=True,
                     rangemode="tozero", range=[0, max(cases + [1]) * 1.25])
    fig = _layout(fig, 230)
    fig.update_layout(margin=dict(l=8, r=8, t=16, b=8))
    return fig
