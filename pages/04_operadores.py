"""
Operadores — Driver performance page.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_operadores_stats

st.set_page_config(
    page_title="Operadores · Transport Analytics",
    page_icon="👤",
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

    fecha_inicio = st.date_input("Fecha inicio", value=hace_30, key="op_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,     key="op_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    top_n = st.slider("Top N operadores a mostrar", min_value=5, max_value=50, value=20, step=5)

    metrica_orden = st.selectbox(
        "Ordenar por",
        options=["Ingresos totales", "Viajes totales", "Millas totales", "Rev/Milla promedio"],
        index=0,
    )

    if st.button("🔄 Actualizar datos", key="op_refresh"):
        st.cache_data.clear()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("👤 Desempeño de Operadores")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando estadísticas de operadores..."):
    df = get_operadores_stats(fi_str, ff_str)

if df.empty:
    st.warning("No se encontraron datos de operadores para el período seleccionado.")
    st.stop()

# ── Sort by selected metric ───────────────────────────────────────────────────
sort_col_map = {
    "Ingresos totales": "total_revenue",
    "Viajes totales": "total_viajes",
    "Millas totales": "total_millas",
    "Rev/Milla promedio": "avg_revenue_per_mile",
}
sort_col = sort_col_map[metrica_orden]
df = df.sort_values(sort_col, ascending=False)
df_top = df.head(top_n).copy()

# ── Summary metrics ───────────────────────────────────────────────────────────
total_operadores = len(df)
total_viajes     = int(df["total_viajes"].sum())
total_millas     = float(df["total_millas"].sum())
total_revenue    = float(df["total_revenue"].sum())
total_expenses   = float(df["total_expenses"].sum())
mejor_op_label   = df.iloc[0]["operador"] if not df.empty else "N/A"

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Operadores activos", f"{total_operadores:,}")
col2.metric("Total viajes", f"{total_viajes:,}")
col3.metric("Total millas", f"{total_millas:,.0f}")
col4.metric("Ingresos totales (USD)", f"${total_revenue:,.2f}")
col5.metric("Mejor operador (ingresos)", f"Op. {mejor_op_label}")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader(f"Viajes por operador (Top {top_n})")
    df_plot = df_top.sort_values("total_viajes", ascending=True)
    fig_viajes = px.bar(
        df_plot,
        x="total_viajes",
        y="operador",
        orientation="h",
        text="total_viajes",
        labels={"total_viajes": "Viajes", "operador": "Operador (ID)"},
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
    st.subheader(f"Ingresos por operador (USD) — Top {top_n}")
    df_plot2 = df_top.sort_values("total_revenue", ascending=True)
    fig_rev = px.bar(
        df_plot2,
        x="total_revenue",
        y="operador",
        orientation="h",
        text=df_plot2["total_revenue"].apply(lambda x: f"${x:,.0f}"),
        labels={"total_revenue": "Ingresos (USD)", "operador": "Operador (ID)"},
        color="total_revenue",
        color_continuous_scale="Greens",
        height=max(400, top_n * 22),
    )
    fig_rev.update_traces(textposition="outside")
    fig_rev.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=10),
        yaxis_title="",
    )
    st.plotly_chart(fig_rev, use_container_width=True)

# ── Miles per operator ────────────────────────────────────────────────────────
col_left2, col_right2 = st.columns(2)

with col_left2:
    st.subheader(f"Millas recorridas por operador (Top {top_n})")
    df_plot3 = df_top.sort_values("total_millas", ascending=True)
    fig_millas = px.bar(
        df_plot3,
        x="total_millas",
        y="operador",
        orientation="h",
        text=df_plot3["total_millas"].apply(lambda x: f"{x:,.0f}"),
        labels={"total_millas": "Millas", "operador": "Operador (ID)"},
        color="total_millas",
        color_continuous_scale="Oranges",
        height=max(400, top_n * 22),
    )
    fig_millas.update_traces(textposition="outside")
    fig_millas.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=10),
        yaxis_title="",
    )
    st.plotly_chart(fig_millas, use_container_width=True)

with col_right2:
    st.subheader(f"Revenue por milla promedio — Top {top_n}")
    df_plot4 = df_top.sort_values("avg_revenue_per_mile", ascending=True)
    fig_rpm = px.bar(
        df_plot4,
        x="avg_revenue_per_mile",
        y="operador",
        orientation="h",
        text=df_plot4["avg_revenue_per_mile"].apply(lambda x: f"${x:,.3f}"),
        labels={
            "avg_revenue_per_mile": "Rev/Milla (USD)",
            "operador": "Operador (ID)",
        },
        color="avg_revenue_per_mile",
        color_continuous_scale="RdYlGn",
        height=max(400, top_n * 22),
    )
    fig_rpm.update_traces(textposition="outside")
    fig_rpm.update_layout(
        coloraxis_showscale=False,
        margin=dict(t=20, b=10, l=10, r=10),
        yaxis_title="",
    )
    st.plotly_chart(fig_rpm, use_container_width=True)

# ── Efficiency scatter ────────────────────────────────────────────────────────
st.subheader("Eficiencia operativa: Ingresos vs Millas por operador")
df_scatter = df_top.copy()
df_scatter["margen"] = df_scatter["total_revenue"] - df_scatter["total_expenses"]
df_scatter["margen_pct"] = (
    df_scatter["margen"] / df_scatter["total_revenue"].replace(0, float("nan")) * 100
)

fig_scatter = px.scatter(
    df_scatter,
    x="total_millas",
    y="total_revenue",
    size="total_viajes",
    color="avg_revenue_per_mile",
    hover_name="operador",
    hover_data={
        "total_viajes": True,
        "total_millas": ":.0f",
        "total_revenue": ":$.2f",
        "total_expenses": ":$.2f",
        "margen": ":$.2f",
        "avg_revenue_per_mile": ":$.3f",
        "avg_costo_per_mile": ":$.3f",
    },
    labels={
        "total_millas": "Millas totales",
        "total_revenue": "Ingresos totales (USD)",
        "avg_revenue_per_mile": "Rev/Milla",
        "total_viajes": "Viajes",
    },
    color_continuous_scale="RdYlGn",
    height=480,
)
fig_scatter.update_layout(margin=dict(t=20, b=10))
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Data table ────────────────────────────────────────────────────────────────
st.divider()
st.subheader("Tabla de desempeño por operador")

df_table = df.copy()
df_table["margen"] = df_table["total_revenue"] - df_table["total_expenses"]

format_usd = lambda x: f"${x:,.2f}"
format_num = lambda x: f"{x:,.0f}"
format_rpm = lambda x: f"${x:,.3f}"

for col_name, fmt in [
    ("total_revenue", format_usd),
    ("total_expenses", format_usd),
    ("margen", format_usd),
    ("total_millas", format_num),
    ("avg_revenue_per_mile", format_rpm),
    ("avg_costo_per_mile", format_rpm),
]:
    if col_name in df_table.columns:
        df_table[col_name] = df_table[col_name].apply(fmt)

df_table = df_table.rename(
    columns={
        "operador": "Operador (ID)",
        "total_viajes": "Viajes",
        "total_millas": "Millas",
        "total_revenue": "Ingresos (USD)",
        "total_expenses": "Gastos (USD)",
        "margen": "Margen (USD)",
        "avg_revenue_per_mile": "Rev/Milla (USD)",
        "avg_costo_per_mile": "Costo/Milla (USD)",
    }
)

st.dataframe(df_table, use_container_width=True, hide_index=True)
st.caption(
    f"Total: {total_operadores} operadores · Período: {fecha_inicio.strftime('%d/%m/%Y')} — "
    f"{fecha_fin.strftime('%d/%m/%Y')} · Fuente: vwBI_trnViajes (idChofer1)"
)
