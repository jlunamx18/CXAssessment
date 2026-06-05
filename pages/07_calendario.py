"""
Calendario de Utilización — matriz flota × días del mes.
Muestra GPS y TMS combinados: huecos visibles de un vistazo.

GPS sources:
  - vwBI_samsaraTrips (DB):  day-level data, up to Nov 2025
  - data/gps_html_2026.json: monthly summary, Jan–May 2026
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

from db import get_samsara_trips_raw, get_tms_dias_por_unidad, get_unidades_catalogo, get_gps_meses_disponibles
from gps_html import (
    best_gps_source, get_excel_gps_days, get_excel_trips_for_month,
    get_html_gps_for_month, get_all_gps_months,
)
from theme import apply_theme, sidebar_header, page_header, kpi_cards, panel_header, insight

st.set_page_config(page_title="Calendario · Transport Analytics", page_icon="📅", layout="wide")
apply_theme()

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo",  6: "Junio",   7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_header()
    st.divider()
    st.markdown("**Período**")

    hoy = datetime.date.today()

    # Default to most recent month with any GPS data (Excel or HTML)
    all_gps_months = get_all_gps_months()
    if all_gps_months:
        _def_anio, _def_mes = max(all_gps_months)
    else:
        _def_anio, _def_mes = hoy.year, hoy.month

    _anios = sorted(set(
        list(range(hoy.year - 3, hoy.year + 1)) + [y for y, _ in all_gps_months]
    ))
    anio_sel = st.selectbox(
        "Año", options=_anios,
        index=_anios.index(_def_anio) if _def_anio in _anios else len(_anios) - 1,
        key="cal_anio",
    )
    mes_sel = st.selectbox(
        "Mes", options=list(range(1, 13)),
        index=_def_mes - 1,
        format_func=lambda m: MESES_ES[m],
        key="cal_mes",
    )

    # Show available GPS months
    if all_gps_months:
        labels = [f"{MESES_ES[m][:3]} {y}" for y, m in sorted(all_gps_months)]
        st.caption(f"GPS disponible: {', '.join(labels)}")

    st.divider()
    st.markdown("**Fuente de datos**")
    fuente = st.radio(
        "Mostrar actividad de:",
        options=["GPS (Samsara)", "TMS (Sistema)", "Ambos"],
        index=2, key="cal_fuente",
    )

    if st.button("🔄 Actualizar datos", key="cal_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Date range ────────────────────────────────────────────────────────────────
primer_dia = datetime.date(anio_sel, mes_sel, 1)
ultimo_dia = datetime.date(anio_sel, mes_sel, calendar.monthrange(anio_sel, mes_sel)[1])
fi_str = primer_dia.strftime("%Y-%m-%d")
ff_str = ultimo_dia.strftime("%Y-%m-%d")
days_in_month = (ultimo_dia - primer_dia).days + 1
dias_del_mes  = [primer_dia + datetime.timedelta(days=i) for i in range(days_in_month)]

# ── Page header ───────────────────────────────────────────────────────────────
page_header(
    "Calendario de Utilización",
    f"Matriz Flota × Días · {MESES_ES[mes_sel]} {anio_sel}",
    "Huecos GPS y TMS visibles de un vistazo · Verde = ambos sistemas · Azul = solo TMS · Cyan = solo GPS",
    meta=f"<strong>{days_in_month} días</strong> del mes",
)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando datos..."):
    df_gps_raw = get_samsara_trips_raw(fi_str, ff_str)
    df_tms_raw = get_tms_dias_por_unidad(fi_str, ff_str)
    df_catalog = get_unidades_catalogo()

# ── Build catalog code → idTransporte map ────────────────────────────────────
code_to_id: dict = {}
if not df_catalog.empty:
    for _, crow in df_catalog.iterrows():
        codigo = str(crow.get("codigo", "")).strip()
        if codigo:
            code_to_id[codigo] = crow["idTransporte"]

# ── Determine GPS source ──────────────────────────────────────────────────────
# Priority: DB (day-level) > Excel files (day-level) > HTML (monthly summary)
gps_source = "db" if not df_gps_raw.empty else best_gps_source(anio_sel, mes_sel)

if gps_source == "excel":
    st.info(
        f"GPS de {MESES_ES[mes_sel]} {anio_sel} — fuente: **archivos Excel Samsara** "
        f"(detalle por día disponible).",
        icon="📊",
    )
elif gps_source == "html":
    st.info(
        f"GPS de {MESES_ES[mes_sel]} {anio_sel} — fuente: **reporte HTML** "
        "(resumen mensual, sin detalle por día — el heatmap muestra solo TMS).",
        icon="📊",
    )

# ── Build GPS active days ─────────────────────────────────────────────────────
gps_dias: dict[tuple, float] = {}   # (idTransporte, date) → km

if gps_source == "db" and not df_gps_raw.empty:
    df_gps_raw["startMs_dt"] = pd.to_datetime(
        pd.to_numeric(df_gps_raw["startMs"], errors="coerce"), unit="ms", errors="coerce"
    )
    df_gps_raw["fecha_dia"] = df_gps_raw["startMs_dt"].dt.date
    for _, row in df_gps_raw.iterrows():
        if pd.notna(row["fecha_dia"]):
            key = (row["idTransporte"], row["fecha_dia"])
            gps_dias[key] = gps_dias.get(key, 0) + float(row.get("distanceMeters") or 0) / 1000

elif gps_source == "excel":
    gps_dias = get_excel_gps_days(anio_sel, mes_sel, code_to_id)

# ── Build HTML GPS monthly summary (fallback, no day-level) ──────────────────
html_gps_summary: dict = {}
use_html_gps = (gps_source == "html")
if use_html_gps:
    df_html_gps = get_html_gps_for_month(anio_sel, mes_sel)
    if not df_html_gps.empty:
        for _, row in df_html_gps.iterrows():
            bus_code = str(row["Bus"]).strip()
            uid = code_to_id.get(bus_code)
            if uid is not None:
                html_gps_summary[uid] = {
                    "dias_activos": int(row.get("dias_activos", 0)),
                    "km":           float(row.get("km", 0)),
                    "viajes":       int(row.get("viajes", 0)),
                    "idle_cal":     int(row.get("idle_cal", 0)),
                    "util_cal":     float(row.get("util_cal", 0)),
                }

# ── Build TMS active days ─────────────────────────────────────────────────────
tms_dias: dict[tuple, int] = {}    # (idTransporte, date) → viajes
if not df_tms_raw.empty:
    df_tms_raw["dia"] = pd.to_datetime(df_tms_raw["dia"], errors="coerce").dt.date
    for _, row in df_tms_raw.iterrows():
        if pd.notna(row["dia"]):
            key = (row["idTransporte"], row["dia"])
            tms_dias[key] = tms_dias.get(key, 0) + int(row.get("viajes_dia") or 0)

# ── Collect all units to display ──────────────────────────────────────────────
ids_gps = set(k[0] for k in gps_dias) | set(html_gps_summary.keys())
ids_tms = set(k[0] for k in tms_dias)
ids_catalog = set(df_catalog["idTransporte"].tolist()) if not df_catalog.empty else set()

# Always include all catalog units so zero-activity ones are visible for validation
if fuente == "GPS (Samsara)":
    ids_show = ids_gps | ids_catalog
elif fuente == "TMS (Sistema)":
    ids_show = ids_tms | ids_catalog
else:
    ids_show = ids_gps | ids_tms | ids_catalog

# Build label map from catalog
label_map: dict = {}
if not df_catalog.empty:
    for _, row in df_catalog.iterrows():
        uid = row["idTransporte"]
        nombre = str(row.get("nombre", "")).strip()
        codigo = str(row.get("codigo", "")).strip()
        label_map[uid] = f"{codigo} — {nombre}" if nombre else f"Unidad {uid}"

def unit_label(uid) -> str:
    return label_map.get(uid, f"Unidad {uid}")

# Sort units by label
sorted_units = sorted(ids_show, key=lambda u: unit_label(u))

if not sorted_units:
    st.warning("No se encontraron datos para el período seleccionado.")
    st.stop()

# ── Legend ────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex;gap:20px;align-items:center;margin-bottom:8px;font-size:11px;flex-wrap:wrap;">
  <span><span style="background:#00823B;padding:2px 10px;color:white;font-weight:700">GPS + TMS</span></span>
  <span><span style="background:#005587;padding:2px 10px;color:white;font-weight:700">Solo TMS</span></span>
  <span><span style="background:#00A0C6;padding:2px 10px;color:white;font-weight:700">Solo GPS</span></span>
  <span><span style="background:#e0e0e0;padding:2px 10px;color:#666">⚫ Sin operación (validar)</span></span>
</div>
""", unsafe_allow_html=True)

