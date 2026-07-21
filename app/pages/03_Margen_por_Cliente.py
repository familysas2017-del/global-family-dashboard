"""Página 3: Rentabilidad por Cliente."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters, apply_filters
from utils.formatters import formato_pesos, formato_pct, formato_numero
from utils.kpi_cards import kpi_row
from utils.charts import donut_chart, PALETA_SERIES, COLOR_PRIMARIO, COLOR_NEGATIVO, COLOR_POSITIVO

st.set_page_config(page_title="Margen por Cliente · GFD", page_icon="👥", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>👥 Rentabilidad por Cliente</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()

# Los datos de margen_x_cliente son AGREGADOS a nivel cliente sin desglose mes/categoría.
# Para respetar el filtro re-computamos por cliente sobre fact_ventas filtrado.
fv = apply_filters(get_data("fact_ventas"), filters)
if fv.empty:
    st.warning("No hay ventas en el periodo seleccionado.")
    st.stop()

fv["fecha"] = pd.to_datetime(fv["fecha"], errors="coerce")
fecha_max = fv["fecha"].max()

# Agrupamos por cliente (nombre más común por ident)
nombre_por_id = fv.groupby("ident_cliente")["cliente"].agg(
    lambda s: s.value_counts().idxmax() if len(s) else None)

_vcol = "venta_neta_linea" if "venta_neta_linea" in fv.columns else "total_venta"
g = fv.groupby("ident_cliente").agg(
    venta_total=(_vcol, "sum"),
    costo_total=("costo_total_linea", "sum"),
    cantidad_facturas=("factura", "nunique"),
    ultima_compra=("fecha", "max"),
    primera_compra=("fecha", "min"),
    generico=("cliente_generico", "first"),
).reset_index()
g["cliente"] = g["ident_cliente"].map(nombre_por_id)
g["margen_bruto"] = g["venta_total"] - g["costo_total"]
g["margen_bruto_pct"] = np.where(g["venta_total"] > 0,
                                  g["margen_bruto"] / g["venta_total"], np.nan)
g["ticket_promedio"] = g["venta_total"] / g["cantidad_facturas"].replace(0, np.nan)
g["dias_sin_comprar"] = (fecha_max - g["ultima_compra"]).dt.days

# ABC sobre no-genéricos
real = g[~g["generico"].fillna(False)].sort_values("venta_total", ascending=False).reset_index(drop=True)
tot = real["venta_total"].sum()
real["acum_pct"] = real["venta_total"].cumsum() / tot
def abc(p):
    if p <= 0.80: return "A"
    if p <= 0.95: return "B"
    return "C"
real["clasificacion_abc"] = real["acum_pct"].map(abc)
g = g.merge(real[["ident_cliente","clasificacion_abc"]], on="ident_cliente", how="left")

# ===== KPIs =====
n_clientes = len(g[~g["generico"].fillna(False)])
margen_prom = float(g["margen_bruto"].mean())
top = g.loc[g["margen_bruto"].idxmax()] if len(g) else None
neg = g[g["margen_bruto_pct"] < 0]

kpi_row([
    {"label": "Clientes activos",     "value": formato_numero(n_clientes)},
    {"label": "Margen promedio",      "value": formato_pesos(margen_prom, 1)},
    {"label": "Cliente #1 margen",
     "value": (top["cliente"] if top is not None else "-"),
     "delta": formato_pesos(top["margen_bruto"], 1) if top is not None else None,
     "delta_color": "off"},
    {"label": "Clientes margen negativo",
     "value": formato_numero(len(neg)),
     "delta": f"⚠ {formato_pesos(neg['margen_bruto'].sum(), 1) if len(neg) else '$0'}",
     "delta_color": "inverse"},
])

st.markdown("---")

# ===== Scatter plot =====
st.subheader("Mapa Venta vs Margen (tamaño = nº facturas)")
scatter_df = real.copy()
scatter_df["margen_pct_num"] = scatter_df["margen_bruto_pct"] * 100
# limitar y-axis para que outliers no rompan la vista
scatter_df = scatter_df[scatter_df["margen_pct_num"].between(-50, 60)]

fig = px.scatter(
    scatter_df, x="venta_total", y="margen_pct_num", size="cantidad_facturas",
    color="clasificacion_abc",
    hover_name="cliente", size_max=45,
    color_discrete_map={"A": "#1B3A5C", "B": "#FFC107", "C": "#ADB5BD"},
    labels={"venta_total": "Venta total", "margen_pct_num": "Margen bruto %"},
)
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=460, margin=dict(l=10, r=10, t=10, b=10),
                  yaxis=dict(ticksuffix="%"))
fig.update_yaxes(gridcolor="#E9ECEF")
fig.update_xaxes(gridcolor="#E9ECEF", tickformat=",")
fig.add_hline(y=0, line_dash="dash", line_color=COLOR_NEGATIVO)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Top 20 clientes =====
st.subheader("Top 20 clientes por venta")
top20 = real.head(20).copy()
show = pd.DataFrame({
    "Cliente": top20["cliente"],
    "Venta Total": top20["venta_total"].map(lambda v: formato_pesos(v, 1)),
    "Costo Total": top20["costo_total"].map(lambda v: formato_pesos(v, 1)),
    "Margen $": top20["margen_bruto"].map(lambda v: formato_pesos(v, 1)),
    "Margen %": top20["margen_bruto_pct"].map(lambda v: formato_pct(v) if pd.notna(v) else "-"),
    "Nº fact.": top20["cantidad_facturas"].map(formato_numero),
    "Ticket": top20["ticket_promedio"].map(lambda v: formato_pesos(v, 1)),
    "Últ. compra": top20["ultima_compra"].dt.strftime("%Y-%m-%d"),
    "Días s/comprar": top20["dias_sin_comprar"].map(lambda v: f"{int(v)}" if pd.notna(v) else "-"),
    "ABC": top20["clasificacion_abc"],
})

def _colorea_margen_bajo(v):
    try:
        pct = float(str(v).replace("%", ""))
        return "background-color: #F8D7DA" if pct < 5 else ""
    except Exception:
        return ""

st.dataframe(
    show.style.map(_colorea_margen_bajo, subset=["Margen %"]),
    use_container_width=True, hide_index=True, height=560,
)

st.markdown("---")

# ===== Distribución =====
c1, c2 = st.columns(2)
with c1:
    st.subheader("Participación ABC en la venta")
    seg = real.groupby("clasificacion_abc").agg(
        venta=("venta_total", "sum"), n=("ident_cliente", "count")).reset_index()
    fig = px.pie(seg, values="venta", names="clasificacion_abc", hole=0.55,
                 color="clasificacion_abc",
                 color_discrete_map={"A":"#1B3A5C","B":"#FFC107","C":"#ADB5BD"})
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=360, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Distribución por rango de margen")
    bins = [-1e9, 0, 0.05, 0.10, 0.15, 0.20, 1e9]
    labels = ["Negativo", "0-5%", "5-10%", "10-15%", "15-20%", ">20%"]
    real["_bucket"] = pd.cut(real["margen_bruto_pct"], bins=bins, labels=labels, include_lowest=True)
    hist = real.groupby("_bucket", observed=False).agg(n=("ident_cliente","count")).reset_index()
    fig = px.bar(hist, x="_bucket", y="n",
                 color="_bucket",
                 color_discrete_sequence=["#DC3545","#FD7E14","#FFC107","#95CE72","#28A745","#1B3A5C"])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=360, margin=dict(l=10, r=10, t=10, b=10),
                      showlegend=False, xaxis_title="Rango de margen",
                      yaxis_title="Nº de clientes")
    fig.update_yaxes(gridcolor="#E9ECEF")
    st.plotly_chart(fig, use_container_width=True)
