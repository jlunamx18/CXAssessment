"""
GPS data sourced from the embedded HTML export (mlv_fleet_platform.html).
Covers January–May 2026. Bus codes match vwBI_trnTransporte.codigo.

This module provides the same-shaped DataFrames as db.py GPS functions
so calendar and GPS pages can use either source transparently.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

import pandas as pd

_DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "gps_html_2026.json")

MESES_ORDER = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5,
    "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9,
    "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}

# Year the HTML data represents
HTML_YEAR = 2026


@lru_cache(maxsize=1)
def _load() -> dict:
    with open(_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_html_bus_month() -> pd.DataFrame:
    """Return bus×month GPS summary from HTML (all months).

    Columns: Bus, Mes, month_order, anio, viajes, km, dias_activos,
             dias_cal, idle_cal, conductores, horas, util_cal
    """
    data = _load()
    df_bm = pd.DataFrame(data["bus_month"])
    df_ur = pd.DataFrame(data["util_rows"])

    # Merge to get dias_cal and util_cal from util_rows
    df_bm = df_bm.merge(
        df_ur[["Mes", "Bus", "dias_cal", "idle_cal", "util_cal", "km_benchmark", "km_gap"]],
        on=["Mes", "Bus"],
        how="left",
    )
    df_bm["anio"] = HTML_YEAR
    df_bm["mes_num"] = df_bm["Mes"].map(MESES_ORDER)
    return df_bm.sort_values(["mes_num", "Bus"]).reset_index(drop=True)


def get_html_months() -> list[tuple[int, int]]:
    """Return list of (year, month) tuples available in the HTML data."""
    df = get_html_bus_month()
    months = df[["anio", "mes_num"]].drop_duplicates()
    return [(int(r["anio"]), int(r["mes_num"])) for _, r in months.iterrows()]


def get_html_gps_for_month(year: int, month: int) -> pd.DataFrame:
    """Return GPS summary per bus for a specific year/month.

    Columns: Bus, dias_activos, dias_cal, idle_cal, km, viajes,
             horas, util_cal, km_benchmark, km_gap
    Note: day-level breakdown is not available in the HTML data.
    """
    if year != HTML_YEAR:
        return pd.DataFrame()
    df = get_html_bus_month()
    result = df[df["mes_num"] == month].copy()
    return result.reset_index(drop=True)


def html_has_data(year: int, month: int) -> bool:
    return (year, month) in get_html_months()
