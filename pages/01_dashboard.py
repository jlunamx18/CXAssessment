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
from theme import (
    apply_theme, sidebar_header, page_header, kpi_cards,
    panel_header, BLUE, GREEN_PRIMARY, RED, AMBER, TEAL, PLOTLY_LAYOUT, CHART_COLORS
)

st.set_page_config(page_title="Dashboard · Transport Analytics", page_icon="📊", layout="wide")
apply_theme()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_header()
    st.divider()
    st.markdown("**Filtros**")

    hoy             = datetime.date.today()
    primer_dia_mes  = hoy.replace(day=1)
    fecha_inicio    = st.date_input("Fecha inicio", value=primer_dia_mes, key="dash_fi")
    fecha_fin       = st.date_input("Fecha fin",    value=hoy,            key="dash_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="dash_refresh"):
        st.cache_data.clear()
        st.rerun()

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")
dias   = (fecha_fin - fecha_inicio).days + 1

# ── Page header ───────────────────────────────────────────────────────────────
page_header(
    "Resumen Ejecutivo",
    "Dashboard · Estado Operativo MLV",
    "KPIs de viajes, ingresos y operación · Corredor Monterrey – Laredo – EEUU",
    meta=f"<strong>{fecha_inicio.strftime('%d/%m/%Y')}</strong> — <strong>{fecha_fin.strftime('%d/%m/%Y')}</strong><br>{dias} días",
)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando KPIs..."):
    df_kpis   = get_kpis_dedup(fi_str, ff_str)
    df_semana = get_viajes_por_semana_dedup(fi_str, ff_str)
    df_mes    = get_viajes_por_mes_dedup(fi_str, ff_str)
    df_tipo   = get_viajes_por_tipo_dedup(fi_str, ff_str)

if df_kpis.empty or df_kpis.iloc[0]["total_viajes"] is None:
    st.warning("No se encontraron datos para el período seleccionado.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
row = df_kpis.iloc[0]
total_viajes     = int(row["total_viajes"]       or 0)
total_revenue    = float(row["total_revenue"]    or 0)
total_expenses   = float(row["total_expenses"]   or 0)
margen           = float(row["margen"]           or 0)
total_miles      = float(row["total_miles"]      or 0)
avg_rev_per_mile = float(row["avg_rev_per_mile"] or 0)
unidades_activas = int(row["unidades_activas"]   or 0)
choferes_activos = int(row["choferes_activos"]   or 0)
margen_pct       = (margen / total_revenue * 100) if total_revenue else 0

kpi_cards([
    {"label": "Viajes (COUNT DISTINCT)",   "value": f"{total_viajes:,}",       "sub": f"{dias} días"},
    {"label": "Ingresos (USD)",            "value": f"${total_revenue:,.0f}",   "sub": "Total período"},
    {"label": "Gastos (USD)",              "value": f"${total_expenses:,.0f}",  "color": "red"},
    {"label": "Margen (USD)",              "value": f"${margen:,.0f}",
     "sub": f"{margen_pct:.1f}% del ingreso",
     "delta": f"{margen_pct:.1f}%", "delta_dir": "up" if margen >= 0 else "dn",
     "color": "green" if margen >= 0 else "red"},
    {"label": "Total millas",              "value": f"{total_miles:,.0f}",      "color": "blue"},
])

st.markdown("<br>", unsafe_allow_html=True)

kpi_cards([
    {"label": "Rev / Milla (USD)",         "value": f"${avg_rev_per_mile:,.2f}", "color": "teal"},
    {"label": "Unidades activas",          "value": f"{unidades_activas:,}",     "sub": "con viajes en el período"},
    {"label": "Choferes activos",          "value": f"{choferes_activos:,}",     "sub": "con viajes en el período"},
    {"label": "",                          "value": ""},
    {"label": "",                          "value": ""},
])

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    panel_header("Tendencia Semanal", "Viajes únicos por semana")
    if df_semana.empty:
        st.warning("Sin datos semanales.")
    else:
        df_semana["semana_label"] = df_semana.apply(
            lambda r: (
                f"Sem {int(r['semana'])} ({r['semana_inicio']})"
                if pd.notna(r.get("semana_inicio")) else f"Sem {int(r['semana'])}"
            ), axis=1,
        )
        fig_bar = px.bar(
            df_semana, x="semana_label", y="total_viajes", text="total_viajes",
            labels={"semana_label": "Semana", "total_viajes": "Viajes únicos"},
            color_discrete_sequence=[BLUE],
        )
        fig_bar.update_traces(textposition="outside")
        fig_bar.update_layout(**PLOTLY_LAYOUT, xaxis_tickangle=-30, height=350)
        st.plotly_chart(fig_bar, use_container_width=True)

with col_right:
    panel_header("Mix de Viajes", "Distribución por tipo")
    if df_tipo.empty:
        st.warning("Sin datos de tipo de viaje.")
    else:
        fig_pie = px.pie(
            df_tipo, names="tipoViaje", values="total_viajes", hole=0.35,
            color_discrete_sequence=CHART_COLORS,
        )
        fig_pie.update_traces(textinfo="label+percent", pull=[0.03] * len(df_tipo))
        fig_pie.update_layout(**PLOTLY_LAYOUT, height=350,
                              legend=dict(orientation="v", yanchor="middle", y=0.5))
        st.plotly_chart(fig_pie, use_container_width=True)

# ── Revenue vs Expenses by month ─────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
panel_header("Ingresos vs Gastos", "Por mes · USD")

if not df_mes.empty:
    MESES_ES = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
                7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
    df_mes["mes_label"] = df_mes.apply(
        lambda r: f"{MESES_ES.get(int(r['mes']), str(int(r['mes'])))} {int(r['anio'])}", axis=1
    )
    df_melted = df_mes[["mes_label","total_revenue","total_expenses"]].rename(
        columns={"total_revenue":"Ingresos","total_expenses":"Gastos"}
    ).melt(id_vars="mes_label", value_vars=["Ingresos","Gastos"], var_name="Categoría", value_name="USD")

    fig_mes = px.bar(
        df_melted, x="mes_label", y="USD", color="Categoría", barmode="group",
        labels={"mes_label": "Mes"},
        color_discrete_map={"Ingresos": GREEN_PRIMARY, "Gastos": RED},
        height=320,
    )
    fig_mes.update_layout(**PLOTLY_LAYOUT, xaxis_tickangle=-30)
    st.plotly_chart(fig_mes, use_container_width=True)

st.caption("Todos los montos en USD · Viajes: COUNT DISTINCT(idViaje) · Fuente: vwBI_trnViajes")
