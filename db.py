"""
Database connection and query helpers.
Uses pymssql with st.cache_data for query caching.
All trip counts use COUNT DISTINCT(idViaje).
All cost/financial aggregations are deduplicated per trip.
"""

from __future__ import annotations

import traceback
from typing import Optional

import pandas as pd
import streamlit as st

from config import DB_CONFIG, CACHE_TTL


def get_connection():
    """Create and return a new pymssql connection."""
    import pymssql  # type: ignore

    return pymssql.connect(
        server=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset=DB_CONFIG["charset"],
        tds_version=DB_CONFIG["tds_version"],
    )


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def run_query(sql: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Execute a SQL query and return results as a DataFrame.
    Results are cached for CACHE_TTL seconds.
    pymssql uses %s placeholders.
    """
    try:
        conn = get_connection()
        try:
            if params:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                df = pd.DataFrame(rows, columns=columns)
                cursor.close()
            else:
                df = pd.read_sql(sql, conn)
        finally:
            conn.close()
        return df
    except Exception as exc:
        error_msg = str(exc)
        st.error(
            f"Error al conectar con la base de datos: {error_msg}\n\n"
            "Verifique que el servidor SQL Server esté accesible y las credenciales sean correctas."
        )
        with st.expander("Detalle técnico del error"):
            st.code(traceback.format_exc(), language="text")
        return pd.DataFrame()


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_viajes_dedup(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Trips deduplicated by idViaje with catalog name joins."""
    sql = """
        SELECT
            v.idViaje,
            v.fechaInicio,
            v.fechaTermino,
            v.tipoViaje,
            v.tipoPago,
            v.idTransporte,
            t.nombre        AS nombreUnidad,
            t.placasMx      AS placasUnidad,
            v.idChofer1,
            c1.nombreCompleto AS nombreChofer1,
            v.idChofer2,
            c2.nombreCompleto AS nombreChofer2,
            v.totalRevenue,
            v.totalExpenses,
            v.totalMiles,
            v.totalMillasRecorridas,
            v.totalFuel,
            v.totalRenta,
            v.diesel,
            v.CASETASPESOSMXP,
            v.CASETASDOLARESUSD,
            v.honorariosOperador_1,
            v.honorariosOperador_2,
            v.viaticosPesos,
            v.viaticosDolares,
            v.tolls,
            v.scales,
            v.lumper,
            v.misc,
            v.advance,
            v.activo,
            v.TRIPSUMMARY
        FROM (
            SELECT DISTINCT
                idViaje, fechaInicio, fechaTermino, tipoViaje, tipoPago,
                idTransporte, idChofer1, idChofer2,
                totalRevenue, totalExpenses, totalMiles, totalMillasRecorridas,
                totalFuel, totalRenta, diesel, CASETASPESOSMXP, CASETASDOLARESUSD,
                honorariosOperador_1, honorariosOperador_2,
                viaticosPesos, viaticosDolares, tolls, scales, lumper, misc, advance,
                activo, TRIPSUMMARY
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) v
        LEFT JOIN vwBI_trnTransporte t ON v.idTransporte = t.idTransporte
        LEFT JOIN vwBI_catChoferes c1 ON v.idChofer1 = c1.idChofer
        LEFT JOIN vwBI_catChoferes c2 ON v.idChofer2 = c2.idChofer
        ORDER BY v.fechaInicio DESC
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_kpis_dedup(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """KPIs with proper deduplication using COUNT DISTINCT(idViaje)."""
    sql = """
        SELECT
            COUNT(DISTINCT idViaje)                     AS total_viajes,
            SUM(totalRevenue)                           AS total_revenue,
            SUM(totalExpenses)                          AS total_expenses,
            SUM(totalRevenue) - SUM(totalExpenses)      AS margen,
            SUM(totalMiles)                             AS total_miles,
            SUM(totalMillasRecorridas)                  AS total_km,
            AVG(CASE WHEN totalMiles > 0
                THEN totalRevenue / totalMiles END)     AS avg_rev_per_mile,
            SUM(totalRenta)                             AS total_renta,
            COUNT(DISTINCT idTransporte)                AS unidades_activas,
            COUNT(DISTINCT idChofer1)                   AS choferes_activos
        FROM (
            SELECT DISTINCT idViaje, totalRevenue, totalExpenses, totalMiles,
                   totalMillasRecorridas, totalFuel, totalRenta, idTransporte, idChofer1
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) t
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_viajes_por_semana_dedup(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Trips grouped by ISO week — COUNT DISTINCT per week."""
    sql = """
        SELECT
            DATEPART(YEAR,  fechaInicio)    AS anio,
            DATEPART(WEEK,  fechaInicio)    AS semana,
            CAST(DATEADD(DAY,
                -(DATEPART(WEEKDAY, fechaInicio) - 2),
                CAST(fechaInicio AS DATE)) AS DATE) AS semana_inicio,
            COUNT(DISTINCT idViaje)                AS total_viajes,
            SUM(totalRevenue)                      AS total_revenue,
            SUM(totalExpenses)                     AS total_expenses
        FROM (
            SELECT DISTINCT idViaje, fechaInicio, totalRevenue, totalExpenses
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) t
        GROUP BY
            DATEPART(YEAR,  fechaInicio),
            DATEPART(WEEK,  fechaInicio),
            CAST(DATEADD(DAY,
                -(DATEPART(WEEKDAY, fechaInicio) - 2),
                CAST(fechaInicio AS DATE)) AS DATE)
        ORDER BY anio, semana
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_viajes_por_mes_dedup(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Trips grouped by month — COUNT DISTINCT per month."""
    sql = """
        SELECT
            YEAR(fechaInicio)   AS anio,
            MONTH(fechaInicio)  AS mes,
            COUNT(DISTINCT idViaje) AS total_viajes,
            SUM(totalRevenue)       AS total_revenue,
            SUM(totalExpenses)      AS total_expenses
        FROM (
            SELECT DISTINCT idViaje, fechaInicio, totalRevenue, totalExpenses
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) t
        GROUP BY YEAR(fechaInicio), MONTH(fechaInicio)
        ORDER BY anio, mes
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_viajes_por_tipo_dedup(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Trips grouped by tipoViaje — COUNT DISTINCT."""
    sql = """
        SELECT
            ISNULL(tipoViaje, 'Sin tipo') AS tipoViaje,
            COUNT(DISTINCT idViaje)       AS total_viajes,
            SUM(totalRevenue)             AS total_revenue
        FROM (
            SELECT DISTINCT idViaje, tipoViaje, totalRevenue
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) t
        GROUP BY tipoViaje
        ORDER BY total_viajes DESC
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_flota_utilizacion(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Fleet utilization with days active calculation."""
    sql = """
        SELECT
            v.idTransporte,
            t.nombre        AS nombreUnidad,
            t.placasMx,
            t.marca,
            t.modelo,
            COUNT(DISTINCT v.idViaje)                       AS viajes_unicos,
            SUM(v.totalMiles)                               AS total_miles,
            SUM(v.totalRevenue)                             AS total_revenue,
            SUM(v.totalExpenses)                            AS total_expenses,
            COUNT(DISTINCT CAST(v.fechaInicio AS DATE))     AS dias_con_viaje
        FROM (
            SELECT DISTINCT idViaje, idTransporte, fechaInicio,
                            totalMiles, totalRevenue, totalExpenses
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) v
        LEFT JOIN vwBI_trnTransporte t ON v.idTransporte = t.idTransporte
        GROUP BY v.idTransporte, t.nombre, t.placasMx, t.marca, t.modelo
        ORDER BY total_revenue DESC
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_operadores_performance(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Driver performance with real names from catalog."""
    sql = """
        SELECT
            v.idChofer1,
            c.nombreCompleto    AS nombreChofer,
            c.licenciaMX,
            c.licenciaUS,
            COUNT(DISTINCT v.idViaje)   AS viajes_unicos,
            SUM(v.totalMiles)           AS total_miles,
            SUM(v.totalRevenue)         AS total_revenue,
            SUM(v.honorariosOperador_1) AS total_honorarios,
            AVG(CASE WHEN v.totalMiles > 0
                THEN v.totalRevenue / v.totalMiles END) AS rev_por_milla
        FROM (
            SELECT DISTINCT idViaje, idChofer1, totalMiles, totalRevenue, honorariosOperador_1
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
              AND idChofer1 IS NOT NULL AND idChofer1 > 0
        ) v
        LEFT JOIN vwBI_catChoferes c ON v.idChofer1 = c.idChofer
        GROUP BY v.idChofer1, c.nombreCompleto, c.licenciaMX, c.licenciaUS
        ORDER BY total_revenue DESC
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_costos_dedup(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Cost breakdown deduplicated per trip."""
    sql = """
        SELECT
            SUM(diesel)                   AS diesel,
            SUM(CASETASPESOSMXP)          AS casetasMXP,
            SUM(CASETASDOLARESUSD)        AS casetasUSD,
            SUM(honorariosOperador_1)
              + SUM(honorariosOperador_2) AS honorarios,
            SUM(viaticosPesos)            AS viaticosMXP,
            SUM(viaticosDolares)          AS viaticosUSD,
            SUM(tolls)                    AS tolls,
            SUM(scales)                   AS scales,
            SUM(lumper)                   AS lumper,
            SUM(misc)                     AS misc,
            SUM(totalRenta)               AS renta,
            SUM(totalExpenses)            AS total_expenses,
            SUM(totalRevenue)             AS total_revenue
        FROM (
            SELECT DISTINCT idViaje, diesel, CASETASPESOSMXP, CASETASDOLARESUSD,
                   honorariosOperador_1, honorariosOperador_2, viaticosPesos,
                   viaticosDolares, tolls, scales, lumper, misc, totalRenta,
                   totalExpenses, totalRevenue
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) t
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_costos_por_mes(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Monthly cost trend deduplicated."""
    sql = """
        SELECT
            YEAR(fechaInicio)   AS anio,
            MONTH(fechaInicio)  AS mes,
            SUM(diesel)         AS diesel,
            SUM(CASETASPESOSMXP + CASETASDOLARESUSD*17) AS casetasTotal,
            SUM(honorariosOperador_1 + honorariosOperador_2) AS honorarios,
            SUM(viaticosPesos)  AS viaticos,
            SUM(totalRenta)     AS renta,
            SUM(totalExpenses)  AS total_expenses,
            SUM(totalRevenue)   AS total_revenue,
            COUNT(DISTINCT idViaje) AS viajes
        FROM (
            SELECT DISTINCT idViaje, fechaInicio, diesel, CASETASPESOSMXP,
                   CASETASDOLARESUSD, honorariosOperador_1, honorariosOperador_2,
                   viaticosPesos, totalRenta, totalExpenses, totalRevenue
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
        ) t
        GROUP BY YEAR(fechaInicio), MONTH(fechaInicio)
        ORDER BY anio, mes
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_samsara_trips_raw(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Raw Samsara trips for GPS block calculation in Python.

    startMs is stored as nvarchar Unix-ms timestamp.
    Filter uses DATEADD(SECOND, TRY_CAST(startMs)/1000, epoch) to get real trip dates.
    Fecha_Creo_Registro is the DB sync date — NOT the trip date — so we avoid it here.
    """
    sql = """
        SELECT
            s.idTrip,
            s.idTransporte,
            t.nombre        AS nombreUnidad,
            t.placasMx,
            s.driverId,
            s.vehicleId,
            s.startMs,
            s.endMs,
            s.startLocation,
            s.endLocation,
            s.startLatitude,
            s.startLongitude,
            s.endLatitude,
            s.endLongitude,
            s.startOdometer,
            s.endOdometer,
            ISNULL(s.distanceMeters, 0)     AS distanceMeters,
            ISNULL(s.fuelConsumedMl, 0)     AS fuelConsumedMl,
            ISNULL(s.tollMeters, 0)         AS tollMeters,
            s.Fecha_Creo_Registro
        FROM vwBI_samsaraTrips s
        LEFT JOIN vwBI_trnTransporte t ON s.idTransporte = t.idTransporte
        WHERE TRY_CAST(s.startMs AS FLOAT) IS NOT NULL
          AND DATEADD(SECOND, CAST(TRY_CAST(s.startMs AS FLOAT) / 1000.0 AS INT), '19700101') >= %s
          AND DATEADD(SECOND, CAST(TRY_CAST(s.startMs AS FLOAT) / 1000.0 AS INT), '19700101') < DATEADD(DAY, 1, CAST(%s AS DATE))
          AND ISNULL(s.distanceMeters, 0) > 0
        ORDER BY s.idTransporte, s.startMs
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=300, show_spinner=False)
def get_gps_diagnostico() -> pd.DataFrame:
    """Return 10 raw GPS rows without date filter to inspect startMs format."""
    sql = """
        SELECT TOP 10
            s.idTransporte,
            s.startMs,
            s.endMs,
            s.Fecha_Creo_Registro,
            ISNULL(s.distanceMeters, 0) AS distanceMeters,
            TRY_CAST(s.startMs AS FLOAT)  AS startMs_float,
            TRY_CAST(s.startMs AS BIGINT) AS startMs_bigint,
            CASE WHEN TRY_CAST(s.startMs AS FLOAT) IS NOT NULL
                 THEN DATEADD(SECOND,
                        CAST(TRY_CAST(s.startMs AS FLOAT) / 1000.0 AS INT),
                        '19700101')
                 ELSE NULL END AS startMs_converted
        FROM vwBI_samsaraTrips s
        WHERE ISNULL(s.distanceMeters, 0) > 0
        ORDER BY s.Fecha_Creo_Registro DESC
    """
    return run_query(sql, ())


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_unidades_catalogo() -> pd.DataFrame:
    """Full unit catalog from vwBI_trnTransporte."""
    sql = """
        SELECT
            idTransporte,
            nombre,
            codigo,
            marca,
            modelo,
            year,
            placasMx,
            placasUs,
            pax,
            activo,
            expiraPlacasMx,
            expiraPlacasUs,
            expiraSeguroMx,
            expiraSeguroUs,
            expiraInspeccionMx,
            expiraInspeccionUs
        FROM vwBI_trnTransporte
        ORDER BY nombre
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_choferes_catalogo() -> pd.DataFrame:
    """Full driver catalog from vwBI_catChoferes."""
    sql = """
        SELECT
            idChofer,
            nombreCompleto,
            codigo,
            licenciaMX,
            licenciaUS,
            situacion,
            fecExpiraLicenciaMX,
            fecExpiraLicenciaUS,
            fecExpiraPasaporte,
            fecProximoExamenDrogas,
            PorMillaRecorrida,
            TarifaFija
        FROM vwBI_catChoferes
        ORDER BY nombreCompleto
    """
    return run_query(sql)


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_tms_dias_por_unidad(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Days with TMS activity per unit — deduplicated by idViaje."""
    sql = """
        SELECT
            v.idTransporte,
            t.nombre        AS nombreUnidad,
            t.codigo        AS codigoUnidad,
            CAST(v.fechaInicio AS DATE) AS dia,
            COUNT(DISTINCT v.idViaje)   AS viajes_dia,
            SUM(v.totalMiles)           AS miles_dia,
            SUM(v.totalMillasRecorridas) AS km_dia,
            MIN(v.tipoViaje)            AS tipo_viaje
        FROM (
            SELECT DISTINCT idViaje, idTransporte, fechaInicio,
                   totalMiles, totalMillasRecorridas, tipoViaje
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
              AND idTransporte IS NOT NULL AND idTransporte > 0
        ) v
        LEFT JOIN vwBI_trnTransporte t ON v.idTransporte = t.idTransporte
        GROUP BY v.idTransporte, t.nombre, t.codigo, CAST(v.fechaInicio AS DATE)
        ORDER BY v.idTransporte, dia
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_gps_dias_por_unidad(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Days with GPS activity per unit."""
    sql = """
        SELECT
            s.idTransporte,
            t.nombre        AS nombreUnidad,
            t.codigo        AS codigoUnidad,
            CAST(s.Fecha_Creo_Registro AS DATE) AS dia,
            COUNT(*)                        AS tramos_gps,
            SUM(ISNULL(s.distanceMeters,0)) AS metros_gps,
            SUM(ISNULL(s.distanceMeters,0)) / 1609.34 AS miles_gps,
            SUM(ISNULL(s.distanceMeters,0)) / 1000.0  AS km_gps
        FROM vwBI_samsaraTrips s
        LEFT JOIN vwBI_trnTransporte t ON s.idTransporte = t.idTransporte
        WHERE s.Fecha_Creo_Registro >= %s
          AND s.Fecha_Creo_Registro <= %s
          AND ISNULL(s.distanceMeters, 0) > 0
        GROUP BY s.idTransporte, t.nombre, t.codigo, CAST(s.Fecha_Creo_Registro AS DATE)
        ORDER BY s.idTransporte, dia
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_resumen_tms_por_unidad(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Monthly TMS summary per unit — deduplicated."""
    sql = """
        SELECT
            v.idTransporte,
            t.nombre        AS nombreUnidad,
            t.codigo        AS codigoUnidad,
            COUNT(DISTINCT v.idViaje)               AS total_viajes,
            COUNT(DISTINCT CAST(v.fechaInicio AS DATE)) AS dias_con_viaje,
            SUM(v.totalMiles)                       AS total_miles,
            SUM(v.totalMillasRecorridas)            AS total_km,
            SUM(v.totalRevenue)                     AS total_revenue,
            SUM(v.totalExpenses)                    AS total_expenses,
            MIN(v.fechaInicio)                      AS primer_viaje,
            MAX(v.fechaInicio)                      AS ultimo_viaje
        FROM (
            SELECT DISTINCT idViaje, idTransporte, fechaInicio,
                   totalMiles, totalMillasRecorridas, totalRevenue, totalExpenses
            FROM vwBI_trnViajes
            WHERE fechaInicio >= %s AND fechaInicio <= %s
              AND idTransporte IS NOT NULL AND idTransporte > 0
        ) v
        LEFT JOIN vwBI_trnTransporte t ON v.idTransporte = t.idTransporte
        GROUP BY v.idTransporte, t.nombre, t.codigo
        ORDER BY total_viajes DESC
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_resumen_gps_por_unidad(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """GPS summary per unit for the period."""
    sql = """
        SELECT
            s.idTransporte,
            t.nombre        AS nombreUnidad,
            t.codigo        AS codigoUnidad,
            COUNT(DISTINCT CAST(s.Fecha_Creo_Registro AS DATE)) AS dias_activos_gps,
            COUNT(*)                        AS total_tramos_gps,
            SUM(ISNULL(s.distanceMeters,0)) / 1000.0  AS total_km_gps,
            SUM(ISNULL(s.distanceMeters,0)) / 1609.34 AS total_miles_gps,
            MIN(s.Fecha_Creo_Registro)      AS primer_gps,
            MAX(s.Fecha_Creo_Registro)      AS ultimo_gps
        FROM vwBI_samsaraTrips s
        LEFT JOIN vwBI_trnTransporte t ON s.idTransporte = t.idTransporte
        WHERE s.Fecha_Creo_Registro >= %s
          AND s.Fecha_Creo_Registro <= %s
          AND ISNULL(s.distanceMeters, 0) > 0
        GROUP BY s.idTransporte, t.nombre, t.codigo
        ORDER BY dias_activos_gps DESC
    """
    return run_query(sql, (fecha_inicio, fecha_fin))


def test_connection() -> bool:
    """Test database connectivity. Returns True if successful."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False
