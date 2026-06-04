"""
GPS / Samsara — Análisis de viajes GPS y comparación con datos operativos.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db import run_query

st.set_page_config(
    page_title="GPS Samsara · Transport Analytics",
    page_icon="📡",
    layout="wide",
)

# ── Query helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def get_samsara_trips(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Fetch Samsara GPS trips within a date range (filter on startMs)."""
    sql = """
        SELECT
            idTrip,
            idTransporte,
            driverId,
            vehicleId,
            activo,
            startMs,
            endMs,
            startLatitude,
            startLongitude,
            endLatitude,
            endLongitude,
            startLocation,
            endLocation,
            startOdometer,
            endOdometer,
            distanceMeters,
            tollMeters,
            fuelConsumedMl,
            idEmpresa,
            Fecha_Creo_Registro,
            Ultimo_Cambio_Fecha
        FROM vwBI_samsaraTrips
        WHERE startMs >= %s
          AND startMs <= %s
        ORDER BY startMs DESC
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=3600, show_spinner=False)
def get_plan_vs_real(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """
    JOIN vwBI_samsaraTrips with vwBI_trnViajes on idTransporte.
    Returns planned vs real (GPS) comparison data.
    """
    sql = """
        SELECT
            t.idViaje,
            t.idTransporte,
            t.fechaInicio,
            t.fechaTermino,
            ISNULL(t.totalMiles, 0)                             AS totalMiles,
            s.idTrip,
            s.driverId,
            s.startMs,
            s.endMs,
            ISNULL(s.distanceMeters, 0)                         AS distanceMeters,
            ISNULL(s.fuelConsumedMl, 0)                         AS fuelConsumedMl,
            ISNULL(s.distanceMeters, 0) / 1609.34               AS milesGPS,
            DATEDIFF(MINUTE, t.fechaInicio, t.fechaTermino)
                / 60.0                                          AS horasPlaneadas,
            DATEDIFF(MINUTE, s.startMs, s.endMs)
                / 60.0                                          AS horasReales,
            (ISNULL(s.distanceMeters, 0) / 1609.34)
                - ISNULL(t.totalMiles, 0)                       AS diferenciaMillas
        FROM vwBI_trnViajes t
        INNER JOIN vwBI_samsaraTrips s
            ON t.idTransporte = s.idTransporte
        WHERE s.startMs >= %s
          AND s.startMs <= %s
          AND t.fechaInicio >= %s
          AND t.fechaInicio <= %s
        ORDER BY t.idViaje DESC
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin, fecha_inicio, fecha_fin))


@st.cache_data(ttl=3600, show_spinner=False)
def get_distancia_por_vehiculo(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Distance aggregated per vehicle (idTransporte), GPS vs planned."""
    sql = """
        SELECT
            ISNULL(CAST(s.idTransporte AS VARCHAR), 'Sin asignar') AS idTransporte,
            SUM(ISNULL(s.distanceMeters, 0)) / 1609.34             AS milesGPS,
            MAX(ISNULL(t.totalMiles, 0))                           AS milesPlaneadas
        FROM vwBI_samsaraTrips s
        LEFT JOIN vwBI_trnViajes t
            ON s.idTransporte = t.idTransporte
           AND t.fechaInicio >= %s
           AND t.fechaInicio <= %s
        WHERE s.startMs >= %s
          AND s.startMs <= %s
        GROUP BY s.idTransporte
        ORDER BY milesGPS DESC
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin, fecha_inicio, fecha_fin))


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
    hace_30 = hoy - datetime.timedelta(days=30)

    fecha_inicio = st.date_input("Fecha inicio", value=hace_30, key="gps_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,     key="gps_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="gps_refresh"):
        st.cache_data.clear()
        st.rerun()

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Page header ───────────────────────────────────────────────────────────────
st.title("📡 GPS / Samsara")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando datos GPS..."):
    df_gps = get_samsara_trips(fi_str, ff_str)

if df_gps.empty:
    st.warning(
        "No se encontraron viajes GPS para el período seleccionado. "
        "Verifique que la vista vwBI_samsaraTrips contenga datos en este rango de fechas."
    )
    st.stop()

# Ensure datetime types
for col in ["startMs", "endMs"]:
    if col in df_gps.columns:
        df_gps[col] = pd.to_datetime(df_gps[col], errors="coerce")

# ── KPIs ─────────────────────────────────────────────────────────────────────
st.subheader("Indicadores clave (GPS)")

total_viajes_gps = len(df_gps)
total_distancia_m = float(df_gps["distanceMeters"].fillna(0).sum())
total_distancia_km = total_distancia_m / 1000.0

# Avg fuel efficiency: distanceMeters / fuelConsumedMl (m/mL); exclude zeros
df_fuel = df_gps[
    (df_gps["fuelConsumedMl"].fillna(0) > 0) &
    (df_gps["distanceMeters"].fillna(0) > 0)
].copy()

