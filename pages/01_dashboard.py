"""
Dashboard — KPI overview page.
Uses COUNT DISTINCT(idViaje) and deduplicated cost aggregations.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_kpis_dedup, get_viajes_por_semana_dedup, get_viajes_por_mes_dedup, get_viajes_por_tipo_dedup

st.set_page_config(
    page_title="Dashboard · Transport Analytics",
    page_icon="📊",
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
    primer_dia_mes = hoy.replace(day=1)

    fecha_inicio = st.date_input("Fecha inicio", value=primer_dia_mes, key="dash_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,            key="dash_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="dash_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📊 Dashboard")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")
st.info(
    "Viajes calculados con COUNT DISTINCT(idViaje) — costos deduplicados por viaje",
    icon="ℹ️",
)

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando KPIs..."):
    df_kpis   = get_kpis_dedup(fi_str, ff_str)
    df_semana = get_viajes_por_semana_dedup(fi_str, ff_str)
    df_mes    = get_viajes_por_mes_dedup(fi_str, ff_str)
    df_tipo   = get_viajes_por_tipo_dedup(fi_str, ff_str)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
if df_kpis.empty or df_kpis.iloc[0]["total_viajes"] is None:
    st.warning("No se encontraron datos para el período seleccionado.")
else:
    row = df_kpis.iloc[0]

    total_viajes     = int(row["total_viajes"]     or 0)
    total_revenue    = float(row["total_revenue"]  or 0)
    total_expenses   = float(row["total_expenses"] or 0)
    margen           = float(row["margen"]         or 0)
    total_miles      = float(row["total_miles"]    or 0)
    avg_rev_per_mile = float(row["avg_rev_per_mile"] or 0)
    unidades_activas = int(row["unidades_activas"] or 0)
    choferes_activos = int(row["choferes_activos"] or 0)

    margen_pct = (margen / total_revenue * 100) if total_revenue else 0

    # Row 1: Trips, Revenue, Expenses, Margin
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(
        label="Viajes totales (COUNT DISTINCT)",
        value=f"{total_viajes:,}",
    )
    col2.metric(
        label="Ingresos (USD)",
        value=f"${total_revenue:,.2f}",
    )
    col3.metric(
        label="Gastos totales (USD)",
        value=f"${total_expenses:,.2f}",
    )
    col4.metric(
        label="Margen (USD)",
        value=f"${margen:,.2f}",
        delta=f"{margen_pct:.1f}%",
        delta_color="normal",
    )

    # Row 2: Miles, Rev/Mile, Units, Drivers
    col5, col6, col7, col8 = st.columns(4)
    col5.metric(
        label="Total millas",
        value=f"{total_miles:,.0f}",
    )
    col6.metric(
        label="Rev / Milla (USD)",
        value=f"${avg_rev_per_mile:,.2f}",
    )
    col7.metric(
        label="Unidades activas",
        value=f"{unidades_activas:,}",
    )
    col8.metric(
        label="Choferes activos",
        value=f"{choferes_activos:,}",
    )

st.divider()

# ── Chart: viajes unicos por semana ──────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Viajes únicos por semana")
    if df_semana.empty:
        st.warning("Sin datos semanales para el período seleccionado.")
    else:
        df_semana["semana_label"] = df_semana.apply(
            lambda r: (
                f"Sem {int(r['semana'])} ({r['semana_inicio']})"
                if pd.notna(r.get("semana_inicio"))
                else f"Sem {int(r['semana'])}"
            ),
            axis=1,
        )
        fig_bar = px.bar(
            df_semana,
            x="semana_label",
            y="total_viajes",
            text="total_viajes",
            labels={"semana_label": "Semana", "total_viajes": "Viajes únicos"},
            color_discrete_sequence=["#1f77b4"],
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(
            xaxis_tickangle=-30,
            margin=dict(t=20, b=10),
            height=380,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    st.subheader("Distribución por tipo de viaje")
    if df_tipo.empty:
        st.warning("Sin datos de tipo de viaje para el período seleccionado.")
    else:
        fig_pie = px.pie(
            df_tipo,
            names="tipoViaje",
            values="total_viajes",
            hole=0.35,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig_pie.update_traces(textinfo="label+percent", pull=[0.03] * len(df_tipo))
        fig_pie.update_layout(
            showlegend=True,
            legend=dict(orientation="v", yanchor="middle", y=0.5),
            margin=dict(t=20, b=10),
            height=380,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

# ── Chart: revenue vs gastos por mes ─────────────────────────────────────────
st.subheader("Ingresos vs Gastos por mes (USD)")
if df_mes.empty:
    st.warning("Sin datos mensuales para el período seleccionado.")
else:
    MESES_ES = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
    }
    df_mes["mes_label"] = df_mes.apply(
        lambda r: f"{MESES_ES.get(int(r['mes']), str(int(r['mes'])))} {int(r['anio'])}",
        axis=1,
    )
    df_melted = df_mes[["mes_label", "total_revenue", "total_expenses"]].copy()
    df_melted = df_melted.rename(
        columns={"total_revenue": "Ingresos", "total_expenses": "Gastos"}
    )
    df_melted = df_melted.melt(
        id_vars="mes_label",
        value_vars=["Ingresos", "Gastos"],
        var_name="Categoria",
        value_name="Monto (USD)",
    )
    fig_mes = px.bar(
        df_melted,
        x="mes_label",
        y="Monto (USD)",
        color="Categoria",
        barmode="group",
        labels={"mes_label": "Mes"},
        color_discrete_map={"Ingresos": "#2ca02c", "Gastos": "#d62728"},
        height=380,
    )
    fig_mes.update_layout(
        xaxis_tickangle=-30,
        margin=dict(t=20, b=10),
    )
    st.plotly_chart(fig_mes, use_container_width=True)

st.caption(
    "Todos los montos en USD salvo indicación contraria · "
    "Viajes: COUNT DISTINCT(idViaje) · Fuente: vwBI_trnViajes"
)
