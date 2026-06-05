"""
MLV Transport Analytics — Design System v2
Replicates BCG Professional palette and component structure from mlv_fleet_platform.html.
"""

from __future__ import annotations
import streamlit as st

# ── Palette ────────────────────────────────────────────────────────────────────
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

# ── Bus palette ────────────────────────────────────────────────────────────────
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

# ── Chart color sequences ──────────────────────────────────────────────────────
CHART_COLORS      = [BLUE, GREEN_PRIMARY, ORANGE, PURPLE, TEAL, RED, AMBER, FOREST, GRAY]
CHART_DIVERGING   = [RED, AMBER, GREEN_PALE, GREEN_PRIMARY]
CHART_GREEN_SCALE = [GREEN_BG, GREEN_PALE, GREEN_LIGHT, GREEN_PRIMARY]

# ── Plotly layout defaults ─────────────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    font          = dict(family="Arial, Helvetica, sans-serif", color=INK3, size=11),
    plot_bgcolor  = WHITE,
    paper_bgcolor = WHITE,
    margin        = dict(t=30, b=10, l=10, r=10),
    legend        = dict(font=dict(size=10, color=INK2), bgcolor="rgba(0,0,0,0)", borderwidth=0),
    xaxis         = dict(gridcolor="#EDEBE6", linecolor=BORDER, tickfont=dict(size=10, color=INK3)),
    yaxis         = dict(gridcolor="#EDEBE6", linecolor=BORDER, tickfont=dict(size=10, color=INK3)),
)

# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = f"""
<style>
/* Base */
html, body, [class*="css"] {{
    font-family: Arial, Helvetica, sans-serif !important;
    font-size: 13px;
}}
.stApp {{ background: {BG} !important; }}

/* Hide Streamlit chrome */
#MainMenu, footer, header {{ visibility: hidden; }}
.stDeployButton {{ display: none; }}
[data-testid="stToolbar"] {{ visibility: hidden; }}

/* Sidebar */
[data-testid="stSidebar"] {{
    background: {WHITE} !important;
    border-right: 1px solid {BORDER} !important;
}}
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label {{
    font-size: 11px !important; color: {INK2} !important;
}}
[data-testid="stSidebar"] hr {{ border-color: {BORDER} !important; }}

/* Headings */
h1 {{
    font-size: 20px !important; font-weight: 700 !important; color: {INK} !important;
    letter-spacing: -0.3px !important; border-bottom: 3px solid {GREEN_PRIMARY};
    padding-bottom: 10px; margin-bottom: 16px !important;
}}
h2 {{ font-size: 13px !important; font-weight: 700 !important; color: {INK} !important;
     text-transform: uppercase; letter-spacing: 0.09em; margin-top: 20px !important; }}
h3 {{ font-size: 12px !important; font-weight: 700 !important; color: {INK2} !important; }}

/* Streamlit metric (fallback styling) */
[data-testid="stMetric"] {{
    background: {WHITE} !important; border: 1px solid {BORDER} !important;
    border-top: 3px solid {GREEN_PRIMARY} !important;
    padding: 12px 14px !important; border-radius: 0 !important;
}}
[data-testid="stMetricLabel"] {{
    font-size: 8px !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.11em !important; color: {INK3} !important;
}}
[data-testid="stMetricValue"] {{
    font-size: 22px !important; font-weight: 700 !important;
    color: {INK} !important; letter-spacing: -0.4px !important;
}}
[data-testid="stMetricDelta"] {{ font-size: 10px !important; font-weight: 700 !important; }}

/* Dataframes */
[data-testid="stDataFrame"] thead th {{
    font-size: 8px !important; font-weight: 700 !important;
    text-transform: uppercase !important; letter-spacing: 0.09em !important;
    color: {INK3} !important; background: {BG2} !important;
    border-bottom: 2px solid {GREEN_PRIMARY} !important;
}}
[data-testid="stDataFrame"] td {{
    font-size: 11px !important; color: {INK2} !important;
    border-bottom: 1px solid #EDEBE6 !important;
}}

/* Buttons */
[data-testid="stButton"] button {{
    background: {GREEN_PRIMARY} !important; color: {WHITE} !important;
    border: none !important; border-radius: 0 !important;
    font-size: 9px !important; font-weight: 700 !important;
    letter-spacing: 0.06em !important; text-transform: uppercase !important;
    padding: 7px 14px !important;
}}
[data-testid="stButton"] button:hover {{ background: {GREEN_LIGHT} !important; }}

