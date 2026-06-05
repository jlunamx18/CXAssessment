"""
Reconciliación TMS vs GPS — contraste entre viajes registrados en sistema
y movimiento real GPS (Samsara).
Solo las 9 unidades Scania/Volvo tienen GPS; el resto aparece únicamente en TMS.
"""

from __future__ import annotations

import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import plotly.express as px
import streamlit as st

from db import (
    get_resumen_tms_por_unidad,
    get_resumen_gps_por_unidad,
    get_tms_dias_por_unidad,
    get_gps_dias_por_unidad,
)
from theme import apply_theme, sidebar_header

st.set_page_config(
    page_title="Reconciliación TMS vs GPS · Transport Analytics",
    page_icon="🔍",
    layout="wide",
)
apply_theme()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    sidebar_header()
    st.divider()
    st.markdown("**Filtros de fecha**")

    hoy = datetime.date.today()
    primer_dia_mes = hoy.replace(day=1)

    fecha_inicio = st.date_input("Fecha inicio", value=primer_dia_mes, key="rec_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,            key="rec_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="rec_refresh"):
        st.cache_data.clear()
        st.rerun()

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Page header ───────────────────────────────────────────────────────────────
st.title("🔍 Reconciliación TMS vs GPS")
st.caption("Contraste entre viajes registrados en sistema y movimiento real GPS")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

# ── Load summary data ─────────────────────────────────────────────────────────
with st.spinner("Cargando resumen TMS..."):
    df_tms = get_resumen_tms_por_unidad(fi_str, ff_str)

with st.spinner("Cargando resumen GPS..."):
    df_gps = get_resumen_gps_por_unidad(fi_str, ff_str)

# Normalize types before merge to avoid dtype issues
def _normalize_id(df: pd.DataFrame) -> pd.DataFrame:
    if not df.empty and "idTransporte" in df.columns:
        df = df.copy()
        df["idTransporte"] = pd.to_numeric(df["idTransporte"], errors="coerce")
    return df

df_tms = _normalize_id(df_tms)
df_gps = _normalize_id(df_gps)

# ── Section 1: KPI summary row ────────────────────────────────────────────────
st.divider()

unidades_tms  = int(df_tms["idTransporte"].nunique()) if not df_tms.empty else 0
unidades_gps  = int(df_gps["idTransporte"].nunique()) if not df_gps.empty else 0

if not df_tms.empty and not df_gps.empty:
    ids_tms = set(df_tms["idTransporte"].dropna().unique())
    ids_gps = set(df_gps["idTransporte"].dropna().unique())
    unidades_sin_gps = len(ids_tms - ids_gps)
else:
    ids_tms = set(df_tms["idTransporte"].dropna().unique()) if not df_tms.empty else set()
    ids_gps = set(df_gps["idTransporte"].dropna().unique()) if not df_gps.empty else set()
    unidades_sin_gps = len(ids_tms - ids_gps)

# Day-level detail for KPI counts — load now, reuse in Section 3
with st.spinner("Cargando detalle por día..."):
    df_tms_dias = get_tms_dias_por_unidad(fi_str, ff_str)
    df_gps_dias = get_gps_dias_por_unidad(fi_str, ff_str)

df_tms_dias = _normalize_id(df_tms_dias)
df_gps_dias = _normalize_id(df_gps_dias)

# Ensure dia column is date type
for df_d in [df_tms_dias, df_gps_dias]:
    if not df_d.empty and "dia" in df_d.columns:
        df_d["dia"] = pd.to_datetime(df_d["dia"], errors="coerce").dt.date

# Merge day-level data for (unit, day) pair counts
if not df_tms_dias.empty and not df_gps_dias.empty:
    df_dias_merge = pd.merge(
        df_tms_dias[["idTransporte", "dia"]].drop_duplicates(),
        df_gps_dias[["idTransporte", "dia"]].drop_duplicates(),
        on=["idTransporte", "dia"],
        how="outer",
        indicator=True,
    )
    dias_tms_sin_gps = int((df_dias_merge["_merge"] == "left_only").sum())
    dias_gps_sin_tms = int((df_dias_merge["_merge"] == "right_only").sum())
elif not df_tms_dias.empty:
    dias_tms_sin_gps = len(df_tms_dias[["idTransporte", "dia"]].drop_duplicates())
    dias_gps_sin_tms = 0
elif not df_gps_dias.empty:
    dias_tms_sin_gps = 0
    dias_gps_sin_tms = len(df_gps_dias[["idTransporte", "dia"]].drop_duplicates())
