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

# ── Sidebar brand ─────────────────────────────────────────────────────────────
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
    hace_30 = hoy - datetime.timedelta(days=30)

    fecha_inicio = st.date_input("Fecha inicio", value=hace_30, key="viajes_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,     key="viajes_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

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

# ── Days in transit ───────────────────────────────────────────────────────────
for col in ["fechaInicio", "fechaTermino"]:
    if col in df_filtered.columns:
        df_filtered[col] = pd.to_datetime(df_filtered[col], errors="coerce")

if "fechaInicio" in df_filtered.columns and "fechaTermino" in df_filtered.columns:
    df_filtered["dias_en_transito"] = (
        df_filtered["fechaTermino"] - df_filtered["fechaInicio"]
    ).dt.days.clip(lower=0)

# ── Summary metrics ───────────────────────────────────────────────────────────
total_viajes = len(df_filtered)
total_rev    = float(df_filtered["totalRevenue"].fillna(0).sum()) if "totalRevenue" in df_filtered.columns else 0.0
total_exp    = float(df_filtered["totalExpenses"].fillna(0).sum()) if "totalExpenses" in df_filtered.columns else 0.0
total_millas = float(df_filtered["totalMiles"].fillna(0).sum()) if "totalMiles" in df_filtered.columns else 0.0
avg_dias     = float(df_filtered["dias_en_transito"].dropna().mean()) if "dias_en_transito" in df_filtered.columns else 0.0
margen       = total_rev - total_exp

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Viajes en período", f"{total_viajes:,}")
col2.metric("Ingresos (USD)", f"${total_rev:,.2f}")
col3.metric("Gastos (USD)", f"${total_exp:,.2f}")
col4.metric("Margen (USD)", f"${margen:,.2f}")
col5.metric("Millas totales", f"{total_millas:,.0f}")
col6.metric("Prom. días tránsito", f"{avg_dias:.1f} días")

st.divider()

# ── Revenue vs Expenses per trip chart ───────────────────────────────────────
st.subheader("Ingresos vs Gastos por viaje (Top 100 por ingresos)")

chart_cols = ["idViaje", "totalRevenue", "totalExpenses"]
chart_ok = all(c in df_filtered.columns for c in chart_cols)

if chart_ok and not df_filtered.empty:
    df_chart = (
        df_filtered[chart_cols]
        .dropna(subset=["totalRevenue", "totalExpenses"])
        .sort_values("totalRevenue", ascending=False)
        .head(100)
        .copy()
    )
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
        xaxis_title="ID Viaje",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No hay datos suficientes para el gráfico de ingresos vs gastos.")

# ── Revenue vs Expenses scatter (all trips) ───────────────────────────────────
if "totalRevenue" in df_filtered.columns and "totalExpenses" in df_filtered.columns:
    st.subheader("Dispersión: Ingresos vs Gastos por viaje")
    df_scatter_viajes = df_filtered[
        ["idViaje", "totalRevenue", "totalExpenses", "tipoViaje", "totalMiles"]
    ].dropna(subset=["totalRevenue", "totalExpenses"]).copy()
    df_scatter_viajes["idViaje"] = df_scatter_viajes["idViaje"].astype(str)
    df_scatter_viajes["margen"] = df_scatter_viajes["totalRevenue"] - df_scatter_viajes["totalExpenses"]

    fig_sc = px.scatter(
        df_scatter_viajes,
        x="totalExpenses",
        y="totalRevenue",
        color="tipoViaje",
        hover_name="idViaje",
        hover_data={"totalMiles": ":.0f", "margen": ":$.2f"},
        labels={
            "totalExpenses": "Gastos (USD)",
            "totalRevenue": "Ingresos (USD)",
            "tipoViaje": "Tipo Viaje",
        },
        opacity=0.75,
        height=420,
    )
    # Draw the break-even line
    max_val = max(
        df_scatter_viajes["totalRevenue"].max(),
        df_scatter_viajes["totalExpenses"].max(),
    )
    import plotly.graph_objects as go
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

st.divider()

# ── Trips table ───────────────────────────────────────────────────────────────
st.subheader(f"Tabla de viajes ({total_viajes:,} registros)")

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
            lambda x: f"${x:,.2f}" if pd.notna(x) else "—"
        )

for mi_col in ["totalMiles"]:
    if mi_col in df_display.columns:
        df_display[mi_col] = df_display[mi_col].apply(
            lambda x: f"{x:,.0f}" if pd.notna(x) else "—"
        )

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
df_display = df_display.rename(
    columns={k: v for k, v in rename_map.items() if k in df_display.columns}
)

st.dataframe(df_display, use_container_width=True, hide_index=True)
st.caption(
    f"Mostrando {total_viajes:,} viajes · Montos en USD · "
    "Fuente: vwBI_trnViajes"
)
