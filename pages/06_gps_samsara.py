"""
GPS / Samsara — Análisis de bloques GPS con algoritmo de agrupación por continuidad.
Implementa el algoritmo de bloques GPS (gap < 8h = mismo bloque).
Clasifica movimientos: Subida, Bajada, Local Base, Traslado.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import get_samsara_trips_raw

st.set_page_config(
    page_title="GPS Samsara · Transport Analytics",
    page_icon="📡",
    layout="wide",
)


# ── GPS block algorithm ───────────────────────────────────────────────────────

def calcular_bloques_gps(df: pd.DataFrame) -> pd.DataFrame:
    """Group GPS trips into operational blocks using 8-hour gap rule."""
    if df.empty:
        return df

    bloques = []
    bloque_id = 0

    for unidad, grupo in df.groupby("idTransporte"):
        grupo = grupo.sort_values("startMs").reset_index(drop=True)
        bloque_actual = bloque_id

        for i, row in grupo.iterrows():
            if i == 0:
                bloque_id += 1
                bloque_actual = bloque_id
            else:
                prev_end   = grupo.loc[i - 1, "endMs"]
                curr_start = row["startMs"]
                if pd.notna(prev_end) and pd.notna(curr_start):
                    gap_hours = (curr_start - prev_end).total_seconds() / 3600
                    if gap_hours >= 8:
                        bloque_id += 1
                        bloque_actual = bloque_id
            bloques.append(bloque_actual)

    df = df.copy()
    df["bloqueGPS"] = bloques
    return df


def clasificar_movimiento(start_loc, end_loc) -> str:
    """Classify GPS movement direction based on location text."""
    usa_keywords = [
        "texas", "tx", "laredo", "eagle pass", "del rio",
        "san antonio", "houston", "usa", "united states", "ee.uu",
        "nuevo laredo", "columbia", "juárez", "cd juarez",
    ]
    mty_keywords = [
        "monterrey", "mty", "nuevo león", "nl", "guadalupe",
        "san nicolás", "apodaca", "escobedo", "santa catarina",
        "san pedro garza",
    ]

    start = str(start_loc).lower() if start_loc else ""
    end   = str(end_loc).lower()   if end_loc   else ""

    end_is_usa  = any(k in end   for k in usa_keywords)
    start_is_usa = any(k in start for k in usa_keywords)
    start_is_mty = any(k in start for k in mty_keywords)
    end_is_mty   = any(k in end   for k in mty_keywords)

    if end_is_usa:
        return "Subida"
    elif start_is_usa:
        return "Bajada"
    elif start_is_mty and end_is_mty:
        return "Local Base"
    else:
        return "Traslado"


def nivel_utilizacion(pct: float) -> str:
    if pct >= 60:
        return "Alto"
    elif pct >= 35:
        return "Medio"
    else:
        return "Bajo"


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

    fecha_inicio = st.date_input("Fecha inicio", value=primer_dia_mes, key="gps_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,            key="gps_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="gps_refresh"):
        st.cache_data.clear()
        st.rerun()

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")
days_in_period = (fecha_fin - fecha_inicio).days + 1

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📡 GPS / Samsara — Bloques Operativos")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando datos GPS..."):
    df_raw = get_samsara_trips_raw(fi_str, ff_str)

if df_raw.empty:
    st.warning(
        "No se encontraron viajes GPS para el período seleccionado. "
        "Verifique que la vista vwBI_samsaraTrips contenga datos en este rango de fechas."
    )
    st.stop()

# ── Prepare timestamps ────────────────────────────────────────────────────────
# startMs/endMs are Unix milliseconds stored as nvarchar — convert via numeric
for col in ["startMs", "endMs"]:
    if col in df_raw.columns:
        numeric = pd.to_numeric(df_raw[col], errors="coerce")
        df_raw[col] = pd.to_datetime(numeric, unit="ms", errors="coerce")

df_raw = df_raw.sort_values(["idTransporte", "startMs"]).reset_index(drop=True)

# ── Calculate GPS blocks ──────────────────────────────────────────────────────
with st.spinner("Calculando bloques GPS..."):
    df_bloques_raw = calcular_bloques_gps(df_raw)

# ── Classify movement ─────────────────────────────────────────────────────────
df_bloques_raw["clasificacion"] = df_bloques_raw.apply(
    lambda r: clasificar_movimiento(r.get("startLocation"), r.get("endLocation")),
    axis=1,
)

# ── Aggregate per block ───────────────────────────────────────────────────────
df_bloques_raw["dist_km"] = df_bloques_raw["distanceMeters"].fillna(0) / 1000.0

df_bloque_agg = (
    df_bloques_raw.groupby(["bloqueGPS", "idTransporte", "nombreUnidad", "placasMx"])
    .agg(
        fecha_inicio_bloque=("startMs", "min"),
        fecha_fin_bloque=("endMs", "max"),
        km_totales=("dist_km", "sum"),
        n_trips=("idTrip", "count"),
        clasificacion=("clasificacion", lambda x: x.mode()[0] if not x.empty else "Traslado"),
        chofer_principal=("driverId", lambda x: x.dropna().mode()[0] if not x.dropna().empty else None),
        start_location_primer=("startLocation", "first"),
        end_location_ultimo=("endLocation", "last"),
    )
    .reset_index()
)

df_bloque_agg["duracion_horas"] = (
    (df_bloque_agg["fecha_fin_bloque"] - df_bloque_agg["fecha_inicio_bloque"])
    .dt.total_seconds()
    .div(3600)
    .round(1)
)

# Flag blocks > 4 days
df_bloque_agg["flag_revision"] = df_bloque_agg["duracion_horas"] > (4 * 24)

# ── Unit label ────────────────────────────────────────────────────────────────
df_bloque_agg["etiqueta_unidad"] = df_bloque_agg.apply(
    lambda r: str(r["nombreUnidad"]) if pd.notna(r.get("nombreUnidad")) and str(r.get("nombreUnidad", "")).strip()
    else f"Unidad {r['idTransporte']}",
    axis=1,
)

# ── Utilization per unit ──────────────────────────────────────────────────────
df_bloques_raw["fecha_dia"] = df_bloques_raw["startMs"].dt.date

df_util = (
    df_bloques_raw.groupby(["idTransporte", "nombreUnidad", "placasMx"])
    .agg(dias_activos=("fecha_dia", "nunique"))
    .reset_index()
)
df_util["pct_utilizacion"] = (df_util["dias_activos"] / days_in_period * 100).round(1)
df_util["nivel"] = df_util["pct_utilizacion"].apply(nivel_utilizacion)
df_util["etiqueta_unidad"] = df_util.apply(
    lambda r: str(r["nombreUnidad"]) if pd.notna(r.get("nombreUnidad")) and str(r.get("nombreUnidad", "")).strip()
    else f"Unidad {r['idTransporte']}",
    axis=1,
)

# ── KPIs ─────────────────────────────────────────────────────────────────────
total_bloques    = df_bloque_agg["bloqueGPS"].nunique()
total_km         = float(df_bloque_agg["km_totales"].sum())
total_unidades   = int(df_util["idTransporte"].nunique())
avg_utilizacion  = float(df_util["pct_utilizacion"].mean())
n_flag           = int(df_bloque_agg["flag_revision"].sum())

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total bloques GPS", f"{total_bloques:,}")
col2.metric("Km totales GPS", f"{total_km:,.1f}")
col3.metric("Unidades con actividad", f"{total_unidades:,}")
col4.metric("% Utilización promedio", f"{avg_utilizacion:.1f}%")
col5.metric("Bloques > 4 días (revisar)", f"{n_flag:,}")

if n_flag > 0:
    st.warning(
        f"{n_flag} bloque(s) GPS tienen duración mayor a 4 días. "
        "Estos registros requieren revisión.",
        icon="⚠️",
    )

st.divider()

# ── Utilization by unit — bar chart ──────────────────────────────────────────
st.subheader("Utilización por unidad (% días activos en el período)")

NIVEL_COLOR_MAP = {"Alto": "#2ca02c", "Medio": "#ff7f0e", "Bajo": "#d62728"}

df_util_sorted = df_util.sort_values("pct_utilizacion", ascending=True)
fig_util = px.bar(
    df_util_sorted,
    x="pct_utilizacion",
    y="etiqueta_unidad",
    orientation="h",
    color="nivel",
    color_discrete_map=NIVEL_COLOR_MAP,
    text=df_util_sorted["pct_utilizacion"].apply(lambda x: f"{x:.1f}%"),
    labels={
        "pct_utilizacion":  "% Utilización",
        "etiqueta_unidad":  "Unidad",
        "nivel":            "Nivel",
    },
    height=max(400, len(df_util_sorted) * 28),
)
fig_util.update_traces(textposition="outside")
fig_util.update_layout(
    margin=dict(t=20, b=10, l=10, r=60),
    yaxis_title="",
    xaxis_title="% Utilización",
)
st.plotly_chart(fig_util, use_container_width=True)

# ── Movement distribution pie ─────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Distribución de movimientos (bloques)")
    df_mov = (
        df_bloque_agg.groupby("clasificacion")
        .agg(total_bloques_mov=("bloqueGPS", "count"), km_mov=("km_totales", "sum"))
        .reset_index()
    )
    if not df_mov.empty:
        fig_mov = px.pie(
            df_mov,
            names="clasificacion",
            values="total_bloques_mov",
            hole=0.35,
            color="clasificacion",
            color_discrete_map={
                "Subida":     "#1f77b4",
                "Bajada":     "#ff7f0e",
                "Local Base": "#2ca02c",
                "Traslado":   "#9467bd",
            },
            height=380,
        )
        fig_mov.update_traces(textinfo="label+percent+value")
        fig_mov.update_layout(
            showlegend=True,
            margin=dict(t=20, b=10),
        )
        st.plotly_chart(fig_mov, use_container_width=True)
    else:
        st.info("Sin datos de movimientos para el período.")

with col_right:
    st.subheader("Km por tipo de movimiento")
    if not df_mov.empty:
        fig_km_mov = px.bar(
            df_mov.sort_values("km_mov", ascending=True),
            x="km_mov",
            y="clasificacion",
            orientation="h",
            text=df_mov.sort_values("km_mov", ascending=True)["km_mov"].apply(
                lambda x: f"{x:,.0f} km"
            ),
            color="clasificacion",
            color_discrete_map={
                "Subida":     "#1f77b4",
                "Bajada":     "#ff7f0e",
                "Local Base": "#2ca02c",
                "Traslado":   "#9467bd",
            },
            labels={"km_mov": "Km totales", "clasificacion": "Tipo"},
            height=380,
        )
        fig_km_mov.update_traces(textposition="outside")
        fig_km_mov.update_layout(
            showlegend=False,
            margin=dict(t=20, b=10, l=10, r=60),
            yaxis_title="",
        )
        st.plotly_chart(fig_km_mov, use_container_width=True)

# ── Utilization heatmap: unit × week ─────────────────────────────────────────
st.divider()
st.subheader("Mapa de calor de utilización: Unidad × Semana")

df_bloques_raw["semana_iso"] = df_bloques_raw["startMs"].dt.isocalendar().week.astype(int)
df_bloques_raw["anio_iso"]   = df_bloques_raw["startMs"].dt.isocalendar().year.astype(int)
df_bloques_raw["sem_label"]  = df_bloques_raw.apply(
    lambda r: f"{int(r['anio_iso'])}-S{int(r['semana_iso']):02d}", axis=1
)

df_heatmap_raw = (
    df_bloques_raw.groupby(["etiqueta_unidad" if "etiqueta_unidad" in df_bloques_raw.columns else "idTransporte", "sem_label"])
    .agg(dias_act=("fecha_dia", "nunique"))
    .reset_index()
)

# Add etiqueta_unidad to df_bloques_raw if needed
if "etiqueta_unidad" not in df_bloques_raw.columns:
    df_bloques_raw["etiqueta_unidad"] = df_bloques_raw.apply(
        lambda r: str(r["nombreUnidad"]) if pd.notna(r.get("nombreUnidad")) and str(r.get("nombreUnidad", "")).strip()
        else f"Unidad {r['idTransporte']}",
        axis=1,
    )
    df_heatmap_raw = (
        df_bloques_raw.groupby(["etiqueta_unidad", "sem_label"])
        .agg(dias_act=("fecha_dia", "nunique"))
        .reset_index()
    )

if not df_heatmap_raw.empty:
    pivot = df_heatmap_raw.pivot(
        index="etiqueta_unidad",
        columns="sem_label",
        values="dias_act",
    ).fillna(0)

    fig_heat = px.imshow(
        pivot,
        labels={"x": "Semana", "y": "Unidad", "color": "Días activos"},
        color_continuous_scale=["#f5f5f5", "#2ca02c"],
        aspect="auto",
        height=max(300, len(pivot) * 30),
    )
    fig_heat.update_layout(
        margin=dict(t=20, b=10, l=10, r=10),
        xaxis_tickangle=-30,
    )
    st.plotly_chart(fig_heat, use_container_width=True)
    st.caption("Color verde = más días activos en esa semana")
else:
    st.info("Sin datos suficientes para el mapa de calor.")

# ── GPS blocks table ──────────────────────────────────────────────────────────
st.divider()
st.subheader(f"Tabla de bloques GPS ({total_bloques:,} bloques)")

df_table = df_bloque_agg[[
    "etiqueta_unidad", "bloqueGPS", "clasificacion",
    "fecha_inicio_bloque", "fecha_fin_bloque", "duracion_horas",
    "km_totales", "n_trips", "chofer_principal", "flag_revision",
]].copy()

for dcol in ["fecha_inicio_bloque", "fecha_fin_bloque"]:
    df_table[dcol] = pd.to_datetime(df_table[dcol], errors="coerce").dt.strftime("%d/%m/%Y %H:%M")

df_table["km_totales"]    = df_table["km_totales"].apply(lambda x: f"{x:,.1f}")
df_table["duracion_horas"] = df_table["duracion_horas"].apply(lambda x: f"{x:,.1f} h")
df_table["flag_revision"] = df_table["flag_revision"].apply(lambda x: "⚠️ Revisar" if x else "")

df_table = df_table.rename(columns={
    "etiqueta_unidad":    "Unidad",
    "bloqueGPS":          "Bloque GPS",
    "clasificacion":      "Clasificación",
    "fecha_inicio_bloque":"Inicio bloque",
    "fecha_fin_bloque":   "Fin bloque",
    "duracion_horas":     "Duración",
    "km_totales":         "Km totales",
    "n_trips":            "Trips GPS",
    "chofer_principal":   "Chofer (driverId)",
    "flag_revision":      "Alerta",
})

st.dataframe(df_table, use_container_width=True, hide_index=True)
st.caption(
    f"Bloques calculados con regla de gap >= 8 horas entre trips consecutivos por unidad · "
    f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')} · "
    "Fuente: vwBI_samsaraTrips"
)
