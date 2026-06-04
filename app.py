"""
Transport Analytics — Main entry point.
Mexico-USA cross-border transport analytics platform.
"""

import streamlit as st

st.set_page_config(
    page_title="Transport Analytics",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar brand header ──────────────────────────────────────────────────────
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

# ── Home page content ─────────────────────────────────────────────────────────
st.title("🚛 Transport Analytics")
st.markdown("### Plataforma de análisis operativo — Transporte Internacional México-USA")

st.info(
    "Utiliza el menú de navegación en el panel lateral (o el menú de páginas) "
    "para acceder a cada módulo.",
    icon="ℹ️",
)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
        #### 📊 Dashboard
        Resumen ejecutivo de KPIs:
        ingresos, gastos, márgenes y
        actividad semanal.
        """
    )

with col2:
    st.markdown(
        """
        #### 🗺️ Viajes
        Análisis detallado de viajes:
        filtros avanzados, tiempos en
        tránsito y rentabilidad por viaje.
        """
    )

with col3:
    st.markdown(
        """
        #### 🚌 Flota
        Utilización de unidades:
        millas recorridas, ingresos y
        viajes por unidad.
        """
    )

col4, col5, col6 = st.columns(3)

with col4:
    st.markdown(
        """
        #### 👤 Operadores
        Desempeño por conductor:
        viajes, ingresos, millas y
        revenue per mile.
        """
    )

with col5:
    st.markdown(
        """
        #### 💰 Costos
        Desglose de costos operativos:
        diesel, casetas, honorarios,
        viáticos y más.
        """
    )

with col6:
    st.markdown(
        """
        #### 📡 GPS / Samsara
        Integración de datos GPS en
        tiempo real. *Próximamente.*
        """
    )

st.divider()
st.caption("Powered by Streamlit · Datos: eGestionMLV SQL Server")
