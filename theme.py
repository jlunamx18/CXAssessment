"""
MLV Transport Analytics — Design System
Based on the BCG Professional palette from mlv_fleet_platform.html.

Usage in any page:
    from theme import apply_theme, BUS_COLORS, CHART_COLORS
    apply_theme()
"""

from __future__ import annotations
import streamlit as st

# ── Palette ───────────────────────────────────────────────────────────────────
GREEN_PRIMARY = "#00823B"
GREEN_LIGHT   = "#00A651"
GREEN_PALE    = "#DCEFE5"
GREEN_BG      = "#F0F8F3"

BLUE          = "#005587"
TEAL          = "#00A0C6"
PURPLE        = "#7B5EA7"
ORANGE        = "#D4460A"
AMBER         = "#F5A800"
RED           = "#C8102E"
FOREST        = "#3D8C40"
GRAY          = "#A8A8A8"

INK           = "#1A1A2E"
INK2          = "#3D3D3D"
INK3          = "#6B6B6B"
INK4          = "#A8A8A8"

BG            = "#F0EEE9"
BG2           = "#F5F5F0"
WHITE         = "#FFFFFF"
BORDER        = "#DDDBD6"
BORDER2       = "#C8C5BE"

# ── Bus palette (one fixed color per unit) ────────────────────────────────────
BUS_COLORS: dict[str, str] = {
    "0903": BLUE,
    "0914": GREEN_PRIMARY,
    "0925": ORANGE,
    "1667": PURPLE,
    "5391": GRAY,
    "8544": TEAL,
    "9552": RED,
    "9900": AMBER,
    "9907": FOREST,
}

# ── Chart color sequences ─────────────────────────────────────────────────────
CHART_COLORS = [BLUE, GREEN_PRIMARY, ORANGE, PURPLE, TEAL, RED, AMBER, FOREST, GRAY]
CHART_DIVERGING = [RED, AMBER, GREEN_PALE, GREEN_PRIMARY]
CHART_GREEN_SCALE = [GREEN_BG, GREEN_PALE, GREEN_LIGHT, GREEN_PRIMARY]

# ── Plotly layout defaults ────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    font=dict(family="Arial, Helvetica, sans-serif", color=INK3, size=11),
    plot_bgcolor=WHITE,
    paper_bgcolor=WHITE,
    margin=dict(t=30, b=10, l=10, r=10),
    legend=dict(
        font=dict(size=10, color=INK2),
        bgcolor="rgba(0,0,0,0)",
        borderwidth=0,
    ),
    xaxis=dict(
        gridcolor="#EDEBE6",
        linecolor=BORDER,
        tickfont=dict(size=10, color=INK3),
    ),
    yaxis=dict(
        gridcolor="#EDEBE6",
        linecolor=BORDER,
        tickfont=dict(size=10, color=INK3),
    ),
)

