"""
Flota — Fleet utilization page.
Utilization levels: >= 60% Alto, 35-59% Medio, < 35% Bajo.
All catalog units shown; zero-activity units listed for validation.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_flota_utilizacion, get_unidades_catalogo
from theme import (
    apply_theme, sidebar_header, page_header, kpi_cards,
    panel_header, insight,
    GREEN_PRIMARY, RED, AMBER, BLUE, TEAL, GRAY, PLOTLY_LAYOUT, BUS_COLORS, CHART_COLORS,
)

st.set_page_config(page_title="Flota · Transport Analytics", page_icon="🚌", layout="wide")
apply_theme()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_header()
    st.divider()
    st.markdown("**Filtros**")

    hoy            = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1)
    fecha_inicio   = st.date_input("Fecha inicio", value=primer_dia_mes, key="flota_fi")
    fecha_fin      = st.date_input("Fecha fin",    value=hoy,            key="flota_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="flota_refresh"):
        st.cache_data.clear()
        st.rerun()

fi_str         = fecha_inicio.strftime("%Y-%m-%d")
ff_str         = fecha_fin.strftime("%Y-%m-%d")
days_in_period = (fecha_fin - fecha_inicio).days + 1

# ── Page header ───────────────────────────────────────────────────────────────
page_header(
    "Utilización Operativa",
    "Utilización de Flota · Días Activos vs Capacidad",
    "Perfil por unidad — ingresos, millas, viajes y nivel de utilización",
    meta=f"<strong>{fecha_inicio.strftime('%d/%m/%Y')}</strong> — <strong>{fecha_fin.strftime('%d/%m/%Y')}</strong><br>{days_in_period} días del período",
)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando estadísticas de flota..."):
    df     = get_flota_utilizacion(fi_str, ff_str)
    df_cat = get_unidades_catalogo()

# ── Merge catalog to include units with zero activity ─────────────────────────
if not df_cat.empty:
    active_ids = set(df["idTransporte"].tolist()) if not df.empty else set()
    zero_rows  = []
    for _, crow in df_cat.iterrows():
        if crow["idTransporte"] not in active_ids:
            zero_rows.append({
                "idTransporte":   crow["idTransporte"],
                "nombreUnidad":   crow.get("nombre",   ""),
                "placasMx":       crow.get("placasMx", ""),
                "marca":          crow.get("marca",    ""),
                "modelo":         crow.get("modelo",   ""),
                "viajes_unicos":  0,
                "total_miles":    0.0,
                "total_revenue":  0.0,
                "total_expenses": 0.0,
                "dias_con_viaje": 0,
            })
    if zero_rows:
        df = pd.concat([df, pd.DataFrame(zero_rows)], ignore_index=True)

if df.empty:
    st.warning("No se encontraron datos de flota para el período seleccionado.")
    st.stop()

# ── Utilization calc ──────────────────────────────────────────────────────────
df["pct_utilizacion"] = (df["dias_con_viaje"].fillna(0) / days_in_period * 100).round(1)

def nivel_utilizacion(pct: float) -> str:
    if pct >= 60:  return "Alto"
    if pct >= 35:  return "Medio"
    if pct > 0:    return "Bajo"
    return "Sin datos"

df["nivel_utilizacion"] = df["pct_utilizacion"].apply(nivel_utilizacion)
df["margen"] = df["total_revenue"].fillna(0) - df["total_expenses"].fillna(0)
df["etiqueta"] = df.apply(
    lambda r: str(r["nombreUnidad"]) if pd.notna(r.get("nombreUnidad")) and str(r.get("nombreUnidad","")).strip()
    else f"Unidad {r['idTransporte']}",
    axis=1,
)
df = df.sort_values(["viajes_unicos","total_revenue"], ascending=[False,False]).reset_index(drop=True)

# ── Summary KPIs ──────────────────────────────────────────────────────────────
total_unidades   = len(df)
unidades_activas = int((df["viajes_unicos"] > 0).sum())
unidades_sin_op  = total_unidades - unidades_activas
total_viajes     = int(df["viajes_unicos"].sum())
total_miles      = float(df["total_miles"].fillna(0).sum())
total_revenue    = float(df["total_revenue"].fillna(0).sum())
avg_util         = float(df[df["pct_utilizacion"] > 0]["pct_utilizacion"].mean()) if (df["pct_utilizacion"] > 0).any() else 0.0

kpi_cards([
    {"label": "Total unidades",     "value": str(total_unidades),
     "sub": f"{unidades_sin_op} sin operación" if unidades_sin_op else "Todas activas",
     "delta": f"{unidades_sin_op} sin operación" if unidades_sin_op else None,
     "delta_dir": "dn" if unidades_sin_op else ""},
    {"label": "Unidades activas",   "value": str(unidades_activas), "sub": "con viajes en el período"},
    {"label": "Viajes totales",     "value": f"{total_viajes:,}",   "color": "blue"},
    {"label": "Total millas",       "value": f"{total_miles:,.0f}", "color": "teal"},
    {"label": "Utilización prom.",  "value": f"{avg_util:.1f}%",
     "sub": "unidades con actividad",
     "delta": "vs std 75%", "delta_dir": "dn" if avg_util < 75 else "up",
     "color": "green" if avg_util >= 60 else ("amber" if avg_util >= 35 else "red")},
])

# ── Filter: show top N active units in charts ─────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
top_n = st.slider("Top N unidades en gráficas", min_value=5, max_value=50, value=20, step=5, key="flota_topn")
df_top = df[df["viajes_unicos"] > 0].head(top_n).copy()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

NIVEL_COLOR_MAP = {"Alto": GREEN_PRIMARY, "Medio": AMBER, "Bajo": RED, "Sin datos": GRAY}

with col_left:
    panel_header("Ingresos por Unidad", f"Top {top_n} · USD")
    df_rev = df_top.sort_values("total_revenue", ascending=True)
    fig_rev = px.bar(
        df_rev, x="total_revenue", y="etiqueta", orientation="h",
        text=df_rev["total_revenue"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—"),
        labels={"total_revenue": "Ingresos (USD)", "etiqueta": "Unidad"},
        color="nivel_utilizacion", color_discrete_map=NIVEL_COLOR_MAP,
        height=max(350, top_n * 26),
    )
    fig_rev.update_traces(textposition="outside")
    fig_rev.update_layout(**PLOTLY_LAYOUT, yaxis_title="", coloraxis_showscale=False,
                          margin=dict(t=20,b=10,l=10,r=70))
    st.plotly_chart(fig_rev, use_container_width=True)

with col_right:
    panel_header("Utilización por Unidad", f"% días activos · {days_in_period} días período")
    df_ut = df[df["viajes_unicos"] > 0].sort_values("pct_utilizacion", ascending=True).head(top_n)
    fig_ut = px.bar(
        df_ut, x="pct_utilizacion", y="etiqueta", orientation="h",
        text=df_ut["pct_utilizacion"].apply(lambda x: f"{x:.1f}%"),
        labels={"pct_utilizacion": "% Utilización", "etiqueta": "Unidad"},
        color="nivel_utilizacion", color_discrete_map=NIVEL_COLOR_MAP,
        height=max(350, top_n * 26),
    )
    fig_ut.update_traces(textposition="outside")
    fig_ut.update_layout(**PLOTLY_LAYOUT, yaxis_title="", coloraxis_showscale=False,
                         margin=dict(t=20,b=10,l=10,r=70))
    st.plotly_chart(fig_ut, use_container_width=True)

# ── Viajes + Millas ───────────────────────────────────────────────────────────
col_l2, col_r2 = st.columns(2)

with col_l2:
    panel_header("Viajes Únicos", f"Top {top_n} · por unidad")
    df_vj = df_top.sort_values("viajes_unicos", ascending=True)
    fig_vj = px.bar(
        df_vj, x="viajes_unicos", y="etiqueta", orientation="h", text="viajes_unicos",
        labels={"viajes_unicos":"Viajes", "etiqueta":"Unidad"},
        color_discrete_sequence=[BLUE],
        height=max(350, top_n * 26),
    )
    fig_vj.update_traces(textposition="outside")
    fig_vj.update_layout(**PLOTLY_LAYOUT, yaxis_title="", margin=dict(t=20,b=10,l=10,r=60))
    st.plotly_chart(fig_vj, use_container_width=True)

with col_r2:
    panel_header("Millas por Unidad", f"Top {top_n}")
    df_mil = df_top.sort_values("total_miles", ascending=True)
    fig_mil = px.bar(
        df_mil, x="total_miles", y="etiqueta", orientation="h",
        text=df_mil["total_miles"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0"),
        labels={"total_miles":"Millas", "etiqueta":"Unidad"},
        color_discrete_sequence=[TEAL],
        height=max(350, top_n * 26),
    )
    fig_mil.update_traces(textposition="outside")
    fig_mil.update_layout(**PLOTLY_LAYOUT, yaxis_title="", margin=dict(t=20,b=10,l=10,r=70))
    st.plotly_chart(fig_mil, use_container_width=True)

# ── Full utilization table ────────────────────────────────────────────────────
st.divider()
panel_header("Tabla de Utilización", f"Todas las unidades · {days_in_period} días · ≥60% Alto · 35-59% Medio · <35% Bajo · ⚫ Sin datos")

df_table = df[["etiqueta","placasMx","marca","modelo","viajes_unicos","total_miles",
               "total_revenue","total_expenses","margen","dias_con_viaje",
               "pct_utilizacion","nivel_utilizacion"]].copy()

NIVEL_ICON = {"Alto": "🟢", "Medio": "🟡", "Bajo": "🔴", "Sin datos": "⚫"}
df_table["nivel_utilizacion"] = df_table["nivel_utilizacion"].apply(
    lambda n: f"{NIVEL_ICON.get(n,'⚫')} {n}"
)
for c in ["total_revenue","total_expenses","margen"]:
    df_table[c] = df_table[c].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
df_table["total_miles"]       = df_table["total_miles"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—")
df_table["pct_utilizacion"]   = df_table["pct_utilizacion"].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "—")

df_table = df_table.rename(columns={
    "etiqueta":"Unidad","placasMx":"Placas MX","marca":"Marca","modelo":"Modelo",
    "viajes_unicos":"Viajes","total_miles":"Millas","total_revenue":"Ingresos (USD)",
    "total_expenses":"Gastos (USD)","margen":"Margen (USD)","dias_con_viaje":"Días c/viaje",
    "pct_utilizacion":"% Util","nivel_utilizacion":"Nivel",
})

st.dataframe(df_table, use_container_width=True, hide_index=True)
st.caption(
    f"{total_unidades} unidades ({unidades_activas} con operación, {unidades_sin_op} sin operación) · "
    f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')} · "
    "Fuente: vwBI_trnViajes + vwBI_trnTransporte"
)

# ── Zero-activity units alert ─────────────────────────────────────────────────
df_sin_op = df[df["viajes_unicos"] == 0].copy()
if not df_sin_op.empty:
    st.divider()
    insight(
        f"Sin operación identificada — {len(df_sin_op)} unidades",
        "Estas unidades están en catálogo pero <strong>no tienen viajes registrados</strong> en el período. "
        "El responsable debe validar: inactivas, en mantenimiento, sin asignación o fuera de ruta.",
        kind="d",
    )
    df_sin_table = df_sin_op[["etiqueta","placasMx","marca","modelo"]].rename(columns={
        "etiqueta":"Unidad","placasMx":"Placas MX","marca":"Marca","modelo":"Modelo",
    })
    st.dataframe(df_sin_table, use_container_width=True, hide_index=True)
