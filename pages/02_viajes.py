"""
Viajes — Trips analysis page.
Uses get_viajes_dedup() with catalog name joins.
Shows real unit names and driver names (not IDs).
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import get_viajes_dedup

st.set_page_config(
    page_title="Viajes · Transport Analytics",
    page_icon="🗺️",
    layout="wide",
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style='text-align:center; padding: 1rem 0 1.5rem 0;'>
            <span style='font-size:2.5rem;'>🚛</span><br>
            <span style='font-size:1.3rem; font-weight:700; color:#1f77b4;'>
                Transport Analytics
            </span><br>
            <span style='font-size:0.75rem; color:#888;'>
                México — USA Cross-Border
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("**Filtros de fecha**")

    hoy = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1)

    fecha_inicio = st.date_input("Fecha inicio", value=primer_dia_mes, key="viajes_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,            key="viajes_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="viajes_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🗺️ Análisis de Viajes")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando viajes..."):
    df = get_viajes_dedup(fi_str, ff_str)

if df.empty:
    st.warning("No se encontraron viajes para el período seleccionado.")
    st.stop()

# Ensure datetime types
for col in ["fechaInicio", "fechaTermino"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# ── Sidebar filters (populated after data loads) ──────────────────────────────
with st.sidebar:
    st.markdown("**Filtros adicionales**")

    tipos_disponibles = sorted(df["tipoViaje"].dropna().unique().tolist())
    tipo_viaje_sel = st.multiselect(
        "Tipo de viaje",
        options=tipos_disponibles,
        default=[],
        placeholder="Todos los tipos",
        key="viajes_tipo",
    )

    activo_filtro = st.selectbox(
        "Estado del viaje",
        options=["Todos", "Activos", "Inactivos"],
        index=0,
        key="viajes_activo",
    )

# ── Apply filters ─────────────────────────────────────────────────────────────
df_filtered = df.copy()

if tipo_viaje_sel:
    df_filtered = df_filtered[df_filtered["tipoViaje"].isin(tipo_viaje_sel)]

if activo_filtro == "Activos":
    df_filtered = df_filtered[df_filtered["activo"] == True]
elif activo_filtro == "Inactivos":
    df_filtered = df_filtered[df_filtered["activo"] == False]

if df_filtered.empty:
    st.warning("No hay viajes que coincidan con los filtros seleccionados.")
    st.stop()

# ── Data quality: fechaTermino < fechaInicio ──────────────────────────────────
if "fechaInicio" in df_filtered.columns and "fechaTermino" in df_filtered.columns:
    mask_bad_dates = (
        df_filtered["fechaTermino"].notna() &
        df_filtered["fechaInicio"].notna() &
        (df_filtered["fechaTermino"] < df_filtered["fechaInicio"])
    )
    n_bad = int(mask_bad_dates.sum())
    if n_bad > 0:
        st.warning(
            f"Alerta de calidad de datos: {n_bad} viaje(s) tienen fechaTermino anterior a fechaInicio. "
            "Revise estos registros en la fuente.",
            icon="⚠️",
        )

# ── Calculate margen ──────────────────────────────────────────────────────────
df_filtered["margen"] = (
    df_filtered["totalRevenue"].fillna(0) - df_filtered["totalExpenses"].fillna(0)
)

# ── Summary metrics ───────────────────────────────────────────────────────────
total_viajes = len(df_filtered)
total_rev    = float(df_filtered["totalRevenue"].fillna(0).sum())
total_exp    = float(df_filtered["totalExpenses"].fillna(0).sum())
total_miles  = float(df_filtered["totalMiles"].fillna(0).sum())
margen_total = total_rev - total_exp
margen_pct   = (margen_total / total_rev * 100) if total_rev else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Viajes únicos", f"{total_viajes:,}")
col2.metric("Ingresos (USD)", f"${total_rev:,.2f}")
col3.metric("Gastos (USD)", f"${total_exp:,.2f}")
col4.metric("Margen (USD)", f"${margen_total:,.2f}", delta=f"{margen_pct:.1f}%")
col5.metric("Millas totales", f"{total_miles:,.0f}")

st.divider()

# ── Scatter: revenue vs expenses per trip ─────────────────────────────────────
st.subheader("Dispersión: Ingresos vs Gastos por viaje")

df_scatter = df_filtered[
    ["idViaje", "totalRevenue", "totalExpenses", "tipoViaje", "totalMiles",
     "nombreUnidad", "nombreChofer1", "margen"]
].dropna(subset=["totalRevenue", "totalExpenses"]).copy()

if not df_scatter.empty:
    df_scatter["idViaje"] = df_scatter["idViaje"].astype(str)
    df_scatter["nombreUnidad"] = df_scatter["nombreUnidad"].fillna("Sin unidad")
    df_scatter["nombreChofer1"] = df_scatter["nombreChofer1"].fillna("Sin chofer")

    max_val = max(
        df_scatter["totalRevenue"].max(),
        df_scatter["totalExpenses"].max(),
    )

    fig_sc = px.scatter(
        df_scatter,
        x="totalExpenses",
        y="totalRevenue",
        color="tipoViaje",
        hover_name="idViaje",
        hover_data={
            "nombreUnidad": True,
            "nombreChofer1": True,
            "totalMiles": ":.0f",
            "margen": ":$.2f",
        },
        labels={
            "totalExpenses": "Gastos (USD)",
            "totalRevenue": "Ingresos (USD)",
            "tipoViaje": "Tipo Viaje",
            "nombreUnidad": "Unidad",
            "nombreChofer1": "Chofer",
            "totalMiles": "Millas",
            "margen": "Margen (USD)",
        },
        opacity=0.75,
        height=420,
    )
    fig_sc.add_trace(
        go.Scatter(
            x=[0, max_val],
            y=[0, max_val],
            mode="lines",
            name="Punto de equilibrio",
            line=dict(dash="dash", color="gray", width=1),
        )
    )
    fig_sc.update_layout(margin=dict(t=20, b=10))
    st.plotly_chart(fig_sc, use_container_width=True)
else:
    st.info("No hay datos suficientes para el gráfico de dispersión.")

st.divider()

# ── Trips table ───────────────────────────────────────────────────────────────
st.subheader(f"Tabla de viajes ({total_viajes:,} registros)")

display_cols = [
    c for c in [
        "idViaje",
        "fechaInicio",
        "fechaTermino",
        "nombreUnidad",
        "placasUnidad",
        "nombreChofer1",
        "tipoViaje",
        "totalRevenue",
        "totalExpenses",
        "margen",
        "totalMiles",
        "tipoPago",
        "activo",
    ]
    if c in df_filtered.columns
]

df_display = df_filtered[display_cols].copy()

for dcol in ["fechaInicio", "fechaTermino"]:
    if dcol in df_display.columns:
        df_display[dcol] = df_display[dcol].dt.strftime("%d/%m/%Y %H:%M").fillna("")

for money_col in ["totalRevenue", "totalExpenses", "margen"]:
    if money_col in df_display.columns:
        df_display[money_col] = df_display[money_col].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )

if "totalMiles" in df_display.columns:
    df_display["totalMiles"] = df_display["totalMiles"].apply(
        lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
    )

rename_map = {
    "idViaje":       "ID Viaje",
    "fechaInicio":   "Fecha Inicio",
    "fechaTermino":  "Fecha Término",
    "nombreUnidad":  "Unidad",
    "placasUnidad":  "Placas",
    "nombreChofer1": "Chofer Principal",
    "tipoViaje":     "Tipo Viaje",
    "totalRevenue":  "Ingresos (USD)",
    "totalExpenses": "Gastos (USD)",
    "margen":        "Margen (USD)",
    "totalMiles":    "Millas",
    "tipoPago":      "Tipo Pago",
    "activo":        "Activo",
}
df_display = df_display.rename(
    columns={k: v for k, v in rename_map.items() if k in df_display.columns}
)

st.dataframe(df_display, use_container_width=True, hide_index=True)
st.caption(
    f"Mostrando {total_viajes:,} viajes únicos (deduplicados por idViaje) · "
    "Montos en USD · Fuente: vwBI_trnViajes"
)