# ── Build matrix ──────────────────────────────────────────────────────────────
# Values: 0=inactivo, 1=solo TMS, 2=solo GPS, 3=ambos
n_units = len(sorted_units)
n_days  = days_in_month

matrix      = np.zeros((n_units, n_days), dtype=float)
text_matrix = [["" for _ in range(n_days)] for _ in range(n_units)]

for i, uid in enumerate(sorted_units):
    for j, dia in enumerate(dias_del_mes):
        has_gps = (uid, dia) in gps_dias  # only day-level from DB
        has_tms = (uid, dia) in tms_dias
        if has_gps and has_tms:
            matrix[i, j] = 3.0
        elif has_tms:
            matrix[i, j] = 1.0
        elif has_gps:
            matrix[i, j] = 2.0
        else:
            matrix[i, j] = 0.0

        parts = []
        if has_tms:
            parts.append(f"TMS: {tms_dias.get((uid, dia), 0)} viajes")
        if has_gps:
            parts.append(f"GPS: {gps_dias.get((uid, dia), 0):.0f} km")
        text_matrix[i][j] = f"Día {dia.day}<br>" + "<br>".join(parts) if parts else f"Día {dia.day}<br>Sin actividad"

# Color scale: 0=gray(sin op), 1=blue(TMS), 2=teal(GPS), 3=green(ambos)
colorscale = [
    [0.00, "#e0e0e0"], [0.24, "#e0e0e0"],
    [0.25, "#005587"], [0.49, "#005587"],
    [0.50, "#00A0C6"], [0.74, "#00A0C6"],
    [0.75, "#00823B"], [1.00, "#00823B"],
]