/* Selectboxes */
[data-testid="stSelectbox"] > div > div,
[data-testid="stDateInput"] input {{
    background: {BG2} !important; border: 1px solid {BORDER} !important;
    border-radius: 0 !important; font-size: 10px !important;
    font-weight: 700 !important; color: {INK} !important;
}}

/* Pills — filter-bar style buttons */
[data-testid="stPillsOptionContainer"] {{
    gap: 4px !important; flex-wrap: wrap !important;
}}
[data-testid="stPillsOptionContainer"] button {{
    font-size: 9px !important; font-weight: 700 !important;
    letter-spacing: .06em !important; text-transform: uppercase !important;
    padding: 4px 10px !important; border-radius: 0 !important;
    border: 1px solid {BORDER} !important;
    background: {WHITE} !important; color: {INK3} !important;
    transition: all .1s !important;
}}
[data-testid="stPillsOptionContainer"] button[aria-pressed="true"] {{
    background: {GREEN_PRIMARY} !important; color: {WHITE} !important;
    border-color: {GREEN_PRIMARY} !important;
}}
[data-testid="stPills"] label {{
    font-size: 9px !important; font-weight: 700 !important;
    letter-spacing: .12em !important; text-transform: uppercase !important;
    color: {INK4} !important;
}}

/* Radio as pills */
div[data-testid="stRadio"] > div[role="radiogroup"] {{
    display: flex !important; flex-direction: row !important;
    flex-wrap: wrap !important; gap: 4px !important;
}}
div[data-testid="stRadio"] > div[role="radiogroup"] label {{
    display: flex !important; align-items: center !important;
    padding: 4px 10px !important; border: 1px solid {BORDER} !important;
    background: {WHITE} !important; color: {INK3} !important;
    font-size: 9px !important; font-weight: 700 !important;
    letter-spacing: .06em !important; text-transform: uppercase !important;
    cursor: pointer !important; border-radius: 0 !important;
}}
div[data-testid="stRadio"] > div[role="radiogroup"] label:has(input:checked) {{
    background: {GREEN_PRIMARY} !important; color: {WHITE} !important;
    border-color: {GREEN_PRIMARY} !important;
}}
div[data-testid="stRadio"] > div[role="radiogroup"] input {{ display: none !important; }}
div[data-testid="stRadio"] > label {{
    font-size: 9px !important; font-weight: 700 !important;
    letter-spacing: .12em !important; text-transform: uppercase !important; color: {INK4} !important;
}}

/* Alert boxes */
[data-testid="stAlert"] {{
    border-radius: 0 !important; border-left-width: 4px !important; font-size: 11px !important;
}}

/* Divider */
hr {{ border-color: {BORDER} !important; margin: 16px 0 !important; }}

/* Expander */
[data-testid="stExpander"] {{
    border: 1px solid {BORDER} !important; border-radius: 0 !important; background: {WHITE} !important;
}}
[data-testid="stExpander"] summary {{
    font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: .06em !important; text-transform: uppercase !important; color: {INK2} !important;
}}

/* Caption */
[data-testid="stCaptionContainer"] {{ font-size: 9px !important; color: {INK4} !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width:4px; height:4px; }}
::-webkit-scrollbar-track {{ background: {BG2}; }}
::-webkit-scrollbar-thumb {{ background: {BORDER2}; }}

/* ── Custom HTML components (used via st.markdown) ── */

/* Sidebar brand */
.mlv-sidebar-header {{
    text-align: center; padding: 16px 0 20px 0;
    border-bottom: 1px solid {BORDER}; margin-bottom: 12px;
}}
.mlv-sidebar-header .brand {{
    font-size: 14px; font-weight: 700; color: {GREEN_PRIMARY}; letter-spacing: .04em;
}}
.mlv-sidebar-header .sub {{
    font-size: 9px; color: {INK4}; letter-spacing: .1em; text-transform: uppercase; margin-top: 2px;
}}

/* Page header */
.pgh {{
    display: flex; align-items: flex-end; justify-content: space-between;
    margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid {BORDER};
}}
.pe  {{ font-size:9px; font-weight:700; letter-spacing:.2em; text-transform:uppercase; color:{GREEN_PRIMARY}; margin-bottom:3px; }}
.pt  {{ font-size:18px; font-weight:700; color:{INK}; }}
.pd  {{ font-size:12px; color:{INK3}; margin-top:2px; }}
.pm  {{ font-size:11px; color:{INK3}; text-align:right; line-height:1.7; }}
.pm strong {{ color:{INK}; }}

