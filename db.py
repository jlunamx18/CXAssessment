"""
Database connection and query helpers.
Uses pymssql with st.cache_data for query caching.
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

    pymssql uses %s placeholders and requires cursor-based execution;
    pd.read_sql is used with the connection for convenience but params
    are substituted via cursor when needed.
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
def get_viajes(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Fetch trips within a date range."""
    sql = """
        SELECT
            idViaje,
            idTransporte,
            idChofer1,
            idChofer2,
            idTipoViaje,
            idLugarOrigen,
            idLugarDestino,
            idPago,
            idEmpresa,
            folioContrato,
            idViajeSubida,
            fechaInicio,
            fechaTermino,
            fechaIniciaRegreso,
            fechaLlegadasSeleccionada,
            Fecha_Creo_Registro,
            Ultimo_Cambio_Fecha,
            tipoViaje,
            tipoPago,
            TRIPSUMMARY,
            ObservacionesVentas,
            COMPLEMENTOS,
            EXPENSIVES,
            empresaRenta,
            comentariosRenta,
            totalRevenue,
            totalExpenses,
            totalMiles,
            totalMillasRecorridas,
            totalFuel,
            totalRenta,
            diesel,
            diselMX,
            diselUSD,
            CASETASDOLARESUSD,
            CASETASPESOSMXP,
            CASETAVIAPASSPESOSMXP,
            honorariosOperador_1,
            honorariosOperador_1_TipoCambio,
            honorariosOperador_2,
            honorariosOperador_2_TipoCambio,
            costoPerMile,
            revenuePerMile,
            grossAver,
            comisionRenta,
            costoRenta,
            tolls,
            scales,
            lumper,
            misc,
            parts,
            ntsfees,
            tklube,
            advance,
            viaticosDolares,
            viaticosPesos,
            PERMISODEPLACASUSD,
            GTOSVARIOSUSA,
            CUOTAUSD,
            milesPerGat,
            beginningOdometer,
            activo
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
        ORDER BY fechaInicio DESC
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_viajes_kpis(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Aggregate KPIs for a date range."""
    sql = """
        SELECT
            COUNT(idViaje)                              AS total_viajes,
            SUM(ISNULL(totalRevenue, 0))               AS total_revenue,
            SUM(ISNULL(totalExpenses, 0))              AS total_expenses,
            SUM(ISNULL(totalRevenue, 0))
              - SUM(ISNULL(totalExpenses, 0))          AS margen,
            SUM(ISNULL(totalMiles, 0))                 AS total_millas,
            AVG(ISNULL(revenuePerMile, 0))             AS avg_revenue_per_mile
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_viajes_por_semana(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Trips grouped by ISO week."""
    sql = """
        SELECT
            DATEPART(YEAR,  fechaInicio)    AS anio,
            DATEPART(WEEK,  fechaInicio)    AS semana,
            CAST(DATEADD(DAY,
                -(DATEPART(WEEKDAY, fechaInicio) - 2),
                CAST(fechaInicio AS DATE)) AS DATE)    AS semana_inicio,
            COUNT(idViaje)                             AS total_viajes,
            SUM(ISNULL(totalRevenue,  0))              AS total_revenue,
            SUM(ISNULL(totalExpenses, 0))              AS total_expenses
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
        GROUP BY
            DATEPART(YEAR,  fechaInicio),
            DATEPART(WEEK,  fechaInicio),
            CAST(DATEADD(DAY,
                -(DATEPART(WEEKDAY, fechaInicio) - 2),
                CAST(fechaInicio AS DATE)) AS DATE)
        ORDER BY anio, semana
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_viajes_por_tipo(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Trips grouped by tipoViaje."""
    sql = """
        SELECT
            ISNULL(tipoViaje, 'Sin tipo') AS tipoViaje,
            COUNT(idViaje)                AS total_viajes,
            SUM(ISNULL(totalRevenue, 0))  AS total_revenue
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
        GROUP BY tipoViaje
        ORDER BY total_viajes DESC
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_flota_stats(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Stats grouped by transport unit (idTransporte)."""
    sql = """
        SELECT
            ISNULL(CAST(idTransporte AS VARCHAR), 'Sin asignar') AS unidad,
            COUNT(idViaje)                AS total_viajes,
            SUM(ISNULL(totalMiles, 0))    AS total_millas,
            SUM(ISNULL(totalRevenue, 0))  AS total_revenue,
            SUM(ISNULL(totalExpenses, 0)) AS total_expenses,
            AVG(ISNULL(revenuePerMile, 0)) AS avg_revenue_per_mile
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
        GROUP BY idTransporte
        ORDER BY total_revenue DESC
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_operadores_stats(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Stats grouped by driver (idChofer1)."""
    sql = """
        SELECT
            ISNULL(CAST(idChofer1 AS VARCHAR), 'Sin asignar') AS operador,
            COUNT(idViaje)                 AS total_viajes,
            SUM(ISNULL(totalMiles, 0))     AS total_millas,
            SUM(ISNULL(totalRevenue, 0))   AS total_revenue,
            SUM(ISNULL(totalExpenses, 0))  AS total_expenses,
            AVG(ISNULL(revenuePerMile, 0)) AS avg_revenue_per_mile,
            AVG(ISNULL(costoPerMile, 0))   AS avg_costo_per_mile
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
        GROUP BY idChofer1
        ORDER BY total_revenue DESC
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_costos_desglose(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Aggregated cost breakdown for the period."""
    sql = """
        SELECT
            SUM(ISNULL(diesel, 0))                              AS diesel_usd,
            SUM(ISNULL(diselMX, 0))                            AS diesel_mxp,
            SUM(ISNULL(diselUSD, 0))                           AS diesel_usd2,
            SUM(ISNULL(CASETASDOLARESUSD, 0))                  AS casetas_usd,
            SUM(ISNULL(CASETASPESOSMXP, 0))                    AS casetas_mxp,
            SUM(ISNULL(CASETAVIAPASSPESOSMXP, 0))              AS casetas_viapass_mxp,
            SUM(ISNULL(honorariosOperador_1, 0))               AS honorarios_op1,
            SUM(ISNULL(honorariosOperador_2, 0))               AS honorarios_op2,
            SUM(ISNULL(tolls, 0))                               AS tolls,
            SUM(ISNULL(scales, 0))                             AS scales,
            SUM(ISNULL(lumper, 0))                             AS lumper,
            SUM(ISNULL(misc, 0))                               AS misc,
            SUM(ISNULL(parts, 0))                              AS parts,
            SUM(ISNULL(ntsfees, 0))                            AS ntsfees,
            SUM(ISNULL(tklube, 0))                             AS tklube,
            SUM(ISNULL(advance, 0))                            AS advance,
            SUM(ISNULL(viaticosDolares, 0))                    AS viaticos_usd,
            SUM(ISNULL(viaticosPesos, 0))                      AS viaticos_mxp,
            SUM(ISNULL(PERMISODEPLACASUSD, 0))                 AS permiso_placas_usd,
            SUM(ISNULL(GTOSVARIOSUSA, 0))                      AS gtos_varios_usa,
            SUM(ISNULL(CUOTAUSD, 0))                           AS cuota_usd,
            SUM(ISNULL(totalExpenses, 0))                      AS total_expenses
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def get_costos_por_semana(fecha_inicio: str, fecha_fin: str) -> pd.DataFrame:
    """Weekly cost per mile trend."""
    sql = """
        SELECT
            DATEPART(YEAR,  fechaInicio)    AS anio,
            DATEPART(WEEK,  fechaInicio)    AS semana,
            CAST(DATEADD(DAY,
                -(DATEPART(WEEKDAY, fechaInicio) - 2),
                CAST(fechaInicio AS DATE)) AS DATE)    AS semana_inicio,
            AVG(ISNULL(costoPerMile, 0))               AS avg_costo_per_mile,
            AVG(ISNULL(revenuePerMile, 0))             AS avg_revenue_per_mile,
            SUM(ISNULL(totalExpenses, 0))              AS total_expenses,
            SUM(ISNULL(totalMiles, 0))                 AS total_millas
        FROM vwBI_trnViajes
        WHERE fechaInicio >= %s
          AND fechaInicio <= %s
        GROUP BY
            DATEPART(YEAR,  fechaInicio),
            DATEPART(WEEK,  fechaInicio),
            CAST(DATEADD(DAY,
                -(DATEPART(WEEKDAY, fechaInicio) - 2),
                CAST(fechaInicio AS DATE)) AS DATE)
        ORDER BY anio, semana
    """
    return run_query(sql, params=(fecha_inicio, fecha_fin))


def test_connection() -> bool:
    """Test database connectivity. Returns True if successful."""
    try:
        conn = get_connection()
        conn.close()
        return True
    except Exception:
        return False