y_labels  = [unit_label(uid) for uid in sorted_units]
x_labels  = [str(d.day) for d in dias_del_mes]

fig = go.Figure(data=go.Heatmap(
    z=matrix,
    x=x_labels,
    y=y_labels,
    text=text_matrix,
    hovertemplate="%{y}<br>%{text}<extra></extra>",
    colorscale=colorscale,
    showscale=False,
    zmin=0, zmax=3,
    xgap=2, ygap=2,
))

fig.update_layout(
    height=max(300, n_units * 42 + 80),
    margin=dict(t=30, b=40, l=220, r=20),
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(
        tickvals=list(range(n_days)),
        ticktext=x_labels,
        tickfont=dict(size=11),
        side="top",
        title=dict(text="Día del mes", font=dict(size=11)),
    ),
    yaxis=dict(
        tickfont=dict(size=11),
        autorange="reversed",
    ),
)

st.plotly_chart(fig, use_container_width=True)

# ── Summary KPI row ───────────────────────────────────────────────────────────
n_gps_active = len(set(k[0] for k in gps_dias) | set(html_gps_summary.keys()))
n_tms_active = len(set(k[0] for k in tms_dias))
n_sin_op     = len([uid for uid in sorted_units
                    if uid not in {k[0] for k in gps_dias}
                    and uid not in html_gps_summary
                    and not any((uid, d) in tms_dias for d in dias_del_mes)])
n_total      = len(sorted_units)

kpi_cards([
    {"label": "Unidades totales",  "value": str(n_total),      "sub": "en catálogo"},
    {"label": "Activas GPS",       "value": str(n_gps_active), "color": "teal"},
    {"label": "Activas TMS",       "value": str(n_tms_active), "color": "blue"},
    {"label": "Sin operación",     "value": str(n_sin_op),
     "sub": "requieren validación",
     "color": "red" if n_sin_op > 0 else "green"},
    {"label": "Días del mes",      "value": str(days_in_month), "sub": f"{MESES_ES[mes_sel]} {anio_sel}"},
])

st.markdown("<br>", unsafe_allow_html=True)

# ── Summary table ─────────────────────────────────────────────────────────────
panel_header("Resumen por Unidad", "Días activos GPS y TMS · utilización vs días del mes")

def nivel_util(pct: float) -> str:
    if pct >= 60:   return "🟢 Alto"
    if pct >= 35:   return "🟡 Medio"
    if pct > 0:     return "🔴 Bajo"
    return "⚫ Sin operación"

