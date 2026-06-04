"""
Calendario — Monthly utilization calendar per unit.
Shows a heatmap calendar (weeks × days) with GPS activity per unit.
Green = active day (has GPS activity), gray = inactive.
"""

from __future__ import annotations

import calendar
import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

from db import get_samsara_trips_raw, get_unidades_catalogo

st.set_page_config(
    page_title="Calendario · Transport Analytics",
    page_icon="📅",
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

    anio_sel = st.selectbox(
        "Año",
        options=list(range(hoy.year - 2, hoy.year + 1)),
        index=2,
        key="cal_anio",
    )
    mes_sel = st.selectbox(
        "Mes",
        options=list(range(1, 13)),
        index=hoy.month - 1,
        format_func=lambda m: {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        }[m],
        key="cal_mes",
    )

    if st.button("Actualizar datos", key="cal_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Compute date range for selected month ─────────────────────────────────────
primer_dia = datetime.date(anio_sel, mes_sel, 1)
ultimo_dia = datetime.date(
    anio_sel, mes_sel, calendar.monthrange(anio_sel, mes_sel)[1]
)
fi_str = primer_dia.strftime("%Y-%m-%d")
ff_str = ultimo_dia.strftime("%Y-%m-%d")
days_in_month = (ultimo_dia - primer_dia).days + 1

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📅 Calendario de Utilización")
st.caption(f"Período: {MESES_ES[mes_sel]} {anio_sel}")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando datos GPS..."):
    df_raw     = get_samsara_trips_raw(fi_str, ff_str)
    df_catalog = get_unidades_catalogo()

if df_raw.empty:
    st.warning(
        "No se encontraron datos GPS para el período seleccionado. "
        "Verifique que vwBI_samsaraTrips tenga datos en este mes."
    )
    st.stop()

# Ensure datetime
df_raw["startMs"] = pd.to_datetime(df_raw["startMs"], errors="coerce")
df_raw["endMs"]   = pd.to_datetime(df_raw["endMs"],   errors="coerce")
df_raw["fecha_dia"] = df_raw["startMs"].dt.date

# ── Build unit options ────────────────────────────────────────────────────────
unidades_con_datos = df_raw["idTransporte"].dropna().unique().tolist()

if not df_catalog.empty:
    df_catalog_filt = df_catalog[df_catalog["idTransporte"].isin(unidades_con_datos)].copy()
    df_catalog_filt["etiqueta"] = df_catalog_filt.apply(
        lambda r: str(r["nombre"]) if pd.notna(r.get("nombre")) and str(r.get("nombre", "")).strip()
        else f"Unidad {r['idTransporte']}",
        axis=1,
    )
    opciones = df_catalog_filt.set_index("etiqueta")["idTransporte"].to_dict()
else:
    opciones = {f"Unidad {uid}": uid for uid in sorted(unidades_con_datos)}

if not opciones:
    st.warning("No se encontraron unidades con datos GPS en el período seleccionado.")
    st.stop()

# ── Unit selector in sidebar ──────────────────────────────────────────────────
with st.sidebar:
    unidad_sel_label = st.selectbox(
        "Seleccionar unidad",
        options=list(opciones.keys()),
        key="cal_unidad",
    )

unidad_sel_id = opciones[unidad_sel_label]

# ── Filter GPS data for selected unit ────────────────────────────────────────
df_unit = df_raw[df_raw["idTransporte"] == unidad_sel_id].copy()

# Collect active days
active_days = set(df_unit["fecha_dia"].dropna().unique())

# ── Build calendar grid ───────────────────────────────────────────────────────
# Weeks as rows, weekdays (Mon=0 ... Sun=6) as columns
DIAS_SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# Get all days of the month
all_days = [
    primer_dia + datetime.timedelta(days=i) for i in range(days_in_month)
]

# Build a 6x7 grid (max 6 weeks)
# Find the weekday of the first day (Mon=0)
first_weekday = primer_dia.weekday()

grid_values  = np.full((6, 7), np.nan)
grid_text    = [["" for _ in range(7)] for _ in range(6)]

for i, day in enumerate(all_days):
    col = (first_weekday + i) % 7
    row = (first_weekday + i) // 7
    if row < 6:
        grid_values[row][col] = 1.0 if day in active_days else 0.0
        grid_text[row][col]   = str(day.day)

# Remove all-NaN rows
max_row = 0
for i, day in enumerate(all_days):
    row = (first_weekday + i) // 7
    max_row = max(max_row, row)
grid_values = grid_values[:max_row + 1]
grid_text   = grid_text[:max_row + 1]

# ── Plotly heatmap calendar ───────────────────────────────────────────────────
st.subheader(f"Calendario de actividad GPS — {unidad_sel_label}")
st.caption("Verde = día con actividad GPS  |  Gris = día sin actividad  |  Blanco = fuera del mes")

fig_cal = go.Figure(
    data=go.Heatmap(
        z=grid_values,
        text=grid_text,
        texttemplate="%{text}",
        textfont={"size": 14},
        colorscale=[
            [0.0, "#e0e0e0"],
            [0.5, "#e0e0e0"],
            [0.5, "#2ca02c"],
            [1.0, "#2ca02c"],
        ],
        showscale=False,
        zmin=0,
        zmax=1,
        xgap=3,
        ygap=3,
    )
)

fig_cal.update_layout(
    xaxis=dict(
        tickvals=list(range(7)),
        ticktext=DIAS_SEMANA,
        side="top",
        tickfont=dict(size=13, color="#333"),
    ),
    yaxis=dict(
        tickvals=list(range(len(grid_values))),
        ticktext=[f"Sem {i+1}" for i in range(len(grid_values))],
        autorange="reversed",
        tickfont=dict(size=12, color="#555"),
    ),
    margin=dict(t=60, b=20, l=60, r=20),
    height=250 + len(grid_values) * 55,
    plot_bgcolor="white",
)
st.plotly_chart(fig_cal, use_container_width=True)

# ── Summary KPIs for selected unit ───────────────────────────────────────────
st.divider()
st.subheader(f"Resumen de {unidad_sel_label} — {MESES_ES[mes_sel]} {anio_sel}")

dias_activos   = len(active_days)
pct_util       = round(dias_activos / days_in_month * 100, 1)
total_km       = float(df_unit["distanceMeters"].fillna(0).sum()) / 1000.0
total_trips    = len(df_unit)
avg_km_por_dia = total_km / dias_activos if dias_activos else 0

def nivel_util(pct: float) -> str:
    if pct >= 60:
        return "Alto"
    elif pct >= 35:
        return "Medio"
    else:
        return "Bajo"

nivel = nivel_util(pct_util)
NIVEL_EMOJI = {"Alto": "🟢", "Medio": "🟡", "Bajo": "🔴"}

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Días activos GPS", f"{dias_activos} / {days_in_month}")
col2.metric("% Utilización", f"{pct_util:.1f}%")
col3.metric("Nivel", f"{NIVEL_EMOJI.get(nivel, '')} {nivel}")
col4.metric("Km totales GPS", f"{total_km:,.1f}")
col5.metric("Km promedio por día activo", f"{avg_km_por_dia:,.1f}")

# ── Daily km bar chart ────────────────────────────────────────────────────────
if not df_unit.empty:
    st.subheader("Kilómetros por día")
    df_daily = (
        df_unit.groupby("fecha_dia")
        .agg(km=("distanceMeters", lambda x: x.fillna(0).sum() / 1000.0))
        .reset_index()
    )
    df_daily["fecha_dia"] = pd.to_datetime(df_daily["fecha_dia"])
    df_daily = df_daily.sort_values("fecha_dia")

    fig_daily = px.bar(
        df_daily,
        x="fecha_dia",
        y="km",
        labels={"fecha_dia": "Fecha", "km": "Km GPS"},
        color_discrete_sequence=["#2ca02c"],
        text=df_daily["km"].apply(lambda x: f"{x:,.0f}"),
        height=300,
    )
    fig_daily.update_traces(textposition="outside")
    fig_daily.update_layout(
        margin=dict(t=20, b=10),
        xaxis_tickformat="%d/%m",
    )
    st.plotly_chart(fig_daily, use_container_width=True)

# ── All units utilization summary ────────────────────────────────────────────
st.divider()
st.subheader(f"Resumen de utilización — todas las unidades — {MESES_ES[mes_sel]} {anio_sel}")

df_util_all = (
    df_raw.groupby("idTransporte")
    .agg(
        dias_activos=("fecha_dia", "nunique"),
        km_totales=("distanceMeters", lambda x: x.fillna(0).sum() / 1000.0),
        trips=("idTrip", "count"),
    )
    .reset_index()
)

# Join names
if not df_catalog.empty:
    df_util_all = df_util_all.merge(
        df_catalog[["idTransporte", "nombre", "placasMx"]],
        on="idTransporte",
        how="left",
    )
    df_util_all["etiqueta"] = df_util_all.apply(
        lambda r: str(r["nombre"]) if pd.notna(r.get("nombre")) and str(r.get("nombre", "")).strip()
        else f"Unidad {r['idTransporte']}",
        axis=1,
    )
else:
    df_util_all["etiqueta"]  = df_util_all["idTransporte"].apply(lambda x: f"Unidad {x}")
    df_util_all["placasMx"]  = ""

df_util_all["pct_utilizacion"] = (df_util_all["dias_activos"] / days_in_month * 100).round(1)
df_util_all["nivel"] = df_util_all["pct_utilizacion"].apply(nivel_util)
df_util_all = df_util_all.sort_values("pct_utilizacion", ascending=False)

# Bar chart utilization all units
fig_all_util = px.bar(
    df_util_all.sort_values("pct_utilizacion", ascending=True),
    x="pct_utilizacion",
    y="etiqueta",
    orientation="h",
    color="nivel",
    color_discrete_map={"Alto": "#2ca02c", "Medio": "#ff7f0e", "Bajo": "#d62728"},
    text=df_util_all.sort_values("pct_utilizacion", ascending=True)["pct_utilizacion"].apply(
        lambda x: f"{x:.1f}%"
    ),
    labels={"pct_utilizacion": "% Utilización", "etiqueta": "Unidad", "nivel": "Nivel"},
    height=max(400, len(df_util_all) * 28),
)
fig_all_util.update_traces(textposition="outside")
fig_all_util.update_layout(
    margin=dict(t=20, b=10, l=10, r=60),
    yaxis_title="",
)
st.plotly_chart(fig_all_util, use_container_width=True)

# Table all units
df_table_all = df_util_all[["etiqueta", "placasMx", "dias_activos", "pct_utilizacion", "nivel", "km_totales", "trips"]].copy()
NIVEL_COLOR = {"Alto": "🟢", "Medio": "🟡", "Bajo": "🔴"}
df_table_all["nivel"] = df_table_all["nivel"].apply(lambda n: f"{NIVEL_COLOR.get(n, '')} {n}")
df_table_all["pct_utilizacion"] = df_table_all["pct_utilizacion"].apply(lambda x: f"{x:.1f}%")
df_table_all["km_totales"] = df_table_all["km_totales"].apply(lambda x: f"{x:,.1f}")

df_table_all = df_table_all.rename(columns={
    "etiqueta":         "Unidad",
    "placasMx":         "Placas MX",
    "dias_activos":     "Días activos",
    "pct_utilizacion":  "% Utilización",
    "nivel":            "Nivel",
    "km_totales":       "Km totales GPS",
    "trips":            "Trips GPS",
})
st.dataframe(df_table_all, use_container_width=True, hide_index=True)
st.caption(
    f"{MESES_ES[mes_sel]} {anio_sel} · {days_in_month} días en el período · "
    "Nivel: >= 60% Alto (verde), 35-59% Medio (amarillo), < 35% Bajo (rojo) · "
    "Fuente: vwBI_samsaraTrips"
)