# ── CSS injected into every page ─────────────────────────────────────────────
_CSS = """
<style>
/* ── Fonts & base ── */
html, body, [class*="css"] {
    font-family: Arial, Helvetica, sans-serif !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #FFFFFF !important;
    border-right: 1px solid #DDDBD6 !important;
}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label {
    font-size: 11px !important;
    color: #3D3D3D !important;
}
[data-testid="stSidebar"] hr {
    border-color: #DDDBD6 !important;
}

/* ── Main header / title ── */
h1 {
    font-size: 20px !important;
    font-weight: 700 !important;
    color: #1A1A2E !important;
    letter-spacing: -0.3px !important;
    border-bottom: 3px solid #00823B;
    padding-bottom: 10px;
    margin-bottom: 16px !important;
}
h2 {
    font-size: 13px !important;
    font-weight: 700 !important;
    color: #1A1A2E !important;
    text-transform: uppercase;
    letter-spacing: 0.09em;
    margin-top: 20px !important;
}
h3 {
    font-size: 12px !important;
    font-weight: 700 !important;
    color: #3D3D3D !important;
}

/* ── KPI metric cards ── */
[data-testid="stMetric"] {
    background: #FFFFFF !important;
    border: 1px solid #DDDBD6 !important;
    border-top: 3px solid #00823B !important;
    padding: 12px 14px !important;
    border-radius: 0 !important;
}
[data-testid="stMetricLabel"] {
    font-size: 8px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.11em !important;
    color: #6B6B6B !important;
}
[data-testid="stMetricValue"] {
    font-size: 22px !important;
    font-weight: 700 !important;
    color: #1A1A2E !important;
    letter-spacing: -0.4px !important;
}
[data-testid="stMetricDelta"] {
    font-size: 10px !important;
    font-weight: 700 !important;
}

/* ── Dataframes / tables ── */
[data-testid="stDataFrame"] thead th {
    font-size: 8px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    color: #6B6B6B !important;
    background: #F5F5F0 !important;
    border-bottom: 2px solid #00823B !important;
}
[data-testid="stDataFrame"] td {
    font-size: 11px !important;
    color: #3D3D3D !important;
    border-bottom: 1px solid #EDEBE6 !important;
}

/* ── Buttons ── */
[data-testid="stButton"] button {
    background: #00823B !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 0 !important;
    font-size: 9px !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    padding: 7px 14px !important;
}
[data-testid="stButton"] button:hover {
    background: #00A651 !important;
}

/* ── Selectboxes & inputs ── */
[data-testid="stSelectbox"] > div > div,
[data-testid="stDateInput"] input {
    background: #F5F5F0 !important;
    border: 1px solid #DDDBD6 !important;
    border-radius: 0 !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    color: #1A1A2E !important;
}

/* ── Radio buttons ── */
[data-testid="stRadio"] label {
    font-size: 10px !important;
    font-weight: 700 !important;
    color: #3D3D3D !important;
}

/* ── Info / warning / error boxes ── */
[data-testid="stAlert"] {
    border-radius: 0 !important;
    border-left-width: 4px !important;
    font-size: 11px !important;
}

/* ── Divider ── */
hr {
    border-color: #DDDBD6 !important;
    margin: 16px 0 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    border: 1px solid #DDDBD6 !important;
    border-radius: 0 !important;
    background: #FFFFFF !important;
}
[data-testid="stExpander"] summary {
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
    color: #3D3D3D !important;
}

/* ── Caption ── */
[data-testid="stCaptionContainer"] {
    font-size: 9px !important;
    color: #A8A8A8 !important;
    letter-spacing: 0.04em !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] p {
    font-size: 10px !important;
    color: #6B6B6B !important;
}

/* ── Sidebar logo block ── */
.mlv-sidebar-header {
    text-align: center;
    padding: 16px 0 20px 0;
    border-bottom: 1px solid #DDDBD6;
    margin-bottom: 12px;
}
.mlv-sidebar-header .brand {
    font-size: 14px;
    font-weight: 700;
    color: #00823B;
    letter-spacing: 0.04em;
}
.mlv-sidebar-header .sub {
    font-size: 9px;
    color: #A8A8A8;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-top: 2px;
}

/* ── Page-level section header ── */
.section-header {
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding-bottom: 10px;
    border-bottom: 1px solid #DDDBD6;
    margin-bottom: 14px;
}
.section-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #1A1A2E;
}

/* ── Insight / alert cards ── */
.insight-card {
    background: #FFFFFF;
    border: 1px solid #DDDBD6;
    border-left: 4px solid #00823B;
    padding: 10px 14px;
    margin-bottom: 8px;
    font-size: 11px;
    color: #3D3D3D;
}
.insight-card.warn  { border-left-color: #F5A800; }
.insight-card.alert { border-left-color: #C8102E; }
.insight-card .ic-title {
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #6B6B6B;
    margin-bottom: 3px;
}

/* ── Util badge ── */
.util-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    font-size: 9px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.util-badge.high   { background: #DCEFE5; color: #00823B; }
.util-badge.medium { background: #FFF5E0; color: #D4460A; }
.util-badge.low    { background: #FFF0F0; color: #C8102E; }

/* ── Remove Streamlit branding ── */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
</style>
"""


def apply_theme() -> None:
    """Inject the MLV design system CSS into the current page."""
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_header(title: str = "Transport Analytics", subtitle: str = "México — USA Cross-Border") -> None:
    """Render the standard MLV sidebar header."""
    st.markdown(
        f"""
        <div class="mlv-sidebar-header">
            <div style="font-size:2rem; margin-bottom:4px;">🚛</div>
            <div class="brand">{title}</div>
            <div class="sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str = "") -> None:
    """Render a section header matching the HTML platform style."""
    sub_html = f'<div style="font-size:10px;color:{INK3};">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f"""
        <div class="section-header">
            <div>
                <div class="section-title">{title}</div>
                {sub_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def insight_card(title: str, body: str, level: str = "info") -> None:
    """Render an insight card (info / warn / alert)."""
    css_class = {"info": "", "warn": " warn", "alert": " alert"}.get(level, "")
    st.markdown(
        f"""
        <div class="insight-card{css_class}">
            <div class="ic-title">{title}</div>
            <div>{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def util_badge(level: str) -> str:
    """Return HTML for a utilization badge. level: 'high', 'medium', 'low'."""
    labels = {"high": "Alto", "medium": "Medio", "low": "Bajo"}
    icons  = {"high": "●", "medium": "●", "low": "●"}
    return (
        f'<span class="util-badge {level}">'
        f'{icons.get(level,"●")} {labels.get(level, level)}'
        f'</span>'
    )


def bus_color(bus_code: str) -> str:
    """Return the hex color assigned to a bus code."""
    return BUS_COLORS.get(str(bus_code).strip(), GRAY)
