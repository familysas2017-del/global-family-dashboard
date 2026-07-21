"""Página 10: Fletes vs Ventas."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_pct
from utils.kpi_cards import kpi_row
from utils.charts import PALETA_SERIES, COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO

st.set_page_config(page_title="Fletes vs Ventas · GFD", page_icon="🚚", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>🚚 Costo Logístico vs Ventas</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()

fl = get_data("fletes_vs_ventas")
if fl.empty:
    st.warning("Sin datos de fletes.")
    st.stop()

ini, fin = filters["anio_mes_inicio"], filters["anio_mes_fin"]
fl_f = fl[(fl["anio_mes"]>=ini)&(fl["anio_mes"]<=fin)] if ini and fin else fl
fl_f = fl_f.sort_values("anio_mes")

# ===== KPIs =====
flete_nal_tot   = float(fl_f["flete_nacional"].sum())
flete_imp_tot   = float(fl_f["flete_importacion"].sum())
flete_total_tot = float(fl_f["flete_total"].sum())
ventas_tot      = float(fl_f["ventas_total"].sum())
pct_total = flete_total_tot / ventas_tot if ventas_tot else 0
pct_nal   = flete_nal_tot / ventas_tot if ventas_tot else 0
pct_imp   = flete_imp_tot / ventas_tot if ventas_tot else 0

kpi_row([
    {"label": "Flete Total",                   "value": formato_pesos(flete_total_tot, 1)},
    {"label": "Flete / Ventas %",              "value": formato_pct(pct_total)},
    {"label": "Flete Nal / Ventas %",          "value": formato_pct(pct_nal)},
    {"label": "Flete Import / Ventas %",       "value": formato_pct(pct_imp)},
])

st.markdown("---")

# ===== Evolución =====
st.subheader("Evolución mensual del costo logístico")
fig = go.Figure()
fig.add_bar(x=fl_f["anio_mes"], y=fl_f["flete_nacional"], name="Flete nacional",
            marker_color=COLOR_PRIMARIO)
fig.add_bar(x=fl_f["anio_mes"], y=fl_f["flete_importacion"], name="Flete importación",
            marker_color=COLOR_NEUTRO)
fig.add_scatter(x=fl_f["anio_mes"], y=fl_f["pct_flete_total_sobre_ventas"], name="% s/ Ventas",
                mode="lines+markers", yaxis="y2",
                line=dict(color=COLOR_NEGATIVO, width=3))
fig.update_layout(
    barmode="stack",
    yaxis=dict(title="Monto"),
    yaxis2=dict(title="Flete / Ventas %", overlaying="y", side="right", tickformat=".1%",
                showgrid=False),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    height=440, margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
fig.update_yaxes(gridcolor="#E9ECEF")
st.plotly_chart(fig, use_container_width=True)

# Tendencia (últimos 3 meses vs 3 anteriores)
if len(fl_f) >= 6:
    recientes = fl_f.tail(3)["pct_flete_total_sobre_ventas"].mean()
    anteriores = fl_f.tail(6).head(3)["pct_flete_total_sobre_ventas"].mean()
    delta = recientes - anteriores
    if delta > 0.005:
        st.error(f"📈 Costo logístico **subiendo**: {anteriores*100:.2f}% → {recientes*100:.2f}%")
    elif delta < -0.005:
        st.success(f"📉 Costo logístico **bajando**: {anteriores*100:.2f}% → {recientes*100:.2f}%")
    else:
        st.info(f"➖ Costo logístico **estable** en ~{recientes*100:.2f}%")

st.markdown("---")

# ===== Comparativo =====
c1, c2 = st.columns([1, 2])
with c1:
    st.subheader("Distribución")
    df_dist = pd.DataFrame({
        "tipo": ["Nacional", "Importación"],
        "monto": [flete_nal_tot, flete_imp_tot],
    })
    fig = px.pie(df_dist, values="monto", names="tipo", hole=0.55,
                 color_discrete_sequence=[COLOR_PRIMARIO, COLOR_NEUTRO])
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=380, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Detalle mensual")
    show = pd.DataFrame({
        "Mes": fl_f["anio_mes"],
        "Ventas": fl_f["ventas_total"].map(lambda v: formato_pesos(v, 1)),
        "Flete Nal": fl_f["flete_nacional"].map(lambda v: formato_pesos(v, 1)),
        "Flete Import": fl_f["flete_importacion"].map(lambda v: formato_pesos(v, 1)),
        "Flete Total": fl_f["flete_total"].map(lambda v: formato_pesos(v, 1)),
        "% s/Ventas": fl_f["pct_flete_total_sobre_ventas"].map(lambda v: formato_pct(v)),
    })
    st.dataframe(show, use_container_width=True, hide_index=True, height=380)