else:
    dias_tms_sin_gps = 0
    dias_gps_sin_tms = 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Unidades en TMS", f"{unidades_tms:,}")
col2.metric("Unidades con GPS", f"{unidades_gps:,}")
col3.metric("Unidades SIN GPS (en TMS)", f"{unidades_sin_gps:,}")
col4.metric("Días-unidad: TMS sin GPS", f"{dias_tms_sin_gps:,}")
col5.metric("Días-unidad: GPS sin TMS", f"{dias_gps_sin_tms:,}")

# ── Section 2: Reconciliation table by unit ───────────────────────────────────
st.divider()
st.subheader("Reconciliación por unidad")

if df_tms.empty and df_gps.empty:
    st.warning("No se encontraron datos para el período seleccionado.")
    st.stop()

# Outer merge on idTransporte
df_recon = pd.merge(
    df_tms.rename(columns={
        "nombreUnidad": "nombreUnidad_tms",
        "codigoUnidad": "codigoUnidad_tms",
    }),
    df_gps.rename(columns={
        "nombreUnidad": "nombreUnidad_gps",
        "codigoUnidad": "codigoUnidad_gps",
    }),
    on="idTransporte",
    how="outer",
)

# Fill numeric NaN with 0
num_cols = [
    "total_viajes", "dias_con_viaje", "total_miles", "total_km",
    "total_revenue", "total_expenses",
    "dias_activos_gps", "total_tramos_gps", "total_km_gps", "total_miles_gps",
]
for c in num_cols:
    if c in df_recon.columns:
        df_recon[c] = pd.to_numeric(df_recon[c], errors="coerce").fillna(0)

# Resolve best unit label
def _label(row: pd.Series) -> str:
    nombre = row.get("nombreUnidad_tms") or row.get("nombreUnidad_gps") or ""
    codigo = row.get("codigoUnidad_tms") or row.get("codigoUnidad_gps") or ""
    nombre = str(nombre).strip() if pd.notna(nombre) else ""
    codigo = str(codigo).strip() if pd.notna(codigo) else ""
    if codigo and nombre:
        return f"{codigo} — {nombre}"
    elif nombre:
        return nombre
    else:
        return f"Unidad {int(row['idTransporte'])}"

df_recon["Unidad"] = df_recon.apply(_label, axis=1)
df_recon["Código"] = df_recon.apply(
    lambda r: str(r.get("codigoUnidad_tms") or r.get("codigoUnidad_gps") or "").strip(),
    axis=1,
)

# GPS coverage %
df_recon["cobertura_gps_pct"] = df_recon.apply(
    lambda r: round(r["dias_activos_gps"] / r["dias_con_viaje"] * 100, 1)
    if r["dias_con_viaje"] > 0 else 0.0,
    axis=1,
)

# Difference km: GPS km vs TMS km converted from miles
df_recon["km_segun_tms"] = df_recon["total_miles"] * 1.609
df_recon["diferencia_km"] = df_recon["total_km_gps"] - df_recon["km_segun_tms"]

# Status
has_gps = df_recon["idTransporte"].isin(ids_gps)
has_tms = df_recon["idTransporte"].isin(ids_tms)

def _estado(row: pd.Series) -> str:
    in_gps = row["idTransporte"] in ids_gps
    in_tms = row["idTransporte"] in ids_tms
    if in_tms and in_gps:
        return "✅ Con GPS"
    elif in_tms:
        return "🔴 Sin GPS"
    else:
        return "⚠️ Solo GPS"

df_recon["Estado"] = df_recon.apply(_estado, axis=1)

# Sort by TMS viajes DESC
df_recon = df_recon.sort_values("total_viajes", ascending=False).reset_index(drop=True)

# Build display table
df_display = df_recon[[
    "Unidad", "Código", "total_viajes", "dias_con_viaje", "total_miles",
    "dias_activos_gps", "total_km_gps", "total_miles_gps",
    "cobertura_gps_pct", "diferencia_km", "Estado",
]].copy()

df_display = df_display.rename(columns={
    "total_viajes":      "Viajes TMS",
    "dias_con_viaje":    "Días TMS",
    "total_miles":       "Millas TMS",
    "dias_activos_gps":  "Días GPS",
    "total_km_gps":      "Km GPS",
    "total_miles_gps":   "Millas GPS",
    "cobertura_gps_pct": "Cobertura GPS (%)",
    "diferencia_km":     "Diferencia km (GPS-TMS)",
})