if not df_fuel.empty:
    df_fuel["eficiencia"] = df_fuel["distanceMeters"] / df_fuel["fuelConsumedMl"]
    avg_eficiencia = float(df_fuel["eficiencia"].mean())
else:
    avg_eficiencia = 0.0

# Duration stats
df_gps_dur = df_gps.copy()
if "startMs" in df_gps_dur.columns and "endMs" in df_gps_dur.columns:
    df_gps_dur["duracion_h"] = (
        (df_gps_dur["endMs"] - df_gps_dur["startMs"])
        .dt.total_seconds()
        .div(3600)
        .clip(lower=0)
    )
    avg_duracion_h = float(df_gps_dur["duracion_h"].dropna().mean()) if not df_gps_dur["duracion_h"].dropna().empty else 0.0
else:
    avg_duracion_h = 0.0

vehiculos_activos = int(df_gps["idTransporte"].nunique())

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Viajes GPS", f"{total_viajes_gps:,}")
col2.metric("Distancia total (km)", f"{total_distancia_km:,.1f}")
col3.metric("Distancia total (millas)", f"{total_distancia_m / 1609.34:,.1f}")
col4.metric("Eficiencia promedio (m/mL)", f"{avg_eficiencia:.2f}")
col5.metric("Vehículos activos", f"{vehiculos_activos:,}")

st.divider()

# ── Plan vs Real table ────────────────────────────────────────────────────────
st.subheader("Comparativo Plan vs Real GPS")

with st.spinner("Cargando comparativo planeado vs real..."):
    df_pvr = get_plan_vs_real(fi_str, ff_str)

if df_pvr.empty:
    st.info(
        "No se encontraron viajes con cruce entre vwBI_trnViajes y vwBI_samsaraTrips "
        "para el período seleccionado."
    )
else:
    # Ensure datetime columns
    for col in ["fechaInicio", "fechaTermino", "startMs", "endMs"]:
        if col in df_pvr.columns:
            df_pvr[col] = pd.to_datetime(df_pvr[col], errors="coerce")

    df_pvr_display = df_pvr.copy()

    # Format columns for display
    for dcol in ["fechaInicio", "fechaTermino", "startMs", "endMs"]:
        if dcol in df_pvr_display.columns:
            df_pvr_display[dcol] = df_pvr_display[dcol].dt.strftime("%d/%m/%Y %H:%M").fillna("—")

    for ncol in ["totalMiles", "milesGPS"]:
        if ncol in df_pvr_display.columns:
            df_pvr_display[ncol] = df_pvr_display[ncol].apply(
                lambda x: f"{x:,.2f}" if pd.notna(x) else "—"
            )

    for ncol in ["horasPlaneadas", "horasReales", "diferenciaMillas"]:
        if ncol in df_pvr_display.columns:
            df_pvr_display[ncol] = df_pvr_display[ncol].apply(
                lambda x: f"{x:,.2f}" if pd.notna(x) else "—"
            )

    rename_pvr = {
        "idViaje":          "ID Viaje",
        "idTransporte":     "Unidad",
        "fechaInicio":      "Inicio Planeado",
        "fechaTermino":     "Fin Planeado",
        "totalMiles":       "Millas Planeadas",
        "idTrip":           "ID Trip GPS",
        "driverId":         "ID Conductor",
        "startMs":          "Inicio GPS",
        "endMs":            "Fin GPS",
        "milesGPS":         "Millas GPS",
        "horasPlaneadas":   "Horas Planeadas",
        "horasReales":      "Horas Reales (GPS)",
        "diferenciaMillas": "Dif. Millas (GPS - Plan)",
    }

    display_cols_pvr = [c for c in rename_pvr.keys() if c in df_pvr_display.columns]
    df_pvr_display = df_pvr_display[display_cols_pvr].rename(
        columns={k: v for k, v in rename_pvr.items() if k in display_cols_pvr}
    )

    st.dataframe(df_pvr_display, use_container_width=True, hide_index=True)
    st.caption(
        f"Mostrando {len(df_pvr):,} registros · "
        "Fuente: vwBI_trnViajes INNER JOIN vwBI_samsaraTrips (idTransporte)"
    )

st.divider()

# ── Map: start locations colored by driverId ──────────────────────────────────
st.subheader("Mapa de puntos de inicio de viajes GPS")

df_map = df_gps[
    df_gps["startLatitude"].notna() &
    df_gps["startLongitude"].notna() &
    (df_gps["startLatitude"] != 0) &
    (df_gps["startLongitude"] != 0)
].copy()

if df_map.empty:
    st.info("No hay coordenadas de inicio disponibles para mostrar en el mapa.")
