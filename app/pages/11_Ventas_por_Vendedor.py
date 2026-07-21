"""Página 11: Desempeño por Vendedor."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st
import plotly.express as px

from utils.data_loader import get_data
from utils.filters import render_sidebar_filters
from utils.formatters import formato_pesos, formato_pct, formato_numero
from utils.kpi_cards import kpi_row
from utils.charts import PALETA_SERIES, COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO

st.set_page_config(page_title="Vendedores · GFD", page_icon="🧑‍💼", layout="wide")
st.markdown(f"<h2 style='color:{COLOR_PRIMARIO}'>🧑‍💼 Desempeño por Vendedor</h2>", unsafe_allow_html=True)

st.info(
    "ℹ️ **Nota:** los datos de vendedor son agregados a nivel mes × vendedor × categoría (Aseo/Importados) × "
    "tipo documento (Electrónica/Remisiones). El histórico transaccional no incluye el nombre del vendedor "
    "en la línea de factura, por lo que no se puede hacer cruce cliente-vendedor a nivel detalle."
)

filters = render_sidebar_filters()

vxv = get_data("ventas_x_vendedor")
if vxv.empty:
    st.warning("No hay datos de ventas por vendedor. Verifica el archivo `Análisis Numérico`.")
    st.stop()

ini, fin = filters["anio_mes_inicio"], filters["anio_mes_fin"]
vxv_f = vxv[(vxv["anio_mes"]>=ini) & (vxv["anio_mes"]<=fin)] if ini and fin else vxv

# ===== KPIs =====
venta_equipo = float(vxv_f["monto_cop"].sum())
por_vend = vxv_f.groupby("vendedor").agg(monto=("monto_cop","sum")).reset_index()
por_vend = por_vend.sort_values("monto", ascending=False)
if len(por_vend):
    top = por_vend.iloc[0]
    top_str = f"{top['vendedor']}"
    top_amt = formato_pesos(top["monto"], 1)
else:
    top_str = "-"; top_amt = "-"

META_2026 = 9_000_000_000
# ventas 2026 acumuladas (de la métrica venta_mensual)
vm = get_data("venta_mensual")
ventas_2026 = float(vm[vm["anio_mes"].str.startswith("2026")]["venta_neta"].sum()) if not vm.empty else 0
cumpl = ventas_2026 / META_2026 if META_2026 else 0

# Proyección lineal a dic 2026 basada en meses transcurridos
meses_hasta_hoy = len(vm[vm["anio_mes"].str.startswith("2026")]) if not vm.empty else 0
if meses_hasta_hoy > 0:
    proy = ventas_2026 / meses_hasta_hoy * 12
else:
    proy = 0

kpi_row([
    {"label": "Venta total equipo (periodo)", "value": formato_pesos(venta_equipo, 1)},
    {"label": "Vendedor #1", "value": top_str, "delta": top_amt, "delta_color": "off"},
    {"label": "Cumplimiento Meta 2026", "value": formato_pct(cumpl),
     "delta": f"{formato_pesos(ventas_2026,1)} / {formato_pesos(META_2026,1)}", "delta_color": "off"},
    {"label": "Proyección lineal Dic 2026",  "value": formato_pesos(proy, 1),
     "delta": ("Sobre meta" if proy >= META_2026 else "Bajo meta"),
     "delta_color": ("normal" if proy >= META_2026 else "inverse")},
])

st.progress(min(cumpl, 1.0), text=f"Cumplimiento anual: {formato_pct(cumpl)}")

st.markdown("---")

# ===== Ranking =====
st.subheader("Ranking de vendedores")
por_vend["pct"] = por_vend["monto"] / por_vend["monto"].sum() if por_vend["monto"].sum() else 0
fig = px.bar(por_vend, x="monto", y="vendedor", orientation="h",
             color="vendedor", color_discrete_sequence=PALETA_SERIES,
             text="monto")
fig.update_traces(texttemplate="$%{text:,.0f}", textposition="outside")
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=380, margin=dict(l=10, r=10, t=10, b=10),
                  yaxis={"categoryorder": "total ascending"},
                  showlegend=False,
                  xaxis_title="Venta total")
fig.update_xaxes(gridcolor="#E9ECEF", tickformat=",")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Evolución =====
st.subheader("Evolución mensual por vendedor")
por_mes_vend = vxv_f.groupby(["anio_mes","vendedor"]).agg(monto=("monto_cop","sum")).reset_index()
fig = px.line(por_mes_vend.sort_values("anio_mes"), x="anio_mes", y="monto",
              color="vendedor", markers=True, color_discrete_sequence=PALETA_SERIES)
fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  height=420, margin=dict(l=10, r=10, t=10, b=10),
                  yaxis_title="Venta (COP)",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
fig.update_yaxes(gridcolor="#E9ECEF", tickformat=",")
st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# ===== Tabla detalle =====
st.subheader("Detalle por vendedor")
por_mes_pivot = vxv_f.pivot_table(index="vendedor", columns="anio_mes", values="monto_cop",
                                    aggfunc="sum", fill_value=0)
if len(por_mes_pivot.columns):
    por_mes_pivot["Total"] = por_mes_pivot.sum(axis=1)
    por_mes_pivot["Promedio"] = por_mes_pivot.drop(columns=["Total"]).mean(axis=1)
    por_mes_pivot["Mejor mes"] = por_mes_pivot.drop(columns=["Total","Promedio"]).max(axis=1)
    por_mes_pivot["Peor mes"] = por_mes_pivot.drop(columns=["Total","Promedio","Mejor mes"]).min(axis=1)
    detalle = por_mes_pivot[["Total","Promedio","Mejor mes","Peor mes"]].reset_index()
    detalle["% Part."] = detalle["Total"] / detalle["Total"].sum() if detalle["Total"].sum() else 0
    detalle = detalle.sort_values("Total", ascending=False)
    show = pd.DataFrame({
        "Vendedor": detalle["vendedor"],
        "Venta Total": detalle["Total"].map(lambda v: formato_pesos(v, 1)),
        "Prom. mensual": detalle["Promedio"].map(lambda v: formato_pesos(v, 1)),
        "Mejor mes": detalle["Mejor mes"].map(lambda v: formato_pesos(v, 1)),
        "Peor mes": detalle["Peor mes"].map(lambda v: formato_pesos(v, 1)),
        "% Part.": detalle["% Part."].map(formato_pct),
    })
    st.dataframe(show, use_container_width=True, hide_index=True)

# ===== Cumplimiento vs meta prorrateada =====
st.subheader("Cumplimiento vs meta prorrateada (por vendedor · último mes)")
if "cumplimiento_meta_prorrata" in vxv_f.columns:
    ult_mes = vxv_f["anio_mes"].max()
    ult = vxv_f[vxv_f["anio_mes"] == ult_mes].groupby("vendedor").agg(
        cumpl=("cumplimiento_meta_prorrata", "sum")).reset_index()
    fig = px.bar(ult.sort_values("cumpl"), x="cumpl", y="vendedor", orientation="h",
                 color="cumpl",
                 color_continuous_scale=[[0, COLOR_NEGATIVO], [0.5, "#FFC107"], [1, COLOR_POSITIVO]],
                 text="cumpl")
    fig.update_traces(texttemplate="%{text:.1%}", textposition="outside")
    fig.add_vline(x=1.0, line_dash="dash", line_color=COLOR_PRIMARIO,
                  annotation_text="100% meta", annotation_position="top")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      height=360, margin=dict(l=10, r=10, t=10, b=10),
                      xaxis=dict(tickformat=".0%"), xaxis_title="Cumplimiento",
                      yaxis_title=None, coloraxis_showscale=False)
    fig.update_xaxes(gridcolor="#E9ECEF")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Mes evaluado: **{ult_mes}**. Meta prorrateada = $9.000M / 12 meses / 5 vendedores.")