# Format numeric columns
df_display["Millas TMS"]   = df_display["Millas TMS"].apply(lambda x: f"{x:,.1f}")
df_display["Km GPS"]       = df_display["Km GPS"].apply(lambda x: f"{x:,.1f}")
df_display["Millas GPS"]   = df_display["Millas GPS"].apply(lambda x: f"{x:,.1f}")
df_display["Cobertura GPS (%)"] = df_display["Cobertura GPS (%)"].apply(lambda x: f"{x:.1f}%")
df_display["Diferencia km (GPS-TMS)"] = df_display["Diferencia km (GPS-TMS)"].apply(
    lambda x: f"{x:+,.1f}"
)

# Color-code rows: red background for "Sin GPS" units
def _row_color(row):
    if "Sin GPS" in str(row["Estado"]):
        return ["background-color: #ffd6d6"] * len(row)
    elif "Solo GPS" in str(row["Estado"]):
        return ["background-color: #fff3cd"] * len(row)
    else:
        return [""] * len(row)

styled = df_display.style.apply(_row_color, axis=1)
st.dataframe(styled, use_container_width=True, hide_index=True)
st.caption(
    f"Total: {len(df_recon)} unidades · "
    f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')} · "
    "Fuente: vwBI_trnViajes + vwBI_samsaraTrips"
)

