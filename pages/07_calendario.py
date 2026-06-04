"""
Calendario de Utilización — matriz flota × días del mes.
Muestra GPS y TMS combinados: huecos visibles de un vistazo.
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

from db import get_samsara_trips_raw, get_tms_dias_por_unidad, get_unidades_catalogo

st.set_page_config(
    page_title="Calendario · Transport Analytics",
    page_icon="📅",
    layout="wide",
)

MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo",  6: "Junio",   7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

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
    st.markdown("**Período**")

    hoy = datetime.date.today()
    anio_sel = st.selectbox(
        "Año", options=list(range(hoy.year - 2, hoy.year + 1)),
        index=2, key="cal_anio",
    )
    mes_sel = st.selectbox(
        "Mes", options=list(range(1, 13)),
        index=hoy.month - 1,
        format_func=lambda m: MESES_ES[m],
        key="cal_mes",
    )
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
st.title("📅 Calendario de Utilización")
st.caption(f"{MESES_ES[mes_sel]} {anio_sel} · {days_in_month} días")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando datos..."):
    df_gps_raw = get_samsara_trips_raw(fi_str, ff_str)
    df_tms_raw = get_tms_dias_por_unidad(fi_str, ff_str)
    df_catalog = get_unidades_catalogo()

# ── Build GPS active days ─────────────────────────────────────────────────────
# startMs is Unix epoch milliseconds stored as nvarchar — convert via numeric
gps_dias: dict[tuple, float] = {}   # (idTransporte, date) → km
if not df_gps_raw.empty:
    df_gps_raw["startMs_dt"] = pd.to_datetime(
        pd.to_numeric(df_gps_raw["startMs"], errors="coerce"), unit="ms", errors="coerce"
    )
    df_gps_raw["fecha_dia"] = df_gps_raw["startMs_dt"].dt.date
    for _, row in df_gps_raw.iterrows():
        if pd.notna(row["fecha_dia"]):
            key = (row["idTransporte"], row["fecha_dia"])
            gps_dias[key] = gps_dias.get(key, 0) + float(row.get("distanceMeters") or 0) / 1000

# ── Build TMS active days ─────────────────────────────────────────────────────
tms_dias: dict[tuple, int] = {}    # (idTransporte, date) → viajes
if not df_tms_raw.empty:
    df_tms_raw["dia"] = pd.to_datetime(df_tms_raw["dia"], errors="coerce").dt.date
    for _, row in df_tms_raw.iterrows():
        if pd.notna(row["dia"]):
            key = (row["idTransporte"], row["dia"])
            tms_dias[key] = tms_dias.get(key, 0) + int(row.get("viajes_dia") or 0)

# ── Collect all units to display ──────────────────────────────────────────────
ids_gps = set(k[0] for k in gps_dias)
ids_tms = set(k[0] for k in tms_dias)

if fuente == "GPS (Samsara)":
    ids_show = ids_gps
elif fuente == "TMS (Sistema)":
    ids_show = ids_tms
else:
    ids_show = ids_gps | ids_tms

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
<div style="display:flex;gap:20px;align-items:center;margin-bottom:8px;font-size:13px;">
  <span><span style="background:#2ca02c;padding:2px 10px;border-radius:3px;color:white">GPS + TMS</span></span>
  <span><span style="background:#1f77b4;padding:2px 10px;border-radius:3px;color:white">Solo TMS</span></span>
  <span><span style="background:#17becf;padding:2px 10px;border-radius:3px;color:white">Solo GPS</span></span>
  <span><span style="background:#e0e0e0;padding:2px 10px;border-radius:3px;color:#666">Inactivo (hueco)</span></span>
</div>
""", unsafe_allow_html=True)

# ── Build matrix ──────────────────────────────────────────────────────────────
# Values: 0=inactivo, 1=solo TMS, 2=solo GPS, 3=ambos
n_units = len(sorted_units)
n_days  = days_in_month

matrix     = np.zeros((n_units, n_days), dtype=float)
text_matrix = [["" for _ in range(n_days)] for _ in range(n_units)]

for i, uid in enumerate(sorted_units):
    for j, dia in enumerate(dias_del_mes):
        has_gps = (uid, dia) in gps_dias
        has_tms = (uid, dia) in tms_dias
        if has_gps and has_tms:
            matrix[i, j] = 3.0
        elif has_tms:
            matrix[i, j] = 1.0
        elif has_gps:
            matrix[i, j] = 2.0
        else:
            matrix[i, j] = 0.0

        # Tooltip text
        parts = []
        if has_tms:
            parts.append(f"TMS: {tms_dias.get((uid, dia), 0)} viajes")
        if has_gps:
            parts.append(f"GPS: {gps_dias.get((uid, dia), 0):.0f} km")
        text_matrix[i][j] = f"Día {dia.day}<br>" + "<br>".join(parts) if parts else f"Día {dia.day}<br>Sin actividad"