else:
    df_map["driverIdStr"] = df_map["driverId"].fillna(0).astype(int).astype(str)
    df_map["distancia_km"] = (df_map["distanceMeters"].fillna(0) / 1000).round(2)
    df_map["startMs_str"] = df_map["startMs"].dt.strftime("%d/%m/%Y %H:%M").fillna("—")

    fig_map = px.scatter_mapbox(
        df_map,
        lat="startLatitude",
        lon="startLongitude",
        color="driverIdStr",
        hover_name="idTrip",
        hover_data={
            "startLocation": True,
            "distancia_km": True,
            "startMs_str": True,
            "startLatitude": False,
            "startLongitude": False,
            "driverIdStr": False,
        },
        labels={
            "driverIdStr": "Conductor (ID)",
            "startLocation": "Ubicación inicio",
            "distancia_km": "Distancia (km)",
            "startMs_str": "Fecha inicio",
        },
        mapbox_style="open-street-map",
        zoom=4,
        height=500,
    )
    fig_map.update_layout(
        margin=dict(t=10, b=10, l=0, r=0),
        legend_title_text="Conductor (ID)",
    )
    st.plotly_chart(fig_map, use_container_width=True)
    st.caption(
        f"Mostrando {len(df_map):,} puntos de inicio · "
        "Coordenadas: startLatitude / startLongitude · Color por conductor (driverId)"
    )

st.divider()

# ── Bar chart: distance per vehicle GPS vs planned ────────────────────────────
st.subheader("Distancia por unidad: GPS vs Planeado (millas)")

with st.spinner("Cargando distancia por vehículo..."):
    df_dist = get_distancia_por_vehiculo(fi_str, ff_str)

if df_dist.empty:
    st.info("No hay datos de distancia por vehículo para el período seleccionado.")
else:
    # Limit to top 30 vehicles by GPS miles for readability
    df_dist = df_dist.sort_values("milesGPS", ascending=False).head(30).copy()

    df_melted = df_dist.melt(
        id_vars="idTransporte",
        value_vars=["milesGPS", "milesPlaneadas"],
        var_name="Tipo",
        value_name="Millas",
    )
    df_melted["Tipo"] = df_melted["Tipo"].map(
        {"milesGPS": "Millas GPS", "milesPlaneadas": "Millas Planeadas"}
    )

    fig_bar = px.bar(
        df_melted,
        x="idTransporte",
        y="Millas",
        color="Tipo",
        barmode="group",
        labels={
            "idTransporte": "Unidad (idTransporte)",
            "Millas": "Millas recorridas",
            "Tipo": "Fuente",
        },
        color_discrete_map={
            "Millas GPS":       "#1f77b4",
            "Millas Planeadas": "#ff7f0e",
        },
        height=450,
    )
    fig_bar.update_layout(
        xaxis_tickangle=-45,
        margin=dict(t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis_title="Unidad (idTransporte)",
        yaxis_title="Millas",
    )
    st.plotly_chart(fig_bar, use_container_width=True)
    st.caption(
        "Top 30 unidades por millas GPS · "
        "Millas GPS = distanceMeters / 1609.34 · "
        "Millas Planeadas = totalMiles de vwBI_trnViajes"
    )

st.divider()

# ── Raw GPS trips table ───────────────────────────────────────────────────────
with st.expander("Ver detalle de viajes GPS", expanded=False):
    df_raw = df_gps.copy()

    for dcol in ["startMs", "endMs", "Fecha_Creo_Registro", "Ultimo_Cambio_Fecha"]:
        if dcol in df_raw.columns:
            df_raw[dcol] = pd.to_datetime(df_raw[dcol], errors="coerce") \
                              .dt.strftime("%d/%m/%Y %H:%M").fillna("—")

    df_raw["distancia_km"] = (df_gps["distanceMeters"].fillna(0) / 1000).round(3)
    df_raw["millas_gps"]   = (df_gps["distanceMeters"].fillna(0) / 1609.34).round(3)

    display_raw_cols = [c for c in [
        "idTrip", "idTransporte", "driverId", "vehicleId", "activo",
        "startMs", "endMs", "startLocation", "endLocation",
        "distancia_km", "millas_gps",
        "fuelConsumedMl", "tollMeters",
        "startLatitude", "startLongitude", "endLatitude", "endLongitude",
    ] if c in df_raw.columns]

    rename_raw = {
        "idTrip":          "ID Trip",
        "idTransporte":    "Unidad",
        "driverId":        "Conductor ID",
        "vehicleId":       "Vehículo ID",
        "activo":          "Activo",
        "startMs":         "Inicio GPS",
        "endMs":           "Fin GPS",
        "startLocation":   "Ubicación inicio",
        "endLocation":     "Ubicación fin",
        "distancia_km":    "Distancia (km)",
        "millas_gps":      "Millas GPS",
        "fuelConsumedMl":  "Combustible (mL)",
        "tollMeters":      "Casetas (m)",
        "startLatitude":   "Lat. inicio",
        "startLongitude":  "Lon. inicio",
        "endLatitude":     "Lat. fin",
        "endLongitude":    "Lon. fin",
    }

    df_raw_display = df_raw[display_raw_cols].rename(
        columns={k: v for k, v in rename_raw.items() if k in display_raw_cols}
    )
    st.dataframe(df_raw_display, use_container_width=True, hide_index=True)
    st.caption(
        f"Total: {len(df_raw):,} viajes GPS · Fuente: vwBI_samsaraTrips · "
        f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"
    )