# ── Section 3: Day-level detail (expandable) ──────────────────────────────────
st.divider()
with st.expander("Detalle por día — unidad × fecha", expanded=False):

    if df_tms_dias.empty and df_gps_dias.empty:
        st.info("No hay datos a nivel día para el período seleccionado.")
    else:
        # Outer merge on (idTransporte, dia)
        tms_d = df_tms_dias[["idTransporte", "dia", "viajes_dia", "miles_dia", "km_dia"]].copy() if not df_tms_dias.empty else pd.DataFrame(columns=["idTransporte", "dia", "viajes_dia", "miles_dia", "km_dia"])
        gps_d = df_gps_dias[["idTransporte", "dia", "tramos_gps", "km_gps", "miles_gps"]].copy() if not df_gps_dias.empty else pd.DataFrame(columns=["idTransporte", "dia", "tramos_gps", "km_gps", "miles_gps"])

        df_dia_merge = pd.merge(
            tms_d,
            gps_d,
            on=["idTransporte", "dia"],
            how="outer",
        )

        # Fill numerics
        for c in ["viajes_dia", "miles_dia", "km_dia", "tramos_gps", "km_gps", "miles_gps"]:
            if c in df_dia_merge.columns:
                df_dia_merge[c] = pd.to_numeric(df_dia_merge[c], errors="coerce").fillna(0)

        # Classify each row
        def _clasificar_dia(row: pd.Series) -> str:
            tiene_tms = row.get("viajes_dia", 0) > 0
            tiene_gps = row.get("tramos_gps", 0) > 0
            if tiene_tms and tiene_gps:
                return "✅ Match"
            elif tiene_gps and not tiene_tms:
                return "⚠️ GPS sin TMS"
            else:
                return "🔴 TMS sin GPS"

        df_dia_merge["clasificacion"] = df_dia_merge.apply(_clasificar_dia, axis=1)

        # Add unit label from summary data
        label_map: dict[int, str] = {}
        for _, r in df_recon.iterrows():
            tid = r["idTransporte"]
            if pd.notna(tid):
                label_map[int(tid)] = r["Unidad"]

        df_dia_merge["Unidad"] = df_dia_merge["idTransporte"].apply(
            lambda x: label_map.get(int(x), f"Unidad {int(x)}") if pd.notna(x) else "—"
        )

        # Summary counts per classification
        st.markdown("**Resumen de clasificaciones:**")
        resumen_cls = df_dia_merge["clasificacion"].value_counts().reset_index()
        resumen_cls.columns = ["Clasificación", "Días-unidad"]
        c1, c2, c3 = st.columns(3)
        for _, cr in resumen_cls.iterrows():
            lbl = cr["Clasificación"]
            cnt = cr["Días-unidad"]
            if "Match" in lbl:
                c1.metric(lbl, f"{cnt:,}")
            elif "GPS sin TMS" in lbl:
                c2.metric(lbl, f"{cnt:,}")
            else:
                c3.metric(lbl, f"{cnt:,}")

        st.markdown("---")

        # Stacked bar chart: days per unit by classification
        st.markdown("**Días por unidad según clasificación:**")
        df_bar_src = (
            df_dia_merge.groupby(["Unidad", "clasificacion"])
            .size()
            .reset_index(name="dias")
        )

        if not df_bar_src.empty:
            # Sort units by total days descending
            order = (
                df_bar_src.groupby("Unidad")["dias"]
                .sum()
                .sort_values(ascending=True)
                .index.tolist()
            )
            fig_bar = px.bar(
                df_bar_src,
                x="dias",
                y="Unidad",
                color="clasificacion",
                orientation="h",
                color_discrete_map={
                    "✅ Match":        "#2ca02c",
                    "⚠️ GPS sin TMS":  "#ff7f0e",
                    "🔴 TMS sin GPS":  "#d62728",
                },
                labels={"dias": "Días", "Unidad": "Unidad", "clasificacion": "Clasificación"},
                height=max(350, len(order) * 30),
                category_orders={"Unidad": order},
            )
            fig_bar.update_layout(
                barmode="stack",
                margin=dict(t=20, b=10, l=10, r=10),
                yaxis_title="",
                legend_title="Clasificación",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # Detail table
        st.markdown("**Tabla de detalle:**")
        df_dia_show = df_dia_merge[[
            "Unidad", "dia", "viajes_dia", "miles_dia", "km_dia",
            "tramos_gps", "km_gps", "clasificacion",
        ]].copy()
        df_dia_show = df_dia_show.sort_values(["Unidad", "dia"]).reset_index(drop=True)
        df_dia_show = df_dia_show.rename(columns={
            "dia":           "Fecha",
            "viajes_dia":    "Viajes TMS",
            "miles_dia":     "Millas TMS",
            "km_dia":        "Km TMS",
            "tramos_gps":    "Tramos GPS",
            "km_gps":        "Km GPS",
            "clasificacion": "Clasificación",
        })
        df_dia_show["Millas TMS"] = df_dia_show["Millas TMS"].apply(lambda x: f"{x:,.1f}")
        df_dia_show["Km TMS"]     = df_dia_show["Km TMS"].apply(lambda x: f"{x:,.1f}")
        df_dia_show["Km GPS"]     = df_dia_show["Km GPS"].apply(lambda x: f"{x:,.1f}")
        st.dataframe(df_dia_show, use_container_width=True, hide_index=True)

# ── Section 4: Alerts ─────────────────────────────────────────────────────────
st.divider()
st.subheader("Alertas de reconciliación")

alerts_generated = False

# Prepare per-unit day counts for alerts (reuse df_dia_merge if available)
if not df_tms_dias.empty or not df_gps_dias.empty:
    tms_d_alert = df_tms_dias[["idTransporte", "dia", "viajes_dia"]].copy() if not df_tms_dias.empty else pd.DataFrame(columns=["idTransporte", "dia", "viajes_dia"])
    gps_d_alert = df_gps_dias[["idTransporte", "dia", "tramos_gps"]].copy() if not df_gps_dias.empty else pd.DataFrame(columns=["idTransporte", "dia", "tramos_gps"])

    df_alert_days = pd.merge(
        tms_d_alert,
        gps_d_alert,
        on=["idTransporte", "dia"],
        how="outer",
    )
    for c in ["viajes_dia", "tramos_gps"]:
        if c in df_alert_days.columns:
            df_alert_days[c] = pd.to_numeric(df_alert_days[c], errors="coerce").fillna(0)

    df_alert_days["tiene_tms"] = df_alert_days["viajes_dia"] > 0
    df_alert_days["tiene_gps"] = df_alert_days["tramos_gps"] > 0

    tms_sin_gps_por_unidad = (
        df_alert_days[df_alert_days["tiene_tms"] & ~df_alert_days["tiene_gps"]]
        .groupby("idTransporte")
        .size()
        .reset_index(name="dias_tms_sin_gps")
    )

    gps_sin_tms_por_unidad = (
        df_alert_days[df_alert_days["tiene_gps"] & ~df_alert_days["tiene_tms"]]
        .groupby("idTransporte")
        .size()
        .reset_index(name="dias_gps_sin_tms")
    )

    # Build label lookup
    label_lookup: dict[int, str] = {}
    for _, r in df_recon.iterrows():
        tid = r["idTransporte"]
        if pd.notna(tid):
            label_lookup[int(tid)] = r["Unidad"]

    # Alert type 1: TMS days without GPS
    if not tms_sin_gps_por_unidad.empty:
        for _, row in tms_sin_gps_por_unidad.sort_values("dias_tms_sin_gps", ascending=False).iterrows():
            tid  = int(row["idTransporte"])
            days = int(row["dias_tms_sin_gps"])
            name = label_lookup.get(tid, f"Unidad {tid}")
            st.error(
                f"🔴 **{name}** — {days} día(s) con viajes en TMS sin registro GPS "
                "(GPS apagado o sin dispositivo)",
                icon=None,
            )
            alerts_generated = True

    # Alert type 2: GPS days without TMS
    if not gps_sin_tms_por_unidad.empty:
        for _, row in gps_sin_tms_por_unidad.sort_values("dias_gps_sin_tms", ascending=False).iterrows():
            tid  = int(row["idTransporte"])
            days = int(row["dias_gps_sin_tms"])
            name = label_lookup.get(tid, f"Unidad {tid}")
            st.warning(
                f"⚠️ **{name}** — {days} día(s) con movimiento GPS sin viaje en TMS "
                "(operación no capturada en sistema)",
                icon=None,
            )
            alerts_generated = True

# Alert type 3: KM discrepancy > 20%
if not df_recon.empty:
    df_km_check = df_recon[df_recon["idTransporte"].isin(ids_gps)].copy()
    df_km_check = df_km_check[df_km_check["km_segun_tms"] > 0].copy()

    if not df_km_check.empty:
        df_km_check["pct_diff"] = (
            (df_km_check["total_km_gps"] - df_km_check["km_segun_tms"]).abs()
            / df_km_check["km_segun_tms"]
            * 100
        ).round(1)

        for _, row in df_km_check[df_km_check["pct_diff"] > 20].sort_values("pct_diff", ascending=False).iterrows():
            name    = row["Unidad"]
            pct     = row["pct_diff"]
            km_gps  = row["total_km_gps"]
            km_tms  = row["km_segun_tms"]
            st.info(
                f"📊 **{name}** — diferencia de {pct:.1f}% entre km GPS ({km_gps:,.0f} km) "
                f"y km TMS ({km_tms:,.0f} km estimados desde millas)",
                icon=None,
            )
            alerts_generated = True

if not alerts_generated:
    st.success("No se detectaron alertas de reconciliación para el período seleccionado.")

# ── Section 5: KM comparison chart ───────────────────────────────────────────
st.divider()
st.subheader("Comparación de kilómetros: TMS vs GPS (unidades con GPS)")

df_km_plot = df_recon[df_recon["idTransporte"].isin(ids_gps)].copy()

if df_km_plot.empty:
    st.info(
        "No se encontraron unidades con datos GPS para el período seleccionado. "
        "Verifique que la vista vwBI_samsaraTrips contenga datos en este rango de fechas."
    )
else:
    df_km_plot = df_km_plot.sort_values("km_segun_tms", ascending=False).reset_index(drop=True)

    # Build long-format dataframe for grouped bar
    rows_long = []
    for _, r in df_km_plot.iterrows():
        rows_long.append({
            "Unidad": r["Unidad"],
            "Fuente": "Km según TMS",
            "Kilómetros": round(float(r["km_segun_tms"]), 1),
        })
        rows_long.append({
            "Unidad": r["Unidad"],
            "Fuente": "Km según GPS",
            "Kilómetros": round(float(r["total_km_gps"]), 1),
        })

    df_long = pd.DataFrame(rows_long)

    fig_km = px.bar(
        df_long,
        x="Unidad",
        y="Kilómetros",
        color="Fuente",
        barmode="group",
        color_discrete_map={
            "Km según TMS": "#1f77b4",
            "Km según GPS": "#2ca02c",
        },
        labels={"Kilómetros": "Kilómetros", "Unidad": "Unidad", "Fuente": "Fuente"},
        text="Kilómetros",
        height=max(400, len(df_km_plot) * 40),
    )
    fig_km.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_km.update_layout(
        margin=dict(t=20, b=10, l=10, r=10),
        xaxis_tickangle=-35,
        yaxis_title="Kilómetros",
        legend_title="Fuente",
        uniformtext_minsize=8,
        uniformtext_mode="hide",
    )
    st.plotly_chart(fig_km, use_container_width=True)
    st.caption(
        "Km TMS calculados desde millas (×1.609) · "
        "Km GPS directamente desde vwBI_samsaraTrips (distanceMeters / 1000) · "
        f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}"
    )
