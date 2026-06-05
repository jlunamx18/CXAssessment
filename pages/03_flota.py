"""
Flota — Fleet utilization page.
Uses get_flota_utilizacion() with real unit names from catalog.
Utilization levels: >= 60% Alto, 35-59% Medio, < 35% Bajo.
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
from theme import apply_theme, sidebar_header

st.set_page_config(
    page_title="Flota · Transport Analytics",
    page_icon="🚌",
    layout="wide",
)
apply_theme()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_header()
    st.divider()
    st.markdown("**Filtros**")

    hoy = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1)

    fecha_inicio = st.date_input("Fecha inicio", value=primer_dia_mes, key="flota_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,            key="flota_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    top_n = st.slider("Top N unidades a mostrar en gráficas", min_value=5, max_value=50, value=20, step=5)

    if st.button("Actualizar datos", key="flota_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🚌 Utilización de Flota")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando estadísticas de flota..."):
    df       = get_flota_utilizacion(fi_str, ff_str)
    df_cat   = get_unidades_catalogo()

# ── Merge catalog to add units with zero activity ─────────────────────────────
if not df_cat.empty:
    active_ids = set(df["idTransporte"].tolist()) if not df.empty else set()
    zero_rows = []
    for _, crow in df_cat.iterrows():
        if crow["idTransporte"] not in active_ids:
            zero_rows.append({
                "idTransporte":  crow["idTransporte"],
                "nombreUnidad":  crow.get("nombre", ""),
                "placasMx":      crow.get("placasMx", ""),
                "marca":         crow.get("marca", ""),
                "modelo":        crow.get("modelo", ""),
                "viajes_unicos": 0,
                "total_miles":   0.0,
                "total_revenue": 0.0,
                "total_expenses":0.0,
                "dias_con_viaje":0,
            })
    if zero_rows:
        df = pd.concat([df, pd.DataFrame(zero_rows)], ignore_index=True)

if df.empty:
    st.warning("No se encontraron datos de flota para el período seleccionado.")
    st.stop()

# ── Calculate utilization ─────────────────────────────────────────────────────
days_in_period = (fecha_fin - fecha_inicio).days + 1

df["pct_utilizacion"] = (
    df["dias_con_viaje"].fillna(0) / days_in_period * 100
).round(1)

def nivel_utilizacion(pct: float) -> str:
    if pct >= 60:
        return "Alto"
    elif pct >= 35:
        return "Medio"
    elif pct > 0:
        return "Bajo"
    else:
        return "Sin datos"

df["nivel_utilizacion"] = df["pct_utilizacion"].apply(nivel_utilizacion)
df["margen"] = df["total_revenue"].fillna(0) - df["total_expenses"].fillna(0)

# Display label: use nombreUnidad if available, else idTransporte
df["etiqueta"] = df.apply(
    lambda r: str(r["nombreUnidad"]) if pd.notna(r.get("nombreUnidad")) and str(r.get("nombreUnidad", "")).strip()
    else f"Unidad {r['idTransporte']}",
    axis=1,
)

# Sort: active units by revenue desc, zero-activity at bottom
df = df.sort_values(["viajes_unicos", "total_revenue"], ascending=[False, False]).reset_index(drop=True)
df_top = df[df["viajes_unicos"] > 0].head(top_n).copy()

# ── Summary metrics ───────────────────────────────────────────────────────────
total_unidades   = len(df)
unidades_activas = int((df["viajes_unicos"] > 0).sum())
unidades_sin_op  = total_unidades - unidades_activas
total_viajes     = int(df["viajes_unicos"].sum())
total_miles      = float(df["total_miles"].fillna(0).sum())
total_revenue    = float(df["total_revenue"].fillna(0).sum())
total_expenses   = float(df["total_expenses"].fillna(0).sum())
avg_utilizacion  = float(df[df["pct_utilizacion"] > 0]["pct_utilizacion"].mean()) if (df["pct_utilizacion"] > 0).any() else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total unidades", f"{total_unidades:,}", delta=f"{unidades_sin_op} sin operación" if unidades_sin_op else None, delta_color="inverse")
col2.metric("Total viajes únicos", f"{total_viajes:,}")
col3.metric("Total millas", f"{total_miles:,.0f}")
col4.metric("Ingresos totales (USD)", f"${total_revenue:,.2f}")
col5.metric("Utilización promedio", f"{avg_utilizacion:.1f}%")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(f"Ingresos por unidad (Top {top_n})")
    df_rev = df_top.sort_values("total_revenue", ascending=True)
    fig_rev = px.bar(
        df_rev,
        x="total_revenue",
        y="etiqueta",
        orientation="h",
        text=df_rev["total_revenue"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—"),
        labels={"total_revenue": "Ingresos (USD)", "etiqueta": "Unidad"},
        color="total_revenue",
        color_continuous_scale="RdYlGn",
        height=max(400, top_n * 24),
    )
    fig_rev.update_traces(textposition="outside")
    fig_rev.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=60),
        yaxis_title="",
    )
    st.plotly_chart(fig_rev, use_container_width=True)

with col_right:
    st.subheader(f"Millas por unidad (Top {top_n})")
    df_mil = df_top.sort_values("total_miles", ascending=True)
    fig_mil = px.bar(
        df_mil,
        x="total_miles",
        y="etiqueta",
        orientation="h",
        text=df_mil["total_miles"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "0"),
        labels={"total_miles": "Millas", "etiqueta": "Unidad"},
        color="total_miles",
        color_continuous_scale="Blues",
        height=max(400, top_n * 24),
    )
    fig_mil.update_traces(textposition="outside")
    fig_mil.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=60),
        yaxis_title="",
    )
    st.plotly_chart(fig_mil, use_container_width=True)

# ── Viajes por unidad ─────────────────────────────────────────────────────────
st.subheader(f"Viajes únicos por unidad (Top {top_n})")
df_vj = df_top.sort_values("viajes_unicos", ascending=True)
fig_vj = px.bar(
    df_vj,
    x="viajes_unicos",
    y="etiqueta",
    orientation="h",
    text="viajes_unicos",
    labels={"viajes_unicos": "Viajes únicos", "etiqueta": "Unidad"},
    color="viajes_unicos",
    color_continuous_scale="Greens",
    height=max(400, top_n * 24),
)
fig_vj.update_traces(textposition="outside")
fig_vj.update_layout(
    coloraxis_showscale=False,
    margin=dict(t=20, b=10, l=10, r=60),
    yaxis_title="",
)
st.plotly_chart(fig_vj, use_container_width=True)

# ── Data table with utilization level ─────────────────────────────────────────
st.divider()
st.subheader("Tabla de utilización por unidad")
st.caption(
    f"Período de {days_in_period} días · "
    "Nivel: >= 60% Alto (verde), 35-59% Medio (amarillo), < 35% Bajo (rojo), ⚫ Sin datos (requiere validación)"
)

df_table = df[[
    "etiqueta", "placasMx", "marca", "modelo",
    "viajes_unicos", "total_miles", "total_revenue", "total_expenses",
    "margen", "dias_con_viaje", "pct_utilizacion", "nivel_utilizacion",
]].copy()

NIVEL_COLOR = {"Alto": "🟢", "Medio": "🟡", "Bajo": "🔴", "Sin datos": "⚫"}
df_table["nivel_utilizacion"] = df_table["nivel_utilizacion"].apply(
    lambda n: f"{NIVEL_COLOR.get(n, '⚫')} {n}"
)

for col_name in ["total_revenue", "total_expenses", "margen"]:
    df_table[col_name] = df_table[col_name].apply(
        lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
    )
df_table["total_miles"] = df_table["total_miles"].apply(
    lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
)
df_table["pct_utilizacion"] = df_table["pct_utilizacion"].apply(
    lambda x: f"{x:.1f}%" if pd.notna(x) else "—"
)

df_table = df_table.rename(columns={
    "etiqueta":          "Unidad",
    "placasMx":          "Placas MX",
    "marca":             "Marca",
    "modelo":            "Modelo",
    "viajes_unicos":     "Viajes únicos",
    "total_miles":       "Millas",
    "total_revenue":     "Ingresos (USD)",
    "total_expenses":    "Gastos (USD)",
    "margen":            "Margen (USD)",
    "dias_con_viaje":    "Días con viaje",
    "pct_utilizacion":   "% Utilización",
    "nivel_utilizacion": "Nivel",
})

st.dataframe(df_table, use_container_width=True, hide_index=True)
st.caption(
    f"Total: {total_unidades} unidades ({unidades_activas} con operación, {unidades_sin_op} sin operación) · "
    f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')} · "
    "Fuente: vwBI_trnViajes + vwBI_trnTransporte"
)

# ── Units with no operation (alert panel) ─────────────────────────────────────
df_sin_op = df[df["viajes_unicos"] == 0].copy()
if not df_sin_op.empty:
    st.divider()
    st.subheader(f"⚫ Unidades sin operación identificada ({len(df_sin_op)})")
    st.caption("Estas unidades están en catálogo pero no tienen viajes registrados en el período. El responsable debe validar.")
    df_sin_op_table = df_sin_op[["etiqueta", "placasMx", "marca", "modelo"]].rename(columns={
        "etiqueta": "Unidad", "placasMx": "Placas MX", "marca": "Marca", "modelo": "Modelo",
    })
    st.dataframe(df_sin_op_table, use_container_width=True, hide_index=True)
