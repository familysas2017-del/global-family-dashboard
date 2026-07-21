"""Página 4: Rentabilidad por Producto."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters, apply_filters
from utils.formatters import formato_pesos, formato_pct, formato_numero
from utils.kpi_cards import kpi_row
from utils.charts import PALETA_SERIES, COLOR_PRIMARIO, COLOR_NEGATIVO

st.set_page_config(page_title="Margen por Producto · GFD", page_icon="📦", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>📦 Rentabilidad por Producto</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()
fv = apply_filters(get_data("fact_ventas"), filters)
if fv.empty:
    st.warning("No hay ventas en el periodo seleccionado.")
    st.stop()

# Agregar por SKU en el periodo
_vcol = "venta_neta_linea" if "venta_neta_linea" in fv.columns else "total_venta"
g = fv.groupby(["cod_interno"]).agg(
    descripcion=("descripcion_producto", "first"),
    categoria=("categoria_producto", "first"),
    marca=("proveedor_marca", "first"),
    venta_total=(_vcol, "sum"),
    costo_total=("costo_total_linea", "sum"),
    cantidad=("cantidad", "sum"),
).reset_index()
g["margen_bruto"] = g["venta_total"] - g["costo_total"]
g["margen_bruto_pct"] = np.where(g["venta_total"] > 0,
                                  g["margen_bruto"] / g["venta_total"], np.nan)
g["precio_venta_prom"] = g["venta_total"] / g["cantidad"].replace(0, np.nan)
g["costo_unit_prom"]   = g["costo_total"] / g["cantidad"].replace(0, np.nan)

# ABC
g_sort = g.sort_values("venta_total", ascending=False).reset_index(drop=True)
total_v = g_sort["venta_total"].sum()
g_sort["acum_pct"] = g_sort["venta_total"].cumsum() / total_v
def abc(p):
    if p <= 0.80: return "A"
    if p <= 0.95: return "B"
    return "C"
g_sort["abc"] = g_sort["acum_pct"].map(abc)
g = g.merge(g_sort[["cod_interno","abc"]], on="cod_interno", how="left")

# ===== KPIs =====
n_skus = len(g)
margen_prom_pct = g["margen_bruto"].sum() / g["venta_total"].sum() if g["venta_total"].sum() else 0
top_prod = g.loc[g["margen_bruto"].idxmax()] if len(g) else None
n_neg = int((g["margen_bruto_pct"] < 0).sum())

kpi_row([
    {"label": "SKUs activos",       "value": formato_numero(n_skus)},
    {"label": "Margen promedio %",  "value": formato_pct(margen_prom_pct)},
    {"label": "Prod. más rentable",
     "value": (str(top_prod["descripcion"])[:35] + "…") if top_prod is not None and len(str(top_prod["descripcion"]))>35 else (top_prod["descripcion"] if top_prod is not None else "-"),
     "delta": formato_pesos(top_prod["margen_bruto"], 1) if top_prod is not None else None,
     "delta_color": "off"},
    {"label": "Con margen negativo", "value": formato_numero(n_neg),
     "delta": "⚠ revisar", "delta_color": "inverse"},
])

st.markdown("---")

# ===== Scatter =====
st.subheader("Volumen vs Margen · por SKU")
g_show = g.copy()
g_show["margen_pct_num"] = g_show["margen_bruto_pct"] * 100
g_show = g_show[g_show["margen_pct_num"].between(-100, 100)]
fig = px.scatter(
    g_show, x="cantidad", y="margen_pct_num",
    color="categoria",
    hover_name="descripcion",
    hover_data={"venta_total": ":,.0f", "costo_total": ":,.0f", "margen_bruto": ":,.0f"},
    color_discrete_sequence=PALETA_SERIES,
    log_x=True,
    labels={"cantidad": "Unidades vendidas (log)", "margen_pct_num": "Margen bruto %"},
)
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=480, margin=dict(l=10, r=10, t=10, b=10),
                  yaxis=dict(ticksuffix="%"),
                  legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02))
fig.update_yaxes(gridcolor="#E9ECEF")
fig.add_hline(y=0, line_dash="dash", line_color=COLOR_NEGATIVO)
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Top 30 =====
st.subheader("Top 30 productos por venta")
cats_disp = sorted(g["categoria"].dropna().unique().tolist())
cat_sel = st.multiselect("Filtrar por categoría", options=cats_disp, default=[])
tabla = g if not cat_sel else g[g["categoria"].isin(cat_sel)]
tabla = tabla.sort_values("venta_total", ascending=False).head(30)

show = pd.DataFrame({
    "Producto": tabla["descripcion"],
    "Categoría": tabla["categoria"],
    "Cantidad": tabla["cantidad"].map(formato_numero),
    "Precio Prom.": tabla["precio_venta_prom"].map(lambda v: formato_pesos(v, 1) if pd.notna(v) else "-"),
    "Costo Prom.": tabla["costo_unit_prom"].map(lambda v: formato_pesos(v, 1) if pd.notna(v) else "-"),
    "Margen %": tabla["margen_bruto_pct"].map(lambda v: formato_pct(v) if pd.notna(v) else "-"),
    "Venta Total": tabla["venta_total"].map(lambda v: formato_pesos(v, 1)),
    "ABC": tabla["abc"],
})
st.dataframe(show, use_container_width=True, hide_index=True, height=560)

st.markdown("---")

# ===== Box por categoría =====
st.subheader("Distribución de margen dentro de cada categoría")
cat_solo = st.selectbox("Ver categoría específica", options=["Todas"] + cats_disp)
if cat_solo == "Todas":
    box_df = g[g["margen_bruto_pct"].between(-1, 1)]
else:
    box_df = g[(g["categoria"] == cat_solo) & (g["margen_bruto_pct"].between(-1, 1))]
fig = px.box(box_df, x="categoria", y="margen_bruto_pct",
             color="categoria", color_discrete_sequence=PALETA_SERIES,
             points="outliers")
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=440, margin=dict(l=10, r=10, t=10, b=10),
                  showlegend=False, yaxis_tickformat=".0%",
                  xaxis_title=None, yaxis_title="Margen bruto %")
fig.update_yaxes(gridcolor="#E9ECEF")
fig.update_xaxes(tickangle=-30)
st.plotly_chart(fig, use_container_width=True)
