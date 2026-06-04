"""
GPS data from Excel files exported from Samsara (trip-level, day-accurate).
Covers January–April 2026 from uploaded GPS_Buses_*.xlsx files.

Also exposes monthly summaries from the legacy HTML export (Jan–May 2026)
as fallback for months not covered by the Excel files.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache

import pandas as pd

_DIR = os.path.dirname(__file__)
_EXCEL_JSON = os.path.join(_DIR, "data", "gps_excel_2026.json")
_HTML_JSON  = os.path.join(_DIR, "data", "gps_html_2026.json")

MESES_ORDER = {
    "Enero": 1, "Febrero": 2, "Marzo": 3, "Abril": 4, "Mayo": 5,
    "Junio": 6, "Julio": 7, "Agosto": 8, "Septiembre": 9,
    "Octubre": 10, "Noviembre": 11, "Diciembre": 12,
}
HTML_YEAR  = 2026
EXCEL_YEAR = 2026


# ── Excel (trip-level) data ───────────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_excel() -> pd.DataFrame:
    """Load trip-level GPS data from Samsara Excel exports."""
    if not os.path.exists(_EXCEL_JSON):
        return pd.DataFrame()
    with open(_EXCEL_JSON, encoding="utf-8") as f:
        records = json.load(f)
    df = pd.DataFrame(records)
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce").dt.date
    df["km"]    = pd.to_numeric(df["km"], errors="coerce").fillna(0)
    return df


def excel_has_data(year: int, month: int) -> bool:
    df = _load_excel()
    if df.empty:
        return False
    return any(
        r.year == year and r.month == month
        for r in df["fecha"].dropna()
    )


def get_excel_months() -> list[tuple[int, int]]:
    """Return sorted list of (year, month) tuples in the Excel data."""
    df = _load_excel()
    if df.empty:
        return []
    pairs = set(
        (d.year, d.month) for d in df["fecha"].dropna()
    )
    return sorted(pairs)


def get_excel_trips_for_month(year: int, month: int) -> pd.DataFrame:
    """Return all trip rows for the given year/month.

    Columns: bus_code, fecha, km, driver, start_addr, end_addr,
             start_time, end_time
    """
    df = _load_excel()
    if df.empty:
        return df
    mask = df["fecha"].apply(lambda d: d is not None and d.year == year and d.month == month)
    return df[mask].copy().reset_index(drop=True)


def get_excel_gps_days(year: int, month: int, code_to_id: dict) -> dict:
    """Build gps_dias dict {(idTransporte, date): km} from Excel data.

    code_to_id: bus_code string → idTransporte int (from vwBI_trnTransporte)
    """
    df = get_excel_trips_for_month(year, month)
    if df.empty:
        return {}
    gps_dias: dict = {}
    for _, row in df.iterrows():
        uid = code_to_id.get(str(row["bus_code"]).strip())
        if uid is None:
            continue
        key = (uid, row["fecha"])
        gps_dias[key] = gps_dias.get(key, 0.0) + float(row["km"])
    return gps_dias


# ── HTML (monthly-summary) data ───────────────────────────────────────────────

@lru_cache(maxsize=1)
def _load_html() -> dict:
    if not os.path.exists(_HTML_JSON):
        return {}
    with open(_HTML_JSON, encoding="utf-8") as f:
        return json.load(f)


def get_html_bus_month() -> pd.DataFrame:
    data = _load_html()
    if not data:
        return pd.DataFrame()
    df_bm = pd.DataFrame(data.get("bus_month", []))
    df_ur = pd.DataFrame(data.get("util_rows", []))
    if df_bm.empty:
        return df_bm
    if not df_ur.empty:
        df_bm = df_bm.merge(
            df_ur[["Mes", "Bus", "dias_cal", "idle_cal", "util_cal",
                   "km_benchmark", "km_gap"]],
            on=["Mes", "Bus"], how="left",
        )
    df_bm["anio"]    = HTML_YEAR
    df_bm["mes_num"] = df_bm["Mes"].map(MESES_ORDER)
    return df_bm.sort_values(["mes_num", "Bus"]).reset_index(drop=True)


def get_html_months() -> list[tuple[int, int]]:
    df = get_html_bus_month()
    if df.empty:
        return []
    months = df[["anio", "mes_num"]].drop_duplicates()
    return [(int(r["anio"]), int(r["mes_num"])) for _, r in months.iterrows()]


def html_has_data(year: int, month: int) -> bool:
    return (year, month) in get_html_months()


def get_html_gps_for_month(year: int, month: int) -> pd.DataFrame:
    if year != HTML_YEAR:
        return pd.DataFrame()
    df = get_html_bus_month()
    result = df[df["mes_num"] == month].copy()
    return result.reset_index(drop=True)


# ── Unified helpers ───────────────────────────────────────────────────────────

def get_all_gps_months() -> list[tuple[int, int]]:
    """All months covered by either Excel or HTML data, sorted."""
    return sorted(set(get_excel_months()) | set(get_html_months()))


def best_gps_source(year: int, month: int) -> str:
    """Return 'excel', 'html', or 'none' for the best GPS source available."""
    if excel_has_data(year, month):
        return "excel"
    if html_has_data(year, month):
        return "html"
    return "none"
