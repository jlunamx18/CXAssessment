"""
Costos — Cost analysis page.
Uses get_costos_dedup() and get_costos_por_mes() with proper trip deduplication.
Costs are summed once per idViaje — no double-counting.
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

from db import get_costos_dedup, get_costos_por_mes

st.set_page_config(
    page_title="Costos · Transport Analytics",
    page_icon="💰",
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
    primer_dia_mes = hoy.replace(day=1)

    fecha_inicio = st.date_input("Fecha inicio", value=primer_dia_mes, key="costos_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,            key="costos_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    if st.button("Actualizar datos", key="costos_refresh"):
        st.cache_data.clear()
        st.rerun()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("💰 Análisis de Costos Operativos")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")
st.info(
    "Costos deduplicados por viaje: cada costo se contabiliza una sola vez por idViaje, "
    "sin importar cuántas peticiones tenga el viaje.",
    icon="ℹ️",
)

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando costos..."):
    df_costos  = get_costos_dedup(fi_str, ff_str)
    df_mensual = get_costos_por_mes(fi_str, ff_str)

if df_costos.empty:
    st.warning("No se encontraron datos de costos para el período seleccionado.")
    st.stop()

row = df_costos.iloc[0]

def val(key: str) -> float:
    v = row.get(key, 0)
    return float(v) if pd.notna(v) else 0.0

# ── Build cost categories ─────────────────────────────────────────────────────
costos_usd = {
    "Diesel (USD)":          val("diesel"),
    "Casetas USD":           val("casetasUSD"),
    "Honorarios operadores": val("honorarios"),
    "Viáticos USD":          val("viaticosUSD"),
    "Tolls (USD)":           val("tolls"),
    "Scales (USD)":          val("scales"),
    "Lumper (USD)":          val("lumper"),
    "Misceláneos (USD)":     val("misc"),
    "Renta (USD)":           val("renta"),
}

costos_mxp = {
    "Casetas MXP":   val("casetasMXP"),
    "Viáticos MXP":  val("viaticosMXP"),
}

total_expenses = val("total_expenses")
total_revenue  = val("total_revenue")
total_honorarios = val("honorarios")
total_diesel = val("diesel")
total_casetas = val("casetasUSD") + val("casetasMXP") / 17  # approximate

# ── Summary KPIs ──────────────────────────────────────────────────────────────
margen = total_revenue - total_expenses
margen_pct = (margen / total_revenue * 100) if total_revenue else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Gastos totales (USD)", f"${total_expenses:,.2f}")
col2.metric("Ingresos totales (USD)", f"${total_revenue:,.2f}")
col3.metric("Margen (USD)", f"${margen:,.2f}", delta=f"{margen_pct:.1f}%")
col4.metric("Honorarios operadores (USD)", f"${total_honorarios:,.2f}")
col5.metric("Diesel (USD)", f"${total_diesel:,.2f}")

st.divider()

# ── Cost breakdown pie + bar ──────────────────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Desglose de costos en USD")
    df_usd = pd.DataFrame(
        {"Concepto": list(costos_usd.keys()), "Monto": list(costos_usd.values())}
    )
    df_usd = df_usd[df_usd["Monto"] > 0].sort_values("Monto", ascending=True)

    if not df_usd.empty:
        fig_bar_usd = px.bar(
            df_usd,
            x="Monto",
            y="Concepto",
            orientation="h",
            text=df_usd["Monto"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—"),
            labels={"Monto": "Monto (USD)", "Concepto": ""},
            color="Monto",
            color_continuous_scale="Reds",
            height=max(300, len(df_usd) * 35),
        )
        fig_bar_usd.update_traces(textposition="outside")
        fig_bar_usd.update_layout(
            coloraxis_showscale=False,
            margin=dict(t=20, b=10, l=10, r=60),
        )
        st.plotly_chart(fig_bar_usd, use_container_width=True)
    else:
        st.info("Sin costos USD para el período.")

    if any(v > 0 for v in costos_mxp.values()):
        st.subheader("Costos en MXP (Pesos Mexicanos)")
        df_mxp = pd.DataFrame(
            {"Concepto": list(costos_mxp.keys()), "Monto": list(costos_mxp.values())}
        )
        df_mxp = df_mxp[df_mxp["Monto"] > 0].sort_values("Monto", ascending=True)
        if not df_mxp.empty:
            fig_bar_mxp = px.bar(
                df_mxp,
                x="Monto",
                y="Concepto",
                orientation="h",
                text=df_mxp["Monto"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—"),
                labels={"Monto": "Monto (MXP)", "Concepto": ""},
                color="Monto",
                color_continuous_scale="Oranges",
                height=max(200, len(df_mxp) * 35),
            )
            fig_bar_mxp.update_traces(textposition="outside")
            fig_bar_mxp.update_layout(
                coloraxis_showscale=False,
                margin=dict(t=20, b=10, l=10, r=60),
            )
            st.plotly_chart(fig_bar_mxp, use_container_width=True)

with col_right:
    st.subheader("Distribución porcentual (USD)")
    df_pie = pd.DataFrame(
        {"Concepto": list(costos_usd.keys()), "Monto": list(costos_usd.values())}
    )
    df_pie = df_pie[df_pie["Monto"] > 0]

    if not df_pie.empty:
        threshold = df_pie["Monto"].sum() * 0.02
        df_main = df_pie[df_pie["Monto"] >= threshold]
        df_otros = df_pie[df_pie["Monto"] < threshold]
        if not df_otros.empty:
            df_main = pd.concat(
                [df_main, pd.DataFrame([{"Concepto": "Otros", "Monto": df_otros["Monto"].sum()}])],
                ignore_index=True,
            )
        fig_pie = px.pie(
            df_main,
            names="Concepto",
            values="Monto",
            hole=0.35,
            color_discrete_sequence=px.colors.qualitative.Set3,
            height=420,
        )
        fig_pie.update_traces(textinfo="label+percent")
        fig_pie.update_layout(
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("Sin costos USD para mostrar.")

# ── Monthly cost trend stacked bar ────────────────────────────────────────────
st.divider()
st.subheader("Tendencia mensual de costos (USD)")

if df_mensual.empty:
    st.warning("Sin datos mensuales para el período seleccionado.")
else:
    MESES_ES = {
        1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
    }
    df_mensual["mes_label"] = df_mensual.apply(
        lambda r: f"{MESES_ES.get(int(r['mes']), str(int(r['mes'])))} {int(r['anio'])}",
        axis=1,
    )

    # Stacked bar with cost components
    cost_cols = {
        "diesel":      "Diesel",
        "honorarios":  "Honorarios",
        "viaticos":    "Viáticos",
        "renta":       "Renta",
    }

    df_plot = df_mensual[["mes_label"] + list(cost_cols.keys())].copy()
    df_plot = df_plot.fillna(0)
    df_melted = df_plot.melt(
        id_vars="mes_label",
        value_vars=list(cost_cols.keys()),
        var_name="concepto_raw",
        value_name="Monto",
    )
    df_melted["Concepto"] = df_melted["concepto_raw"].map(cost_cols)

    fig_stack = px.bar(
        df_melted,
        x="mes_label",
        y="Monto",
        color="Concepto",
        barmode="stack",
        labels={"mes_label": "Mes", "Monto": "Monto (USD)"},
        color_discrete_sequence=px.colors.qualitative.Set2,
        height=400,
    )
    fig_stack.update_layout(
        xaxis_tickangle=-30,
        margin=dict(t=20, b=10),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

    # Revenue vs Expenses monthly
    st.subheader("Ingresos vs Gastos totales por mes (USD)")
    df_rev_exp = df_mensual[["mes_label", "total_revenue", "total_expenses"]].copy().fillna(0)
    df_rev_exp = df_rev_exp.rename(
        columns={"total_revenue": "Ingresos", "total_expenses": "Gastos"}
    )
    df_rev_melt = df_rev_exp.melt(
        id_vars="mes_label",
        value_vars=["Ingresos", "Gastos"],
        var_name="Categoria",
        value_name="Monto (USD)",
    )
    fig_rev = px.bar(
        df_rev_melt,
        x="mes_label",
        y="Monto (USD)",
        color="Categoria",
        barmode="group",
        labels={"mes_label": "Mes"},
        color_discrete_map={"Ingresos": "#2ca02c", "Gastos": "#d62728"},
        height=380,
    )
    fig_rev.update_layout(xaxis_tickangle=-30, margin=dict(t=20, b=10))
    st.plotly_chart(fig_rev, use_container_width=True)

# ── Detailed cost table ────────────────────────────────────────────────────────
st.divider()
st.subheader("Desglose de costos — período completo")

rows_usd = [
    {"Concepto": k, "Moneda": "USD", "Monto": v}
    for k, v in costos_usd.items()
    if v != 0
]
rows_mxp = [
    {"Concepto": k, "Moneda": "MXP", "Monto": v}
    for k, v in costos_mxp.items()
    if v != 0
]

df_breakdown = pd.DataFrame(rows_usd + rows_mxp)
if not df_breakdown.empty:
    df_breakdown = df_breakdown.sort_values(["Moneda", "Monto"], ascending=[True, False])
    df_breakdown["Monto"] = df_breakdown["Monto"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
else:
    st.info("Sin datos de desglose disponibles.")

st.caption(
    f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')} · "
    "Costos deduplicados: suma una vez por idViaje · "
    "USD = dólares americanos, MXP = pesos mexicanos · "
    "Fuente: vwBI_trnViajes"
)