# Color scale: 0=gray, 1=blue(TMS), 2=teal(GPS), 3=green(ambos)
colorscale = [
    [0.00, "#e0e0e0"], [0.24, "#e0e0e0"],
    [0.25, "#1f77b4"], [0.49, "#1f77b4"],
    [0.50, "#17becf"], [0.74, "#17becf"],
    [0.75, "#2ca02c"], [1.00, "#2ca02c"],
]

y_labels  = [unit_label(uid) for uid in sorted_units]
x_labels  = [str(d.day) for d in dias_del_mes]

# Mark weekends
x_ticks_color = []
for d in dias_del_mes:
    if d.weekday() >= 5:  # Sat/Sun
        x_ticks_color.append("#c0392b")
    else:
        x_ticks_color.append("#333333")

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

# ── Summary KPI table ─────────────────────────────────────────────────────────
st.subheader("Resumen por unidad")

def nivel_util(pct: float) -> str:
    if pct >= 60: return "🟢 Alto"
    if pct >= 35: return "🟡 Medio"
    return "🔴 Bajo"

rows_summary = []
for uid in sorted_units:
    dias_gps = sum(1 for d in dias_del_mes if (uid, d) in gps_dias)
    dias_tms = sum(1 for d in dias_del_mes if (uid, d) in tms_dias)
    dias_match = sum(1 for d in dias_del_mes if (uid, d) in gps_dias and (uid, d) in tms_dias)
    dias_tms_only = sum(1 for d in dias_del_mes if (uid, d) in tms_dias and (uid, d) not in gps_dias)
    dias_gps_only = sum(1 for d in dias_del_mes if (uid, d) in gps_dias and (uid, d) not in tms_dias)
    km_gps = sum(gps_dias.get((uid, d), 0) for d in dias_del_mes)
    viajes_tms = sum(tms_dias.get((uid, d), 0) for d in dias_del_mes)

    dias_activos = max(dias_gps, dias_tms)
    pct = round(dias_activos / days_in_month * 100, 1)

    rows_summary.append({
        "Unidad": unit_label(uid),
        "Días GPS": dias_gps,
        "Días TMS": dias_tms,
        "✅ Ambos": dias_match,
        "🔵 Solo TMS": dias_tms_only,
        "🔷 Solo GPS": dias_gps_only,
        "Huecos": days_in_month - dias_activos,
        "% Utilización": f"{pct:.1f}%",
        "Nivel": nivel_util(pct),
        "Km GPS": f"{km_gps:,.0f}",
        "Viajes TMS": viajes_tms,
    })

df_summary = pd.DataFrame(rows_summary)
st.dataframe(df_summary, use_container_width=True, hide_index=True)

# ── Per-unit detail expandable ────────────────────────────────────────────────
st.divider()
st.subheader("Detalle por unidad")

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
        "Día": dia.strftime("%d/%m/%Y"),
        "Semana": f"Sem {(dia.day - 1) // 7 + 1}",
        "DiaSemana": ["Lun","Mar","Mié","Jue","Vie","Sáb","Dom"][dia.weekday()],
        "Estado": estado,
        "Km GPS": round(km, 1) if has_gps else 0,
        "Viajes TMS": viajes if has_tms else 0,
    })

df_detail = pd.DataFrame(detail_rows)

# KPIs for selected unit
dias_gps_u   = sum(1 for d in dias_del_mes if (uid_sel, d) in gps_dias)
dias_tms_u   = sum(1 for d in dias_del_mes if (uid_sel, d) in tms_dias)
huecos_u     = days_in_month - max(dias_gps_u, dias_tms_u)
km_total_u   = sum(gps_dias.get((uid_sel, d), 0) for d in dias_del_mes)
pct_u        = round(max(dias_gps_u, dias_tms_u) / days_in_month * 100, 1)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Días activos GPS", dias_gps_u)
c2.metric("Días activos TMS", dias_tms_u)
c3.metric("Huecos (inactivos)", huecos_u)
c4.metric("Km GPS totales", f"{km_total_u:,.0f}")
c5.metric("% Utilización", f"{pct_u:.1f}%")

# Daily km bar chart
if km_total_u > 0:
    df_km = df_detail[df_detail["Km GPS"] > 0].copy()
    df_km["Día_dt"] = pd.to_datetime(df_km["Día"], format="%d/%m/%Y")
    fig_km = px.bar(
        df_km, x="Día_dt", y="Km GPS",
        color_discrete_sequence=["#17becf"],
        labels={"Día_dt": "Fecha", "Km GPS": "Km GPS"},
        height=250,
    )
    fig_km.update_layout(
        margin=dict(t=10, b=10),
        xaxis_tickformat="%d/%m",
    )
    st.plotly_chart(fig_km, use_container_width=True)

# Detail table — highlight inactive days
st.dataframe(
    df_detail[["Día", "DiaSemana", "Estado", "Km GPS", "Viajes TMS"]],
    use_container_width=True,
    hide_index=True,
)

st.caption(
    f"Fuente: vwBI_samsaraTrips (GPS) + vwBI_trnViajes (TMS) · "
    f"Nivel utilización: ≥60% Alto · 35-59% Medio · <35% Bajo"
)
