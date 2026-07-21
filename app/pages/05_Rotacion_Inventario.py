"""Página 5: Rotación de Inventario."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_numero, formato_dias
from utils.kpi_cards import kpi_row
from utils.charts import PALETA_SERIES, COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO

st.set_page_config(page_title="Rotación · GFD", page_icon="🔄", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>🔄 Rotación de Inventario</h2>", unsafe_allow_html=True)

filters = render_sidebar_filters()  # se mantiene sidebar coherente; no afecta inventario snapshot

esc = get_data("escalera_rotacion_productos")
rot_cat = get_data("rotacion_x_categoria")
inv = get_data("dim_inventario")

if esc.empty or inv.empty:
    st.warning("No hay datos de inventario. Ejecuta el pipeline primero.")
    st.stop()

# Filtro por categoría (solo aplica a inventario)
cats_sel = filters.get("categorias") or []
if cats_sel and "categoria_producto" in esc.columns:
    esc = esc[esc["categoria_producto"].isin(cats_sel)]
if cats_sel and "categoria_producto" in inv.columns:
    inv = inv[inv["categoria_producto"].isin(cats_sel)]

# ===== KPIs =====
inv_total = float(inv["costo_total_inventario"].sum())
esc_muerto = esc[esc["clasificacion_rotacion"] == "MUERTO"]
esc_dormido = esc[esc["clasificacion_rotacion"] == "DORMIDO"]
esc_activo  = esc[esc["clasificacion_rotacion"] == "ACTIVO"]
inv_muerto = float(esc_muerto["costo_total_inventario"].sum())

# Rotación agregada
rot_promedio_dias = float(rot_cat["dias_inventario"].mean()) if not rot_cat.empty else 0
rot_veces = 365 / rot_promedio_dias if rot_promedio_dias > 0 else 0

kpi_row([
    {"label": "Valor inventario",         "value": formato_pesos(inv_total, 1)},
    {"label": "Rotación promedio (veces/año)", "value": f"{rot_veces:.2f}"},
    {"label": "Días inventario prom.",     "value": formato_dias(rot_promedio_dias)},
    {"label": "Inventario MUERTO",
     "value": formato_pesos(inv_muerto, 1),
     "delta": f"{(inv_muerto/inv_total*100):.1f}% del total" if inv_total else "-",
     "delta_color": "inverse"},
])

st.markdown("---")

# ===== Escalera semaforo =====
st.subheader("Escalera de rotación: SKUs y valor detenido")

col1, col2, col3 = st.columns(3)

def _bloque(col, titulo, color, n_sk, valor, pct, top_prods):
    with col:
        st.markdown(
            f"<div style='background:{color}; padding:16px; border-radius:12px; color:white; margin-bottom:10px'>"
            f"<div style='font-size:12px; opacity:0.8'>{titulo}</div>"
            f"<div style='font-size:30px; font-weight:700'>{n_sk:,} SKUs</div>"
            f"<div style='font-size:14px'>{formato_pesos(valor,1)}   ·   {pct*100:.1f}%</div>"
            f"</div>", unsafe_allow_html=True,
        )
        if len(top_prods):
            fig = px.bar(top_prods.head(10), x="costo_total_inventario", y="descripcion",
                         orientation="h",
                         color_discrete_sequence=[color])
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                              height=330, margin=dict(l=10, r=10, t=10, b=10),
                              xaxis_title=None, yaxis_title=None, showlegend=False,
                              yaxis={"categoryorder":"total ascending"},
                              font=dict(size=10))
            fig.update_xaxes(tickformat=",", gridcolor="#E9ECEF")
            st.plotly_chart(fig, use_container_width=True)

_bloque(col1, "ACTIVOS · vendieron en últimos 30d", COLOR_POSITIVO,
        len(esc_activo), esc_activo["costo_total_inventario"].sum(),
        esc_activo["costo_total_inventario"].sum() / inv_total if inv_total else 0,
        esc_activo.sort_values("costo_total_inventario", ascending=False))
_bloque(col2, "DORMIDOS · 31-90 días sin vender", COLOR_NEUTRO,
        len(esc_dormido), esc_dormido["costo_total_inventario"].sum(),
        esc_dormido["costo_total_inventario"].sum() / inv_total if inv_total else 0,
        esc_dormido.sort_values("costo_total_inventario", ascending=False))
_bloque(col3, "MUERTOS · >90 días sin vender", COLOR_NEGATIVO,
        len(esc_muerto), esc_muerto["costo_total_inventario"].sum(),
        esc_muerto["costo_total_inventario"].sum() / inv_total if inv_total else 0,
        esc_muerto.sort_values("costo_total_inventario", ascending=False))

st.markdown("---")

# ===== Rotación por categoría =====
st.subheader("Días de inventario por categoría")
if not rot_cat.empty:
    rot_cat_show = rot_cat.dropna(subset=["dias_inventario"]).copy()
    rot_cat_show = rot_cat_show.sort_values("dias_inventario", ascending=True)
    fig = px.bar(rot_cat_show, x="dias_inventario", y="categoria_producto",
                 orientation="h",
                 color="dias_inventario",
                 color_continuous_scale=[[0, COLOR_POSITIVO], [0.5, COLOR_NEUTRO], [1, COLOR_NEGATIVO]],
                 text="dias_inventario")
    fig.update_traces(texttemplate="%{text:.0f} d", textposition="outside")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=440, margin=dict(l=10, r=10, t=10, b=10),
                      yaxis={"categoryorder": "total ascending"},
                      coloraxis_showscale=False,
                      xaxis_title="Días de inventario", yaxis_title=None)
    fig.add_vline(x=90, line_dash="dash", line_color=COLOR_PRIMARIO,
                  annotation_text="90 días", annotation_position="top")
    fig.update_xaxes(gridcolor="#E9ECEF")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Detalle de muertos =====
st.subheader("Top 50 MUERTOS por costo detenido")
top_muertos = esc_muerto.sort_values("costo_total_inventario", ascending=False).head(50)
show = pd.DataFrame({
    "Producto": top_muertos["descripcion"],
    "Categoría": top_muertos["categoria_producto"],
    "Stock": top_muertos["stock_actual"].map(formato_numero),
    "Costo Inventario": top_muertos["costo_total_inventario"].map(lambda v: formato_pesos(v, 1)),
    "Última Venta": pd.to_datetime(top_muertos["ultima_venta"], errors="coerce").dt.strftime("%Y-%m-%d"),
    "Días s/venta": top_muertos["dias_sin_venta"].map(lambda v: f"{int(v)}" if pd.notna(v) else "-"),
    "Meses Inv.": top_muertos["meses_inventario"].map(
        lambda v: f"{v:.1f}" if pd.notna(v) and np.isfinite(v) else "∞"),
})
st.dataframe(show, use_container_width=True, hide_index=True, height=520)

# Comparativa contra utilidad bruta reciente
ub = get_data("utilidad_bruta_mensual")
if not ub.empty:
    ub_prom_mensual = ub[ub["utilidad_bruta"] > 0]["utilidad_bruta"].tail(6).mean()
    if ub_prom_mensual and ub_prom_mensual > 0:
        meses_ub = inv_muerto / ub_prom_mensual
        st.error(
            f"🚨 **Inventario muerto = {formato_pesos(inv_muerto, 1)}** — "
            f"equivale a **{meses_ub:.1f} meses** de utilidad bruta promedio."
        )
