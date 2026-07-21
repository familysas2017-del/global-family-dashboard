"""Página principal: Resumen Ejecutivo."""
from __future__ import annotations
import sys
from pathlib import Path

# Permite importar utils sin instalar el paquete
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from utils.data_loader import get_data, get_last_data_date
from utils.filters import render_sidebar_filters, apply_filters, periodo_anterior
from utils.formatters import (
    formato_pesos, formato_pesos_completo, formato_pct, formato_numero,
    formato_dias, emoji_tendencia,
)
from utils.kpi_cards import kpi_row
from utils.charts import line_chart, bar_chart, PALETA_SERIES, COLOR_PRIMARIO, COLOR_POSITIVO, COLOR_NEGATIVO, COLOR_NEUTRO

# --- Page config ---
st.set_page_config(
    page_title="GFD · Inteligencia Comercial",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Header ---
st.markdown(
    f"<h1 style='color:{COLOR_PRIMARIO}; margin-bottom:0'>Global Family Distribuciones</h1>"
    f"<p style='color:#6C757D; margin-top:0'>Inteligencia Comercial · Resumen Ejecutivo</p>",
    unsafe_allow_html=True,
)
last_date = get_last_data_date()
st.caption(f"📅 Datos actualizados al **{last_date}**")

# --- Sidebar filtros ---
filters = render_sidebar_filters()

st.markdown("---")

# ============================================================
# FILA 1: 4 KPIs principales
# ============================================================
fv = apply_filters(get_data("fact_ventas"), filters)
# Ventas Netas = post-devoluciones prorrateadas (base oficial del margen)
_vcol = "venta_neta_linea" if not fv.empty and "venta_neta_linea" in fv.columns else "total_venta"
ventas_netas = float(fv[_vcol].sum()) if not fv.empty else 0
utilidad_bruta = float(fv["margen_bruto_linea"].sum()) if not fv.empty else 0
margen_pct = utilidad_bruta / ventas_netas if ventas_netas > 0 else 0

wc = get_data("working_capital")
if not wc.empty:
    capital_trabajo = float(wc.iloc[0]["capital_de_trabajo"])
    razon_corriente = float(wc.iloc[0]["razon_corriente"])
else:
    capital_trabajo = razon_corriente = 0

# Deltas vs periodo anterior
prev = periodo_anterior(filters)
fv_prev = apply_filters(get_data("fact_ventas"), prev)
_vcol_prev = "venta_neta_linea" if not fv_prev.empty and "venta_neta_linea" in fv_prev.columns else "total_venta"
ventas_prev = float(fv_prev[_vcol_prev].sum()) if not fv_prev.empty else 0
delta_ventas = ((ventas_netas - ventas_prev) / ventas_prev) if ventas_prev > 0 else None

# Semáforo razón corriente
rc_semaforo = "🟢" if razon_corriente >= 1.5 else "🟡" if razon_corriente >= 1.0 else "🔴"

kpi_row([
    {"label": "Ventas Netas (periodo)",
     "value": formato_pesos(ventas_netas, 0),
     "delta": f"{delta_ventas*100:+.1f}% vs periodo anterior" if delta_ventas is not None else None,
     "delta_color": "normal"},
    {"label": "Utilidad Bruta",
     "value": formato_pesos(utilidad_bruta, 0),
     "delta": f"Margen {margen_pct*100:.1f}%",
     "delta_color": "off"},
    {"label": "Capital de Trabajo",
     "value": formato_pesos(capital_trabajo, 0),
     "delta": "Snapshot actual",
     "delta_color": "off"},
    {"label": f"{rc_semaforo} Razón Corriente",
     "value": f"{razon_corriente:.2f}",
     "delta": "Saludable (>1.5)" if razon_corriente >= 1.5 else ("Ajustada" if razon_corriente >= 1 else "Crítica"),
     "delta_color": "off"},
])

st.markdown("<br>", unsafe_allow_html=True)

# ============================================================
# FILA 2: 4 KPIs secundarios
# ============================================================
dso_df = get_data("dias_cartera_resumen")
dso = float(dso_df.iloc[0]["valor"]) if not dso_df.empty else 0

dpo_df = get_data("dias_cxp_resumen")
if not dpo_df.empty:
    row_global = dpo_df[dpo_df["tipo"] == "global"]
    dpo = float(row_global.iloc[0]["dpo"]) if not row_global.empty else 0
else:
    dpo = 0

aging = get_data("dias_cartera_aging")
if not aging.empty:
    total_cartera = float(aging["monto"].sum())
    vencida_gt90 = float(aging[aging["tramo_aging"] == ">90"]["monto"].sum())
    pct_vencida = vencida_gt90 / total_cartera if total_cartera > 0 else 0
else:
    total_cartera = vencida_gt90 = pct_vencida = 0
semaforo_vencida = "🟢" if pct_vencida < 0.05 else "🟡" if pct_vencida < 0.10 else "🔴"

META_2026 = 9_000_000_000
vm = get_data("venta_mensual")
if not vm.empty:
    ventas_2026 = float(vm[vm["anio_mes"].str.startswith("2026")]["venta_neta"].sum())
else:
    ventas_2026 = 0
cumplimiento_meta = ventas_2026 / META_2026 if META_2026 > 0 else 0

kpi_row([
    {"label": "DSO (días cartera)",
     "value": formato_dias(dso),
     "delta": "Cobra a los ~44 días",
     "delta_color": "off"},
    {"label": "DPO (días pago)",
     "value": formato_dias(dpo),
     "delta": "Paga a los ~56 días",
     "delta_color": "off"},
    {"label": f"{semaforo_vencida} Cartera vencida >90d",
     "value": formato_pesos(vencida_gt90, 0),
     "delta": f"{pct_vencida*100:.1f}% del total",
     "delta_color": "off"},
    {"label": "Cumplimiento Meta 2026",
     "value": formato_pct(cumplimiento_meta, 1),
     "delta": f"{formato_pesos(ventas_2026, 0)} / {formato_pesos(META_2026, 0)}",
     "delta_color": "off"},
])

# Barra de progreso meta
st.progress(min(cumplimiento_meta, 1.0), text=f"Meta anual 2026: {formato_pct(cumplimiento_meta)}")

st.markdown("---")

# ============================================================
# FILA 3: 2 gráficos lado a lado
# ============================================================
col1, col2 = st.columns([3, 2])
with col1:
    st.subheader("Ventas mensuales — últimos 12 meses")
    vm_all = get_data("venta_mensual").sort_values("anio_mes")
    ultimos_12 = vm_all.tail(12)
    fig = line_chart(ultimos_12, x="anio_mes", y="venta_neta",
                     show_trend=True, height=360)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Composición por categoría · últimos 6 meses")
    vxc = apply_filters(get_data("venta_x_categoria_mes"), filters)
    if not vxc.empty:
        meses_recientes = sorted(vxc["anio_mes"].unique())[-6:]
        vxc_6m = vxc[vxc["anio_mes"].isin(meses_recientes)]
        # top 6 categorías por venta agregada
        top_cats = (vxc_6m.groupby("categoria_producto")["venta_neta"].sum()
                    .nlargest(6).index.tolist())
        vxc_6m_top = vxc_6m[vxc_6m["categoria_producto"].isin(top_cats)]
        import plotly.express as px
        fig2 = px.bar(vxc_6m_top, x="anio_mes", y="venta_neta",
                      color="categoria_producto",
                      color_discrete_sequence=PALETA_SERIES)
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            height=360, margin=dict(l=10, r=10, t=10, b=10),
            barmode="stack", legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
            font=dict(size=11),
        )
        fig2.update_yaxes(gridcolor="#E9ECEF", tickformat=",.0f")
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Sin datos en el periodo seleccionado.")

