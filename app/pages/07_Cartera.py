"""Página 7: Gestión de Cartera."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_pct, formato_dias, formato_numero
from utils.kpi_cards import kpi_row
from utils.charts import (
    stacked_horizontal_aging, PALETA_SERIES,
    COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO,
)

st.set_page_config(page_title="Cartera · GFD", page_icon="💵", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>💵 Gestión de Cartera</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()  # el filtro no altera este snapshot; solo mantiene consistencia visual

cartera = get_data("fact_cartera")
aging   = get_data("dias_cartera_aging")
resumen = get_data("dias_cartera_resumen")

if cartera.empty:
    st.warning("Datos de cartera no disponibles.")
    st.stop()

# ===== KPIs =====
cartera_total = float(cartera["saldo_pendiente"].sum())
dso = float(resumen.iloc[0]["valor"]) if not resumen.empty else 0
corriente = float(aging[aging["tramo_aging"]=="corriente"]["monto"].sum()) if not aging.empty else 0
vencida_gt90 = float(aging[aging["tramo_aging"]==">90"]["monto"].sum()) if not aging.empty else 0
pct_corr = corriente / cartera_total if cartera_total else 0
pct_v90  = vencida_gt90 / cartera_total if cartera_total else 0

kpi_row([
    {"label": "Cartera Total",       "value": formato_pesos(cartera_total, 1)},
    {"label": "DSO",                  "value": formato_dias(dso)},
    {"label": "Cartera Corriente",    "value": formato_pct(pct_corr),
     "delta": formato_pesos(corriente, 1), "delta_color": "off"},
    {"label": "Vencida >90 días",
     "value": formato_pesos(vencida_gt90, 1),
     "delta": formato_pct(pct_v90),
     "delta_color": "inverse"},
])

st.markdown("---")

# ===== Aging apilado =====
st.subheader("Aging de cartera")
if not aging.empty:
    tramos_orden = ["corriente","1-30","31-60","61-90",">90"]
    aging_orden = aging.set_index("tramo_aging").reindex(tramos_orden).fillna(0).reset_index()
    montos = dict(zip(aging_orden["tramo_aging"], aging_orden["monto"].astype(float)))
    fig = stacked_horizontal_aging(list(montos.keys()), montos, height=200)
    st.plotly_chart(fig, use_container_width=True)
    # Tabla resumen
    aging_show = pd.DataFrame({
        "Tramo": aging_orden["tramo_aging"],
        "Monto": aging_orden["monto"].map(lambda v: formato_pesos(v, 1)),
        "Nº facturas": aging_orden["n_facturas"].map(formato_numero),
        "% del total": aging_orden["pct_total"].map(lambda v: f"{v*100:.1f}%"),
    })
    st.dataframe(aging_show, use_container_width=True, hide_index=True)

st.markdown("---")

# ===== Top 20 clientes con más cartera =====
st.subheader("Top 20 clientes con mayor cartera")
cartera_por_cliente = cartera.groupby("cliente").agg(
    saldo_total=("saldo_pendiente", "sum"),
    n_fact=("num_factura", "count"),
    dias_max=("dias_vencido", "max"),
).reset_index().sort_values("saldo_total", ascending=False).head(20)

# aging por cliente
def _tramo_por_dias(v):
    if v <= 0: return "corriente"
    if v <= 30: return "1-30"
    if v <= 60: return "31-60"
    if v <= 90: return "61-90"
    return ">90"

pivot = (cartera.assign(tramo=cartera["dias_vencido"].map(_tramo_por_dias))
         .pivot_table(index="cliente", columns="tramo", values="saldo_pendiente", aggfunc="sum")
         .fillna(0))
for tramo in ["corriente","1-30","31-60","61-90",">90"]:
    if tramo not in pivot.columns:
        pivot[tramo] = 0
pivot = pivot[["corriente","1-30","31-60","61-90",">90"]]
pivot["total"] = pivot.sum(axis=1)
pivot = pivot.sort_values("total", ascending=False).head(20)

show = pd.DataFrame({
    "Cliente": pivot.index,
    "Saldo Total": pivot["total"].map(lambda v: formato_pesos(v, 1)),
    "Corriente":   pivot["corriente"].map(lambda v: formato_pesos(v, 1)),
    "1-30":        pivot["1-30"].map(lambda v: formato_pesos(v, 1)),
    "31-60":       pivot["31-60"].map(lambda v: formato_pesos(v, 1)),
    "61-90":       pivot["61-90"].map(lambda v: formato_pesos(v, 1)),
    ">90":         pivot[">90"].map(lambda v: formato_pesos(v, 1)),
})
st.dataframe(show, use_container_width=True, hide_index=True, height=560)

st.markdown("---")

# ===== Alertas críticas: vencidas >90 =====
st.subheader("Facturas vencidas >90 días")
gt90 = get_data("dias_cartera_vencidas_gt90")
if not gt90.empty:
    total_gt90 = gt90["saldo_pendiente"].sum() if "saldo_pendiente" in gt90 else 0
    st.error(f"🚨 **{len(gt90)} facturas** vencidas >90 días · **{formato_pesos(total_gt90, 1)}**")
    show = gt90.copy()
    if "fecha_limite_pago" in show.columns:
        show["fecha_limite_pago"] = pd.to_datetime(show["fecha_limite_pago"], errors="coerce").dt.strftime("%Y-%m-%d")
    # ordenar por saldo desc
    if "saldo_pendiente" in show.columns:
        show = show.sort_values("saldo_pendiente", ascending=False)
    st.dataframe(show, use_container_width=True, hide_index=True, height=420)
else:
    st.success("✅ No hay facturas vencidas más de 90 días.")