/* KPI card */
.kc  {{ background:{WHITE}; border:1px solid {BORDER}; border-top:3px solid {GREEN_PRIMARY}; padding:12px 14px; margin-bottom:0; }}
.kc.r {{ border-top-color:{RED}; }}
.kc.a {{ border-top-color:{AMBER}; }}
.kc.b {{ border-top-color:{BLUE}; }}
.kc.t {{ border-top-color:{TEAL}; }}
.kl   {{ font-size:8px; font-weight:700; letter-spacing:.11em; text-transform:uppercase; color:{INK3}; margin-bottom:3px; }}
.kv   {{ font-size:22px; font-weight:700; color:{INK}; letter-spacing:-.4px; line-height:1.1; }}
.ks   {{ font-size:11px; color:{INK3}; margin-top:2px; }}
.kd   {{ font-size:10px; font-weight:700; margin-top:2px; }}
.kd.up {{ color:{GREEN_PRIMARY}; }}
.kd.dn {{ color:{RED}; }}
.kd.nt {{ color:{INK4}; }}

/* Panel */
.mlv-panel {{ background:{WHITE}; border:1px solid {BORDER}; padding:14px 16px; margin-bottom:12px; }}
.pl  {{ font-size:8px; font-weight:700; letter-spacing:.13em; text-transform:uppercase; color:{INK4}; margin-bottom:2px; }}
.ptl {{ font-size:12px; font-weight:700; color:{INK}; margin-bottom:10px; }}