st.markdown("---")

# ============================================================
# FILA 4: Tabla resumen — Top 5 categorías y Top 5 clientes
# ============================================================
c1, c2 = st.columns(2)

with c1:
    st.subheader("Top 5 categorías por venta")
    if not vxc.empty:
        agg_cat = (vxc.groupby("categoria_producto")
                     .agg(venta=("venta_neta", "sum"))
                     .reset_index()
                     .sort_values("venta", ascending=False)
                     .head(5))
        # Margen % desde utilidad_bruta_x_categoria
        ubxc = apply_filters(get_data("utilidad_bruta_x_categoria"), filters)
        if not ubxc.empty:
            mrg = ubxc.groupby("categoria_producto").agg(
                vt=("venta_total", "sum"), ub=("utilidad_bruta", "sum")).reset_index()
            mrg["margen_pct"] = mrg["ub"] / mrg["vt"]
            agg_cat = agg_cat.merge(mrg[["categoria_producto", "margen_pct"]],
                                    on="categoria_producto", how="left")
        # Crecimiento vs periodo anterior
        vxc_prev = apply_filters(get_data("venta_x_categoria_mes"), prev)
        if not vxc_prev.empty:
            prev_agg = (vxc_prev.groupby("categoria_producto")
                        .agg(venta_prev=("venta_neta", "sum")).reset_index())
            agg_cat = agg_cat.merge(prev_agg, on="categoria_producto", how="left")
            agg_cat["crecimiento"] = ((agg_cat["venta"] - agg_cat["venta_prev"])
                                     / agg_cat["venta_prev"].replace(0, pd.NA))
            agg_cat["tendencia"] = agg_cat["crecimiento"].apply(
                lambda x: emoji_tendencia(x if pd.notna(x) else 0))
        else:
            agg_cat["crecimiento"] = pd.NA
            agg_cat["tendencia"] = "►"

        show = pd.DataFrame({
            "Categoría": agg_cat["categoria_producto"],
            "Venta": agg_cat["venta"].map(lambda v: formato_pesos(v, 0)),
            "Margen %": agg_cat["margen_pct"].map(lambda v: formato_pct(v) if pd.notna(v) else "-") if "margen_pct" in agg_cat else "-",
            "Crecim.": agg_cat["crecimiento"].map(
                lambda v: f"{v*100:+.1f}%" if pd.notna(v) else "-"),
            "": agg_cat["tendencia"],
        })
        st.dataframe(show, use_container_width=True, hide_index=True)

with c2:
    st.subheader("Top 5 clientes por venta")
    mx = get_data("margen_x_cliente")
    if not mx.empty:
        mx_top = mx[~mx["generico"].fillna(False)].nlargest(5, "venta_total")
        show = pd.DataFrame({
            "Cliente": mx_top["cliente"].fillna("(sin nombre)"),
            "Venta": mx_top["venta_total"].map(lambda v: formato_pesos(v, 0)),
            "Margen %": mx_top["margen_bruto_pct"].map(lambda v: formato_pct(v) if pd.notna(v) else "-"),
            "Días s/comprar": mx_top["dias_sin_comprar"].map(lambda v: f"{int(v)}" if pd.notna(v) else "-"),
        })
        st.dataframe(show, use_container_width=True, hide_index=True)

# ============================================================
# Footer
# ============================================================
st.markdown("---")
st.caption(
    "**Nota:** Los costos vienen de dos fuentes: (1) el sistema de facturación cuando existe el dato, "
    "(2) juego de inventarios prorrateado usando el Estado de Resultados oficial cuando no. "
    "Usa el menú lateral para navegar entre las páginas."
)
