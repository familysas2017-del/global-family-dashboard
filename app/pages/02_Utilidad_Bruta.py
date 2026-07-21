"""Página 2: Utilidad Bruta y Rentabilidad."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters, apply_filters
from utils.formatters import formato_pesos, formato_pct
from utils.kpi_cards import kpi_row
from utils.charts import (
    line_chart, horizontal_bar, PALETA_SERIES, COLOR_PRIMARIO,
    COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO, COLOR_SECUNDARIO,
    _base_layout,
)

st.set_page_config(page_title="Utilidad Bruta · GFD", page_icon="💰", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>💰 Utilidad Bruta y Rentabilidad</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()

fv = apply_filters(get_data("fact_ventas"), filters)
if fv.empty:
    st.warning("No hay ventas en el periodo seleccionado.")
    st.stop()

# ===== KPIs =====
_vcol = "venta_neta_linea" if "venta_neta_linea" in fv.columns else "total_venta"
venta = float(fv[_vcol].sum())
costo = float(fv["costo_total_linea"].sum())
utilidad = venta - costo
margen = utilidad / venta if venta else 0

ubxc = apply_filters(get_data("utilidad_bruta_x_categoria"), filters)
if not ubxc.empty:
    mrg_cat = (ubxc.groupby("categoria_producto")
                 .agg(vt=("venta_total", "sum"), ub=("utilidad_bruta", "sum")).reset_index())
    mrg_cat["mp"] = mrg_cat["ub"] / mrg_cat["vt"]
    mrg_cat = mrg_cat[mrg_cat["vt"] > 0].sort_values("mp", ascending=False)
    cat_top = mrg_cat.iloc[0]
    cat_bot = mrg_cat.iloc[-1]
else:
    cat_top = cat_bot = None

kpi_row([
    {"label": "Utilidad Bruta",  "value": formato_pesos(utilidad, 1)},
    {"label": "Margen Bruto %",  "value": formato_pct(margen)},
    {"label": "Cat. más rentable", "value": (cat_top["categoria_producto"] if cat_top is not None else "-"),
     "delta": f"{cat_top['mp']*100:.1f}%" if cat_top is not None else None, "delta_color": "off"},
    {"label": "Cat. menos rentable", "value": (cat_bot["categoria_producto"] if cat_bot is not None else "-"),
     "delta": f"{cat_bot['mp']*100:.1f}%" if cat_bot is not None else None, "delta_color": "off"},
])

st.markdown("---")

# ===== Combo: barras venta+costo, línea margen =====
st.subheader("Evolución: Venta, Costo y Margen Bruto %")
ubm = get_data("utilidad_bruta_mensual").sort_values("anio_mes")
ini, fin = filters["anio_mes_inicio"], filters["anio_mes_fin"]
if ini and fin:
    ubm = ubm[(ubm["anio_mes"] >= ini) & (ubm["anio_mes"] <= fin)]

if not ubm.empty:
    fig = go.Figure()
    fig.add_bar(x=ubm["anio_mes"], y=ubm["venta_total"], name="Venta",
                marker_color=COLOR_SECUNDARIO)
    fig.add_bar(x=ubm["anio_mes"], y=ubm["costo_total"], name="Costo",
                marker_color="#95CE72")
    fig.add_scatter(x=ubm["anio_mes"], y=ubm["margen_bruto_pct"], name="Margen %",
                    mode="lines+markers", yaxis="y2",
                    line=dict(color=COLOR_NEGATIVO, width=3))
    fig.update_layout(
        barmode="group",
        yaxis=dict(title="Monto"),
        yaxis2=dict(title="Margen %", overlaying="y", side="right",
                    tickformat=".0%", showgrid=False, range=[0, max(0.35, ubm["margen_bruto_pct"].max()*1.2 if len(ubm) else 0.3)]),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=440, margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(gridcolor="#E9ECEF")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Ranking margen por categoría =====
st.subheader("Ranking de categorías por Margen Bruto %")
if not mrg_cat.empty:
    mrg_cat_show = mrg_cat.copy()
    mrg_cat_show["margen_pct_num"] = mrg_cat_show["mp"] * 100
    fig = px.bar(
        mrg_cat_show, x="margen_pct_num", y="categoria_producto",
        orientation="h",
        color="margen_pct_num",
        color_continuous_scale=[[0, COLOR_NEGATIVO], [0.5, COLOR_NEUTRO], [1, COLOR_POSITIVO]],
        text="margen_pct_num",
    )
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=550, margin=dict(l=10, r=10, t=10, b=10),
        yaxis={"categoryorder": "total ascending"},
        xaxis_title="Margen bruto %", yaxis_title=None,
        coloraxis_showscale=False,
    )
    fig.add_vline(x=margen*100, line=dict(color=COLOR_PRIMARIO, dash="dash"),
                  annotation_text=f"Promedio {margen*100:.1f}%", annotation_position="top")
    fig.update_xaxes(gridcolor="#E9ECEF")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Evolución margen por categoría (top 5) =====
st.subheader("Evolución del margen por categoría (top 5 por venta)")
if not ubxc.empty:
    top_by_vt = (ubxc.groupby("categoria_producto").agg(vt=("venta_total","sum"))
                 .nlargest(5, "vt").index.tolist())
    ubxc_top = ubxc[ubxc["categoria_producto"].isin(top_by_vt)].copy()
    ubxc_top["margen_pct"] = ubxc_top["utilidad_bruta"] / ubxc_top["venta_total"].replace(0, pd.NA)
    ubxc_top = ubxc_top.sort_values("anio_mes")
    fig = px.line(ubxc_top, x="anio_mes", y="margen_pct", color="categoria_producto",
                  markers=True, color_discrete_sequence=PALETA_SERIES)
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=380, margin=dict(l=10, r=10, t=10, b=10),
        yaxis=dict(tickformat=".0%"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_yaxes(gridcolor="#E9ECEF")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Nota de calidad de datos =====
st.subheader("Calidad del dato de costo")
if "fuente_costo" in fv.columns:
    n_sist = int((fv["fuente_costo"] == "SISTEMA").sum())
    n_juego = int((fv["fuente_costo"] == "JUEGO_INV").sum())
    n_total = len(fv)
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Costo del sistema (dato original)",
                  f"{n_sist/n_total*100:.1f}%",
                  delta=f"{n_sist:,} de {n_total:,} líneas", delta_color="off")
    with c2:
        st.metric("Costo prorrateado (juego de inv.)",
                  f"{n_juego/n_total*100:.1f}%",
                  delta=f"{n_juego:,} de {n_total:,} líneas", delta_color="off")

    er = get_data("costo_ventas_er")
    if not er.empty:
        st.caption(
            f"Meses con COGS del ER (fuente oficial): **{len(er)}** "
            f"({er['anio_mes'].min()} → {er['anio_mes'].max()}). "
            "Los demás meses usan la razón COGS/Ventas promedio del ER (81.66%)."
        )