/* Insight */
.ins {{ border-left:3px solid {GREEN_PRIMARY}; background:{GREEN_BG}; padding:9px 12px; margin-bottom:7px; }}
.ins.w {{ border-left-color:{AMBER}; background:#FFFBF0; }}
.ins.d {{ border-left-color:{RED};   background:#FFF5F5; }}
.ins.b {{ border-left-color:{BLUE};  background:#EFF6FC; }}
.inl   {{ font-size:8px; font-weight:700; letter-spacing:.14em; text-transform:uppercase; color:{GREEN_PRIMARY}; margin-bottom:2px; }}
.ins.w .inl {{ color:{AMBER}; }}
.ins.d .inl {{ color:{RED}; }}
.ins.b .inl {{ color:{BLUE}; }}
.ins p {{ font-size:11px; color:{INK2}; line-height:1.5; }}
.ins strong {{ color:{INK}; }}

/* Table */
.tbl {{ width:100%; border-collapse:collapse; font-size:11px; }}
.tbl th {{
    font-size:8px; font-weight:700; letter-spacing:.09em; text-transform:uppercase;
    color:{INK3}; text-align:left; padding:7px 9px;
    border-bottom:2px solid {GREEN_PRIMARY}; background:{BG2}; white-space:nowrap;
}}
.tbl td {{ padding:7px 9px; border-bottom:1px solid #EDEBE6; color:{INK2}; vertical-align:middle; }}
.tbl tr:last-child td {{ border-bottom:none; }}
.tbl tr:hover td {{ background:{GREEN_BG}; }}
.tbl td.n {{ text-align:right; font-weight:600; }}
.tbl td.g {{ color:{GREEN_PRIMARY}; font-weight:700; text-align:right; }}
.tbl td.a {{ color:{AMBER}; font-weight:700; text-align:right; }}
.tbl td.r {{ color:{RED}; font-weight:700; text-align:right; }}

/* Util badge */
.util-badge {{ display:inline-flex; align-items:center; gap:4px; padding:2px 8px;
    font-size:9px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; }}
.util-badge.high   {{ background:{GREEN_PALE}; color:{GREEN_PRIMARY}; }}
.util-badge.medium {{ background:#FFF5E0; color:{ORANGE}; }}
.util-badge.low    {{ background:#FFF0F0; color:{RED}; }}
.util-badge.none   {{ background:#F0F0F0; color:{INK3}; }}

/* Bus dot */
.bus-dot {{ display:inline-flex; align-items:center; gap:5px; font-size:11px; font-weight:700; }}
.bus-dot-circle {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}

/* Filter bar */
.fbar {{
    display:flex; align-items:center; gap:8px; padding:8px 12px;
    background:{WHITE}; border:1px solid {BORDER}; flex-wrap:wrap; margin-bottom:14px;
}}
.fbar-label {{ font-size:9px; font-weight:700; letter-spacing:.12em; text-transform:uppercase; color:{INK4}; white-space:nowrap; margin-right:4px; }}
.fbar-sep {{ width:1px; background:{BORDER}; height:22px; margin:0 6px; }}
</style>
"""


def apply_theme() -> None:
    """Inject the full MLV design system CSS."""
    st.markdown(_CSS, unsafe_allow_html=True)


def sidebar_header(title: str = "Transport Analytics", subtitle: str = "México — USA Cross-Border") -> None:
    st.markdown(
        f"""<div class="mlv-sidebar-header">
            <div style="font-size:2rem;margin-bottom:4px;">🚛</div>
            <div class="brand">{title}</div>
            <div class="sub">{subtitle}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def page_header(eyebrow: str, title: str, desc: str = "", meta: str = "") -> None:
    """Render BCG-style page header (.pgh/.pe/.pt/.pd)."""
    desc_h = f'<div class="pd">{desc}</div>' if desc else ""
    meta_h = f'<div class="pm">{meta}</div>' if meta else ""
    st.markdown(
        f"""<div class="pgh">
            <div><div class="pe">{eyebrow}</div><div class="pt">{title}</div>{desc_h}</div>
            {meta_h}
        </div>""",
        unsafe_allow_html=True,
    )


def panel_header(label: str, title: str = "") -> None:
    """Render chart panel eyebrow + title (.pl/.ptl)."""
    title_h = f'<div class="ptl">{title}</div>' if title else ""
    st.markdown(f'<div class="pl">{label}</div>{title_h}', unsafe_allow_html=True)


def kpi_cards(cards: list[dict]) -> None:
    """Render a horizontal row of BCG KPI cards.

    Each dict: label, value, sub="", delta="", delta_dir="up"|"dn"|"nt", color="green"|"red"|"amber"|"blue"|"teal"
    """
    color_cls = {"green": "", "red": " r", "amber": " a", "blue": " b", "teal": " t"}
    cols = st.columns(len(cards))
    for col, card in zip(cols, cards):
        cls   = color_cls.get(card.get("color", "green"), "")
        lbl   = card.get("label", "")
        val   = card.get("value", "—")
        sub   = card.get("sub", "")
        dlt   = card.get("delta", "")
        ddir  = card.get("delta_dir", "")
        sub_h = f'<div class="ks">{sub}</div>' if sub else ""
        if dlt:
            arrow = {"up": "▲ ", "dn": "▼ "}.get(ddir, "→ ")
            dlt_h = f'<div class="kd {ddir}">{arrow}{dlt}</div>'
        else:
            dlt_h = ""
        col.markdown(
            f'<div class="kc{cls}"><div class="kl">{lbl}</div>'
            f'<div class="kv">{val}</div>{sub_h}{dlt_h}</div>',
            unsafe_allow_html=True,
        )


def insight(label: str, body: str, kind: str = "") -> None:
    """Render insight card. kind: ''|'w'|'d'|'b'"""
    cls = f" {kind}" if kind in ("w", "d", "b") else ""
    st.markdown(
        f'<div class="ins{cls}"><div class="inl">{label}</div><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def html_table(headers: list[str], rows: list[list], col_classes: list[str] | None = None) -> None:
    """Render a custom HTML table matching .tbl style."""
    th_html = "".join(f"<th>{h}</th>" for h in headers)
    rows_html = ""
    for row in rows:
        tds = ""
        for i, cell in enumerate(row):
            cls = col_classes[i] if col_classes and i < len(col_classes) else ""
            cls_attr = f' class="{cls}"' if cls else ""
            tds += f"<td{cls_attr}>{cell}</td>"
        rows_html += f"<tr>{tds}</tr>"
    st.markdown(
        f'<div style="overflow-x:auto"><table class="tbl">'
        f'<thead><tr>{th_html}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True,
    )


# ── Backward-compat aliases ────────────────────────────────────────────────────

def section_header(title: str, subtitle: str = "") -> None:
    sub_h = f'<div style="font-size:10px;color:{INK3};">{subtitle}</div>' if subtitle else ""
    st.markdown(
        f'<div style="display:flex;align-items:flex-end;justify-content:space-between;'
        f'padding-bottom:10px;border-bottom:1px solid {BORDER};margin-bottom:14px;">'
        f'<div><div class="pe">{title}</div>{sub_h}</div></div>',
        unsafe_allow_html=True,
    )


def insight_card(title: str, body: str, level: str = "info") -> None:
    kind = {"warn": "w", "alert": "d", "info": "b"}.get(level, "")
    insight(title, body, kind)


def util_badge(level: str) -> str:
    labels = {"high": "Alto", "medium": "Medio", "low": "Bajo", "none": "Sin datos"}
    icons  = {"high": "●", "medium": "●", "low": "●", "none": "○"}
    return (
        f'<span class="util-badge {level}">'
        f'{icons.get(level, "○")} {labels.get(level, level)}'
        f'</span>'
    )


def bus_color(bus_code: str) -> str:
    return BUS_COLORS.get(str(bus_code).strip(), GRAY)