rows_summary = []
for uid in sorted_units:
    dias_gps_db  = sum(1 for d in dias_del_mes if (uid, d) in gps_dias)
    dias_tms     = sum(1 for d in dias_del_mes if (uid, d) in tms_dias)
    dias_match   = sum(1 for d in dias_del_mes if (uid, d) in gps_dias and (uid, d) in tms_dias)
    dias_tms_only = sum(1 for d in dias_del_mes if (uid, d) in tms_dias and (uid, d) not in gps_dias)
    dias_gps_only = sum(1 for d in dias_del_mes if (uid, d) in gps_dias and (uid, d) not in tms_dias)
    km_gps_db    = sum(gps_dias.get((uid, d), 0) for d in dias_del_mes)
    viajes_tms   = sum(tms_dias.get((uid, d), 0) for d in dias_del_mes)

    # Overlay HTML GPS summary when DB has no day-level data
    html = html_gps_summary.get(uid, {})
    dias_gps  = html.get("dias_activos", dias_gps_db) if use_html_gps else dias_gps_db
    km_gps    = html.get("km",           km_gps_db)   if use_html_gps else km_gps_db
    viajes_gps = html.get("viajes",      0)            if use_html_gps else 0

    dias_activos = max(dias_gps, dias_tms)
    pct = round(dias_activos / days_in_month * 100, 1)

    row: dict = {
        "Unidad":        unit_label(uid),
        "Días GPS":      dias_gps,
        "Días TMS":      dias_tms,
        "Huecos GPS":    days_in_month - dias_gps if dias_gps else "—",
        "Huecos TMS":    days_in_month - dias_tms,
        "% Util GPS":    f"{round(dias_gps/days_in_month*100,1):.1f}%" if dias_gps else "—",
        "% Util TMS":    f"{pct:.1f}%",
        "Nivel":         nivel_util(pct),
        "Km GPS":        f"{km_gps:,.0f}" if km_gps else "—",
        "Viajes TMS":    viajes_tms,
    }
    if not use_html_gps:
        row["✅ Ambos"]    = dias_match
        row["🔵 Solo TMS"] = dias_tms_only
        row["🔷 Solo GPS"] = dias_gps_only

    rows_summary.append(row)

df_summary = pd.DataFrame(rows_summary)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

if use_html_gps:
    st.caption("⚠️ Días GPS y Km GPS provienen del reporte HTML (resumen mensual por unidad, no detalle por día).")

# ── Units with no activity at all ─────────────────────────────────────────────
sin_op = [unit_label(uid) for uid in sorted_units
          if uid not in {k[0] for k in gps_dias}
          and uid not in html_gps_summary
          and not any((uid, d) in tms_dias for d in dias_del_mes)]
if sin_op:
    st.divider()
    insight(
        f"Sin operación identificada · {len(sin_op)} unidades · {MESES_ES[mes_sel]} {anio_sel}",
        "Sin actividad GPS ni TMS en el período. <strong>El responsable debe validar</strong>: "
        "inactivas, en mantenimiento, fuera de ruta o problema con dispositivo Samsara.",
        kind="d",
    )
    st.dataframe(pd.DataFrame({"Unidad": sin_op}), use_container_width=True, hide_index=True)

# ── Per-unit detail ────────────────────────────────────────────────────────────
st.divider()
panel_header("Detalle por Unidad", "Actividad diaria GPS y TMS")

unidad_detail = st.selectbox(
    "Seleccionar unidad para ver detalle diario:",
    options=[unit_label(u) for u in sorted_units],
    key="cal_detail_sel",
)

uid_sel = sorted_units[[unit_label(u) for u in sorted_units].index(unidad_detail)]

# Build daily detail for selected unit
detail_rows = []
for dia in dias_del_mes:
    has_gps = (uid_sel, dia) in gps_dias
    has_tms = (uid_sel, dia) in tms_dias
    km = gps_dias.get((uid_sel, dia), 0)
    viajes = tms_dias.get((uid_sel, dia), 0)

    if has_gps and has_tms:
        estado = "✅ GPS + TMS"
    elif has_tms:
        estado = "🔵 Solo TMS"
    elif has_gps:
        estado = "🔷 Solo GPS"
    else:
        estado = "⬜ Inactivo"

    detail_rows.append({
        "Día":       dia.strftime("%d/%m/%Y"),
        "Semana":    f"Sem {(dia.day - 1) // 7 + 1}",
        "DiaSemana": ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][dia.weekday()],
        "Estado":    estado,
        "Km GPS":    round(km, 1) if has_gps else 0,
        "Viajes TMS": viajes if has_tms else 0,
    })

