"""Página 1: Análisis de Ventas."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters, apply_filters, periodo_anterior
from utils.formatters import formato_pesos, formato_pct, formato_numero, emoji_tendencia
from utils.kpi_cards import kpi_row
from utils.charts import (
    line_chart, horizontal_bar, heatmap, PALETA_SERIES, COLOR_PRIMARIO,
    COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO,
)

st.set_page_config(page_title="Ventas · GFD", page_icon="📈", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>📈 Análisis de Ventas</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()
fv = apply_filters(get_data("fact_ventas"), filters)

# ===== KPIs =====
if fv.empty:
    st.warning("No hay ventas en el periodo seleccionado.")
    st.stop()

_vcol = "venta_neta_linea" if "venta_neta_linea" in fv.columns else "total_venta"
venta_neta    = float(fv[_vcol].sum())
n_facturas     = int(fv["factura"].nunique())
ticket_prom    = venta_neta / n_facturas if n_facturas else 0
n_clientes     = int(fv["cliente"].nunique())

kpi_row([
    {"label": "Venta Neta (periodo)", "value": formato_pesos(venta_neta, 1)},
    {"label": "Nº de facturas",    "value": formato_numero(n_facturas)},
    {"label": "Ticket promedio",   "value": formato_pesos(ticket_prom, 1)},
    {"label": "Clientes activos",  "value": formato_numero(n_clientes)},
])

st.markdown("---")

# ===== Gráfico principal: venta mensual + tendencia =====
st.subheader("Evolución mensual de ventas")
vm = apply_filters(get_data("venta_mensual"), filters)
vm = vm.sort_values("anio_mes")

if not vm.empty:
    fig = line_chart(vm, x="anio_mes", y="venta_neta", show_trend=True, height=380)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Venta por categoría =====
col_izq, col_der = st.columns([1, 1])
vxc = apply_filters(get_data("venta_x_categoria_mes"), filters)
vxc_prev = apply_filters(get_data("venta_x_categoria_mes"), periodo_anterior(filters))

if not vxc.empty:
    agg_cat = (vxc.groupby("categoria_producto")
                 .agg(venta=("venta_neta", "sum"))
                 .reset_index()
                 .sort_values("venta", ascending=False))
    total_venta = agg_cat["venta"].sum()
    agg_cat["pct"] = agg_cat["venta"] / total_venta
    if not vxc_prev.empty:
        prev = vxc_prev.groupby("categoria_producto").agg(vprev=("venta_neta","sum")).reset_index()
        agg_cat = agg_cat.merge(prev, on="categoria_producto", how="left")
        agg_cat["crecimiento"] = (agg_cat["venta"] - agg_cat["vprev"]) / agg_cat["vprev"].replace(0, pd.NA)
    else:
        agg_cat["crecimiento"] = pd.NA

    with col_izq:
        st.subheader("Ranking por venta")
        fig = horizontal_bar(agg_cat.head(15), x="venta", y="categoria_producto", height=460)
        st.plotly_chart(fig, use_container_width=True)

    with col_der:
        st.subheader("Detalle categorías")
        def _color_row(v):
            if pd.isna(v):
                return "background-color: #F8F9FA"
            if v > 0.05:
                return "background-color: #D4EDDA"
            if v < -0.05:
                return "background-color: #F8D7DA"
            return "background-color: #FFF3CD"

        show = pd.DataFrame({
            "Categoría": agg_cat["categoria_producto"],
            "Venta": agg_cat["venta"].map(lambda v: formato_pesos(v, 1)),
            "% Part.": agg_cat["pct"].map(lambda v: formato_pct(v, 1)),
            "Crecim.": agg_cat["crecimiento"].map(
                lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "-"),
            "": agg_cat["crecimiento"].map(lambda v: emoji_tendencia(v if pd.notna(v) else 0)),
            "_c": agg_cat["crecimiento"],
        })
        st.dataframe(
            show.drop(columns=["_c"]).style
                .apply(lambda row: [_color_row(agg_cat["crecimiento"].iloc[row.name])] * len(row), axis=1),
            use_container_width=True, hide_index=True, height=460,
        )

st.markdown("---")

# ===== Heatmap categoría x mes =====
st.subheader("Estacionalidad: categoría × mes")
if not vxc.empty:
    # Reducir a las top 12 categorías para que el heatmap sea legible
    top_cats = agg_cat.head(12)["categoria_producto"].tolist()
    vxc_h = vxc[vxc["categoria_producto"].isin(top_cats)]
    fig = heatmap(vxc_h, x="anio_mes", y="categoria_producto", z="venta_neta", height=440)
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Drill-down por categoría =====
st.subheader("Detalle por categoría (drill-down)")
if not vxc.empty:
    cat_sel = st.selectbox("Elige categoría", options=agg_cat["categoria_producto"].tolist())
    fv_cat = fv[fv["categoria_producto"] == cat_sel]
    prod_agg = (fv_cat.groupby(["cod_interno", "descripcion_producto"])
                .agg(venta=("venta_neta_linea", "sum"),
                     cantidad=("cantidad", "sum"),
                     n_facturas=("factura", "nunique"))
                .reset_index()
                .sort_values("venta", ascending=False)
                .head(30))
    show = pd.DataFrame({
        "Producto": prod_agg["descripcion_producto"],
        "Cantidad": prod_agg["cantidad"].map(formato_numero),
        "Nº fact.": prod_agg["n_facturas"].map(formato_numero),
        "Venta": prod_agg["venta"].map(lambda v: formato_pesos(v, 1)),
    })
    st.dataframe(show, use_container_width=True, hide_index=True)
