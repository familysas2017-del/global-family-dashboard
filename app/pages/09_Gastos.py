"""Página 9: Análisis de Gastos."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_pct
from utils.kpi_cards import kpi_row
from utils.charts import (
    heatmap, PALETA_SERIES,
    COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO, COLOR_SECUNDARIO,
)

st.set_page_config(page_title="Gastos · GFD", page_icon="💸", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>💸 Análisis de Gastos</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()

fg = get_data("fact_gastos")
if fg.empty:
    st.warning("Sin datos de gastos.")
    st.stop()

# Filtro por rango de meses (categoría no aplica a gastos)
ini, fin = filters["anio_mes_inicio"], filters["anio_mes_fin"]
fg_f = fg[(fg["anio_mes"] >= ini) & (fg["anio_mes"] <= fin)] if ini and fin else fg

# ===== KPIs =====
gastos_total = float(fg_f["valor_cop"].sum())
gastos_fijos = float(fg_f[fg_f["clasificacion_fx"]=="fijo"]["valor_cop"].sum())
gastos_var   = float(fg_f[fg_f["clasificacion_fx"]=="variable"]["valor_cop"].sum())

# Ventas en el mismo periodo
vm = get_data("venta_mensual")
if not vm.empty and ini and fin:
    ventas_periodo = float(vm[(vm["anio_mes"]>=ini)&(vm["anio_mes"]<=fin)]["venta_neta"].sum())
else:
    ventas_periodo = 0
pct_gastos_ventas = gastos_total / ventas_periodo if ventas_periodo else 0

kpi_row([
    {"label": "Gastos totales",       "value": formato_pesos(gastos_total, 1)},
    {"label": "Gastos / Ventas",      "value": formato_pct(pct_gastos_ventas)},
    {"label": "Gastos fijos",         "value": formato_pesos(gastos_fijos, 1),
     "delta": f"{gastos_fijos/gastos_total*100:.1f}%" if gastos_total else "-", "delta_color": "off"},
    {"label": "Gastos variables",     "value": formato_pesos(gastos_var, 1),
     "delta": f"{gastos_var/gastos_total*100:.1f}%" if gastos_total else "-", "delta_color": "off"},
])

st.markdown("---")

# ===== Evolución fijo + variable con % sobre ventas =====
st.subheader("Evolución mensual: fijos + variables")
gfv = get_data("gastos_fijo_variable")
if not gfv.empty:
    gfv_f = gfv[(gfv["anio_mes"]>=ini)&(gfv["anio_mes"]<=fin)] if ini and fin else gfv
    gfv_f = gfv_f.sort_values("anio_mes")
    gfv_f["pct_total"] = (gfv_f["fijo"] + gfv_f["variable"]) / gfv_f["ventas_totales"].replace(0, pd.NA)
    fig = go.Figure()
    fig.add_bar(x=gfv_f["anio_mes"], y=gfv_f["fijo"], name="Fijos",
                marker_color=COLOR_PRIMARIO)
    fig.add_bar(x=gfv_f["anio_mes"], y=gfv_f["variable"], name="Variables",
                marker_color=COLOR_NEUTRO)
    fig.add_scatter(x=gfv_f["anio_mes"], y=gfv_f["pct_total"], name="Gastos/Ventas %",
                    mode="lines+markers", yaxis="y2",
                    line=dict(color=COLOR_NEGATIVO, width=3))
    fig.update_layout(
        barmode="stack",
        yaxis=dict(title="Monto"),
        yaxis2=dict(title="Gastos/Ventas %", overlaying="y", side="right",
                    showgrid=False, tickformat=".0%"),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=420, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(gridcolor="#E9ECEF")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Ranking por tipo de gasto =====
st.subheader("Ranking por tipo de gasto")
tipo_agg = (fg_f.groupby(["tipo","clasificacion_fx"])
            .agg(total=("valor_cop","sum")).reset_index()
            .sort_values("total", ascending=False).head(20))
fig = px.bar(
    tipo_agg, x="total", y="tipo", orientation="h", color="clasificacion_fx",
    color_discrete_map={"fijo": COLOR_PRIMARIO, "variable": COLOR_NEUTRO},
    text="total",
)
fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=560, margin=dict(l=10, r=10, t=10, b=10),
                  yaxis={"categoryorder": "total ascending"},
                  xaxis_title="Monto (COP)", yaxis_title=None,
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
fig.update_xaxes(gridcolor="#E9ECEF", tickformat=",")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Op vs No Op =====
st.subheader("Operacional vs No Operacional")
c1, c2 = st.columns(2)
op_df = fg_f[fg_f["clasificacion_op"]=="operacional"]
noop_df = fg_f[fg_f["clasificacion_op"].isin(["no_operacional","costo_importacion"])]
with c1:
    st.markdown("**Operacional**")
    op_agg = op_df.groupby("tipo").agg(total=("valor_cop","sum")).reset_index().nlargest(10, "total")
    fig = px.pie(op_agg, values="total", names="tipo", hole=0.55,
                 color_discrete_sequence=PALETA_SERIES)
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
with c2:
    st.markdown("**No Operacional + Costo Importación**")
    noop_agg = noop_df.groupby("tipo").agg(total=("valor_cop","sum")).reset_index().nlargest(10, "total")
    fig = px.pie(noop_agg, values="total", names="tipo", hole=0.55,
                 color_discrete_sequence=PALETA_SERIES)
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=380, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Heatmap tipo × mes =====
st.subheader("Heatmap: tipo de gasto × mes")
if not fg_f.empty:
    top_tipos = tipo_agg["tipo"].head(15).tolist()
    hg = fg_f[fg_f["tipo"].isin(top_tipos)]
    fig = heatmap(hg, x="anio_mes", y="tipo", z="valor_cop", height=460)
    st.plotly_chart(fig, use_container_width=True)
