"""
Viajes — Trips analysis page.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_viajes

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
    st.markdown("**Filtros**")

    hoy = datetime.date.today()
    hace_30 = hoy - datetime.timedelta(days=30)

    fecha_inicio = st.date_input("Fecha inicio", value=hace_30, key="viajes_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,     key="viajes_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    tipo_viaje_filtro = st.multiselect(
        "Tipo de viaje",
        options=[],
        placeholder="Todos los tipos",
        key="viajes_tipo",
    )

    activo_filtro = st.selectbox(
        "Estado del viaje",
        options=["Todos", "Activos", "Inactivos"],
        index=0,
        key="viajes_activo",
    )

    if st.button("🔄 Actualizar datos", key="viajes_refresh"):
        st.cache_data.clear()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🗺️ Análisis de Viajes")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando viajes..."):
    df = get_viajes(fi_str, ff_str)

if df.empty:
    st.warning("No se encontraron viajes para el período seleccionado.")
    st.stop()

# ── Apply sidebar filters ─────────────────────────────────────────────────────
# Populate tipo_viaje options dynamically after data loads
tipos_disponibles = sorted(df["tipoViaje"].dropna().unique().tolist())

# Re-render tipo_viaje multiselect with actual options using session state trick
with st.sidebar:
    tipo_viaje_sel = st.multiselect(
        "Tipo de viaje (opciones)",
        options=tipos_disponibles,
        placeholder="Todos los tipos",
        key="viajes_tipo_real",
    )

df_filtered = df.copy()

if tipo_viaje_sel:
    df_filtered = df_filtered[df_filtered["tipoViaje"].isin(tipo_viaje_sel)]

if activo_filtro == "Activos":
    df_filtered = df_filtered[df_filtered["activo"] == True]
elif activo_filtro == "Inactivos":
    df_filtered = df_filtered[df_filtered["activo"] == False]

# ── Days in transit ───────────────────────────────────────────────────────────
for col in ["fechaInicio", "fechaTermino"]:
    if col in df_filtered.columns:
        df_filtered[col] = pd.to_datetime(df_filtered[col], errors="coerce")

if "fechaInicio" in df_filtered.columns and "fechaTermino" in df_filtered.columns:
    df_filtered["dias_en_transito"] = (
        df_filtered["fechaTermino"] - df_filtered["fechaInicio"]
    ).dt.days

# ── Summary metrics ───────────────────────────────────────────────────────────
total_viajes   = len(df_filtered)
total_rev      = df_filtered["totalRevenue"].sum() if "totalRevenue" in df_filtered.columns else 0
total_exp      = df_filtered["totalExpenses"].sum() if "totalExpenses" in df_filtered.columns else 0
total_millas   = df_filtered["totalMiles"].sum() if "totalMiles" in df_filtered.columns else 0
avg_dias       = df_filtered["dias_en_transito"].mean() if "dias_en_transito" in df_filtered.columns else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Viajes en período", f"{total_viajes:,}")
col2.metric("Ingresos totales (USD)", f"${total_rev:,.2f}")
col3.metric("Gastos totales (USD)", f"${total_exp:,.2f}")
col4.metric("Millas totales", f"{total_millas:,.0f}")
col5.metric("Promedio días en tránsito", f"{avg_dias:.1f} días")

st.divider()

# ── Revenue vs Expenses per trip chart ───────────────────────────────────────
st.subheader("Ingresos vs Gastos por viaje")

chart_cols = ["idViaje", "totalRevenue", "totalExpenses"]
chart_ok = all(c in df_filtered.columns for c in chart_cols)

if chart_ok and not df_filtered.empty:
    df_chart = df_filtered[chart_cols].dropna(subset=["totalRevenue", "totalExpenses"]).copy()
    df_chart = df_chart.sort_values("totalRevenue", ascending=False).head(100)
    df_chart["idViaje"] = df_chart["idViaje"].astype(str)

    df_melted = df_chart.melt(
        id_vars="idViaje",
        value_vars=["totalRevenue", "totalExpenses"],
        var_name="Categoría",
        value_name="Monto (USD)",
    )
    df_melted["Categoría"] = df_melted["Categoría"].map(
        {"totalRevenue": "Ingresos", "totalExpenses": "Gastos"}
    )

    fig = px.bar(
        df_melted,
        x="idViaje",
        y="Monto (USD)",
        color="Categoría",
        barmode="group",
        labels={"idViaje": "ID Viaje"},
        color_discrete_map={"Ingresos": "#2ca02c", "Gastos": "#d62728"},
        height=420,
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        margin=dict(t=20, b=10),
        xaxis_title="ID Viaje (Top 100 por ingresos)",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos suficientes para el gráfico de ingresos vs gastos.")

st.divider()

# ── Trips table ───────────────────────────────────────────────────────────────
st.subheader("Tabla de viajes")

display_cols = [
    c for c in [
        "idViaje",
        "idTransporte",
        "idChofer1",
        "idChofer2",
        "tipoViaje",
        "folioContrato",
        "fechaInicio",
        "fechaTermino",
        "dias_en_transito",
        "totalRevenue",
        "totalExpenses",
        "totalMiles",
        "revenuePerMile",
        "costoPerMile",
        "tipoPago",
        "activo",
    ]
    if c in df_filtered.columns
]

df_display = df_filtered[display_cols].copy()

# Format date columns
for dcol in ["fechaInicio", "fechaTermino"]:
    if dcol in df_display.columns:
        df_display[dcol] = df_display[dcol].dt.strftime("%d/%m/%Y %H:%M").fillna("")

# Format currency columns
for money_col in ["totalRevenue", "totalExpenses", "revenuePerMile", "costoPerMile"]:
    if money_col in df_display.columns:
        df_display[money_col] = df_display[money_col].apply(
            lambda x: f"${x:,.2f}" if pd.notna(x) else ""
        )

for mi_col in ["totalMiles"]:
    if mi_col in df_display.columns:
        df_display[mi_col] = df_display[mi_col].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else ""
        )

# Rename columns to Spanish
rename_map = {
    "idViaje": "ID Viaje",
    "idTransporte": "Unidad",
    "idChofer1": "Operador 1",
    "idChofer2": "Operador 2",
    "tipoViaje": "Tipo Viaje",
    "folioContrato": "Folio Contrato",
    "fechaInicio": "Fecha Inicio",
    "fechaTermino": "Fecha Término",
    "dias_en_transito": "Días Tránsito",
    "totalRevenue": "Ingresos (USD)",
    "totalExpenses": "Gastos (USD)",
    "totalMiles": "Millas",
    "revenuePerMile": "Rev/Milla (USD)",
    "costoPerMile": "Costo/Milla (USD)",
    "tipoPago": "Tipo Pago",
    "activo": "Activo",
}
df_display = df_display.rename(columns={k: v for k, v in rename_map.items() if k in df_display.columns})

st.dataframe(df_display, use_container_width=True, hide_index=True)
st.caption(
    f"Mostrando {len(df_filtered):,} viajes · Todos los montos en USD · Fuente: vwBI_trnViajes"
)