df_detail = pd.DataFrame(detail_rows)

# KPIs for selected unit
dias_gps_u  = sum(1 for d in dias_del_mes if (uid_sel, d) in gps_dias)
dias_tms_u  = sum(1 for d in dias_del_mes if (uid_sel, d) in tms_dias)
km_total_u  = sum(gps_dias.get((uid_sel, d), 0) for d in dias_del_mes)
huecos_u    = days_in_month - max(dias_gps_u, dias_tms_u)
pct_u       = round(max(dias_gps_u, dias_tms_u) / days_in_month * 100, 1)

# Supplement with HTML GPS if DB is empty
if use_html_gps and uid_sel in html_gps_summary:
    html_u = html_gps_summary[uid_sel]
    dias_gps_u = html_u["dias_activos"]
    km_total_u = html_u["km"]
    huecos_u   = days_in_month - max(dias_gps_u, dias_tms_u)
    pct_u      = round(max(dias_gps_u, dias_tms_u) / days_in_month * 100, 1)

from theme import PLOTLY_LAYOUT, TEAL, GREEN_PRIMARY
kpi_cards([
    {"label": "Días activos GPS",  "value": str(dias_gps_u),       "color": "teal"},
    {"label": "Días activos TMS",  "value": str(dias_tms_u),       "color": "blue"},
    {"label": "Huecos (inactivos)","value": str(huecos_u),
     "color": "red" if huecos_u > days_in_month * 0.4 else "amber"},
    {"label": "Km GPS totales",    "value": f"{km_total_u:,.0f}",  "color": "green"},
    {"label": "% Utilización",     "value": f"{pct_u:.1f}%",
     "color": "green" if pct_u >= 60 else ("amber" if pct_u >= 35 else "red")},
])

# Daily km bar chart (only for DB GPS mode)
if km_total_u > 0 and not use_html_gps:
    df_km = df_detail[df_detail["Km GPS"] > 0].copy()
    df_km["Día_dt"] = pd.to_datetime(df_km["Día"], format="%d/%m/%Y")
    fig_km = px.bar(
        df_km, x="Día_dt", y="Km GPS",
        color_discrete_sequence=[TEAL],
        labels={"Día_dt": "Fecha", "Km GPS": "Km GPS"},
        height=220,
    )
    fig_km.update_layout(**PLOTLY_LAYOUT, xaxis_tickformat="%d/%m", margin=dict(t=10,b=10))
    st.plotly_chart(fig_km, use_container_width=True)

if use_html_gps:
    st.info(
        "El detalle diario GPS no está disponible para este mes (fuente: reporte HTML). "
        "El mapa muestra solo actividad TMS. Los KPIs GPS son del resumen mensual.",
        icon="ℹ️",
    )

# Detail table
st.dataframe(
    df_detail[["Día", "DiaSemana", "Estado", "Km GPS", "Viajes TMS"]],
    use_container_width=True,
    hide_index=True,
)

# ── GPS DB months diagnostic ───────────────────────────────────────────────────
with st.expander("🔍 Meses con datos GPS en BD (vwBI_samsaraTrips)"):
    df_meses = get_gps_meses_disponibles()
    if df_meses.empty:
        st.warning("No se encontraron registros en vwBI_samsaraTrips.")
    else:
        MESES_ES_CORTO = {1:"Ene",2:"Feb",3:"Mar",4:"Abr",5:"May",6:"Jun",
                          7:"Jul",8:"Ago",9:"Sep",10:"Oct",11:"Nov",12:"Dic"}
        df_meses["Período"] = df_meses.apply(
            lambda r: f"{MESES_ES_CORTO.get(int(r['mes']), str(int(r['mes'])))} {int(r['anio'])}", axis=1
        )
        df_meses = df_meses.rename(columns={"registros": "Registros GPS", "unidades": "Unidades"})
        st.dataframe(df_meses[["Período","Registros GPS","Unidades"]], use_container_width=True, hide_index=True)

_src_label = {"db": "vwBI_samsaraTrips", "excel": "Excel Samsara 2026",
              "html": "HTML reporte 2026", "none": "sin datos GPS"}
st.caption(
    f"Fuente GPS: {_src_label.get(gps_source, gps_source)} · "
    f"Fuente TMS: vwBI_trnViajes · "
    f"Nivel utilización: ≥60% Alto · 35-59% Medio · <35% Bajo"
)
