"""
Costos — Cost analysis page.
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

from db import get_costos_desglose, get_costos_por_semana

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
    hace_30 = hoy - datetime.timedelta(days=30)

    fecha_inicio = st.date_input("Fecha inicio", value=hace_30, key="costos_fi")
    fecha_fin    = st.date_input("Fecha fin",    value=hoy,     key="costos_ff")

    if fecha_inicio > fecha_fin:
        st.error("La fecha de inicio debe ser anterior a la fecha fin.")
        st.stop()

    moneda_vista = st.radio(
        "Vista de moneda",
        options=["USD (Dólares)", "MXP (Pesos)", "Ambas"],
        index=0,
        help="Selecciona la moneda para visualizar los costos. "
             "Algunos campos ya están en USD, otros en MXP según el origen del gasto.",
    )

    if st.button("🔄 Actualizar datos", key="costos_refresh"):
        st.cache_data.clear()

# ── Page header ───────────────────────────────────────────────────────────────
st.title("💰 Análisis de Costos Operativos")
st.caption(f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')}")

fi_str = fecha_inicio.strftime("%Y-%m-%d")
ff_str = fecha_fin.strftime("%Y-%m-%d")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Cargando costos..."):
    df_desglose  = get_costos_desglose(fi_str, ff_str)
    df_tendencia = get_costos_por_semana(fi_str, ff_str)

if df_desglose.empty:
    st.warning("No se encontraron datos de costos para el período seleccionado.")
    st.stop()

row = df_desglose.iloc[0]

# ── Helper to safely get float ────────────────────────────────────────────────
def val(key: str) -> float:
    v = row.get(key, 0)
    return float(v) if pd.notna(v) else 0.0

# ── Build cost categories ─────────────────────────────────────────────────────
costos_usd = {
    "Diesel (USD)":         val("diesel_usd") + val("diesel_usd2"),
    "Casetas (USD)":        val("casetas_usd"),
    "Honorarios Op.1 (USD)":val("honorarios_op1"),
    "Honorarios Op.2 (USD)":val("honorarios_op2"),
    "Tolls (USD)":          val("tolls"),
    "Scales (USD)":         val("scales"),
    "Lumper (USD)":         val("lumper"),
    "Misceláneos (USD)":    val("misc"),
    "Partes (USD)":         val("parts"),
    "NTS Fees (USD)":       val("ntsfees"),
    "TK Lube (USD)":        val("tklube"),
    "Advance (USD)":        val("advance"),
    "Viáticos (USD)":       val("viaticos_usd"),
    "Permiso Placas (USD)": val("permiso_placas_usd"),
    "Gtos Varios USA (USD)":val("gtos_varios_usa"),
    "Cuota (USD)":          val("cuota_usd"),
}

costos_mxp = {
    "Diesel (MXP)":           val("diesel_mxp"),
    "Casetas (MXP)":          val("casetas_mxp"),
    "Casetas ViaPass (MXP)":  val("casetas_viapass_mxp"),
    "Viáticos (MXP)":         val("viaticos_mxp"),
}

total_expenses = val("total_expenses")

# ── Summary KPIs ──────────────────────────────────────────────────────────────
total_costos_usd = sum(costos_usd.values())
total_costos_mxp = sum(costos_mxp.values())
total_diesel     = val("diesel_usd") + val("diesel_usd2") + val("diesel_mxp") / 17  # rough estimate
total_casetas    = val("casetas_usd") + val("casetas_mxp") / 17
total_honorarios = val("honorarios_op1") + val("honorarios_op2")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Gastos totales (USD)", f"${total_expenses:,.2f}")
col2.metric("Suma costos en USD", f"${total_costos_usd:,.2f}")
col3.metric("Suma costos en MXP", f"${total_costos_mxp:,.2f}")
col4.metric("Total honorarios operadores (USD)", f"${total_honorarios:,.2f}")
col5.metric("Total casetas (USD)", f"${val('casetas_usd'):,.2f}")

st.info(
    "Nota: Los costos en MXP (pesos mexicanos) se muestran en su moneda original. "
    "Los costos en USD son dólares americanos. No se aplica conversión automática.",
    icon="ℹ️",
)

st.divider()

# ── Desglose de costos — Stacked / Pie ───────────────────────────────────────
col_left, col_right = st.columns([2, 1])

with col_left:
    st.subheader("Desglose de costos operativos")

    if moneda_vista in ("USD (Dólares)", "Ambas"):
        df_usd = pd.DataFrame(
            {"Categoría": list(costos_usd.keys()), "Monto": list(costos_usd.values())}
        )
        df_usd = df_usd[df_usd["Monto"] > 0].sort_values("Monto", ascending=True)

        if not df_usd.empty:
            fig_h_usd = px.bar(
                df_usd,
                x="Monto",
                y="Categoría",
                orientation="h",
                text=df_usd["Monto"].apply(lambda x: f"${x:,.2f}"),
                labels={"Monto": "Monto (USD)", "Categoría": ""},
                color="Monto",
                color_continuous_scale="Reds",
                title="Costos en USD",
                height=max(350, len(df_usd) * 28),
            )
            fig_h_usd.update_traces(textposition="outside")
            fig_h_usd.update_layout(
                coloraxis_showscale=False,
                margin=dict(t=40, b=10, l=10, r=40),
            )
            st.plotly_chart(fig_h_usd, use_container_width=True)

    if moneda_vista in ("MXP (Pesos)", "Ambas"):
        df_mxp = pd.DataFrame(
            {"Categoría": list(costos_mxp.keys()), "Monto": list(costos_mxp.values())}
        )
        df_mxp = df_mxp[df_mxp["Monto"] > 0].sort_values("Monto", ascending=True)

        if not df_mxp.empty:
            fig_h_mxp = px.bar(
                df_mxp,
                x="Monto",
                y="Categoría",
                orientation="h",
                text=df_mxp["Monto"].apply(lambda x: f"${x:,.2f}"),
                labels={"Monto": "Monto (MXP)", "Categoría": ""},
                color="Monto",
                color_continuous_scale="Oranges",
                title="Costos en MXP (Pesos Mexicanos)",
                height=max(200, len(df_mxp) * 28),
            )
            fig_h_mxp.update_traces(textposition="outside")
            fig_h_mxp.update_layout(
                coloraxis_showscale=False,
                margin=dict(t=40, b=10, l=10, r=40),
            )
            st.plotly_chart(fig_h_mxp, use_container_width=True)

with col_right:
    st.subheader("Distribución porcentual (USD)")
    df_pie_data = pd.DataFrame(
        {"Categoría": list(costos_usd.keys()), "Monto": list(costos_usd.values())}
    )
    df_pie_data = df_pie_data[df_pie_data["Monto"] > 0]

    if not df_pie_data.empty:
        # Group small categories into "Otros"
        threshold = df_pie_data["Monto"].sum() * 0.02
        df_pie_main = df_pie_data[df_pie_data["Monto"] >= threshold]
        df_pie_otros = df_pie_data[df_pie_data["Monto"] < threshold]

        if not df_pie_otros.empty:
            otros_row = pd.DataFrame(
                [{"Categoría": "Otros", "Monto": df_pie_otros["Monto"].sum()}]
            )
            df_pie_main = pd.concat([df_pie_main, otros_row], ignore_index=True)

        fig_pie = px.pie(
            df_pie_main,
            names="Categoría",
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
        st.info("Sin datos de costos USD para mostrar.")

# ── Weekly cost per mile trend ─────────────────────────────────────────────────
st.divider()
st.subheader("Tendencia semanal: Costo y Revenue por milla")

if df_tendencia.empty:
    st.info("Sin datos semanales para el período seleccionado.")
else:
    df_tend = df_tendencia.copy()

    if "semana_inicio" in df_tend.columns:
        df_tend["semana_label"] = df_tend.apply(
            lambda r: f"Sem {int(r['semana'])} ({r['semana_inicio']})"
            if pd.notna(r.get("semana_inicio"))
            else f"Sem {int(r['semana'])}",
            axis=1,
        )
    else:
        df_tend["semana_label"] = df_tend["semana"].apply(lambda x: f"Sem {int(x)}")

    fig_trend = go.Figure()

    fig_trend.add_trace(
        go.Scatter(
            x=df_tend["semana_label"],
            y=df_tend["avg_costo_per_mile"],
            mode="lines+markers",
            name="Costo/Milla (USD)",
            line=dict(color="#d62728", width=2),
            marker=dict(size=8),
        )
    )
    fig_trend.add_trace(
        go.Scatter(
            x=df_tend["semana_label"],
            y=df_tend["avg_revenue_per_mile"],
            mode="lines+markers",
            name="Revenue/Milla (USD)",
            line=dict(color="#2ca02c", width=2),
            marker=dict(size=8),
        )
    )

    fig_trend.update_layout(
        height=380,
        xaxis_title="Semana",
        yaxis_title="USD por Milla",
        xaxis_tickangle=-30,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=40, b=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # Weekly expenses bar chart
    st.subheader("Gastos totales por semana (USD)")
    fig_exp_bar = px.bar(
        df_tend,
        x="semana_label",
        y="total_expenses",
        text=df_tend["total_expenses"].apply(lambda x: f"${x:,.0f}"),
        labels={"semana_label": "Semana", "total_expenses": "Gastos (USD)"},
        color_discrete_sequence=["#e15759"],
        height=340,
    )
    fig_exp_bar.update_traces(textposition="outside")
    fig_exp_bar.update_layout(xaxis_tickangle=-30, margin=dict(t=20, b=10))
    st.plotly_chart(fig_exp_bar, use_container_width=True)

# ── Detailed cost table ────────────────────────────────────────────────────────
st.divider()
st.subheader("Tabla de desglose de costos — período completo")

all_costs = {**costos_usd}
all_costs_mxp = costos_mxp

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
    df_breakdown["Monto"] = df_breakdown["Monto"].apply(lambda x: f"${x:,.2f}")
    st.dataframe(df_breakdown, use_container_width=True, hide_index=True)
else:
    st.info("Sin datos de desglose disponibles.")

st.caption(
    f"Período: {fecha_inicio.strftime('%d/%m/%Y')} — {fecha_fin.strftime('%d/%m/%Y')} · "
    "Fuente: vwBI_trnViajes · Montos USD = dólares americanos, MXP = pesos mexicanos"
)
