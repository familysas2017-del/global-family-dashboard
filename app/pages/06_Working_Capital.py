"""Página 6: Capital de Trabajo."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_pesos_completo
from utils.kpi_cards import kpi_row
from utils.charts import (
    waterfall_chart, donut_chart, PALETA_SERIES,
    COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO, COLOR_SECUNDARIO,
)

st.set_page_config(page_title="Working Capital · GFD", page_icon="⚖️", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>⚖️ Capital de Trabajo</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()

wc = get_data("working_capital")
if wc.empty:
    st.warning("Métrica de working capital no disponible.")
    st.stop()
row = wc.iloc[0]
cartera        = float(row["cartera_total"])
inventario     = float(row["inventario_total"])
caja           = float(row.get("caja_estimada", 0))
activo_corr    = float(row["activo_corriente"])
cxp_nal        = float(row["cxp_nacional_total"])
cxp_int        = float(row["cxp_internacional_total"])
jeison         = float(row["cuotas_jeison_12m"])
pasivo_corr    = float(row["pasivo_corriente"])
cap_trabajo    = float(row["capital_de_trabajo"])
razon_corr     = float(row["razon_corriente"])
fecha_calc     = row["fecha_calculo"]

# ===== KPIs =====
kpi_row([
    {"label": "Capital de Trabajo Neto", "value": formato_pesos(cap_trabajo, 1)},
    {"label": "Razón Corriente",         "value": f"{razon_corr:.2f}",
     "delta": ("Saludable" if razon_corr>=1.5 else "Ajustada" if razon_corr>=1 else "Crítica"), "delta_color": "off"},
    {"label": "Activo Corriente",  "value": formato_pesos(activo_corr, 1)},
    {"label": "Pasivo Corriente",  "value": formato_pesos(pasivo_corr, 1)},
])
st.caption(f"Cálculo a la fecha: **{fecha_calc}**")

st.markdown("---")

# ===== Waterfall =====
st.subheader("Estructura del Capital de Trabajo")
labels = ["Cartera", "Inventario", "Caja est.", "CxP Nacional", "CxP Internac.", "Jeison 12m", "Cap. Trabajo Neto"]
values = [cartera, inventario, caja, -cxp_nal, -cxp_int, -jeison, cap_trabajo]
tipos = ["relative","relative","relative","relative","relative","relative","total"]
fig = waterfall_chart(labels, values, tipos, height=460)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Desglose activo/pasivo =====
c1, c2 = st.columns(2)
with c1:
    st.subheader("Activo Corriente")
    df_a = pd.DataFrame({"componente":["Cartera","Inventario","Caja est."],
                         "monto":[cartera, inventario, caja]})
    st.plotly_chart(donut_chart(df_a, values="monto", names="componente", height=340), use_container_width=True)
with c2:
    st.subheader("Pasivo Corriente")
    df_p = pd.DataFrame({"componente":["CxP Nacional","CxP Internac.","Jeison 12m"],
                         "monto":[cxp_nal, cxp_int, jeison]})
    st.plotly_chart(donut_chart(df_p, values="monto", names="componente", height=340), use_container_width=True)

st.markdown("---")

# ===== Deuda Jeison detalle =====
st.subheader("Deuda con Jeison (compra del negocio)")
dj = get_data("fact_deuda_jeison")
if not dj.empty:
    cuotas = dj[dj["es_cuota"].astype(str).str.lower().isin(["true","1","verdadero"])].copy()
    if "estado" not in cuotas.columns:
        cuotas["estado"] = "?"
    n_pagadas = (cuotas["estado"] == "pagada").sum()
    n_pend = (cuotas["estado"] == "pendiente_futura").sum()
    n_venc = (cuotas["estado"] == "vencida_sin_pago").sum()
    # Saldo actual = valor del "saldo" de la última cuota con saldo válido
    saldo_actual = float(cuotas["saldo"].dropna().iloc[-1]) if len(cuotas["saldo"].dropna()) else 0

    kA, kB, kC, kD = st.columns(4)
    with kA: st.metric("Saldo actual", formato_pesos(saldo_actual, 1))
    with kB: st.metric("Cuotas pagadas", f"{int(n_pagadas)}")
    with kC: st.metric("Cuotas pendientes", f"{int(n_pend)}")
    with kD: st.metric("Cuotas vencidas", f"{int(n_venc)}",
                       delta="⚠" if n_venc else "OK",
                       delta_color=("inverse" if n_venc else "off"))

    # Timeline
    cuotas_show = cuotas[["cuota","fecha_cuota","valor_cuota","abono","saldo","estado"]].copy()
    cuotas_show = cuotas_show.sort_values("fecha_cuota")
    cuotas_show["cuota_lbl"] = cuotas_show["cuota"].astype("Int64").astype(str) + " — " + \
                               pd.to_datetime(cuotas_show["fecha_cuota"]).dt.strftime("%Y-%m-%d").fillna("s/f")
    color_map = {"pagada": COLOR_POSITIVO, "pendiente_futura": COLOR_SECUNDARIO,
                 "vencida_sin_pago": COLOR_NEGATIVO, "?": "#ADB5BD"}
    fig = px.bar(cuotas_show, x="fecha_cuota", y="valor_cuota",
                 color="estado", color_discrete_map=color_map,
                 hover_data=["cuota","abono","saldo"])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=360, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis_title="Fecha de cuota", yaxis_title="Valor cuota")
    fig.update_yaxes(gridcolor="#E9ECEF", tickformat=",")
    st.plotly_chart(fig, use_container_width=True)
    # Próxima cuota
    proximas = cuotas[cuotas["estado"] == "pendiente_futura"].sort_values("fecha_cuota")
    if len(proximas):
        p = proximas.iloc[0]
        st.info(
            f"💡 **Próxima cuota:** {formato_pesos_completo(p['valor_cuota'])} "
            f"con vencimiento {pd.to_datetime(p['fecha_cuota']).strftime('%Y-%m-%d')}."
        )
