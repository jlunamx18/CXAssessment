"""
Operadores — Driver performance page.
Uses get_operadores_performance() with real driver names from catalog.
All charts show nombreChofer on axes, not numeric IDs.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_operadores_performance
from theme import apply_theme, sidebar_header

st.set_page_config(
    page_title="Operadores · Transport Analytics",
    page_icon="👤",
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

    fecha_inicio = st.date_input("Fecha inicio", value=primer_dia_mes, key="op_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,            key="op_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    top_n = st.slider("Top N operadores a mostrar", min_value=5, max_value=50, value=20, step=5)

    metrica_orden = st.selectbox(
        "Ordenar por",
        options=["Ingresos totales", "Viajes únicos", "Millas totales", "Rev/Milla promedio"],
        index=0,
    )

    if st.button("Actualizar datos", key="op_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("👤 Desempeño de Operadores")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando estadísticas de operadores..."):
    df = get_operadores_performance(fi_str, ff_str)

if df.empty:
    st.warning("No se encontraron datos de operadores para el período seleccionado.")
    st.stop()

# Fill missing names
df["nombreChofer"] = df["nombreChofer"].fillna("Sin nombre").replace("", "Sin nombre")
df["etiqueta"] = df.apply(
    lambda r: r["nombreChofer"] if r["nombreChofer"] not in ("Sin nombre", "")
    else f"Chofer ID {r['idChofer1']}",
    axis=1,
)

# ── Sort by selected metric ───────────────────────────────────────────────────
sort_col_map = {
    "Ingresos totales":    "total_revenue",
    "Viajes únicos":       "viajes_unicos",
    "Millas totales":      "total_miles",
    "Rev/Milla promedio":  "rev_por_milla",
}
sort_col = sort_col_map[metrica_orden]
df = df.sort_values(sort_col, ascending=False, na_position="last")
df_top = df.head(top_n).copy()

# ── Summary metrics ───────────────────────────────────────────────────────────
total_operadores = len(df)
total_viajes     = int(df["viajes_unicos"].sum())
total_miles      = float(df["total_miles"].fillna(0).sum())
total_revenue    = float(df["total_revenue"].fillna(0).sum())
total_honorarios = float(df["total_honorarios"].fillna(0).sum())
mejor_op         = df.iloc[0]["etiqueta"] if not df.empty else "N/A"

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Operadores activos", f"{total_operadores:,}")
col2.metric("Total viajes únicos", f"{total_viajes:,}")
col3.metric("Total millas", f"{total_miles:,.0f}")
col4.metric("Ingresos totales (USD)", f"${total_revenue:,.2f}")
col5.metric("Mejor por ingresos", mejor_op[:25] + ("..." if len(mejor_op) > 25 else ""))

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(f"Viajes únicos por operador (Top {top_n})")
    df_plot = df_top.sort_values("viajes_unicos", ascending=True)
    fig_viajes = px.bar(
        df_plot,
        x="viajes_unicos",
        y="etiqueta",
        orientation="h",
        text="viajes_unicos",
        labels={"viajes_unicos": "Viajes únicos", "etiqueta": "Operador"},
        color="viajes_unicos",
        color_continuous_scale="Blues",
        height=max(400, top_n * 24),
    )
    fig_viajes.update_traces(textposition="outside")
    fig_viajes.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=10),
        yaxis_title="",
    )
    st.plotly_chart(fig_viajes, use_container_width=True)

with col_right:
    st.subheader(f"Ingresos por operador (USD) — Top {top_n}")
    df_plot2 = df_top.sort_values("total_revenue", ascending=True)
    fig_rev = px.bar(
        df_plot2,
        x="total_revenue",
        y="etiqueta",
        orientation="h",
        text=df_plot2["total_revenue"].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "—"),
        labels={"total_revenue": "Ingresos (USD)", "etiqueta": "Operador"},
        color="total_revenue",
        color_continuous_scale="Greens",
        height=max(400, top_n * 24),
    )
    fig_rev.update_traces(textposition="outside")
    fig_rev.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=60),
        yaxis_title="",
    )
    st.plotly_chart(fig_rev, use_container_width=True)

col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader(f"Millas por operador (Top {top_n})")
    df_plot3 = df_top.sort_values("total_miles", ascending=True)
    fig_millas = px.bar(
        df_plot3,
        x="total_miles",
        y="etiqueta",
        orientation="h",
        text=df_plot3["total_miles"].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "—"),
        labels={"total_miles": "Millas", "etiqueta": "Operador"},
        color="total_miles",
        color_continuous_scale="Oranges",
        height=max(400, top_n * 24),
    )
    fig_millas.update_traces(textposition="outside")
    fig_millas.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=60),
        yaxis_title="",
    )
    st.plotly_chart(fig_millas, use_container_width=True)

with col_right2:
    st.subheader(f"Revenue por milla promedio — Top {top_n}")
    df_plot4 = df_top.sort_values("rev_por_milla", ascending=True)
    fig_rpm = px.bar(
        df_plot4,
        x="rev_por_milla",
        y="etiqueta",
        orientation="h",
        text=df_plot4["rev_por_milla"].apply(lambda x: f"${x:,.3f}" if pd.notna(x) else "—"),
        labels={"rev_por_milla": "Rev/Milla (USD)", "etiqueta": "Operador"},
        color="rev_por_milla",
        color_continuous_scale="RdYlGn",
        height=max(400, top_n * 24),
    )
    fig_rpm.update_traces(textposition="outside")
    fig_rpm.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=60),
        yaxis_title="",
    )
    st.plotly_chart(fig_rpm, use_container_width=True)

# ── Honorarios chart ──────────────────────────────────────────────────────────
st.subheader(f"Honorarios pagados por operador (Top {top_n})")
df_hon = df_top[df_top["total_honorarios"].fillna(0) > 0].sort_values("total_honorarios", ascending=True)
if not df_hon.empty:
    fig_hon = px.bar(
        df_hon,
        x="total_honorarios",
        y="etiqueta",
        orientation="h",
        text=df_hon["total_honorarios"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—"),
        labels={"total_honorarios": "Honorarios (USD)", "etiqueta": "Operador"},
        color="total_honorarios",
        color_continuous_scale="Purples",
        height=max(300, len(df_hon) * 28),
    )
    fig_hon.update_traces(textposition="outside")
    fig_hon.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=60),
        yaxis_title="",
    )
    st.plotly_chart(fig_hon, use_container_width=True)
else:
    st.info("Sin datos de honorarios para el período seleccionado.")

# ── Data table ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Tabla de desempeño por operador")

df_table = df[["etiqueta", "licenciaMX", "licenciaUS", "viajes_unicos", "total_miles",
               "total_revenue", "total_honorarios", "rev_por_milla"]].copy()

df_table["total_revenue"] = df_table["total_revenue"].apply(
    lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
)
df_table["total_honorarios"] = df_table["total_honorarios"].apply(
    lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
)
df_table["total_miles"] = df_table["total_miles"].apply(
    lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
)
df_table["rev_por_milla"] = df_table["rev_por_milla"].apply(
    lambda x: f"${x:,.3f}" if pd.notna(x) else "—"
)

df_table = df_table.rename(columns={
    "etiqueta":          "Operador",
    "licenciaMX":        "Licencia MX",
    "licenciaUS":        "Licencia US",
    "viajes_unicos":     "Viajes únicos",
    "total_miles":       "Millas",
    "total_revenue":     "Ingresos (USD)",
    "total_honorarios":  "Honorarios (USD)",
    "rev_por_milla":     "Rev/Milla (USD)",
})

st.dataframe(df_table, use_container_width=True, hide_index=True)
st.caption(
    f"Total: {total_operadores} operadores · "
    f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')} · "
    "Fuente: vwBI_trnViajes + vwBI_catChoferes"
)
