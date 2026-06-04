"""
Flota — Fleet utilization page.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_flota_stats

st.set_page_config(
    page_title="Flota · Transport Analytics",
    page_icon="🚌",
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

    fecha_inicio = st.date_input("Fecha inicio", value=hace_30, key="flota_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,     key="flota_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    top_n = st.slider("Top N unidades a mostrar", min_value=5, max_value=50, value=20, step=5)

    if st.button("🔄 Actualizar datos", key="flota_refresh"):
        st.cache_data.clear()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🚌 Utilización de Flota")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando estadísticas de flota..."):
    df = get_flota_stats(fi_str, ff_str)

if df.empty:
    st.warning("No se encontraron datos de flota para el período seleccionado.")
    st.stop()

df_top = df.head(top_n).copy()

# ── Summary metrics ───────────────────────────────────────────────────────────
total_unidades    = len(df)
total_viajes      = int(df["total_viajes"].sum())
total_millas      = float(df["total_millas"].sum())
total_revenue     = float(df["total_revenue"].sum())
mejor_unidad_rev  = df.iloc[0]["unidad"] if not df.empty else "N/A"
avg_rev_por_unit  = total_revenue / total_unidades if total_unidades else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Unidades activas", f"{total_unidades:,}")
col2.metric("Total viajes", f"{total_viajes:,}")
col3.metric("Total millas recorridas", f"{total_millas:,.0f}")
col4.metric("Ingresos totales (USD)", f"${total_revenue:,.2f}")
col5.metric("Rev. promedio / unidad (USD)", f"${avg_rev_por_unit:,.2f}")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(f"Viajes por unidad (Top {top_n})")
    fig_viajes = px.bar(
        df_top.sort_values("total_viajes", ascending=True),
        x="total_viajes",
        y="unidad",
        orientation="h",
        text="total_viajes",
        labels={"total_viajes": "Viajes", "unidad": "Unidad (ID)"},
        color="total_viajes",
        color_continuous_scale="Blues",
        height=max(400, top_n * 22),
    )
    fig_viajes.update_traces(textposition="outside")
    fig_viajes.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=10),
        yaxis_title="",
    )
    st.plotly_chart(fig_viajes, use_container_width=True)

with col_right:
    st.subheader(f"Millas recorridas por unidad (Top {top_n})")
    fig_millas = px.bar(
        df_top.sort_values("total_millas", ascending=True),
        x="total_millas",
        y="unidad",
        orientation="h",
        text=df_top.sort_values("total_millas", ascending=True)["total_millas"].apply(
            lambda x: f"{x:,.0f}"
        ),
        labels={"total_millas": "Millas", "unidad": "Unidad (ID)"},
        color="total_millas",
        color_continuous_scale="Greens",
        height=max(400, top_n * 22),
    )
    fig_millas.update_traces(textposition="outside")
    fig_millas.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=10),
        yaxis_title="",
    )
    st.plotly_chart(fig_millas, use_container_width=True)

# ── Revenue per unit ──────────────────────────────────────────────────────────
st.subheader(f"Ingresos por unidad (USD) — Top {top_n}")
fig_rev = px.bar(
    df_top.sort_values("total_revenue", ascending=True),
    x="total_revenue",
    y="unidad",
    orientation="h",
    text=df_top.sort_values("total_revenue", ascending=True)["total_revenue"].apply(
        lambda x: f"${x:,.0f}"
    ),
    labels={"total_revenue": "Ingresos (USD)", "unidad": "Unidad (ID)"},
    color="total_revenue",
    color_continuous_scale="RdYlGn",
    height=max(400, top_n * 22),
)
fig_rev.update_traces(textposition="outside")
fig_rev.update_layout(
    coloraxis_showscale=False,
    margin=dict(t=20, b=10, l=10, r=40),
    yaxis_title="",
)
st.plotly_chart(fig_rev, use_container_width=True)

# ── Revenue per mile scatter ──────────────────────────────────────────────────
st.subheader("Eficiencia: Ingresos vs Millas por unidad")
df_scatter = df_top.copy()
df_scatter["margen"] = df_scatter["total_revenue"] - df_scatter["total_expenses"]
fig_scatter = px.scatter(
    df_scatter,
    x="total_millas",
    y="total_revenue",
    size="total_viajes",
    color="avg_revenue_per_mile",
    hover_name="unidad",
    hover_data={
        "total_viajes": True,
        "total_millas": ":.0f",
        "total_revenue": ":$.2f",
        "avg_revenue_per_mile": ":$.3f",
        "margen": ":$.2f",
    },
    labels={
        "total_millas": "Millas totales",
        "total_revenue": "Ingresos totales (USD)",
        "avg_revenue_per_mile": "Rev/Milla",
        "total_viajes": "Viajes",
    },
    color_continuous_scale="RdYlGn",
    height=450,
)
fig_scatter.update_layout(margin=dict(t=20, b=10))
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Data table ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Tabla de estadísticas por unidad")

df_table = df.copy()
df_table["total_revenue"] = df_table["total_revenue"].apply(lambda x: f"${x:,.2f}")
df_table["total_expenses"] = df_table["total_expenses"].apply(lambda x: f"${x:,.2f}")
df_table["total_millas"] = df_table["total_millas"].apply(lambda x: f"{x:,.0f}")
df_table["avg_revenue_per_mile"] = df_table["avg_revenue_per_mile"].apply(lambda x: f"${x:,.3f}")

df_table = df_table.rename(
    columns={
        "unidad": "Unidad (ID)",
        "total_viajes": "Viajes",
        "total_millas": "Millas",
        "total_revenue": "Ingresos (USD)",
        "total_expenses": "Gastos (USD)",
        "avg_revenue_per_mile": "Rev/Milla (USD)",
    }
)

st.dataframe(df_table, use_container_width=True, hide_index=True)
st.caption(
    f"Total: {total_unidades} unidades · Período: {fecha_inicio.strftime('%d/%m/%Y')} — "
    f"{fecha_fin.strftime('%d/%m/%Y')} · Fuente: vwBI_trnViajes"
)
